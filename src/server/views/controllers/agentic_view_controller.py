# src/server/views/controllers/agentic_view_controller.py
from typing import Optional, Dict, Any, List
from uuid import UUID
from ..models.view_state import ViewState
from ..models.view_types import ViewType
from ..components.tree_component import TreeNode
from datetime import datetime

class AgenticViewController:
    """Controller for agentic configuration view."""
    
    def __init__(self, persistence_model):
        self.persistence_model = persistence_model
        self.view_state = ViewState(view_type=ViewType.AGENTIC_CONFIG)
        
    async def get_agent_tree(self) -> Optional[TreeNode]:
        """Get agent configurations as tree structure."""
        try:
            # Create root node
            root = TreeNode(UUID('00000000-0000-0000-0000-000000000000'), "Agents", "root")
            
            # Create category nodes with metadata
            roles = TreeNode(
                UUID('11111111-1111-1111-1111-111111111111'), 
                "Roles", 
                "category",
                {"description": "Agent roles and capabilities"}
            )
            workflows = TreeNode(
                UUID('22222222-2222-2222-2222-222222222222'), 
                "Workflows", 
                "category",
                {"description": "Agent workflow configurations"}
            )
            configs = TreeNode(
                UUID('33333333-3333-3333-3333-333333333333'), 
                "Configurations", 
                "category",
                {"description": "General agent configurations"}
            )
            
            # Add categories to root
            root.children.extend([roles, workflows, configs])
            
            # Get agent configurations from persistence model
            if hasattr(self.persistence_model, 'agent_configs'):
                agent_configs = self.persistence_model.agent_configs.list()
                
                for config in agent_configs:
                    config_type = config.metadata.get('type', 'config')
                    node = TreeNode(
                        UUID(config.id), 
                        config.name, 
                        config_type,
                        config.metadata
                    )
                    
                    # Add to appropriate category
                    if config_type == 'role':
                        roles.children.append(node)
                    elif config_type == 'workflow':
                        workflows.children.append(node)
                    else:
                        configs.children.append(node)
            
            return root
            
        except Exception as e:
            print(f"Error building agent tree: {str(e)}")
            return None
            
    async def handle_chat(self, message: str) -> str:
        """Process chat messages for agent configuration."""
        try:
            # Add message to chat history
            self.view_state.chat_history.append({
                "role": "user",
                "content": message
            })
            
            # Process the command
            response = await self._process_config_command(message)
            
            # Add response to chat history
            self.view_state.chat_history.append({
                "role": "assistant",
                "content": response
            })
            
            return response
            
        except Exception as e:
            return f"Error processing message: {str(e)}"
            
    async def _process_config_command(self, message: str) -> str:
        """Process configuration management commands."""
        try:
            # Basic command processing
            message = message.lower().strip()
            
            if "create role" in message:
                # Extract role name and details
                name = message.split("create role")[-1].strip()
                if name:
                    config = {
                        "name": name,
                        "type": "role",
                        "metadata": {
                            "created_at": str(datetime.now()),
                            "type": "role"
                        }
                    }
                    if hasattr(self.persistence_model, 'agent_configs'):
                        self.persistence_model.agent_configs.create(config)
                        return f"Created new agent role: {name}"
                return "Please specify a name for the role"
                
            elif "create workflow" in message:
                # Extract workflow name and details
                name = message.split("create workflow")[-1].strip()
                if name:
                    config = {
                        "name": name,
                        "type": "workflow",
                        "metadata": {
                            "created_at": str(datetime.now()),
                            "type": "workflow"
                        }
                    }
                    if hasattr(self.persistence_model, 'agent_configs'):
                        self.persistence_model.agent_configs.create(config)
                        return f"Created new workflow: {name}"
                return "Please specify a name for the workflow"
                
            elif "list" in message:
                # List existing configurations
                if hasattr(self.persistence_model, 'agent_configs'):
                    configs = self.persistence_model.agent_configs.list()
                    if configs:
                        return "Existing configurations:\n" + "\n".join(
                            f"- {c.name} ({c.metadata.get('type', 'config')})"
                            for c in configs
                        )
                return "No configurations found"
                
            return "Available commands:\n- create role <name>\n- create workflow <name>\n- list"
            
        except Exception as e:
            return f"Error processing command: {str(e)}"
            
    def handle_node_click(self, node: TreeNode):
        """Handle tree node click events."""
        self.view_state.selected_node = node.id
        if node.type in ["role", "workflow", "config"]:
            # Store metadata in view state
            self.view_state.selected_node_metadata = node.metadata
            # Show configuration dialog
            if hasattr(self, 'show_config_dialog'):
                self.show_config_dialog()