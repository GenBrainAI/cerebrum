from typing import List, Dict, Any
from uuid import UUID, uuid4
from ..components.tree_component import TreeNode

class ToolsTreeProvider:
    """Organizes tools catalog into tree structure."""
    
    def __init__(self, persistence_model):
        self.persistence_model = persistence_model
        
    def get_tools_tree(self) -> TreeNode:
        """Build tree structure from tools catalog."""
        # Create root node
        root = TreeNode(
            id=uuid4(),
            name="Tools Catalog",
            node_type="root"
        )
        
        # Create category nodes
        categories = {
            "api": TreeNode(id=uuid4(), name="API Tools", node_type="category"),
            "python": TreeNode(id=uuid4(), name="Python Tools", node_type="category"),
            "system": TreeNode(id=uuid4(), name="System Tools", node_type="category")
        }
        
        # Add tools to categories
        tools = self._get_tools()
        for tool in tools:
            category = categories.get(tool.get("category", "system"))
            if category:
                tool_node = TreeNode(
                    id=uuid4(),
                    name=tool["name"],
                    node_type="tool",
                    metadata=tool
                )
                category.children.append(tool_node)
                
        # Add categories to root
        root.children = list(categories.values())
        return root
        
    def _get_tools(self) -> List[Dict[str, Any]]:
        """Get tools from persistence model."""
        # TODO: Implement actual tool retrieval from persistence model
        tools = self.persistence_model.tools.list() if hasattr(self.persistence_model, 'tools') else []
        
        # Convert tools to dictionary format
        return [
            {
                "name": tool.name,
                "category": getattr(tool, "category", "system"),
                "description": getattr(tool, "description", ""),
                "type": getattr(tool, "type", "unknown")
            }
            for tool in tools
        ] or [
            {"name": "Sample API Tool", "category": "api"},
            {"name": "Sample Python Tool", "category": "python"}
        ]
