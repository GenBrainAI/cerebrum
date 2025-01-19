"""Internal file operation tools."""
import os
import logging
from typing import Dict, Any
from pathlib import Path
from datetime import datetime
from .tools_metrics import ToolExecutionMetrics

logger = logging.getLogger(__name__)

class InternalFileTools:
    """Tool for internal file operations."""
    
    def __init__(self, base_dir: str = "src/tools"):
        """Initialize file tools.
        
        Args:
            base_dir: Base directory for file operations
        """
        self.base_dir = base_dir
        self._execution_metrics = ToolExecutionMetrics()
        os.makedirs(base_dir, exist_ok=True)
        
    async def read_documentation(self, file_path: str) -> Dict[str, Any]:
        """Read documentation files.
        
        Args:
            file_path: Path to the documentation file
            
        Returns:
            Dictionary containing file contents
            
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
            Dictionary containing path to saved file
            
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
            
            logger.info(f"Target file path: {file_path}")
            # Create the directory if it doesn't exist
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            # Save the code
            with open(file_path, 'w') as f:
                f.write(code)
            
            logger.info(f"Successfully saved implementation to: {file_path}")
            self._execution_metrics.success = True
            self._execution_metrics.output = file_path
            return {"path": file_path}
            
        except IOError as e:
            logger.error(f"Failed to save implementation: {str(e)}")
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
        
    async def save_tests(self, test_code: str, tool_name: str) -> Dict[str, Any]:
        """Save test code to file.
        
        Args:
            test_code: The test code to save
            tool_name: Name of the tool
            
        Returns:
            Dictionary containing path to saved file
            
        Raises:
            IOError: If there is an error saving the file
        """
        self._execution_metrics.start_time = datetime.now()
        self._execution_metrics.input_params = {"test_code": test_code, "tool_name": tool_name}
        
        try:
            logger.info(f"Attempting to save tests for tool: {tool_name}")
            # Create a valid filename from the tool name
            filename = f"test_{tool_name.lower().replace(' ', '_')}.py"
            test_dir = os.path.join(self.base_dir, "tests")
            file_path = os.path.join(test_dir, filename)
            
            logger.info(f"Target test file path: {file_path}")
            # Create the test directory if it doesn't exist
            os.makedirs(test_dir, exist_ok=True)
            
            # Save the test code
            with open(file_path, 'w') as f:
                f.write(test_code)
            
            logger.info(f"Successfully saved tests to: {file_path}")
            self._execution_metrics.success = True
            self._execution_metrics.output = file_path
            return {"path": file_path}
            
        except IOError as e:
            logger.error(f"Failed to save tests: {str(e)}")
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