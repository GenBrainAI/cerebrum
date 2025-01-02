"""Tools for managing persistence operations."""
import logging
from typing import Dict, Any, Optional
from .in_memory_persistence import InMemoryPersistenceModel
from ..models.toolset import Tool

logger = logging.getLogger(__name__)

class PersistenceTools:
    """Tool for managing persistence operations."""
    
    def __init__(self, persistence_model: Optional[InMemoryPersistenceModel] = None):
        """Initialize persistence tools.
        
        Args:
            persistence_model: Optional persistence model to use
        """
        self.persistence_model = persistence_model
        
    def save_tool(self, tool_model: Tool) -> Dict[str, Any]:
        """Save a Tool model to the persistence model.
        
        Args:
            tool_model: The Tool model to save
            
        Returns:
            Dictionary containing status and saved tool
        """
        try:
            logger.info(f"Attempting to save tool model: {tool_model.function.name}")
            
            if self.persistence_model is None:
                self.persistence_model = InMemoryPersistenceModel()
                logger.info("Created new InMemoryPersistenceModel")
            
            # Save the tool
            saved_tool = self.persistence_model.tools.create(tool_model)
            logger.info(f"Successfully saved tool: {saved_tool.function.name}")
            
            return {
                "status": "success",
                "message": f"Tool {tool_model.function.name} saved successfully",
                "tool": saved_tool
            }
        except Exception as e:
            logger.error(f"Failed to save tool: {str(e)}", exc_info=True)
            return {
                "status": "error",
                "message": f"Failed to save tool: {str(e)}",
                "tool": None
            } 