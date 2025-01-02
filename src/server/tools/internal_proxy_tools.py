"""Internal proxy tools."""
import logging
from typing import Dict, Any, Set

logger = logging.getLogger(__name__)

class InternalProxyTools:
    """Tool for managing dynamic tool registration."""
    
    def __init__(self):
        """Initialize proxy tools."""
        self.registered_tools: Set[str] = set()

    async def register_tool(self, tool_name: str, tool_instance: Any) -> Dict[str, Any]:
        """Register a tool with the global CurriedProxy.
        
        Args:
            tool_name: Name to register the tool under
            tool_instance: The tool instance to register
            
        Returns:
            Dictionary containing registration status
        """
        try:
            logger.info(f"Attempting to register tool: {tool_name}")
            from server.controllers.curried_proxy import global_proxy
            
            # Register the tool
            global_proxy.add_tool(tool_name, tool_instance)
            self.registered_tools.add(tool_name)
            
            logger.info(f"Successfully registered tool: {tool_name}")
            return {
                "status": "success",
                "message": f"Tool {tool_name} registered successfully"
            }
        except Exception as e:
            logger.error(f"Error registering tool: {str(e)}", exc_info=True)
            return {
                "status": "error",
                "message": str(e)
            } 