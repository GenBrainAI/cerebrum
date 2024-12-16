# src/server/views/controllers/tools_view_controller.py
from typing import Optional, Dict, Any, List
from uuid import UUID
from datetime import datetime
from ...models.exceptions import StateError, StateNotFoundError
from ...models.tool import Tool
from ..models.view_state import ViewState
from ..models.view_types import ViewType
from ...models.specialized_state import StateType, ToolManagementState
from ..data.tools_tree_provider import ToolsTreeProvider
from ..components.dialogs.tool_dialog import ToolDialog
from ..state.state_manager import ViewStateManager
from ..components.tree_component import TreeNode
from ...utils.state_loader import StateLoader

class ToolsCatalogController:
    """Controller for tools catalog view with specialized state support."""
    
    def __init__(self, persistence_model):
        self.persistence_model = persistence_model
        self.view_state = ViewState(view_type=ViewType.TOOLS_CATALOG)
        self.tree_provider = ToolsTreeProvider(persistence_model)
        self.state_manager = ViewStateManager(persistence_model)
        self.tool_state: Optional[ToolManagementState] = None
        
        # Load existing state
        state_ids = StateLoader.get_state_ids("tools_management")
        if state_ids:
            self.tools_manager_id = state_ids["tools_manager_id"]
            self.task_id = state_ids["task_id"]
        
    async def initialize(self):
        """Initialize controller with specialized state."""
        # Try to load existing state first
        state_file = StateLoader.get_state_file("tools_management")
        if state_file and state_file.exists():
            self.tool_state = await self.state_manager.load_specialized_state(state_file)
        
        # Create new state if none exists
        if not self.tool_state:
            self.tool_state = await self.state_manager.create_specialized_state(
                state_type=StateType.TOOL_MANAGEMENT,
                name="Tool Management State",
                initial_data={
                    "active_view": ViewType.TOOLS_CATALOG.value,
                    "selected_tool": None,
                    "active_tools": []
                }
            )
    
    async def get_tools_tree(self) -> Optional[TreeNode]:
        """Get tools catalog as tree structure with state tracking."""
        try:
            tools = self.persistence_model.tools.list()
            
            # Update tool state
            if self.tool_state:
                self.tool_state.active_tools = [tool.id for tool in tools]
                await self.state_manager._persist_specialized_state(self.tool_state)
            
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
            
    async def handle_chat(self, message: str) -> None:
        """Handle chat messages with state tracking."""
        try:
            response = await self._process_tool_command(message)
            self.view_state.add_message("user", message)
            self.view_state.add_message("assistant", response)
        except Exception as e:
            error_msg = f"Error processing message: {str(e)}"
            self.view_state.add_message("assistant", error_msg)
            
    async def _process_tool_command(self, message: str) -> str:
        """Process tool management commands with state tracking."""
        try:
            command = message.lower().strip()
            
            if "add tool" in command:
                name = command.split("add tool")[-1].strip()
                if not name:
                    raise StateValidationError("Tool name is required")
                    
                tool = await self._create_tool(name)
                if self.tool_state:
                    self.tool_state.active_tools.append(tool.id)
                    await self.state_manager._persist_specialized_state(self.tool_state)
                return f"Added tool: {tool.name}"
                
            elif "list tools" in command:
                tools = await self._get_active_tools()
                if not tools:
                    return "No active tools found"
                return "Active tools:\n" + "\n".join(f"- {t.name}" for t in tools)
                
            elif "help" in command:
                return """Available commands:
- add tool <name>
- list tools
- help"""
                
            return f"Unknown command. Type 'help' for available commands."
            
        except StateError as e:
            raise
        except Exception as e:
            print(f"Command processing error: {str(e)}")
            raise StateError(f"Failed to process command: {str(e)}")
            
    async def _create_tool(self, name: str) -> Tool:
        """Create a tool with state tracking."""
        try:
            tool = Tool(name=name)
            created = self.persistence_model.tools.create(tool)
            
            if self.tool_state:
                await self.state_manager.update_state(
                    self.tool_state.id,
                    {
                        "last_created_tool": created.id,
                        "total_tools": len(self.tool_state.active_tools) + 1
                    }
                )
            
            return created
            
        except Exception as e:
            raise StateError(f"Failed to create tool: {str(e)}")
            
    async def _get_active_tools(self) -> List[Tool]:
        """Get active tools from state."""
        if not self.tool_state:
            raise StateNotFoundError("Tool state not initialized")
            
        try:
            return [
                self.persistence_model.tools.get(tool_id)
                for tool_id in self.tool_state.active_tools
                if self.persistence_model.tools.get(tool_id)
            ]
        except Exception as e:
            raise StateError(f"Failed to get active tools: {str(e)}")
        
    def show_tool_dialog(self) -> Optional[Dict[str, Any]]:
        """Show dialog for adding/configuring tools."""
        dialog = ToolDialog(self.view_state, self.persistence_model)
        result = dialog.render()
        
        if result:
            # TODO: Implement tool creation/configuration
            if hasattr(self.persistence_model, 'tools'):
                return self.persistence_model.tools.create(result)
        return None
        
    def handle_node_click(self, node: TreeNode):
        """Handle tree node click events."""
        self.view_state.selected_node = node.id
        if node.type == "tool":
            # Show tool configuration dialog
            self.show_tool_dialog()