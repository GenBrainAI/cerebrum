"""Internal file operation tools."""
import os
import logging
from typing import Dict, Any
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