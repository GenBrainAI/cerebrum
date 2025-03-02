from typing import Dict, List, Optional, Any, Tuple, Set
import asyncio
import logging
import os
import sys
import json
import re
import importlib
import unittest
import coverage
import inspect
import ast
from datetime import datetime
from pathlib import Path
import uuid

logger = logging.getLogger(__name__)

class TestRunner:
    """Manages test discovery, execution, and analysis."""
    
    def __init__(self, project_root: Optional[str] = None):
        """
        Initialize with project root directory.
        
        Args:
            project_root: Root directory of the project
        """
        self.project_root = project_root or os.getcwd()
        self.test_results_cache: Dict[str, Dict[str, Any]] = {}
        self.coverage_data = None
        self.test_registry: Dict[str, Dict[str, Any]] = {}
    
    async def discover_tests(self, path: Optional[str] = None, pattern: str = "test_*.py") -> List[Dict[str, Any]]:
        """
        Discover tests in the specified path.
        
        Args:
            path: Path to search for tests
            pattern: Pattern to match test files
            
        Returns:
            List of dictionaries with test information
        """
        search_path = os.path.join(self.project_root, path) if path else self.project_root
        
        try:
            logger.info(f"Discovering tests in {search_path} with pattern {pattern}")
            
            # Use unittest discovery
            loader = unittest.TestLoader()
            suite = loader.discover(search_path, pattern=pattern)
            
            # Extract test information
            tests = []
            self.test_registry = {}
            
            for test_suite in self._flatten_test_suite(suite):
                for test_case in test_suite:
                    test_id = str(uuid.uuid4())
                    test_name = test_case.id()
                    
                    # Extract class and method names
                    parts = test_name.split(".")
                    if len(parts) >= 3:
                        module_name = ".".join(parts[:-2])
                        class_name = parts[-2]
                        method_name = parts[-1]
                    else:
                        module_name = ".".join(parts[:-1])
                        class_name = ""
                        method_name = parts[-1]
                    
                    # Get file path
                    module = importlib.import_module(module_name)
                    file_path = os.path.relpath(inspect.getfile(module), self.project_root)
                    
                    # Get docstring if available
                    docstring = ""
                    try:
                        if class_name:
                            test_class = getattr(module, class_name)
                            test_method = getattr(test_class, method_name)
                            docstring = inspect.getdoc(test_method) or ""
                        else:
                            test_method = getattr(module, method_name)
                            docstring = inspect.getdoc(test_method) or ""
                    except (AttributeError, TypeError):
                        pass
                    
                    test_info = {
                        "id": test_id,
                        "name": test_name,
                        "module": module_name,
                        "class": class_name,
                        "method": method_name,
                        "file": file_path,
                        "description": docstring
                    }
                    
                    tests.append(test_info)
                    self.test_registry[test_id] = {
                        "test_case": test_case,
                        "info": test_info
                    }
            
            return tests
        except Exception as e:
            logger.exception(f"Error discovering tests: {e}")
            return []
    
    async def run_tests(self, test_path: Optional[str] = None, pattern: Optional[str] = None, 
                       verbosity: int = 2) -> Dict[str, Any]:
        """
        Run tests and return results.
        
        Args:
            test_path: Path to the tests to run
            pattern: Pattern to match test files
            verbosity: Verbosity level for test output
            
        Returns:
            Dictionary with test results
        """
        try:
            logger.info(f"Running tests in {test_path or self.project_root}")
            
            # Discover tests if needed
            if not self.test_registry or test_path or pattern:
                await self.discover_tests(test_path, pattern or "test_*.py")
            
            # Create a test suite with all tests
            suite = unittest.TestSuite()
            for test_info in self.test_registry.values():
                suite.addTest(test_info["test_case"])
            
            # Run the tests with coverage
            cov = coverage.Coverage(source=[self.project_root])
            cov.start()
            
            # Use a StringIO to capture test output
            from io import StringIO
            output = StringIO()
            runner = unittest.TextTestRunner(stream=output, verbosity=verbosity)
            
            # Run the tests
            start_time = datetime.now()
            result = runner.run(suite)
            end_time = datetime.now()
            
            # Stop coverage
            cov.stop()
            cov.save()
            self.coverage_data = cov
            
            # Process results
            test_results = {
                "success": result.wasSuccessful(),
                "total": result.testsRun,
                "failures": len(result.failures),
                "errors": len(result.errors),
                "skipped": len(result.skipped),
                "execution_time": (end_time - start_time).total_seconds(),
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat(),
                "output": output.getvalue(),
                "failures_detail": [
                    {
                        "test": test[0].id(),
                        "message": test[1]
                    }
                    for test in result.failures
                ],
                "errors_detail": [
                    {
                        "test": test[0].id(),
                        "message": test[1]
                    }
                    for test in result.errors
                ],
                "skipped_detail": [
                    {
                        "test": test[0].id(),
                        "message": test[1]
                    }
                    for test in result.skipped
                ]
            }
            
            # Cache the results
            result_id = str(uuid.uuid4())
            self.test_results_cache[result_id] = test_results
            test_results["id"] = result_id
            
            return test_results
        except Exception as e:
            logger.exception(f"Error running tests: {e}")
            return {
                "success": False,
                "error": str(e),
                "total": 0,
                "failures": 0,
                "errors": 1,
                "skipped": 0,
                "execution_time": 0,
                "output": f"Error: {str(e)}"
            }
    
    async def run_specific_test(self, test_id: str) -> Dict[str, Any]:
        """
        Run a specific test by ID.
        
        Args:
            test_id: ID of the test to run
            
        Returns:
            Dictionary with test results
        """
        try:
            logger.info(f"Running specific test with ID {test_id}")
            
            # Check if test exists
            if test_id not in self.test_registry:
                return {
                    "success": False,
                    "error": f"Test with ID {test_id} not found",
                    "total": 0,
                    "failures": 0,
                    "errors": 1,
                    "skipped": 0,
                    "execution_time": 0,
                    "output": f"Error: Test with ID {test_id} not found"
                }
            
            # Create a test suite with the specific test
            suite = unittest.TestSuite()
            suite.addTest(self.test_registry[test_id]["test_case"])
            
            # Run the test with coverage
            cov = coverage.Coverage(source=[self.project_root])
            cov.start()
            
            # Use a StringIO to capture test output
            from io import StringIO
            output = StringIO()
            runner = unittest.TextTestRunner(stream=output, verbosity=2)
            
            # Run the test
            start_time = datetime.now()
            result = runner.run(suite)
            end_time = datetime.now()
            
            # Stop coverage
            cov.stop()
            cov.save()
            
            # Process results
            test_results = {
                "success": result.wasSuccessful(),
                "total": result.testsRun,
                "failures": len(result.failures),
                "errors": len(result.errors),
                "skipped": len(result.skipped),
                "execution_time": (end_time - start_time).total_seconds(),
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat(),
                "output": output.getvalue(),
                "test_info": self.test_registry[test_id]["info"],
                "failures_detail": [
                    {
                        "test": test[0].id(),
                        "message": test[1]
                    }
                    for test in result.failures
                ],
                "errors_detail": [
                    {
                        "test": test[0].id(),
                        "message": test[1]
                    }
                    for test in result.errors
                ],
                "skipped_detail": [
                    {
                        "test": test[0].id(),
                        "message": test[1]
                    }
                    for test in result.skipped
                ]
            }
            
            # Cache the results
            result_id = str(uuid.uuid4())
            self.test_results_cache[result_id] = test_results
            test_results["id"] = result_id
            
            return test_results
        except Exception as e:
            logger.exception(f"Error running specific test: {e}")
            return {
                "success": False,
                "error": str(e),
                "total": 0,
                "failures": 0,
                "errors": 1,
                "skipped": 0,
                "execution_time": 0,
                "output": f"Error: {str(e)}"
            }
    
    async def analyze_test_results(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze test results for patterns and issues.
        
        Args:
            results: Test results to analyze
            
        Returns:
            Dictionary with analysis results
        """
        try:
            logger.info("Analyzing test results")
            
            # Get results from cache if ID is provided
            if isinstance(results, str) and results in self.test_results_cache:
                results = self.test_results_cache[results]
            
            # Basic analysis
            analysis = {
                "success_rate": (results["total"] - results["failures"] - results["errors"]) / results["total"] if results["total"] > 0 else 0,
                "execution_time": results["execution_time"],
                "total_tests": results["total"],
                "issues": []
            }
            
            # Analyze failures and errors
            for failure in results.get("failures_detail", []):
                analysis["issues"].append({
                    "type": "failure",
                    "test": failure["test"],
                    "message": failure["message"],
                    "analysis": self._analyze_test_failure(failure["message"])
                })
            
            for error in results.get("errors_detail", []):
                analysis["issues"].append({
                    "type": "error",
                    "test": error["test"],
                    "message": error["message"],
                    "analysis": self._analyze_test_error(error["message"])
                })
            
            # Add recommendations
            analysis["recommendations"] = self._generate_recommendations(analysis["issues"])
            
            return analysis
        except Exception as e:
            logger.exception(f"Error analyzing test results: {e}")
            return {
                "error": str(e),
                "success_rate": 0,
                "issues": [],
                "recommendations": ["Error analyzing test results"]
            }
    
    async def get_test_coverage(self, test_path: Optional[str] = None) -> Dict[str, Any]:
        """
        Get test coverage information.
        
        Args:
            test_path: Path to the tests to run for coverage
            
        Returns:
            Dictionary with coverage information
        """
        try:
            logger.info("Getting test coverage")
            
            # Run tests if coverage data is not available
            if not self.coverage_data:
                await self.run_tests(test_path)
            
            if not self.coverage_data:
                return {
                    "error": "No coverage data available",
                    "total_coverage": 0,
                    "files": []
                }
            
            # Get coverage data
            cov = self.coverage_data
            
            # Generate coverage report
            from coverage.report import get_analysis
            from coverage.results import Analysis
            
            # Get coverage data for each file
            file_coverage = []
            total_statements = 0
            total_missing = 0
            
            for file_path in cov.get_data().measured_files():
                # Skip files outside the project root
                if not file_path.startswith(self.project_root):
                    continue
                
                # Get relative path
                rel_path = os.path.relpath(file_path, self.project_root)
                
                # Skip test files
                if "test_" in rel_path or "tests/" in rel_path:
                    continue
                
                # Get coverage analysis
                analysis = cov._analyze(file_path)
                
                # Calculate coverage
                statements = len(analysis.statements)
                missing = len(analysis.missing)
                covered = statements - missing
                
                if statements > 0:
                    percent_covered = (covered / statements) * 100
                else:
                    percent_covered = 100.0
                
                # Add to totals
                total_statements += statements
                total_missing += missing
                
                # Get missing lines
                missing_lines = sorted(analysis.missing)
                
                file_coverage.append({
                    "file": rel_path,
                    "statements": statements,
                    "missing": missing,
                    "covered": covered,
                    "percent_covered": percent_covered,
                    "missing_lines": missing_lines
                })
            
            # Calculate total coverage
            if total_statements > 0:
                total_coverage = ((total_statements - total_missing) / total_statements) * 100
            else:
                total_coverage = 100.0
            
            return {
                "total_coverage": total_coverage,
                "total_statements": total_statements,
                "total_missing": total_missing,
                "total_covered": total_statements - total_missing,
                "files": sorted(file_coverage, key=lambda x: x["percent_covered"])
            }
        except Exception as e:
            logger.exception(f"Error getting test coverage: {e}")
            return {
                "error": str(e),
                "total_coverage": 0,
                "files": []
            }
    
    async def generate_test(self, source_file: str, output_file: Optional[str] = None) -> str:
        """
        Generate a test file for the given source file.
        
        Args:
            source_file: Path to the source file
            output_file: Path to write the test file
            
        Returns:
            Path to the generated test file
        """
        try:
            logger.info(f"Generating test for {source_file}")
            
            # Get absolute path
            source_path = os.path.join(self.project_root, source_file)
            
            # Check if file exists
            if not os.path.isfile(source_path):
                return f"Error: Source file {source_file} not found"
            
            # Parse the source file
            with open(source_path, "r") as f:
                source_code = f.read()
            
            # Parse the AST
            tree = ast.parse(source_code)
            
            # Extract classes and functions
            classes = []
            functions = []
            
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    methods = []
                    for item in node.body:
                        if isinstance(item, ast.FunctionDef):
                            methods.append(item.name)
                    
                    classes.append({
                        "name": node.name,
                        "methods": methods
                    })
                elif isinstance(node, ast.FunctionDef) and node.name != "__init__":
                    # Only include top-level functions
                    if not hasattr(node, 'parent') or isinstance(node.parent, ast.Module):
                        functions.append(node.name)
            
            # Generate test file content
            module_name = os.path.splitext(os.path.basename(source_file))[0]
            test_content = self._generate_test_content(module_name, classes, functions, source_file)
            
            # Determine output file path
            if not output_file:
                dir_name = os.path.dirname(source_file)
                base_name = os.path.basename(source_file)
                test_name = f"test_{base_name}"
                output_file = os.path.join(dir_name, test_name)
            
            output_path = os.path.join(self.project_root, output_file)
            
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            # Write the test file
            with open(output_path, "w") as f:
                f.write(test_content)
            
            return output_file
        except Exception as e:
            logger.exception(f"Error generating test: {e}")
            return f"Error: {str(e)}"
    
    def _flatten_test_suite(self, suite):
        """Flatten a test suite into a list of test suites."""
        flattened = []
        for test in suite:
            if isinstance(test, unittest.TestSuite):
                if test._tests:
                    flattened.extend(self._flatten_test_suite(test))
            else:
                flattened.append(unittest.TestSuite([test]))
        return flattened
    
    def _analyze_test_failure(self, message: str) -> str:
        """Analyze a test failure message."""
        # Check for common assertion failures
        if "AssertionError" in message:
            if "!=" in message:
                return "Values don't match. Check expected vs actual values."
            elif "==" in message:
                return "Values match when they shouldn't. Check your test conditions."
            elif "is not" in message:
                return "Objects are not the same instance. Consider using == instead of is."
            elif "is" in message:
                return "Objects are the same instance when they shouldn't be. Consider using != instead of is not."
            else:
                return "Assertion failed. Check your test conditions."
        
        return "Unknown failure pattern."
    
    def _analyze_test_error(self, message: str) -> str:
        """Analyze a test error message."""
        # Check for common errors
        if "ImportError" in message or "ModuleNotFoundError" in message:
            return "Import error. Check that the module exists and is in the Python path."
        elif "AttributeError" in message:
            return "Attribute error. Check that the object has the attribute you're trying to access."
        elif "TypeError" in message:
            return "Type error. Check the types of your arguments and return values."
        elif "ValueError" in message:
            return "Value error. Check that your values are valid for the operation."
        elif "KeyError" in message:
            return "Key error. Check that the key exists in the dictionary."
        elif "IndexError" in message:
            return "Index error. Check that the index is within the bounds of the list."
        elif "FileNotFoundError" in message:
            return "File not found. Check that the file exists and the path is correct."
        elif "PermissionError" in message:
            return "Permission error. Check that you have permission to access the file or resource."
        elif "TimeoutError" in message:
            return "Timeout error. Check that the operation doesn't take too long."
        
        return "Unknown error pattern."
    
    def _generate_recommendations(self, issues: List[Dict[str, Any]]) -> List[str]:
        """Generate recommendations based on test issues."""
        recommendations = []
        
        # Count issue types
        issue_types = {}
        for issue in issues:
            issue_type = issue["type"]
            issue_types[issue_type] = issue_types.get(issue_type, 0) + 1
        
        # Generate recommendations
        if issue_types.get("failure", 0) > 0:
            recommendations.append("Fix assertion failures by checking expected vs actual values.")
        
        if issue_types.get("error", 0) > 0:
            recommendations.append("Fix errors by checking exception messages and stack traces.")
        
        if len(issues) > 0:
            recommendations.append("Run tests individually to isolate issues.")
        
        return recommendations
    
    def _generate_test_content(self, module_name: str, classes: List[Dict[str, Any]], 
                              functions: List[str], source_file: str) -> str:
        """Generate test file content."""
        # Import statements
        content = f"""import unittest
from {module_name} import *

"""
        
        # Generate test class for each class
        for cls in classes:
            content += f"""class Test{cls['name']}(unittest.TestCase):
    \"\"\"Test cases for {cls['name']} class.\"\"\"
    
    def setUp(self):
        \"\"\"Set up test fixtures.\"\"\"
        pass
    
    def tearDown(self):
        \"\"\"Tear down test fixtures.\"\"\"
        pass
    
"""
            
            # Generate test methods
            for method in cls["methods"]:
                if method.startswith("_"):
                    continue
                    
                content += f"""    def test_{method}(self):
        \"\"\"Test {method} method.\"\"\"
        # TODO: Implement test
        self.assertTrue(True)
    
"""
            
            content += "\n"
        
        # Generate test functions
        if functions:
            content += f"""class TestFunctions(unittest.TestCase):
    \"\"\"Test cases for module functions.\"\"\"
    
    def setUp(self):
        \"\"\"Set up test fixtures.\"\"\"
        pass
    
    def tearDown(self):
        \"\"\"Tear down test fixtures.\"\"\"
        pass
    
"""
            
            for func in functions:
                if func.startswith("_"):
                    continue
                    
                content += f"""    def test_{func}(self):
        \"\"\"Test {func} function.\"\"\"
        # TODO: Implement test
        self.assertTrue(True)
    
"""
            
            content += "\n"
        
        # Add main block
        content += """if __name__ == '__main__':
    unittest.main()
"""
        
        return content