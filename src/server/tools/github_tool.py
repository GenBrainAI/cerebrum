from typing import Optional, Any, Dict
from github import Github
from github.Repository import Repository
import inspect

class GithubTool:
    def __init__(self, access_token: str, repo_name: str):
        if access_token is None:
            raise ValueError("Access token cannot be None")
        if repo_name is None:
            raise ValueError("Repository name cannot be None")

        try:
            self.github = Github(access_token)
            self.repo = self.github.get_repo(repo_name)
        except Exception as e:
            print(f"Failed to initialize GitHub connection: {e}")
            raise

        print(f"GitHub connected to {self.repo.full_name} successfully")

        self.tools: Dict[str, Dict[str, Any]] = {}
        self._generate_tools()

    def _generate_tools(self):
        for name, method in inspect.getmembers(self.repo, predicate=inspect.ismethod):
            if not name.startswith('_'):  # Exclude private methods
                docstring = inspect.getdoc(method) or "No description available."
                signature = inspect.signature(method)
                
                parameters = []
                for param_name, param in signature.parameters.items():
                    if param_name != 'self':
                        param_desc = {
                            "name": param_name,
                            "type": str(param.annotation) if param.annotation != inspect.Parameter.empty else "Any",
                            "default": str(param.default) if param.default != inspect.Parameter.empty else None,
                        }
                        parameters.append(param_desc)

                self.tools[name] = {
                    "method": method,
                    "description": docstring,
                    "parameters": parameters
                }

    def get_tool_descriptions(self):
        return {name: {"description": info["description"], "parameters": info["parameters"]} 
                for name, info in self.tools.items()}

    async def __call__(self, method_name: str, arguments: Dict[str, Any]) -> Any:
        if method_name not in self.tools:
            raise ValueError(f"Method '{method_name}' not found.")
        
        method = self.tools[method_name]["method"]
        return method(**arguments)