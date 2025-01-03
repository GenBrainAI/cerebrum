"""Internal testing tools."""
import os
import logging
import unittest
import importlib.util
import coverage
from io import StringIO
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class InternalTestingTools:
    """Tool for running tests and validating coverage."""
    
    def __init__(self):
        """Initialize testing tools."""
        self.test_runner = unittest.TextTestRunner(verbosity=2)
        
    def run_unit_tests(self, test_file_path: str) -> Dict[str, Any]:
        """Run unit tests and get results.
        
        Args:
            test_file_path: Path to the test file
            
        Returns:
            Dictionary containing test results
        """
        try:
            logger.info(f"Attempting to run tests from file: {test_file_path}")
            
            if not os.path.exists(test_file_path):
                logger.error(f"Test file not found: {test_file_path}")
                return {
                    "status": "error",
                    "message": f"Test file not found: {test_file_path}",
                    "results": None
                }
                
            logger.info(f"Loading test module from: {test_file_path}")
            # Load the test module
            spec = importlib.util.spec_from_file_location("test_module", test_file_path)
            if spec is None:
                logger.error(f"Failed to create module spec for: {test_file_path}")
                return {
                    "status": "error",
                    "message": "Failed to create module spec",
                    "results": None
                }
                
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            logger.info(f"Successfully loaded test module: {module.__name__}")
            
            # Find and run tests
            loader = unittest.TestLoader()
            suite = loader.loadTestsFromModule(module)
            logger.info(f"Found {suite.countTestCases()} test cases")
            
            result = self.test_runner.run(suite)
            logger.info(f"Test execution completed: {result.testsRun} tests run")
            
            return {
                "status": "success",
                "message": "Tests executed successfully",
                "results": {
                    "run": result.testsRun,
                    "failures": len(result.failures),
                    "errors": len(result.errors),
                    "skipped": len(result.skipped)
                }
            }
        except Exception as e:
            logger.error(f"Error running tests: {str(e)}", exc_info=True)
            return {
                "status": "error",
                "message": f"Failed to run tests: {str(e)}",
                "results": None
            }
            
    def validate_test_coverage(self, test_file_path: str) -> Dict[str, Any]:
        """Calculate test coverage.
        
        Args:
            test_file_path: Path to the test file
            
        Returns:
            Dictionary containing coverage results
        """
        try:
            if not os.path.exists(test_file_path):
                return {
                    "status": "error",
                    "message": f"Test file not found: {test_file_path}",
                    "coverage": None
                }
                
            # Initialize coverage
            cov = coverage.Coverage()
            cov.start()
            
            # Run the tests
            test_result = self.run_unit_tests(test_file_path)
            
            # Stop coverage
            cov.stop()
            cov.save()
            
            # Get coverage report
            report = StringIO()
            cov.report(file=report)
            coverage_output = report.getvalue()
            
            return {
                "status": "success",
                "message": "Coverage analysis completed",
                "coverage": {
                    "report": coverage_output,
                    "test_results": test_result["results"]
                }
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to analyze coverage: {str(e)}",
                "coverage": None
            } 