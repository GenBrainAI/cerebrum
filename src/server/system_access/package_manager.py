from typing import Dict, List, Optional, Any, Tuple
import asyncio
import logging
import os
import json
import re
import subprocess
import sys
from datetime import datetime

logger = logging.getLogger(__name__)

class PackageManager:
    """Manages Python package installation and dependencies."""
    
    def __init__(self, security_config: Optional[Dict[str, Any]] = None):
        """
        Initialize with security configuration.
        
        Args:
            security_config: Dictionary with security settings
                - allowed_sources: List of allowed package sources
                - blocked_packages: List of blocked package names
                - require_approval: Whether to require approval for all operations
                - vulnerability_check: Whether to check for vulnerabilities
        """
        self.security_config = security_config or {
            "allowed_sources": ["pypi"],
            "blocked_packages": [],
            "require_approval": True,
            "vulnerability_check": True
        }
        
        # Initialize package cache
        self.package_cache: Dict[str, Dict[str, Any]] = {}
        self.vulnerability_cache: Dict[str, Dict[str, Any]] = {}
        self.last_cache_update = None
    
    async def install_package(self, package_name: str, version: Optional[str] = None, 
                             upgrade: bool = False, requires_approval: bool = True) -> Dict[str, Any]:
        """
        Install a Python package with optional version specification.
        
        Args:
            package_name: Name of the package to install
            version: Optional version specification
            upgrade: Whether to upgrade the package if already installed
            requires_approval: Whether this operation requires approval
            
        Returns:
            Dictionary with installation result information
        """
        # Check security constraints
        security_check = await self.check_package_security(package_name, version)
        if not security_check["is_safe"]:
            return {
                "success": False,
                "message": f"Package {package_name} failed security check: {security_check['reason']}",
                "details": security_check
            }
        
        # Build the pip command
        cmd = [sys.executable, "-m", "pip", "install"]
        
        if upgrade:
            cmd.append("--upgrade")
        
        if version:
            package_spec = f"{package_name}=={version}"
        else:
            package_spec = package_name
        
        cmd.append(package_spec)
        
        # Check if we need approval
        if requires_approval and self.security_config.get("require_approval", True):
            return {
                "success": False,
                "message": "Installation requires approval",
                "command": " ".join(cmd),
                "package": package_spec,
                "requires_approval": True
            }
        
        # Execute the pip command
        try:
            logger.info(f"Installing package: {package_spec}")
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                # Update package cache
                await self._update_package_cache()
                
                return {
                    "success": True,
                    "message": f"Successfully installed {package_spec}",
                    "stdout": stdout.decode(),
                    "stderr": stderr.decode(),
                    "package": package_spec
                }
            else:
                return {
                    "success": False,
                    "message": f"Failed to install {package_spec}",
                    "stdout": stdout.decode(),
                    "stderr": stderr.decode(),
                    "package": package_spec,
                    "returncode": process.returncode
                }
        except Exception as e:
            logger.exception(f"Error installing package {package_spec}: {e}")
            return {
                "success": False,
                "message": f"Error installing {package_spec}: {str(e)}",
                "package": package_spec,
                "error": str(e)
            }
    
    async def uninstall_package(self, package_name: str, requires_approval: bool = True) -> Dict[str, Any]:
        """
        Uninstall a Python package.
        
        Args:
            package_name: Name of the package to uninstall
            requires_approval: Whether this operation requires approval
            
        Returns:
            Dictionary with uninstallation result information
        """
        # Build the pip command
        cmd = [sys.executable, "-m", "pip", "uninstall", "-y", package_name]
        
        # Check if we need approval
        if requires_approval and self.security_config.get("require_approval", True):
            return {
                "success": False,
                "message": "Uninstallation requires approval",
                "command": " ".join(cmd),
                "package": package_name,
                "requires_approval": True
            }
        
        # Execute the pip command
        try:
            logger.info(f"Uninstalling package: {package_name}")
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                # Update package cache
                await self._update_package_cache()
                
                return {
                    "success": True,
                    "message": f"Successfully uninstalled {package_name}",
                    "stdout": stdout.decode(),
                    "stderr": stderr.decode(),
                    "package": package_name
                }
            else:
                return {
                    "success": False,
                    "message": f"Failed to uninstall {package_name}",
                    "stdout": stdout.decode(),
                    "stderr": stderr.decode(),
                    "package": package_name,
                    "returncode": process.returncode
                }
        except Exception as e:
            logger.exception(f"Error uninstalling package {package_name}: {e}")
            return {
                "success": False,
                "message": f"Error uninstalling {package_name}: {str(e)}",
                "package": package_name,
                "error": str(e)
            }
    
    async def list_installed_packages(self) -> List[Dict[str, str]]:
        """
        List all installed packages with versions.
        
        Returns:
            List of dictionaries with package information
        """
        await self._update_package_cache()
        
        return [
            {
                "name": name,
                "version": info.get("version", "unknown"),
                "location": info.get("location", "unknown")
            }
            for name, info in self.package_cache.items()
        ]
    
    async def check_package_security(self, package_name: str, version: Optional[str] = None) -> Dict[str, Any]:
        """
        Check package security against known vulnerabilities.
        
        Args:
            package_name: Name of the package to check
            version: Optional version to check
            
        Returns:
            Dictionary with security check results
        """
        # Check if package is in blocked list
        if package_name in self.security_config.get("blocked_packages", []):
            return {
                "is_safe": False,
                "reason": "Package is in blocked list",
                "package": package_name,
                "version": version
            }
        
        # If vulnerability check is disabled, return safe
        if not self.security_config.get("vulnerability_check", True):
            return {
                "is_safe": True,
                "reason": "Vulnerability check disabled",
                "package": package_name,
                "version": version
            }
        
        # Check for vulnerabilities using safety
        try:
            # Use safety if available, otherwise just return safe
            cmd = [sys.executable, "-m", "pip", "show", "safety"]
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            _, _ = await process.communicate()
            
            if process.returncode != 0:
                logger.warning("Safety package not installed, skipping vulnerability check")
                return {
                    "is_safe": True,
                    "reason": "Safety package not installed, skipping vulnerability check",
                    "package": package_name,
                    "version": version
                }
            
            # Run safety check
            package_spec = f"{package_name}"
            if version:
                package_spec = f"{package_name}=={version}"
            
            cmd = [sys.executable, "-m", "safety", "check", "--json", package_spec]
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                # No vulnerabilities found
                return {
                    "is_safe": True,
                    "reason": "No vulnerabilities found",
                    "package": package_name,
                    "version": version
                }
            else:
                # Parse the JSON output
                try:
                    vulnerabilities = json.loads(stdout.decode())
                    return {
                        "is_safe": False,
                        "reason": "Vulnerabilities found",
                        "package": package_name,
                        "version": version,
                        "vulnerabilities": vulnerabilities
                    }
                except json.JSONDecodeError:
                    logger.warning(f"Failed to parse safety output: {stdout.decode()}")
                    return {
                        "is_safe": False,
                        "reason": "Failed to parse vulnerability check output",
                        "package": package_name,
                        "version": version,
                        "stdout": stdout.decode(),
                        "stderr": stderr.decode()
                    }
        except Exception as e:
            logger.exception(f"Error checking package security for {package_name}: {e}")
            return {
                "is_safe": False,
                "reason": f"Error checking security: {str(e)}",
                "package": package_name,
                "version": version,
                "error": str(e)
            }
    
    async def create_requirements_file(self, path: str = "requirements.txt") -> str:
        """
        Generate a requirements.txt file from installed packages.
        
        Args:
            path: Path to write the requirements file
            
        Returns:
            Path to the created requirements file
        """
        try:
            # Get installed packages
            packages = await self.list_installed_packages()
            
            # Write requirements file
            with open(path, "w") as f:
                f.write("# Generated by Cerebrum Package Manager\n")
                f.write(f"# Date: {datetime.now().isoformat()}\n\n")
                
                for package in sorted(packages, key=lambda p: p["name"].lower()):
                    f.write(f"{package['name']}=={package['version']}\n")
            
            return path
        except Exception as e:
            logger.exception(f"Error creating requirements file: {e}")
            return f"Error: {str(e)}"
    
    async def _update_package_cache(self) -> None:
        """Update the internal package cache."""
        try:
            # Run pip list in JSON format
            cmd = [sys.executable, "-m", "pip", "list", "--format=json"]
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                packages = json.loads(stdout.decode())
                
                # Update cache
                for package in packages:
                    name = package["name"]
                    version = package["version"]
                    
                    # Get additional info
                    info_cmd = [sys.executable, "-m", "pip", "show", name]
                    info_process = await asyncio.create_subprocess_exec(
                        *info_cmd,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE
                    )
                    info_stdout, _ = await info_process.communicate()
                    
                    # Parse the output
                    info = {}
                    if info_process.returncode == 0:
                        info_text = info_stdout.decode()
                        for line in info_text.split("\n"):
                            if ":" in line:
                                key, value = line.split(":", 1)
                                info[key.strip().lower()] = value.strip()
                    
                    # Update cache
                    self.package_cache[name] = {
                        "version": version,
                        "location": info.get("location", "unknown"),
                        "summary": info.get("summary", ""),
                        "requires": info.get("requires", "").split(", ") if info.get("requires") else []
                    }
                
                self.last_cache_update = datetime.now()
            else:
                logger.error(f"Failed to update package cache: {stderr.decode()}")
        except Exception as e:
            logger.exception(f"Error updating package cache: {e}")
    
    async def get_package_info(self, package_name: str) -> Dict[str, Any]:
        """
        Get detailed information about a package.
        
        Args:
            package_name: Name of the package
            
        Returns:
            Dictionary with package information
        """
        # Update cache if needed
        if package_name not in self.package_cache:
            await self._update_package_cache()
        
        # Return from cache if available
        if package_name in self.package_cache:
            return self.package_cache[package_name]
        
        # Try to get info from PyPI
        try:
            # Use pip to get info
            cmd = [sys.executable, "-m", "pip", "show", package_name]
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                # Parse the output
                info = {}
                info_text = stdout.decode()
                for line in info_text.split("\n"):
                    if ":" in line:
                        key, value = line.split(":", 1)
                        info[key.strip().lower()] = value.strip()
                
                return {
                    "name": package_name,
                    "version": info.get("version", "unknown"),
                    "location": info.get("location", "unknown"),
                    "summary": info.get("summary", ""),
                    "requires": info.get("requires", "").split(", ") if info.get("requires") else [],
                    "installed": True
                }
            else:
                # Package not installed, try to get info from PyPI
                return {
                    "name": package_name,
                    "installed": False,
                    "message": "Package not installed"
                }
        except Exception as e:
            logger.exception(f"Error getting package info for {package_name}: {e}")
            return {
                "name": package_name,
                "error": str(e),
                "installed": False
            } 