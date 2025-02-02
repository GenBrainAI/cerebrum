"""Internal tools for file operations, credentials management, testing, and proxy management."""
import os
import logging
import unittest
import importlib.util
import coverage
import dotenv
from io import StringIO
from typing import Dict, Any, Optional, Set
from pathlib import Path
from datetime import datetime
from .tools_metrics import ToolExecutionMetrics

logger = logging.getLogger(__name__)

class InternalFileTools:
    """Tool for internal file operations.
    
    This tool provides functionality for reading documentation and saving generated code.
    It handles file operations with proper error handling and metrics tracking.
    
    Methods:
        read_documentation: Read documentation from a file
        save_implementation: Save generated tool implementation to file
        save_tests: Save generated test code to file
    """
    
    def __init__(self, base_dir: str = "src/tools"):
        """Initialize file tools.
        
        Args:
            base_dir: Base directory for file operations
        """
        self.base_dir = base_dir
        self._execution_metrics = ToolExecutionMetrics()
        os.makedirs(base_dir, exist_ok=True)
        
    async def read_documentation(self, file_path: str) -> Dict[str, Any]:
        """Read documentation from a file.
        
        Args:
            file_path: Path to the documentation file to read
            
        Returns:
            Dict[str, Any]: Dictionary containing:
                - content: The contents of the documentation file
            
        Raises:
            FileNotFoundError: If the file does not exist
            IOError: If there is an error reading the file
        """
        self._execution_metrics.start_time = datetime.now()
        self._execution_metrics.input_params = {"file_path": file_path}
        
        try:
            logger.info(f"Reading documentation from: {file_path}")
            with open(file_path, 'r') as f:
                content = f.read()
            
            logger.info(f"Successfully read documentation from: {file_path}")
            self._execution_metrics.success = True
            self._execution_metrics.output = content
            return {"content": content}
            
        except FileNotFoundError as e:
            logger.error(f"Documentation file not found: {file_path}")
            self._execution_metrics.success = False
            self._execution_metrics.error = str(e)
            raise
            
        except IOError as e:
            logger.error(f"Error reading documentation: {str(e)}")
            self._execution_metrics.success = False
            self._execution_metrics.error = str(e)
            raise
            
        except Exception as e:
            logger.error(f"Unexpected error reading documentation: {str(e)}")
            self._execution_metrics.success = False
            self._execution_metrics.error = str(e)
            raise
            
        finally:
            self._execution_metrics.end_time = datetime.now()
        
    async def save_implementation(self, code: str, tool_name: str) -> Dict[str, Any]:
        """Save generated tool implementation to file.
        
        Args:
            code: The code to save
            tool_name: Name of the tool
            
        Returns:
            Dict[str, Any]: Dictionary containing:
                - file_path: Path to the saved file
            
        Raises:
            IOError: If there is an error saving the file
        """
        self._execution_metrics.start_time = datetime.now()
        self._execution_metrics.input_params = {"code": code, "tool_name": tool_name}
        
        try:
            logger.info(f"Attempting to save implementation for tool: {tool_name}")
            # Create a valid filename from the tool name
            filename = f"{tool_name.lower().replace(' ', '_')}.py"
            file_path = os.path.join(self.base_dir, filename)
            
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            # Save the code
            with open(file_path, 'w') as f:
                f.write(code)
                
            logger.info(f"Successfully saved implementation to: {file_path}")
            self._execution_metrics.success = True
            self._execution_metrics.output = file_path
            return {"file_path": file_path}
            
        except IOError as e:
            logger.error(f"Error saving implementation: {str(e)}")
            self._execution_metrics.success = False
            self._execution_metrics.error = str(e)
            raise
            
        except Exception as e:
            logger.error(f"Unexpected error saving implementation: {str(e)}")
            self._execution_metrics.success = False
            self._execution_metrics.error = str(e)
            raise
            
        finally:
            self._execution_metrics.end_time = datetime.now()
            
    async def save_tests(self, code: str, tool_name: str) -> Dict[str, Any]:
        """Save generated test code to file.
        
        Args:
            code: The test code to save
            tool_name: Name of the tool
            
        Returns:
            Dict[str, Any]: Dictionary containing:
                - file_path: Path to the saved test file
            
        Raises:
            IOError: If there is an error saving the file
        """
        self._execution_metrics.start_time = datetime.now()
        self._execution_metrics.input_params = {"code": code, "tool_name": tool_name}
        
        try:
            logger.info(f"Attempting to save tests for tool: {tool_name}")
            # Create a valid filename from the tool name
            filename = f"test_{tool_name.lower().replace(' ', '_')}.py"
            file_path = os.path.join(self.base_dir, "tests", filename)
            
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            # Save the code
            with open(file_path, 'w') as f:
                f.write(code)
                
            logger.info(f"Successfully saved tests to: {file_path}")
            self._execution_metrics.success = True
            self._execution_metrics.output = file_path
            return {"file_path": file_path}
            
        except IOError as e:
            logger.error(f"Error saving tests: {str(e)}")
            self._execution_metrics.success = False
            self._execution_metrics.error = str(e)
            raise
            
        except Exception as e:
            logger.error(f"Unexpected error saving tests: {str(e)}")
            self._execution_metrics.success = False
            self._execution_metrics.error = str(e)
            raise
            
        finally:
            self._execution_metrics.end_time = datetime.now()

class InternalCredentialsTools:
    """Tool for managing project credentials.
    
    This tool provides functionality for loading and validating credentials.
    It handles credential file operations with proper error handling and validation.
    
    Methods:
        load_credentials: Load credentials from .env file
        validate_credentials: Validate that required credentials are present
    """
    
    def __init__(self, env_path: str = None):
        """Initialize credentials tools.
        
        Args:
            env_path: Path to the .env file
        """
        project_root = str(Path(__file__).parents[2])
        self.env_path = env_path or os.path.join(project_root, '.env')
        self._execution_metrics = ToolExecutionMetrics()

    async def load_credentials(self) -> Dict[str, Any]:
        """Load credentials from .env file.
        
        Returns:
            Dict[str, Any]: Dictionary containing:
                - credentials: Dictionary of loaded credentials
            
        Raises:
            FileNotFoundError: If the .env file does not exist
            IOError: If there is an error reading the file
        """
        self._execution_metrics.start_time = datetime.now()
        self._execution_metrics.input_params = {"env_path": self.env_path}
        
        try:
            logger.info(f"Loading credentials from: {self.env_path}")
            if not os.path.exists(self.env_path):
                raise FileNotFoundError(f".env file not found at {self.env_path}")
                
            creds = dotenv.dotenv_values(self.env_path)
            logger.info("Successfully loaded credentials")
            
            self._execution_metrics.success = True
            self._execution_metrics.output = "Credentials loaded successfully"
            return {"credentials": creds}
            
        except FileNotFoundError as e:
            logger.error(f"Credentials file not found: {str(e)}")
            self._execution_metrics.success = False
            self._execution_metrics.error = str(e)
            raise
            
        except Exception as e:
            logger.error(f"Error loading credentials: {str(e)}")
            self._execution_metrics.success = False
            self._execution_metrics.error = str(e)
            raise
            
        finally:
            self._execution_metrics.end_time = datetime.now()

    async def validate_credentials(self, credentials: Dict[str, str]) -> Dict[str, Any]:
        """Validate that required credentials are present.
        
        Args:
            credentials: Dictionary of credentials to validate
            
        Returns:
            Dict[str, Any]: Dictionary containing:
                - message: Validation status message
            
        Raises:
            ValueError: If required credentials are missing
        """
        self._execution_metrics.start_time = datetime.now()
        self._execution_metrics.input_params = {"credentials": credentials}
        
        try:
            logger.info("Validating credentials")
            required_keys = ['API_KEY', 'DATABASE_URL']
            missing = [key for key in required_keys if key not in credentials]
            
            if missing:
                raise ValueError(f"Missing required credentials: {', '.join(missing)}")
                
            logger.info("All required credentials present")
            self._execution_metrics.success = True
            self._execution_metrics.output = "All required credentials present"
            return {"message": "All required credentials present"}
            
        except ValueError as e:
            logger.error(f"Validation error: {str(e)}")
            self._execution_metrics.success = False
            self._execution_metrics.error = str(e)
            raise
            
        except Exception as e:
            logger.error(f"Unexpected error validating credentials: {str(e)}")
            self._execution_metrics.success = False
            self._execution_metrics.error = str(e)
            raise
            
        finally:
            self._execution_metrics.end_time = datetime.now()

class InternalTestingTools:
    """Tool for running tests and validating coverage.
    
    This tool provides functionality for running unit tests and validating test coverage.
    It handles test execution with proper error handling and metrics tracking.
    
    Methods:
        run_unit_tests: Run unit tests from a file
        validate_test_coverage: Validate test coverage for a file
    """
    
    def __init__(self):
        """Initialize testing tools."""
        self.test_runner = unittest.TextTestRunner(verbosity=2)
        self._execution_metrics = ToolExecutionMetrics()
        
    async def run_unit_tests(self, test_file_path: str) -> Dict[str, Any]:
        """Run unit tests from a file.
        
        Args:
            test_file_path: Path to the test file
            
        Returns:
            Dict[str, Any]: Dictionary containing:
                - results: Dictionary with test execution results
                    - run: Number of tests run
                    - failures: Number of test failures
                    - errors: Number of test errors
                    - skipped: Number of skipped tests
            
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
            
    async def validate_test_coverage(self, test_file_path: str) -> Dict[str, Any]:
        """Validate test coverage for a file.
        
        Args:
            test_file_path: Path to the test file
            
        Returns:
            Dict[str, Any]: Dictionary containing:
                - coverage: Dictionary with coverage results
                    - total: Total coverage percentage
                    - missing: List of uncovered lines
                    - covered: List of covered lines
            
        Raises:
            FileNotFoundError: If the test file does not exist
            ImportError: If there is an error importing the test module
            RuntimeError: If there is an error running coverage
        """
        self._execution_metrics.start_time = datetime.now()
        self._execution_metrics.input_params = {"test_file_path": test_file_path}
        
        try:
            logger.info(f"Validating coverage for: {test_file_path}")
            
            if not os.path.exists(test_file_path):
                raise FileNotFoundError(f"Test file not found: {test_file_path}")
            
            # Create coverage object
            cov = coverage.Coverage()
            cov.start()
            
            # Import and run the test module
            spec = importlib.util.spec_from_file_location("test_module", test_file_path)
            if not spec or not spec.loader:
                raise ImportError(f"Could not load test module from {test_file_path}")
                
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            # Stop coverage and get results
            cov.stop()
            cov.save()
            
            # Get coverage data
            total = cov.report(file=StringIO())
            analysis = cov.analysis2()
            
            coverage_data = {
                "total": total,
                "missing": analysis[3],
                "covered": analysis[2]
            }
            
            logger.info(f"Coverage analysis completed: {total}% coverage")
            self._execution_metrics.success = True
            self._execution_metrics.output = coverage_data
            return {"coverage": coverage_data}
            
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
            
        except Exception as e:
            logger.error(f"Unexpected error validating coverage: {str(e)}")
            self._execution_metrics.success = False
            self._execution_metrics.error = str(e)
            raise
            
        finally:
            self._execution_metrics.end_time = datetime.now()

class InternalProxyTools:
    """Tool for managing dynamic tool registration.
    
    This tool provides functionality for registering tools with the global CurriedProxy.
    It handles tool registration with proper error handling and tracking.
    
    Methods:
        register_tool: Register a tool with the global CurriedProxy
    """
    
    def __init__(self):
        """Initialize proxy tools."""
        self.registered_tools: Set[str] = set()

    async def register_tool(self, tool_name: str, tool_instance: Any) -> Dict[str, Any]:
        """Register a tool with the global CurriedProxy.
        
        Args:
            tool_name: Name to register the tool under
            tool_instance: The tool instance to register
            
        Returns:
            Dict[str, Any]: Dictionary containing:
                - status: Registration status ('success' or 'error')
                - message: Status message
            
        Raises:
            ValueError: If the tool registration fails
        """
        try:
            logger.info(f"Attempting to register tool: {tool_name}")
            from server.controllers.curried_proxy import global_proxy
            
            # Register the tool
            global_proxy.add_tool(tool_name, tool_instance)
            self.registered_tools.add(tool_name)
            
            logger.info(f"Successfully registered tool: {tool_name}")
            return {
                "status": "success",
                "message": f"Tool {tool_name} registered successfully"
            }
        except Exception as e:
            logger.error(f"Error registering tool: {str(e)}", exc_info=True)
            return {
                "status": "error",
                "message": str(e)
            }