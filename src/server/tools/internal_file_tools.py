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
        
    def save_implementation(self, code: str, tool_name: str) -> Dict[str, str]:
        """Save generated tool implementation to file."""
        try:
            # Ensure the tool name has a .py extension but not double extension
            if not tool_name.endswith('.py'):
                tool_name = f"{tool_name}.py"
            tool_name = tool_name.replace('.py.py', '.py')
            
            # Construct the correct path in src/tools directory
            file_path = os.path.join('src', 'tools', tool_name)
            
            # Create directories if they don't exist
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            # Save the file
            with open(file_path, 'w') as f:
                f.write(code)
            
            return {'file_path': file_path}
        except Exception as e:
            logger.error(f"Error saving implementation: {str(e)}")
            raise

    def save_tests(self, code: str, tool_name: str) -> Dict[str, str]:
        """Save generated test code to file."""
        try:
            # Ensure the tool name has correct test prefix and .py extension
            base_name = tool_name.replace('.py', '').replace('test_', '')
            test_file_name = f"test_{base_name}.py"
            
            # Construct the correct path in src/tools/tests directory
            file_path = test_file_name
            
            # Create directories if they don't exist
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            # Save the file
            with open(file_path, 'w') as f:
                f.write(code)
            
            return {'file_path': file_path}
        except Exception as e:
            logger.error(f"Error saving tests: {str(e)}")
            raise