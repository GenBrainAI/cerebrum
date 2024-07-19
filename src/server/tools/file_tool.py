from datetime import datetime

from crewai_tools import BaseTool


class FileTool(BaseTool):
    name: str = "File Tool"
    description: str = "A tool to write files of a certain type"
    def _run(self, content: str, type: str) -> str:
        # Determine file extension based on type
        extension_map = {
            'text': '.txt',
            'markdown': '.md',
            'html': '.html'
        }
        extension = extension_map.get(type, '.txt')

        # Create a unique file name
        file_name = f"{datetime.now().strftime('%Y%m%d%H%M%S')}{extension}"

        # Write content to the file
        with open(file_name, 'w') as file:
            file.write(content)

        return f"File written: {file_name}"