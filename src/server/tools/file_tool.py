from typing import Callable, Any
from crewai_tools import BaseTool

class FileTool(BaseTool):
    name: str = "file_tool"
    description: str = "Saves and reads files"

    def __call__(self, **kwargs):
        """Make the tool directly callable."""
        return self._run(**kwargs)

    def _run(self, file_path: str, file_content: str) -> str:
        """Save content to a file.
        
        Args:
            file_path: Path where to save the file
            file_content: Content to write to the file
            
        Returns:
            Confirmation message with the file path
        """
        try:
            # Write content to the file
            with open(file_path, 'w') as file:
                file.write(file_content)

            return f"File written: {file_path}"
        except Exception as e:
            return f"Error writing file: {str(e)}"
def save_file(file_path: str, file_content: str) -> str:

    # Write content to the file
    with open(file_path, 'w') as file:
        file.write(file_content)

    print(f"File written: {file_path}")
    return f"File written: {file_path}"