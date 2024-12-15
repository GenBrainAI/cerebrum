# src/server/views/controllers/tools_view_controller.py
from typing import Optional, Dict, Any
from uuid import UUID
from ..models.view_state import ViewState
from ..models.view_types import ViewType
from ..data.tools_tree_provider import ToolsTreeProvider
from ..components.dialogs.tool_dialog import ToolDialog
from ..state.state_manager import ViewStateManager
from ..components.tree_component import TreeNode

class ToolsCatalogController:
    """Controller for tools catalog view."""
    
    def __init__(self, persistence_model):
        self.persistence_model = persistence_model
        self.view_state = ViewState(view_type=ViewType.TOOLS_CATALOG)
        self.tree_provider = ToolsTreeProvider(persistence_model)
        self.state_manager = ViewStateManager(persistence_model)
        
    async def get_tools_tree(self) -> Optional[TreeNode]:
        """Get tools catalog as tree structure."""
        try:
            # Get all tools from persistence model
            tools = self.persistence_model.tools.list() if hasattr(self.persistence_model, 'tools') else []
            
            # Create root node
            root = TreeNode(UUID('00000000-0000-0000-0000-000000000000'), "Tools", "root")
            
            # Create category nodes
            categories = {
                "api": TreeNode(UUID('11111111-1111-1111-1111-111111111111'), "API Tools", "category"),
                "local": TreeNode(UUID('22222222-2222-2222-2222-222222222222'), "Local Tools", "category"),
                "custom": TreeNode(UUID('33333333-3333-3333-3333-333333333333'), "Custom Tools", "category")
            }
            
            # Add categories to root
            for category in categories.values():
                root.children.append(category)
            
            # Add tools to appropriate categories
            for tool in tools:
                tool_type = tool.metadata.get('type', 'custom')
                node = TreeNode(UUID(tool.id), tool.name, "tool")
                if tool_type in categories:
                    categories[tool_type].children.append(node)
                else:
                    categories['custom'].children.append(node)
            
            return root
        except Exception as e:
            print(f"Error building tools tree: {str(e)}")
            return None
        
    async def handle_chat(self, message: str) -> str:
        """Process chat messages for tools management."""
        try:
            # Add message to chat history
            self.view_state.chat_history.append({
                "role": "user",
                "content": message
            })
            
            # TODO: Implement tools management logic
            response = await self._process_tool_command(message)
            
            # Add response to chat history
            self.view_state.chat_history.append({
                "role": "assistant",
                "content": response
            })
            
            # Save state
            self.state_manager.save_state(ViewType.TOOLS_CATALOG, self.view_state)
            
            return response
            
        except Exception as e:
            return f"Error processing message: {str(e)}"
            
    def show_tool_dialog(self) -> Optional[Dict[str, Any]]:
        """Show dialog for adding/configuring tools."""
        dialog = ToolDialog(self.view_state, self.persistence_model)
        result = dialog.render()
        
        if result:
            # TODO: Implement tool creation/configuration
            if hasattr(self.persistence_model, 'tools'):
                return self.persistence_model.tools.create(result)
        return None
        
    async def _process_tool_command(self, message: str) -> str:
        """Process tool management commands."""
        # TODO: Implement natural language command processing
        return "Tool management commands not yet implemented"
        
    def handle_node_click(self, node: TreeNode):
        """Handle tree node click events."""
        self.view_state.selected_node = node.id
        if node.type == "tool":
            # Show tool configuration dialog
            self.show_tool_dialog()