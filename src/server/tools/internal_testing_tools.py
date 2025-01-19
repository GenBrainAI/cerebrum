"""Internal testing tools."""
import os
import logging
import unittest
import importlib.util
import coverage
from io import StringIO
from typing import Dict, Any, Optional
from datetime import datetime
from .tools_metrics import ToolExecutionMetrics

logger = logging.getLogger(__name__)

class InternalTestingTools:
    """Tool for running tests and validating coverage."""
    
    def __init__(self):
        """Initialize testing tools."""
        self.test_runner = unittest.TextTestRunner(verbosity=2)
        self._execution_metrics = ToolExecutionMetrics()
        
    async def run_unit_tests(self, test_file_path: str) -> Dict[str, Any]:
        """Run unit tests from a file.
        
        Args:
            test_file_path: Path to the test file
            
        Returns:
            Dictionary containing test results
            
        Raises:
            FileNotFoundError: If the test file does not exist
            ImportError: If there is an error importing the test module
            RuntimeError: If there is an error running the tests
        """
        self._execution_metrics.start_time = datetime.now()
        self._execution_metrics.input_params = {"test_file_path": test_file_path}
        
        try:
            logger.info(f"Running tests from: {test_file_path}")
            
            if not os.path.exists(test_file_path):
                raise FileNotFoundError(f"Test file not found: {test_file_path}")
            
            # Import the test module
            spec = importlib.util.spec_from_file_location("test_module", test_file_path)
            if not spec or not spec.loader:
                raise ImportError(f"Could not load test module from {test_file_path}")
                
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            logger.info("Successfully imported test module")
            
            # Find and run tests
            loader = unittest.TestLoader()
            suite = loader.loadTestsFromModule(module)
            logger.info(f"Found {suite.countTestCases()} test cases")
            
            result = self.test_runner.run(suite)
            logger.info(f"Test execution completed: {result.testsRun} tests run")
            
            if result.failures or result.errors:
                raise RuntimeError(f"Tests failed: {len(result.failures)} failures, {len(result.errors)} errors")
            
            self._execution_metrics.success = True
            self._execution_metrics.output = {
                "run": result.testsRun,
                "failures": len(result.failures),
                "errors": len(result.errors),
                "skipped": len(result.skipped)
            }
            return {"results": self._execution_metrics.output}
            
        except FileNotFoundError as e:
            logger.error(f"Test file not found: {str(e)}")
            self._execution_metrics.success = False
            self._execution_metrics.error = str(e)
            raise
            
        except ImportError as e:
            logger.error(f"Error importing test module: {str(e)}")
            self._execution_metrics.success = False
            self._execution_metrics.error = str(e)
            raise
            
        except RuntimeError as e:
            logger.error(f"Test execution failed: {str(e)}")
            self._execution_metrics.success = False
            self._execution_metrics.error = str(e)
            raise
            
        except Exception as e:
            logger.error(f"Unexpected error running tests: {str(e)}")
            self._execution_metrics.success = False
            self._execution_metrics.error = str(e)
            raise
            
        finally:
            self._execution_metrics.end_time = datetime.now()
            
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