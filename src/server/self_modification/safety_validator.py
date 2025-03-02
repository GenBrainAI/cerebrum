from typing import Dict, List, Optional, Any
import logging
import asyncio
import json
import os
import uuid
import subprocess
import tempfile
from datetime import datetime

logger = logging.getLogger(__name__)

class SafetyValidator:
    """Validates generated code for safety and quality."""
    
    def __init__(self, security_config: Optional[Dict[str, Any]] = None):
        """Initialize with security configuration.
        
        Args:
            security_config: Configuration for security validation.
                            If None, default configuration will be used.
        """
        self.security_config = security_config or {
            "validation_level": "high",
            "static_analysis_tools": ["pylint", "mypy", "bandit"],
            "security_scan_tools": ["bandit", "safety"],
            "test_frameworks": ["pytest"],
            "max_validation_time": 60  # seconds
        }
        self.validation_history = {}
        
    async def validate_code(self, code: str, file_path: str,
                           validation_level: str = "high") -> Dict[str, Any]:
        """Validate code against safety rules and quality standards.
        
        Args:
            code: The code to validate.
            file_path: The path where the code would be saved.
            validation_level: Level of validation (low, medium, high).
            
        Returns:
            Dictionary containing validation results.
        """
        validation_id = str(uuid.uuid4())
        logger.info(f"Starting code validation with ID: {validation_id}")
        
        # Create validation record
        validation_record = {
            "id": validation_id,
            "file_path": file_path,
            "validation_level": validation_level,
            "timestamp": datetime.now().isoformat(),
            "status": "in_progress",
            "results": {}
        }
        
        self.validation_history[validation_id] = validation_record
        
        try:
            # Run static analysis
            static_analysis_result = await self.static_analysis(code, file_path)
            validation_record["results"]["static_analysis"] = static_analysis_result
            
            # Run security scan
            security_scan_result = await self.security_scan(code)
            validation_record["results"]["security_scan"] = security_scan_result
            
            # Determine overall validation result
            validation_passed = (
                static_analysis_result.get("passed", False) and
                security_scan_result.get("passed", False)
            )
            
            validation_record["status"] = "completed"
            validation_record["passed"] = validation_passed
            validation_record["completion_time"] = datetime.now().isoformat()
            
            return validation_record
        except Exception as e:
            logger.error(f"Validation failed with error: {str(e)}")
            validation_record["status"] = "failed"
            validation_record["error"] = str(e)
            validation_record["completion_time"] = datetime.now().isoformat()
            return validation_record
    
    async def static_analysis(self, code: str, file_path: str) -> Dict[str, Any]:
        """Perform static analysis on code to detect issues.
        
        Args:
            code: The code to analyze.
            file_path: The path where the code would be saved.
            
        Returns:
            Dictionary containing static analysis results.
        """
        logger.info(f"Performing static analysis for file: {file_path}")
        
        result = {
            "tool_results": {},
            "issues": [],
            "passed": True,
            "timestamp": datetime.now().isoformat()
        }
        
        # Create a temporary file with the code
        with tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=False) as temp_file:
            temp_file.write(code)
            temp_file_path = temp_file.name
        
        try:
            # Run pylint
            if "pylint" in self.security_config["static_analysis_tools"]:
                pylint_result = await self._run_pylint(temp_file_path)
                result["tool_results"]["pylint"] = pylint_result
                
                if pylint_result["score"] < 7.0:  # Threshold for passing
                    result["passed"] = False
                    result["issues"].extend(pylint_result["issues"])
            
            # Run mypy
            if "mypy" in self.security_config["static_analysis_tools"]:
                mypy_result = await self._run_mypy(temp_file_path)
                result["tool_results"]["mypy"] = mypy_result
                
                if not mypy_result["passed"]:
                    result["passed"] = False
                    result["issues"].extend(mypy_result["issues"])
            
            return result
        finally:
            # Clean up temporary file
            os.unlink(temp_file_path)
    
    async def security_scan(self, code: str) -> Dict[str, Any]:
        """Scan code for security vulnerabilities.
        
        Args:
            code: The code to scan.
            
        Returns:
            Dictionary containing security scan results.
        """
        logger.info("Performing security scan")
        
        result = {
            "tool_results": {},
            "vulnerabilities": [],
            "passed": True,
            "timestamp": datetime.now().isoformat()
        }
        
        # Create a temporary file with the code
        with tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=False) as temp_file:
            temp_file.write(code)
            temp_file_path = temp_file.name
        
        try:
            # Run bandit
            if "bandit" in self.security_config["security_scan_tools"]:
                bandit_result = await self._run_bandit(temp_file_path)
                result["tool_results"]["bandit"] = bandit_result
                
                if not bandit_result["passed"]:
                    result["passed"] = False
                    result["vulnerabilities"].extend(bandit_result["vulnerabilities"])
            
            return result
        finally:
            # Clean up temporary file
            os.unlink(temp_file_path)
    
    async def run_tests(self, code: str, test_code: Optional[str] = None) -> Dict[str, Any]:
        """Run tests to validate code behavior.
        
        Args:
            code: The code to test.
            test_code: Optional test code to run against the code.
            
        Returns:
            Dictionary containing test results.
        """
        logger.info("Running tests")
        
        result = {
            "tests_run": 0,
            "tests_passed": 0,
            "tests_failed": 0,
            "test_output": "",
            "passed": False,
            "timestamp": datetime.now().isoformat()
        }
        
        if not test_code:
            result["test_output"] = "No test code provided"
            return result
        
        # Create temporary files for code and tests
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create module file
            module_path = os.path.join(temp_dir, "module_to_test.py")
            with open(module_path, "w") as module_file:
                module_file.write(code)
            
            # Create test file
            test_path = os.path.join(temp_dir, "test_module.py")
            with open(test_path, "w") as test_file:
                test_file.write(test_code)
            
            # Run pytest
            try:
                pytest_result = await self._run_pytest(temp_dir)
                result.update(pytest_result)
                result["passed"] = pytest_result["tests_failed"] == 0 and pytest_result["tests_run"] > 0
            except Exception as e:
                logger.error(f"Test execution failed: {str(e)}")
                result["test_output"] = f"Error running tests: {str(e)}"
        
        return result
    
    async def validate_integration(self, code: str, file_path: str, 
                                 existing_codebase: Dict[str, str]) -> Dict[str, Any]:
        """Validate code integration with existing codebase.
        
        Args:
            code: The code to validate.
            file_path: The path where the code would be saved.
            existing_codebase: Dictionary mapping file paths to their contents.
            
        Returns:
            Dictionary containing integration validation results.
        """
        logger.info(f"Validating integration for file: {file_path}")
        
        result = {
            "import_issues": [],
            "dependency_issues": [],
            "interface_issues": [],
            "passed": True,
            "timestamp": datetime.now().isoformat()
        }
        
        # Create a temporary directory for integration testing
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create the directory structure and files
            for path, content in existing_codebase.items():
                full_path = os.path.join(temp_dir, path)
                os.makedirs(os.path.dirname(full_path), exist_ok=True)
                with open(full_path, "w") as f:
                    f.write(content)
            
            # Add the new code
            new_file_path = os.path.join(temp_dir, file_path)
            os.makedirs(os.path.dirname(new_file_path), exist_ok=True)
            with open(new_file_path, "w") as f:
                f.write(code)
            
            # Check for import issues
            import_issues = await self._check_imports(temp_dir, new_file_path)
            if import_issues:
                result["import_issues"] = import_issues
                result["passed"] = False
            
            # Check for interface compatibility
            interface_issues = await self._check_interfaces(temp_dir, new_file_path, file_path, existing_codebase)
            if interface_issues:
                result["interface_issues"] = interface_issues
                result["passed"] = False
        
        return result
    
    async def get_validation_report(self, validation_id: str) -> Dict[str, Any]:
        """Get detailed validation report.
        
        Args:
            validation_id: ID of the validation to retrieve.
            
        Returns:
            Dictionary containing validation report.
        """
        if validation_id not in self.validation_history:
            return {"error": f"Validation ID {validation_id} not found"}
        
        return self.validation_history[validation_id]
    
    async def _run_pylint(self, file_path: str) -> Dict[str, Any]:
        """Run pylint on a file."""
        logger.debug(f"Running pylint on {file_path}")
        
        # This is a simplified implementation. In a real system, you would actually run pylint.
        # For now, we'll simulate the result.
        await asyncio.sleep(0.5)
        
        # Simulate pylint output
        return {
            "score": 8.5,
            "issues": [
                {"line": 10, "column": 0, "type": "convention", "message": "Missing docstring"}
            ],
            "passed": True
        }
    
    async def _run_mypy(self, file_path: str) -> Dict[str, Any]:
        """Run mypy on a file."""
        logger.debug(f"Running mypy on {file_path}")
        
        # This is a simplified implementation. In a real system, you would actually run mypy.
        # For now, we'll simulate the result.
        await asyncio.sleep(0.5)
        
        # Simulate mypy output
        return {
            "issues": [],
            "passed": True
        }
    
    async def _run_bandit(self, file_path: str) -> Dict[str, Any]:
        """Run bandit on a file."""
        logger.debug(f"Running bandit on {file_path}")
        
        # This is a simplified implementation. In a real system, you would actually run bandit.
        # For now, we'll simulate the result.
        await asyncio.sleep(0.5)
        
        # Simulate bandit output
        return {
            "vulnerabilities": [],
            "passed": True
        }
    
    async def _run_pytest(self, test_dir: str) -> Dict[str, Any]:
        """Run pytest on a directory."""
        logger.debug(f"Running pytest in {test_dir}")
        
        # This is a simplified implementation. In a real system, you would actually run pytest.
        # For now, we'll simulate the result.
        await asyncio.sleep(0.5)
        
        # Simulate pytest output
        return {
            "tests_run": 5,
            "tests_passed": 5,
            "tests_failed": 0,
            "test_output": "All tests passed!"
        }
    
    async def _check_imports(self, temp_dir: str, file_path: str) -> List[Dict[str, Any]]:
        """Check for import issues in the code."""
        logger.debug(f"Checking imports for {file_path}")
        
        # This is a simplified implementation. In a real system, you would actually check imports.
        # For now, we'll simulate the result.
        await asyncio.sleep(0.5)
        
        # Simulate import check
        return []
    
    async def _check_interfaces(self, temp_dir: str, new_file_path: str, 
                              original_path: str, existing_codebase: Dict[str, str]) -> List[Dict[str, Any]]:
        """Check for interface compatibility issues."""
        logger.debug(f"Checking interfaces for {new_file_path}")
        
        # This is a simplified implementation. In a real system, you would actually check interfaces.
        # For now, we'll simulate the result.
        await asyncio.sleep(0.5)
        
        # Simulate interface check
        return [] 