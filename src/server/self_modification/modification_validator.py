from typing import Dict, List, Optional, Any
import logging
import asyncio
import json
import os
import uuid
import tempfile
import subprocess
import shutil
import ast
import re
from pathlib import Path
from datetime import datetime
import importlib
import sys

logger = logging.getLogger(__name__)

class StaticAnalyzer:
    """Static code analyzer for Python code."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize with configuration.
        
        Args:
            config: Configuration for static analysis.
                   If None, default configuration will be used.
        """
        self.config = config or {
            "check_syntax": True,
            "check_pep8": True,
            "check_security": True,
            "check_type_hints": True,
            "tools": {
                "pylint": True,
                "mypy": True,
                "bandit": True,
                "pycodestyle": True
            },
            "severity_threshold": "warning"  # error, warning, info
        }
    
    async def parse_syntax(self, code: str) -> Dict[str, Any]:
        """Check code for syntax errors.
        
        Args:
            code: Python code to check.
            
        Returns:
            Dict with results of syntax check.
        """
        result = {
            "has_syntax_errors": False,
            "errors": []
        }
        
        try:
            ast.parse(code)
        except SyntaxError as e:
            result["has_syntax_errors"] = True
            result["errors"].append({
                "line": e.lineno,
                "column": e.offset,
                "message": str(e),
                "severity": "error"
            })
        
        return result
    
    async def check_coding_standards(self, code: str) -> Dict[str, Any]:
        """Check code against PEP 8 coding standards.
        
        Args:
            code: Python code to check.
            
        Returns:
            Dict with results of standards check.
        """
        if not self.config.get("check_pep8", True):
            return {"has_style_issues": False, "issues": []}
        
        result = {
            "has_style_issues": False,
            "issues": []
        }
        
        # Write code to a temporary file for analysis
        with tempfile.NamedTemporaryFile(suffix='.py', delete=False) as temp_file:
            temp_path = temp_file.name
            temp_file.write(code.encode('utf-8'))
        
        try:
            # Use pycodestyle to check PEP 8 compliance
            if self.config.get("tools", {}).get("pycodestyle", True):
                try:
                    cmd = ["pycodestyle", temp_path]
                    process = await asyncio.create_subprocess_exec(
                        *cmd,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE
                    )
                    stdout, stderr = await process.communicate()
                    
                    if stdout:
                        result["has_style_issues"] = True
                        for line in stdout.decode().splitlines():
                            parts = line.split(':', 3)
                            if len(parts) >= 3:
                                result["issues"].append({
                                    "line": int(parts[1]),
                                    "column": int(parts[2].split(' ')[0]),
                                    "message": parts[3] if len(parts) > 3 else "",
                                    "severity": "warning"
                                })
                except Exception as e:
                    logger.error(f"Error running pycodestyle: {str(e)}")
                    result["issues"].append({
                        "line": 0,
                        "column": 0,
                        "message": f"Error running style check: {str(e)}",
                        "severity": "error"
                    })
        finally:
            # Remove temporary file
            os.unlink(temp_path)
        
        return result
    
    async def check_security_vulnerabilities(self, code: str) -> Dict[str, Any]:
        """Check code for security vulnerabilities.
        
        Args:
            code: Python code to check.
            
        Returns:
            Dict with results of security check.
        """
        if not self.config.get("check_security", True):
            return {"has_vulnerabilities": False, "vulnerabilities": []}
        
        result = {
            "has_vulnerabilities": False,
            "vulnerabilities": []
        }
        
        # Write code to a temporary file for analysis
        with tempfile.NamedTemporaryFile(suffix='.py', delete=False) as temp_file:
            temp_path = temp_file.name
            temp_file.write(code.encode('utf-8'))
        
        try:
            # Use bandit to check security vulnerabilities
            if self.config.get("tools", {}).get("bandit", True):
                try:
                    cmd = ["bandit", "-f", "json", temp_path]
                    process = await asyncio.create_subprocess_exec(
                        *cmd,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE
                    )
                    stdout, stderr = await process.communicate()
                    
                    if stdout:
                        try:
                            bandit_data = json.loads(stdout.decode())
                            if bandit_data.get("results"):
                                result["has_vulnerabilities"] = True
                                for issue in bandit_data.get("results", []):
                                    result["vulnerabilities"].append({
                                        "line": issue.get("line_number", 0),
                                        "column": 0,  # Bandit doesn't provide column info
                                        "message": issue.get("issue_text", ""),
                                        "severity": issue.get("issue_severity", "medium"),
                                        "confidence": issue.get("issue_confidence", "medium"),
                                        "cwe": issue.get("cwe", "")
                                    })
                        except json.JSONDecodeError:
                            # If not valid JSON, try to extract info from plain text
                            for line in stdout.decode().splitlines():
                                if ">>>" in line and ":" in line:
                                    parts = line.split(":", 1)
                                    line_info = parts[0].strip()
                                    message = parts[1].strip() if len(parts) > 1 else ""
                                    line_match = re.search(r"line (\d+)", line_info)
                                    line_num = int(line_match.group(1)) if line_match else 0
                                    
                                    result["has_vulnerabilities"] = True
                                    result["vulnerabilities"].append({
                                        "line": line_num,
                                        "column": 0,
                                        "message": message,
                                        "severity": "medium",
                                        "confidence": "medium"
                                    })
                except Exception as e:
                    logger.error(f"Error running bandit: {str(e)}")
                    result["vulnerabilities"].append({
                        "line": 0,
                        "column": 0,
                        "message": f"Error running security check: {str(e)}",
                        "severity": "error"
                    })
        finally:
            # Remove temporary file
            os.unlink(temp_path)
        
        return result
    
    async def check_type_hints(self, code: str) -> Dict[str, Any]:
        """Check code for type hint errors.
        
        Args:
            code: Python code to check.
            
        Returns:
            Dict with results of type hint check.
        """
        if not self.config.get("check_type_hints", True):
            return {"has_type_issues": False, "issues": []}
        
        result = {
            "has_type_issues": False,
            "issues": []
        }
        
        # Write code to a temporary file for analysis
        with tempfile.NamedTemporaryFile(suffix='.py', delete=False) as temp_file:
            temp_path = temp_file.name
            temp_file.write(code.encode('utf-8'))
        
        try:
            # Use mypy to check type hints
            if self.config.get("tools", {}).get("mypy", True):
                try:
                    cmd = ["mypy", "--no-incremental", temp_path]
                    process = await asyncio.create_subprocess_exec(
                        *cmd,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE
                    )
                    stdout, stderr = await process.communicate()
                    
                    if stdout:
                        for line in stdout.decode().splitlines():
                            if ":" in line:
                                parts = line.split(":")
                                if len(parts) >= 3:
                                    try:
                                        line_num = int(parts[1])
                                        message = parts[2].strip()
                                        # Check if it's an error message
                                        if "error" in message:
                                            result["has_type_issues"] = True
                                            result["issues"].append({
                                                "line": line_num,
                                                "column": 0,  # Usually not provided by mypy in simple output
                                                "message": message,
                                                "severity": "error" if "error" in message.lower() else "warning"
                                            })
                                    except ValueError:
                                        # If line number cannot be parsed
                                        continue
                except Exception as e:
                    logger.error(f"Error running mypy: {str(e)}")
                    result["issues"].append({
                        "line": 0,
                        "column": 0,
                        "message": f"Error running type check: {str(e)}",
                        "severity": "error"
                    })
        finally:
            # Remove temporary file
            os.unlink(temp_path)
        
        return result
    
    async def check_antipatterns(self, code: str) -> Dict[str, Any]:
        """Check code for anti-patterns and code smells.
        
        Args:
            code: Python code to check.
            
        Returns:
            Dict with results of anti-pattern check.
        """
        result = {
            "has_antipatterns": False,
            "issues": []
        }
        
        # Basic anti-pattern checks
        # 1. Check for wildcard imports
        if "import *" in code:
            result["has_antipatterns"] = True
            result["issues"].append({
                "line": 0,  # Would need to scan for actual line
                "message": "Wildcard import found. Use specific imports instead.",
                "severity": "warning",
                "pattern": "wildcard_import"
            })
        
        # 2. Check for multiple statements on the same line
        if ";" in code:
            result["has_antipatterns"] = True
            lines = code.split("\n")
            for i, line in enumerate(lines):
                if ";" in line and not line.strip().startswith("#"):
                    result["issues"].append({
                        "line": i + 1,
                        "message": "Multiple statements on the same line. Each statement should be on a separate line.",
                        "severity": "warning",
                        "pattern": "multiple_statements"
                    })
        
        # 3. Check for very long lines
        lines = code.split("\n")
        for i, line in enumerate(lines):
            if len(line) > 100:  # PEP 8 recommends max 79/80 chars
                result["has_antipatterns"] = True
                result["issues"].append({
                    "line": i + 1,
                    "message": f"Line too long ({len(line)} characters). PEP 8 recommends lines no longer than 79 characters.",
                    "severity": "info",
                    "pattern": "long_line"
                })
        
        # 4. Check for very large functions
        try:
            tree = ast.parse(code)
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    if len(node.body) > 50:  # Arbitrary threshold for demonstration
                        result["has_antipatterns"] = True
                        result["issues"].append({
                            "line": node.lineno,
                            "message": f"Function '{node.name}' is too large ({len(node.body)} lines). Consider refactoring.",
                            "severity": "warning",
                            "pattern": "large_function"
                        })
        except SyntaxError:
            # If code has syntax errors, we'll skip this check as it's already covered by parse_syntax
            pass
        
        return result
    
    async def analyze_code(self, code: str) -> Dict[str, Any]:
        """Run a comprehensive static analysis on the code.
        
        Args:
            code: Python code to analyze.
            
        Returns:
            Dictionary with comprehensive analysis results.
        """
        logger.info("Running static analysis on code")
        
        # Run all checks in parallel
        syntax_result, standards_result, security_result, type_result, antipattern_result = await asyncio.gather(
            self.parse_syntax(code),
            self.check_coding_standards(code),
            self.check_security_vulnerabilities(code),
            self.check_type_hints(code),
            self.check_antipatterns(code)
        )
        
        # Aggregate all issues
        all_issues = []
        
        if syntax_result.get("has_syntax_errors", False):
            all_issues.extend(syntax_result.get("errors", []))
        
        if standards_result.get("has_style_issues", False):
            all_issues.extend(standards_result.get("issues", []))
        
        if security_result.get("has_vulnerabilities", False):
            all_issues.extend(security_result.get("vulnerabilities", []))
        
        if type_result.get("has_type_issues", False):
            all_issues.extend(type_result.get("issues", []))
        
        if antipattern_result.get("has_antipatterns", False):
            all_issues.extend(antipattern_result.get("issues", []))
        
        # Filter issues based on severity threshold
        filtered_issues = []
        severity_levels = {"error": 3, "warning": 2, "info": 1}
        threshold_level = severity_levels.get(self.config.get("severity_threshold", "warning"), 2)
        
        for issue in all_issues:
            issue_severity = issue.get("severity", "warning")
            issue_level = severity_levels.get(issue_severity, 2)
            if issue_level >= threshold_level:
                filtered_issues.append(issue)
        
        # Sort issues by line number
        filtered_issues.sort(key=lambda x: x.get("line", 0))
        
        return {
            "passed": len(filtered_issues) == 0,
            "issues": filtered_issues,
            "summary": {
                "total_issues": len(filtered_issues),
                "syntax_errors": syntax_result.get("has_syntax_errors", False),
                "style_issues": standards_result.get("has_style_issues", False),
                "security_vulnerabilities": security_result.get("has_vulnerabilities", False),
                "type_issues": type_result.get("has_type_issues", False),
                "antipatterns": antipattern_result.get("has_antipatterns", False)
            }
        }


class TestRunner:
    """Runs tests to validate code modifications."""
    
    def __init__(self, test_config: Optional[Dict[str, Any]] = None):
        """Initialize with test configuration.
        
        Args:
            test_config: Configuration for test execution.
                        If None, default configuration will be used.
        """
        self.test_config = test_config or {
            "test_framework": "pytest",
            "max_test_time": 60,  # seconds
            "run_unit_tests": True,
            "run_integration_tests": True,
            "coverage_threshold": 80.0,
            "test_dir": "tests"
        }
    
    async def prepare_test_environment(self, modified_file: str, modified_code: str) -> Dict[str, Any]:
        """Prepare a test environment with the modified code.
        
        Args:
            modified_file: Path to the file being modified.
            modified_code: The modified code.
            
        Returns:
            Dictionary with test environment details.
        """
        logger.info(f"Preparing test environment for {modified_file}")
        
        try:
            # Create a temporary directory for testing
            temp_dir = tempfile.mkdtemp(prefix="cerebrum_test_")
            
            # Create a copy of the relevant project structure
            # In a real implementation, this would be more sophisticated
            # to handle proper imports and dependencies
            project_dir = os.path.dirname(os.path.abspath(modified_file))
            relative_path = os.path.relpath(modified_file, project_dir)
            
            test_dir = os.path.join(project_dir, self.test_config.get("test_dir", "tests"))
            if not os.path.exists(test_dir):
                # Try to find tests directory
                test_dir = None
                for root, dirs, _ in os.walk(project_dir):
                    for d in dirs:
                        if d.lower() == "tests" or d.lower() == "test":
                            test_dir = os.path.join(root, d)
                            break
                    if test_dir:
                        break
            
            if not test_dir:
                raise ValueError(f"Could not find test directory for {modified_file}")
            
            # Copy the modified file to the temp directory
            temp_file_path = os.path.join(temp_dir, os.path.basename(modified_file))
            with open(temp_file_path, 'w') as f:
                f.write(modified_code)
            
            # Copy relevant test files
            temp_test_dir = os.path.join(temp_dir, "tests")
            os.makedirs(temp_test_dir, exist_ok=True)
            
            # Copy test files related to the modified file
            for root, _, files in os.walk(test_dir):
                for file in files:
                    if file.startswith("test_") and file.endswith(".py"):
                        source = os.path.join(root, file)
                        target = os.path.join(temp_test_dir, os.path.basename(file))
                        shutil.copy2(source, target)
            
            return {
                "success": True,
                "temp_dir": temp_dir,
                "temp_file_path": temp_file_path,
                "temp_test_dir": temp_test_dir
            }
        except Exception as e:
            logger.error(f"Error preparing test environment: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def run_tests(self, test_env: Dict[str, Any]) -> Dict[str, Any]:
        """Run tests in the prepared environment.
        
        Args:
            test_env: Test environment prepared by prepare_test_environment.
            
        Returns:
            Dictionary with test results.
        """
        if not test_env.get("success", False):
            return {
                "success": False,
                "error": test_env.get("error", "Test environment preparation failed"),
                "tests_passed": False
            }
        
        logger.info(f"Running tests in {test_env['temp_dir']}")
        
        try:
            # Change to the test directory
            original_dir = os.getcwd()
            os.chdir(test_env["temp_dir"])
            
            # Run pytest
            if self.test_config.get("test_framework", "pytest") == "pytest":
                cmd = ["pytest", test_env["temp_test_dir"], "-v"]
                
                if self.test_config.get("run_unit_tests", True) and not self.test_config.get("run_integration_tests", True):
                    cmd.append("-m")
                    cmd.append("not integration")
                
                process = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                
                # Set a timeout for test execution
                try:
                    stdout, stderr = await asyncio.wait_for(
                        process.communicate(),
                        timeout=self.test_config.get("max_test_time", 60)
                    )
                    
                    # Process test results
                    output = stdout.decode()
                    exit_code = process.returncode
                    
                    # Parse test summary
                    test_summary = self._parse_pytest_output(output)
                    
                    return {
                        "success": True,
                        "tests_passed": exit_code == 0,
                        "exit_code": exit_code,
                        "output": output,
                        "error_output": stderr.decode(),
                        "summary": test_summary
                    }
                except asyncio.TimeoutError:
                    return {
                        "success": False,
                        "error": f"Tests timed out after {self.test_config.get('max_test_time', 60)} seconds",
                        "tests_passed": False
                    }
            else:
                return {
                    "success": False,
                    "error": f"Unsupported test framework: {self.test_config.get('test_framework')}",
                    "tests_passed": False
                }
        except Exception as e:
            logger.error(f"Error running tests: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "tests_passed": False
            }
        finally:
            # Change back to the original directory
            os.chdir(original_dir)
    
    def _parse_pytest_output(self, output: str) -> Dict[str, Any]:
        """Parse pytest output to extract test summary.
        
        Args:
            output: Pytest output as string.
            
        Returns:
            Dictionary with test summary.
        """
        summary = {
            "total": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "errors": []
        }
        
        # Extract failed tests and their errors
        for line in output.splitlines():
            if line.startswith("FAILED"):
                parts = line.split("::", 1)
                if len(parts) > 1:
                    test_name = parts[1].strip()
                    summary["errors"].append({"test": test_name})
        
        # Extract summary line
        summary_line = re.search(r"=+ (.*) in .*", output)
        if summary_line:
            summary_text = summary_line.group(1)
            
            # Extract passed tests
            passed_match = re.search(r"(\d+) passed", summary_text)
            if passed_match:
                summary["passed"] = int(passed_match.group(1))
            
            # Extract failed tests
            failed_match = re.search(r"(\d+) failed", summary_text)
            if failed_match:
                summary["failed"] = int(failed_match.group(1))
            
            # Extract skipped tests
            skipped_match = re.search(r"(\d+) skipped", summary_text)
            if skipped_match:
                summary["skipped"] = int(skipped_match.group(1))
            
            # Calculate total
            summary["total"] = summary["passed"] + summary["failed"] + summary["skipped"]
        
        return summary
    
    async def cleanup_test_environment(self, test_env: Dict[str, Any]) -> None:
        """Clean up the test environment.
        
        Args:
            test_env: Test environment to clean up.
        """
        if test_env.get("temp_dir") and os.path.exists(test_env["temp_dir"]):
            try:
                shutil.rmtree(test_env["temp_dir"])
                logger.info(f"Cleaned up test environment: {test_env['temp_dir']}")
            except Exception as e:
                logger.error(f"Error cleaning up test environment: {str(e)}")
    
    async def validate_code_with_tests(self, modified_file: str, modified_code: str) -> Dict[str, Any]:
        """Validate code modification with tests.
        
        Args:
            modified_file: Path to the file being modified.
            modified_code: The modified code.
            
        Returns:
            Dictionary with validation results.
        """
        logger.info(f"Validating code with tests: {modified_file}")
        
        # Prepare test environment
        test_env = await self.prepare_test_environment(modified_file, modified_code)
        
        try:
            # Run tests
            test_results = await self.run_tests(test_env)
            
            # Process results
            validation_result = {
                "passed": test_results.get("tests_passed", False),
                "summary": test_results.get("summary", {}),
                "output": test_results.get("output", ""),
                "error_output": test_results.get("error_output", ""),
                "error": test_results.get("error", None)
            }
            
            return validation_result
        finally:
            # Clean up the test environment
            await self.cleanup_test_environment(test_env)


class ModificationValidator:
    """Validates code modifications for safety, quality, and functionality."""
    
    def __init__(self, test_runner: Optional[TestRunner] = None, static_analyzer: Optional[StaticAnalyzer] = None):
        """Initialize with required components.
        
        Args:
            test_runner: TestRunner instance for running tests.
            static_analyzer: StaticAnalyzer instance for static analysis.
        """
        self.test_runner = test_runner or TestRunner()
        self.static_analyzer = static_analyzer or StaticAnalyzer()
        self.validation_history = {}
    
    async def validate_syntax(self, code: str) -> Dict[str, Any]:
        """Validate code syntax.
        
        Args:
            code: Code to validate.
            
        Returns:
            Results of syntax validation.
        """
        return await self.static_analyzer.parse_syntax(code)
    
    async def validate_semantics(self, code: str) -> Dict[str, Any]:
        """Validate code semantics and standards.
        
        Args:
            code: Code to validate.
            
        Returns:
            Results of semantic validation.
        """
        # Combine various semantic checks
        standards_result = await self.static_analyzer.check_coding_standards(code)
        type_result = await self.static_analyzer.check_type_hints(code)
        antipattern_result = await self.static_analyzer.check_antipatterns(code)
        
        # Combine all issues
        all_issues = []
        all_issues.extend(standards_result.get("issues", []))
        all_issues.extend(type_result.get("issues", []))
        all_issues.extend(antipattern_result.get("issues", []))
        
        # Sort by line number
        all_issues.sort(key=lambda x: x.get("line", 0))
        
        return {
            "passed": len(all_issues) == 0,
            "issues": all_issues,
            "summary": {
                "total_issues": len(all_issues),
                "style_issues": standards_result.get("has_style_issues", False),
                "type_issues": type_result.get("has_type_issues", False),
                "antipatterns": antipattern_result.get("has_antipatterns", False)
            }
        }
    
    async def run_tests(self, code: str, file_path: str) -> Dict[str, Any]:
        """Run tests to ensure functionality isn't broken.
        
        Args:
            code: Modified code.
            file_path: Path to the file being modified.
            
        Returns:
            Results of test execution.
        """
        return await self.test_runner.validate_code_with_tests(file_path, code)
    
    async def assess_impact(self, code: str, original_code: str, file_path: str) -> Dict[str, Any]:
        """Assess the potential impact of the modification.
        
        Args:
            code: Modified code.
            original_code: Original code.
            file_path: Path to the file being modified.
            
        Returns:
            Assessment of potential impact.
        """
        impact_assessment = {
            "high_risk": False,
            "reasons": [],
            "affected_components": [],
            "metrics": {
                "change_size": 0,
                "complexity_change": 0,
                "risk_score": 0
            }
        }
        
        try:
            # Calculate change size
            original_lines = original_code.splitlines()
            modified_lines = code.splitlines()
            
            # Simple diff
            diff_count = 0
            added_count = 0
            removed_count = 0
            
            if len(original_lines) <= len(modified_lines):
                for i in range(len(original_lines)):
                    if original_lines[i] != modified_lines[i]:
                        diff_count += 1
                added_count = len(modified_lines) - len(original_lines)
            else:
                for i in range(len(modified_lines)):
                    if modified_lines[i] != original_lines[i]:
                        diff_count += 1
                removed_count = len(original_lines) - len(modified_lines)
            
            change_size = diff_count + added_count + removed_count
            impact_assessment["metrics"]["change_size"] = change_size
            
            # Calculate complexity change
            try:
                original_complexity = self._calculate_complexity(original_code)
                modified_complexity = self._calculate_complexity(code)
                complexity_change = modified_complexity - original_complexity
                impact_assessment["metrics"]["complexity_change"] = complexity_change
            except:
                # If complexity calculation fails, assume no change
                impact_assessment["metrics"]["complexity_change"] = 0
            
            # Identify high-risk patterns
            risk_patterns = [
                (r"os\.system", "Use of os.system() is potentially dangerous"),
                (r"exec\s*\(", "Use of exec() is potentially dangerous"),
                (r"eval\s*\(", "Use of eval() is potentially dangerous"),
                (r"__import__", "Dynamic imports may be risky"),
                (r"subprocess", "Subprocess calls can be risky if not properly sanitized"),
                (r"open\s*\(.+, 'w'", "File writing operations may have unintended consequences")
            ]
            
            for pattern, reason in risk_patterns:
                if re.search(pattern, code) and not re.search(pattern, original_code):
                    impact_assessment["high_risk"] = True
                    impact_assessment["reasons"].append(reason)
            
            # Calculate risk score (0-100)
            risk_score = min(100, (
                (change_size / max(1, len(original_lines))) * 50 +
                (abs(complexity_change) / max(1, original_complexity if original_complexity > 0 else 1)) * 30 +
                (len(impact_assessment["reasons"]) * 20)
            ))
            impact_assessment["metrics"]["risk_score"] = int(risk_score)
            
            # Identify affected components
            # In a real implementation, this would analyze imports, dependencies,
            # and call hierarchies to determine affected components
            
            # For now, we'll just include the file itself
            impact_assessment["affected_components"].append(file_path)
            
            # Classify high risk if score > 70
            if impact_assessment["metrics"]["risk_score"] > 70:
                impact_assessment["high_risk"] = True
                impact_assessment["reasons"].append(f"High risk score: {impact_assessment['metrics']['risk_score']}")
            
            return impact_assessment
        except Exception as e:
            logger.error(f"Error assessing impact: {str(e)}")
            return {
                "high_risk": True,
                "reasons": [f"Error assessing impact: {str(e)}"],
                "affected_components": [file_path],
                "metrics": {
                    "change_size": 0,
                    "complexity_change": 0,
                    "risk_score": 100  # Assume high risk on error
                }
            }
    
    def _calculate_complexity(self, code: str) -> int:
        """Calculate code complexity using AST.
        
        Args:
            code: Code to analyze.
            
        Returns:
            Complexity score.
        """
        try:
            tree = ast.parse(code)
            complexity = 0
            
            for node in ast.walk(tree):
                # Count control flow statements
                if isinstance(node, (ast.If, ast.For, ast.While, ast.Try, ast.With)):
                    complexity += 1
                # Count boolean operations
                elif isinstance(node, ast.BoolOp):
                    complexity += len(node.values) - 1
                # Count function definitions
                elif isinstance(node, ast.FunctionDef):
                    complexity += 1
                # Count comprehensions
                elif isinstance(node, (ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp)):
                    complexity += 1
            
            return complexity
        except SyntaxError:
            # If code has syntax errors, return 0
            return 0
    
    async def validate_code(self, code: str, file_path: str, original_code: Optional[str] = None) -> Dict[str, Any]:
        """Validate code for syntax, semantics, and functionality.
        
        Args:
            code: Code to validate.
            file_path: Path to the file being modified.
            original_code: Original code before modification.
            
        Returns:
            Dictionary with validation results.
        """
        validation_id = str(uuid.uuid4())
        logger.info(f"Validating code with ID: {validation_id}")
        
        validation_record = {
            "id": validation_id,
            "file_path": file_path,
            "timestamp": datetime.now().isoformat(),
            "results": {}
        }
        
        try:
            # If original code is not provided, try to load it
            if original_code is None:
                try:
                    with open(file_path, 'r') as f:
                        original_code = f.read()
                except:
                    original_code = ""
            
            # Run validation steps in parallel
            syntax_results, semantics_results, static_analysis_results = await asyncio.gather(
                self.validate_syntax(code),
                self.validate_semantics(code),
                self.static_analyzer.analyze_code(code)
            )
            
            # Check if we need to run tests
            test_results = {"passed": True, "summary": {}, "run": False}
            if syntax_results.get("has_syntax_errors", False) == False:
                test_results = await self.run_tests(code, file_path)
                test_results["run"] = True
            
            # Assess impact
            impact_assessment = await self.assess_impact(code, original_code, file_path)
            
            # Combine all results
            all_passed = (
                not syntax_results.get("has_syntax_errors", False) and 
                semantics_results.get("passed", False) and
                static_analysis_results.get("passed", False) and
                test_results.get("passed", False) and
                not impact_assessment.get("high_risk", False)
            )
            
            validation_results = {
                "passed": all_passed,
                "syntax_check": syntax_results,
                "semantics_check": semantics_results,
                "static_analysis": static_analysis_results,
                "test_results": test_results,
                "impact_assessment": impact_assessment,
                "errors": []
            }
            
            # Collect all errors for easy access
            if syntax_results.get("has_syntax_errors", False):
                validation_results["errors"].extend(syntax_results.get("errors", []))
            
            if not semantics_results.get("passed", False):
                validation_results["errors"].extend(semantics_results.get("issues", []))
            
            if not static_analysis_results.get("passed", False):
                validation_results["errors"].extend(static_analysis_results.get("issues", []))
            
            if test_results.get("run", False) and not test_results.get("passed", False):
                validation_results["errors"].append({
                    "message": "Tests failed",
                    "details": test_results.get("summary", {})
                })
            
            if impact_assessment.get("high_risk", False):
                for reason in impact_assessment.get("reasons", []):
                    validation_results["errors"].append({
                        "message": f"High risk: {reason}",
                        "severity": "warning"
                    })
            
            validation_record["results"] = validation_results
            self.validation_history[validation_id] = validation_record
            
            return validation_results
        except Exception as e:
            logger.error(f"Error validating code: {str(e)}")
            error_result = {
                "passed": False,
                "errors": [{
                    "message": f"Validation error: {str(e)}",
                    "severity": "error"
                }]
            }
            validation_record["results"] = error_result
            self.validation_history[validation_id] = validation_record
            return error_result 