from typing import Dict, Type, Any, List
from src.server.controllers.curried_proxy import CurriedProxy
from src.server.tools.file_tool import FileTool
from src.server.tools.github_tool import GitHubTool

class ToolFactory:
    # Class-level tools registry
    TOOLS: Dict[str, Any] = {
        'save_file': FileTool,
        'TestClassTool': lambda: None,  # Placeholder for test tool
        # Add other tools here
    }

    def __init__(self, name: str, curried_proxy: CurriedProxy):
        if name not in self.TOOLS:
            raise ValueError(f"Unknown tool: {name}")
        self.name = name
        self.curried_proxy = curried_proxy
        self.tool = self.TOOLS[name]

    def set_curried_proxy(self) -> None:
        """Add the tool to the curried proxy."""
        return self.curried_proxy.add_tool(self.name, self.tool())

    @classmethod
    def register_tool(cls, name: str, tool_class: Any) -> None:
        """Register a new tool class."""
        cls.TOOLS[name] = tool_class

    @classmethod
    def get_available_tools(cls) -> List[str]:
        """Get list of available tool names."""
        return list(cls.TOOLS.keys())