"""Safety validator component for code validation and security checks."""

from typing import Dict, List, Optional, Any
import logging
import asyncio
import json
import os
import uuid
import subprocess
import tempfile
from datetime import datetime
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

class ValidationLevel(Enum):
    """Validation levels for code safety checks."""
    BASIC = "basic"
    STANDARD = "standard"
    STRICT = "strict"
    CUSTOM = "custom"

@dataclass
class ValidationRule:
    """Rule for code validation."""
    name: str
    pattern: str
    description: str
    severity: str
    category: str
    remediation: Optional[str] = None

class SafetyValidator:
    """Validates code for safety and quality."""
    
    def __init__(self, security_config: Optional[Dict[str, Any]] = None):
        """Initialize the safety validator.
        
        Args:
            security_config: Configuration for security validation
        """
        self.security_config = security_config or {
            "validation_level": ValidationLevel.STANDARD.value,
            "static_analysis": {
                "enabled": True,
                "tools": ["pylint", "mypy"]
            },
            "security_scan": {
                "enabled": True,
                "tools": ["bandit"]
            },
            "test_framework": {
                "enabled": True,
                "tools": ["pytest"]
            },
            "sandbox": {
                "enabled": True,
                "timeout": 30
            },
            "dependency_check": {
                "enabled": True,
                "tools": ["safety"]
            }
        }
        self.validation_rules = self._load_validation_rules()
        self.validation_history = {}
    
    def _load_validation_rules(self) -> List[ValidationRule]:
        """Load default validation rules.
        
        Returns:
            List of validation rules
        """
        return [
            ValidationRule(
                name="no_eval",
                pattern=r"eval\(.*\)",
                description="Use of eval() is prohibited",
                severity="high",
                category="security",
                remediation="Remove eval() calls and use safer alternatives"
            ),
            ValidationRule(
                name="no_exec",
                pattern=r"exec\(.*\)",
                description="Use of exec() is prohibited",
                severity="high",
                category="security",
                remediation="Remove exec() calls and use safer alternatives"
            ),
            ValidationRule(
                name="sql_injection",
                pattern=r"f.*SELECT.*FROM|f.*INSERT.*INTO|f.*UPDATE.*SET|f.*DELETE.*FROM",
                description="Potential SQL injection vulnerability",
                severity="high",
                category="security",
                remediation="Use parameterized queries or ORM"
            ),
            ValidationRule(
                name="shell_injection",
                pattern=r"os\.system\(.*\)|subprocess\.call\(.*shell=True.*\)",
                description="Potential shell injection vulnerability",
                severity="high",
                category="security",
                remediation="Use subprocess with shell=False and proper argument lists"
            )
        ]
    
    async def validate_code(self, code: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Validate code for safety and quality.
        
        Args:
            code: Code to validate
            context: Additional context for validation
            
        Returns:
            Dictionary containing validation results
        """
        validation_id = str(uuid.uuid4())
        logger.info(f"Starting code validation with ID: {validation_id}")
        
        # Create validation record
        record = {
            "id": validation_id,
            "timestamp": datetime.now().isoformat(),
            "status": "in_progress",
            "context": context or {}
        }
        
        self.validation_history[validation_id] = record
        
        try:
            # Create temporary file for code
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as temp_file:
                temp_file.write(code)
                temp_file_path = temp_file.name
            
            # Perform static analysis
            static_results = await self.static_analysis(temp_file_path)
            
            # Perform security scan
            security_results = await self.security_scan(temp_file_path)
            
            # Check dependencies
            dependency_results = await self.check_dependencies(code)
            
            # Validate against custom rules
            custom_results = await self._validate_custom_rules(code)
            
            # Aggregate results
            results = {
                "static_analysis": static_results,
                "security_scan": security_results,
                "dependency_check": dependency_results,
                "custom_rules": custom_results,
                "overall_status": "pass"
            }
            
            # Determine overall status
            if any(r.get("status") == "fail" for r in [
                static_results, security_results, dependency_results, custom_results
            ]):
                results["overall_status"] = "fail"
            
            # Update record with results
            record.update({
                "status": "completed",
                "results": results,
                "completion_time": datetime.now().isoformat()
            })
            
            # Cleanup
            os.unlink(temp_file_path)
            
            return record
            
        except Exception as e:
            logger.error(f"Code validation failed with error: {str(e)}")
            record.update({
                "status": "failed",
                "error": str(e),
                "completion_time": datetime.now().isoformat()
            })
            return record
    
    async def static_analysis(self, file_path: str) -> Dict[str, Any]:
        """Perform static analysis on code.
        
        Args:
            file_path: Path to file to analyze
            
        Returns:
            Dictionary containing analysis results
        """
        results = {
            "status": "pass",
            "tools": {},
            "issues": []
        }
        
        if not self.security_config["static_analysis"]["enabled"]:
            return results
        
        for tool in self.security_config["static_analysis"]["tools"]:
            tool_result = await getattr(self, f"_run_{tool}")(file_path)
            results["tools"][tool] = tool_result
            if tool_result["status"] == "fail":
                results["status"] = "fail"
                results["issues"].extend(tool_result["issues"])
        
        return results
    
    async def security_scan(self, file_path: str) -> Dict[str, Any]:
        """Perform security scan on code.
        
        Args:
            file_path: Path to file to scan
            
        Returns:
            Dictionary containing scan results
        """
        results = {
            "status": "pass",
            "tools": {},
            "vulnerabilities": []
        }
        
        if not self.security_config["security_scan"]["enabled"]:
            return results
        
        for tool in self.security_config["security_scan"]["tools"]:
            tool_result = await getattr(self, f"_run_{tool}")(file_path)
            results["tools"][tool] = tool_result
            if tool_result["status"] == "fail":
                results["status"] = "fail"
                results["vulnerabilities"].extend(tool_result["vulnerabilities"])
        
        return results
    
    async def check_dependencies(self, code: str) -> Dict[str, Any]:
        """Check dependencies for known vulnerabilities.
        
        Args:
            code: Code to check dependencies for
            
        Returns:
            Dictionary containing dependency check results
        """
        results = {
            "status": "pass",
            "dependencies": [],
            "vulnerabilities": []
        }
        
        if not self.security_config["dependency_check"]["enabled"]:
            return results
        
        # Extract import statements
        import_lines = [line for line in code.split("\n") if line.strip().startswith("import") or line.strip().startswith("from")]
        
        for line in import_lines:
            package = line.split()[1].split(".")[0]
            results["dependencies"].append(package)
        
        # Check dependencies with safety
        if "safety" in self.security_config["dependency_check"]["tools"]:
            safety_result = await self._run_safety(results["dependencies"])
            if safety_result["vulnerabilities"]:
                results["status"] = "fail"
                results["vulnerabilities"].extend(safety_result["vulnerabilities"])
        
        return results
    
    async def _validate_custom_rules(self, code: str) -> Dict[str, Any]:
        """Validate code against custom rules.
        
        Args:
            code: Code to validate
            
        Returns:
            Dictionary containing validation results
        """
        results = {
            "status": "pass",
            "violations": []
        }
        
        import re
        
        for rule in self.validation_rules:
            matches = re.finditer(rule.pattern, code)
            for match in matches:
                results["violations"].append({
                    "rule": rule.name,
                    "description": rule.description,
                    "severity": rule.severity,
                    "line": code.count("\n", 0, match.start()) + 1,
                    "snippet": match.group(),
                    "remediation": rule.remediation
                })
        
        if results["violations"]:
            results["status"] = "fail"
        
        return results
    
    async def _run_pylint(self, file_path: str) -> Dict[str, Any]:
        """Run pylint on file.
        
        Args:
            file_path: Path to file to analyze
            
        Returns:
            Dictionary containing pylint results
        """
        try:
            result = subprocess.run(
                ["pylint", "--output-format=json", file_path],
                capture_output=True,
                text=True
            )
            
            issues = json.loads(result.stdout) if result.stdout else []
            
            return {
                "status": "fail" if issues else "pass",
                "issues": issues
            }
            
        except Exception as e:
            logger.error(f"Pylint analysis failed: {str(e)}")
            return {
                "status": "error",
                "error": str(e),
                "issues": []
            }
    
    async def _run_mypy(self, file_path: str) -> Dict[str, Any]:
        """Run mypy on file.
        
        Args:
            file_path: Path to file to analyze
            
        Returns:
            Dictionary containing mypy results
        """
        try:
            result = subprocess.run(
                ["mypy", "--show-error-codes", "--no-error-summary", file_path],
                capture_output=True,
                text=True
            )
            
            issues = []
            for line in result.stdout.split("\n"):
                if line.strip():
                    issues.append({
                        "message": line,
                        "type": "type_error"
                    })
            
            return {
                "status": "fail" if issues else "pass",
                "issues": issues
            }
            
        except Exception as e:
            logger.error(f"Mypy analysis failed: {str(e)}")
            return {
                "status": "error",
                "error": str(e),
                "issues": []
            }
    
    async def _run_bandit(self, file_path: str) -> Dict[str, Any]:
        """Run bandit security scan on file.
        
        Args:
            file_path: Path to file to scan
            
        Returns:
            Dictionary containing bandit results
        """
        try:
            result = subprocess.run(
                ["bandit", "-f", "json", "-q", file_path],
                capture_output=True,
                text=True
            )
            
            data = json.loads(result.stdout) if result.stdout else {"results": []}
            
            return {
                "status": "fail" if data["results"] else "pass",
                "vulnerabilities": data["results"]
            }
            
        except Exception as e:
            logger.error(f"Bandit scan failed: {str(e)}")
            return {
                "status": "error",
                "error": str(e),
                "vulnerabilities": []
            }
    
    async def _run_safety(self, dependencies: List[str]) -> Dict[str, Any]:
        """Run safety check on dependencies.
        
        Args:
            dependencies: List of dependencies to check
            
        Returns:
            Dictionary containing safety check results
        """
        try:
            # Create requirements file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as temp_file:
                for dep in dependencies:
                    temp_file.write(f"{dep}\n")
                temp_file_path = temp_file.name
            
            result = subprocess.run(
                ["safety", "check", "-r", temp_file_path, "--json"],
                capture_output=True,
                text=True
            )
            
            os.unlink(temp_file_path)
            
            vulnerabilities = json.loads(result.stdout) if result.stdout else []
            
            return {
                "status": "fail" if vulnerabilities else "pass",
                "vulnerabilities": vulnerabilities
            }
            
        except Exception as e:
            logger.error(f"Safety check failed: {str(e)}")
            return {
                "status": "error",
                "error": str(e),
                "vulnerabilities": []
            } 