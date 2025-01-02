"""Internal file operation tools."""
import os
import logging
from typing import Dict, Any
from pathlib import Path

logger = logging.getLogger(__name__)

class InternalFileTools:
    """Tool for internal file operations."""
    
    def __init__(self, base_dir: str = "src/tools"):
        """Initialize file tools.
        
        Args:
            base_dir: Base directory for file operations
        """
        self.base_dir = base_dir
        os.makedirs(base_dir, exist_ok=True)
        
    def save_implementation(self, code: str, tool_name: str) -> Dict[str, Any]:
        """Save generated tool implementation to file.
        
        Args:
            code: The code to save
            tool_name: Name of the tool
            
        Returns:
            Dictionary containing status, message, and path
        """
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
            return {
                "status": "success",
                "message": f"Code saved to {file_path}",
                "path": file_path
            }
        except Exception as e:
            logger.error(f"Failed to save implementation: {str(e)}", exc_info=True)
            return {
                "status": "error",
                "message": f"Failed to save implementation: {str(e)}",
                "path": None
            }
            
    def save_tests(self, test_code: str, tool_name: str) -> Dict[str, Any]:
        """Save test code to file.
        
        Args:
            test_code: The test code to save
            tool_name: Name of the tool
            
        Returns:
            Dictionary containing status, message, and path
        """
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
            return {
                "status": "success",
                "message": f"Tests saved to {file_path}",
                "path": file_path
            }
        except Exception as e:
            logger.error(f"Failed to save tests: {str(e)}", exc_info=True)
            return {
                "status": "error",
                "message": f"Failed to save tests: {str(e)}",
                "path": None
            }
            
    async def read_documentation(self, file_path: str) -> Dict[str, Any]:
        """Read documentation from a file.
        
        Args:
            file_path: Path to the documentation file
            
        Returns:
            Dictionary containing file content
        """
        print(f"\n📖 Reading documentation from: {file_path}")
        try:
            with open(file_path, 'r') as f:
                content = f.read()
            print(f"✅ Successfully read documentation ({len(content)} chars)")
            return {"status": "success", "content": content}
        except Exception as e:
            error_msg = f"Error reading documentation: {str(e)}"
            logger.error(error_msg)
            print(f"❌ {error_msg}")
            return {"status": "error", "message": str(e)} 