from typing import Callable

from src.server.controllers.curried_proxy import PythonFunctionTool


class FileTool(PythonFunctionTool):
    @staticmethod
    def save_file(file_path: str, file_content: str) -> str:

        # Write content to the file
        with open(file_path, 'w') as file:
            file.write(file_content)

        print(f"File written: {file_path}")
        return f"File written: {file_path}"

    description: str = "creates a txt, .md or .html file and stores the content on the given path with the given name"
    name: str = "file_tool"
    function: Callable = save_file
