"""
System Access Layer implementation.
"""
import os
import re
import git
import asyncio
import logging
import tempfile
from typing import Dict, List, Optional, Any, Union
import pkg_resources
from dataclasses import dataclass, field
from enum import Enum, auto

logger = logging.getLogger(__name__)

class AccessLevel(Enum):
    """Access levels for system operations."""
    READ = auto()
    WRITE = auto()
    EXECUTE = auto()

class ResourceType(Enum):
    """Types of resources that can be accessed."""
    FILE = auto()
    DIRECTORY = auto()
    REPOSITORY = auto()
    COMMAND = auto()
    PACKAGE = auto()

@dataclass
class AccessPolicy:
    """Access policy for system resources."""
    resource_type: ResourceType
    path_pattern: str
    allowed_levels: List[AccessLevel]
    requires_approval: bool = False
    max_size: Optional[int] = None
    allowed_operations: Optional[List[str]] = field(default_factory=list)

class SystemAccessLayer:
    """System access layer with security controls."""

    def __init__(self,
                 security_config: Optional[Dict[str, Any]] = None,
                 access_policies: Optional[List[AccessPolicy]] = None):
        """Initialize the system access layer."""
        self.security_config = security_config or {
            "sandbox_enabled": True,
            "require_approval": False,
            "max_process_time": 300,  # 5 minutes
            "max_file_size": 10 * 1024 * 1024,  # 10MB
            "allowed_packages": ["*"],
            "protected_paths": [
                "^/etc/.*",
                "^/usr/.*",
                "^/var/.*",
                "^/root/.*",
                "^/private/.*"
            ],
            "temp_dir": tempfile.gettempdir()
        }

        self.access_policies = access_policies or [
            AccessPolicy(
                resource_type=ResourceType.FILE,
                path_pattern=f"^{self.security_config['temp_dir']}/.*",
                allowed_levels=[AccessLevel.READ, AccessLevel.WRITE],
                requires_approval=False
            ),
            AccessPolicy(
                resource_type=ResourceType.DIRECTORY,
                path_pattern=f"^{self.security_config['temp_dir']}/.*",
                allowed_levels=[AccessLevel.READ, AccessLevel.WRITE],
                requires_approval=False
            ),
            AccessPolicy(
                resource_type=ResourceType.COMMAND,
                path_pattern=r"^(echo|ls|cat|pwd|cd|mkdir|rm\s+(?!-rf\s+/)|cp|mv|git|python|pip|sleep\s+\d+)(?:\s+(?!(/etc|/usr|/var|/root|/private)/).*)?$",
                allowed_levels=[AccessLevel.EXECUTE],
                requires_approval=False
            )
        ]

        self.operation_history: List[Dict[str, Any]] = []

    async def _validate_path(self, path: str, level: AccessLevel) -> bool:
        """Validate path against access policies."""
        # Check protected paths
        for pattern in self.security_config["protected_paths"]:
            if re.match(pattern, path):
                return False

        # Check access policies
        for policy in self.access_policies:
            if policy.resource_type in [ResourceType.FILE, ResourceType.DIRECTORY]:
                if re.match(policy.path_pattern, path):
                    return level in policy.allowed_levels

        # Default to deny
        return False

    async def _validate_command(self, command: str) -> bool:
        """Validate command against access policies."""
        # Check for dangerous patterns
        dangerous_patterns = [
            r"rm\s+-rf\s+/",  # Remove root
            r"sudo",          # Sudo commands
            r">\s*[^|]",     # File redirection
            r"[|&]{2}",      # Command chaining
            r";\s*\w+",      # Multiple commands
        ]
        
        for pattern in dangerous_patterns:
            if re.search(pattern, command):
                return False

        # Check for protected paths in command arguments
        for path in self.security_config["protected_paths"]:
            if re.search(path[1:-2], command):  # Remove ^ and .* from pattern
                return False

        # Check access policies
        for policy in self.access_policies:
            if policy.resource_type == ResourceType.COMMAND:
                if re.match(policy.path_pattern, command):
                    return True
        return False

    async def execute_command(self, command: str,
                            working_dir: Optional[str] = None,
                            timeout: Optional[int] = None) -> Dict[str, Any]:
        """Execute a system command securely."""
        logger.info(f"Executing command: {command}")

        try:
            # Validate command
            if not await self._validate_command(command):
                raise ValueError(f"Command not allowed: {command}")

            # Set timeout
            timeout = timeout or self.security_config["max_process_time"]

            # Create subprocess
            proc = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=working_dir
            )

            # Wait for completion with timeout
            try:
                stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
            except asyncio.TimeoutError:
                proc.kill()
                raise

            result = {
                "success": proc.returncode == 0,
                "command": command,
                "exit_code": proc.returncode,
                "stdout": stdout.decode().strip(),
                "stderr": stderr.decode().strip()
            }

            # Record operation
            self.operation_history.append({
                "type": "command",
                "command": command,
                "result": result
            })

            return result

        except Exception as e:
            logger.error(f"Command execution failed: {str(e)}")
            raise

    async def install_package(self, package_name: str) -> Dict[str, Any]:
        """Install a Python package securely."""
        logger.info(f"Installing package: {package_name}")

        try:
            # Check if package is allowed
            if "*" not in self.security_config["allowed_packages"] and \
               package_name not in self.security_config["allowed_packages"]:
                raise ValueError(f"Package not allowed: {package_name}")

            # Install package using pip
            result = await self.execute_command(f"pip install {package_name}")

            # Verify installation
            try:
                pkg_resources.require(package_name)
                result["success"] = True
            except pkg_resources.DistributionNotFound:
                result["success"] = False

            # Record operation
            self.operation_history.append({
                "type": "package",
                "package": package_name,
                "result": result
            })

            return result

        except Exception as e:
            logger.error(f"Package installation failed: {str(e)}")
            raise

    async def clone_repository(self, repo_url: str,
                             target_path: str,
                             branch: Optional[str] = None) -> Dict[str, Any]:
        """Clone a git repository securely."""
        logger.info(f"Cloning repository: {repo_url}")

        try:
            # Validate target path
            if not await self._validate_path(target_path, AccessLevel.WRITE):
                raise ValueError(f"Invalid target path: {target_path}")

            # Create parent directory if it doesn't exist
            os.makedirs(os.path.dirname(target_path), exist_ok=True)

            # Clone repository
            repo = git.Repo.clone_from(repo_url, target_path, branch=branch)

            result = {
                "success": True,
                "repo_url": repo_url,
                "target_path": target_path,
                "branch": repo.active_branch.name,
                "commit": repo.head.commit.hexsha
            }

            # Record operation
            self.operation_history.append({
                "type": "repository",
                "repo_url": repo_url,
                "result": result
            })

            return result

        except Exception as e:
            logger.error(f"Repository cloning failed: {str(e)}")
            raise

    async def read_file(self, file_path: str) -> Dict[str, Any]:
        """Read from a file securely."""
        logger.info(f"Reading file: {file_path}")

        try:
            # Validate path
            if not await self._validate_path(file_path, AccessLevel.READ):
                raise ValueError(f"Access denied to file: {file_path}")

            # Check file size
            if os.path.getsize(file_path) > self.security_config["max_file_size"]:
                raise ValueError(f"File too large: {file_path}")

            # Read file
            with open(file_path, 'r') as f:
                content = f.read()

            result = {
                "success": True,
                "file_path": file_path,
                "content": content
            }

            # Record operation
            self.operation_history.append({
                "type": "file_read",
                "file_path": file_path,
                "result": result
            })

            return result

        except Exception as e:
            logger.error(f"File read failed: {str(e)}")
            raise

    async def write_file(self, file_path: str,
                        content: str,
                        create_dirs: bool = False) -> Dict[str, Any]:
        """Write to a file securely."""
        logger.info(f"Writing to file: {file_path}")

        try:
            # Validate path
            if not await self._validate_path(file_path, AccessLevel.WRITE):
                raise ValueError(f"Access denied to file: {file_path}")

            # Create parent directory if requested
            if create_dirs:
                os.makedirs(os.path.dirname(file_path), exist_ok=True)

            # Write file
            with open(file_path, 'w') as f:
                f.write(content)

            result = {
                "success": True,
                "file_path": file_path,
                "bytes_written": len(content)
            }

            # Record operation
            self.operation_history.append({
                "type": "file_write",
                "file_path": file_path,
                "result": result
            })

            return result

        except Exception as e:
            logger.error(f"File write failed: {str(e)}")
            raise

    def get_operation_history(self) -> List[Dict[str, Any]]:
        """Get the operation history."""
        return self.operation_history.copy()