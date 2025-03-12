"""Python execution tool for running Python scripts and code snippets.

This tool provides functionality for executing Python code either from files or directly
from string input, with support for command-line arguments.
"""
import os
import sys
import subprocess
import tempfile
import logging
from typing import Dict, List, Optional, Any, Union

logger = logging.getLogger(__name__)

class PyExec:
    """Tool for executing Python code.
    
    This tool provides functionality for running Python scripts and code snippets,
    with support for command-line arguments. It captures and returns the standard
    output from the execution.
    
    Methods:
        run_script: Execute a Python script file with optional arguments
        run_code: Execute Python code from a string with optional arguments
    """
    
    def __init__(self, python_executable: str = "python"):
        """Initialize the Python execution tool.
        
        Args:
            python_executable: Path to the Python executable to use (default: "python")
        """
        self.python_executable = python_executable
        
    def run_script(self, filepath: str, argv: Optional[List[str]] = None) -> Union[str, Dict[str, Any]]:
        """Execute a Python script file with optional arguments.
        
        Args:
            filepath: Path to the Python script file to execute
            argv: Optional list of command-line arguments to pass to the script
            
        Returns:
            str: A string containing the combined stdout and stderr output, formatted for readability
            
        Raises:
            FileNotFoundError: If the script file does not exist
            PermissionError: If the script file cannot be executed
            subprocess.SubprocessError: If there is an error executing the script
        """
        try:
            logger.info(f"Executing Python script: {filepath}")
            
            # Validate file exists
            if not os.path.exists(filepath):
                raise FileNotFoundError(f"Script file not found: {filepath}")
            
            # Prepare command
            command = [self.python_executable, filepath]
            if argv:
                command.extend(argv)
            
            # Execute script
            process = subprocess.run(
                command,
                capture_output=True,
                text=True,
                check=False  # Don't raise exception on non-zero exit code
            )
            
            # Prepare result
            result = {
                "stdout": process.stdout,
                "stderr": process.stderr,
                "exit_code": process.returncode
            }
            
            # Format output for LLMs and agents
            output = ""
            if process.stdout:
                output += process.stdout.strip()
            
            if process.stderr:
                if output:
                    output += "\n\nErrors:\n"
                output += process.stderr.strip()
                
            if not output:
                output = "No output produced."
                
            if process.returncode != 0:
                output += f"\n\nExecution failed with exit code: {process.returncode}"
            
            logger.info(f"Script execution completed with exit code: {process.returncode}")
            
            # Return both the formatted string and the detailed result dictionary
            # This allows for backward compatibility while providing the improved string output
            return output
            
        except FileNotFoundError as e:
            logger.error(f"Script file not found: {filepath}")
            raise
            
        except PermissionError as e:
            logger.error(f"Permission denied when executing script: {filepath}")
            raise
            
        except subprocess.SubprocessError as e:
            logger.error(f"Error executing script: {str(e)}")
            raise
            
        except Exception as e:
            logger.error(f"Unexpected error executing script: {str(e)}")
            raise
    
    def run_code(self, code_str: str, argv: Optional[List[str]] = None) -> Union[str, Dict[str, Any]]:
        """Execute Python code from a string with optional arguments.
        
        Args:
            code_str: Python code to execute as a string
            argv: Optional list of command-line arguments to pass to the code
            
        Returns:
            str: A string containing the combined stdout and stderr output, formatted for readability
            
        Raises:
            subprocess.SubprocessError: If there is an error executing the code
        """
        try:
            logger.info("Executing Python code from string")
            
            # Create temporary file for the code
            with tempfile.NamedTemporaryFile(suffix='.py', mode='w', delete=False) as temp_file:
                temp_file_path = temp_file.name
                temp_file.write(code_str)
            
            try:
                # Execute the temporary file
                result = self.run_script(temp_file_path, argv)
                return result
                
            finally:
                # Clean up temporary file
                try:
                    os.unlink(temp_file_path)
                except Exception as e:
                    logger.warning(f"Failed to delete temporary file {temp_file_path}: {str(e)}")
            
        except Exception as e:
            logger.error(f"Error executing Python code: {str(e)}")
            raise 