from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, List

class CurriedProxy(BaseModel):
    """Model for a curried proxy that can export tools to CrewAI."""
    id: Optional[str] = None
    name: Optional[str] = None
    description: Optional[str] = None
    tools: Dict[str, Any] = Field(default_factory=dict)
    
    def register_tool(self, name: str, tool: Any) -> None:
        """Register a tool with this proxy.
        
        Args:
            name: The name of the tool
            tool: The tool instance
        """
        self.tools[name] = tool
    
    async def execute(self, tool_name: str, args: Dict[str, Any]) -> Any:
        """Execute a tool with the given name and arguments.
        
        Args:
            tool_name: The name of the tool to execute
            args: The arguments to pass to the tool
            
        Returns:
            The result of the tool execution
            
        Raises:
            KeyError: If the tool is not found
            Exception: If the tool execution fails
        """
        if tool_name not in self.tools:
            raise KeyError(f"Tool {tool_name} not found")
        
        tool = self.tools[tool_name]
        return await tool(**args)
    
    def export_to_crewai(self) -> List[Any]:
        """Export tools in a format compatible with CrewAI."""
        return list(self.tools.values())
        
    def to_info(self) -> 'CurriedProxy':
        """Get a copy of this proxy with only basic info."""
        return CurriedProxy(
            id=self.id,
            name=self.name,
            description=self.description
        ) 