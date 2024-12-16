# src/server/views/controllers/agentic_view_controller.py
from typing import Optional, Dict, Any, List
from uuid import UUID
from datetime import datetime
from ...models.exceptions import StateError, StateNotFoundError
from ...models.agent import Agent
from ..models.view_state import ViewState
from ..models.view_types import ViewType
from ...models.specialized_state import StateType, AgentFrameworkState
from ..data.agent_tree_provider import AgentTreeProvider
from ..components.dialogs.agent_dialog import AgentDialog
from ..state.state_manager import ViewStateManager
from ..components.tree_component import TreeNode
from ...utils.state_loader import StateLoader

class AgenticViewController:
    """Controller for agentic configuration view with specialized state support."""
    
    def __init__(self, persistence_model):
        self.persistence_model = persistence_model
        self.view_state = ViewState(view_type=ViewType.AGENTIC_CONFIG)
        self.tree_provider = AgentTreeProvider(persistence_model)
        self.state_manager = ViewStateManager(persistence_model)
        self.agent_state: Optional[AgentFrameworkState] = None
        
        # Load existing state
        state_ids = StateLoader.get_state_ids("agentic_framework")
        if state_ids:
            self.agentic_manager_id = state_ids["agentic_manager_id"]
            self.task_id = state_ids["task_id"]
        
    async def initialize(self):
        """Initialize controller with specialized state."""
        # Try to load existing state first
        state_file = StateLoader.get_state_file("agentic_framework")
        if state_file and state_file.exists():
            self.agent_state = await self.state_manager.load_specialized_state(state_file)
        
        # Create new state if none exists
        if not self.agent_state:
            self.agent_state = await self.state_manager.create_specialized_state(
                state_type=StateType.AGENT_FRAMEWORK,
                name="Agent Framework State",
                initial_data={
                    "active_view": ViewType.AGENTIC_CONFIG.value,
                    "selected_agent": None,
                    "active_agents": []
                }
            )
    
    async def get_agents_tree(self) -> Optional[TreeNode]:
        """Get agent hierarchy as tree structure with state tracking."""
        try:
            agents = self.persistence_model.agents.list()
            
            # Update agent state
            if self.agent_state:
                self.agent_state.active_agents = [agent.id for agent in agents]
                await self.state_manager._persist_specialized_state(self.agent_state)
            
            # Create root node
            root = TreeNode(UUID('00000000-0000-0000-0000-000000000000'), "Agents", "root")
            
            # Create category nodes
            categories = {
                "task": TreeNode(UUID('11111111-1111-1111-1111-111111111111'), "Task Agents", "category"),
                "tool": TreeNode(UUID('22222222-2222-2222-2222-222222222222'), "Tool Agents", "category"),
                "system": TreeNode(UUID('33333333-3333-3333-3333-333333333333'), "System Agents", "category")
            }
            
            # Add categories to root
            for category in categories.values():
                root.children.append(category)
            
            # Add agents to appropriate categories
            for agent in agents:
                agent_type = agent.metadata.get('type', 'system')
                node = TreeNode(UUID(agent.id), agent.name, "agent")
                if agent_type in categories:
                    categories[agent_type].children.append(node)
                else:
                    categories['system'].children.append(node)
            
            return root
            
        except Exception as e:
            print(f"Error building agents tree: {str(e)}")
            return None
            
    async def handle_chat(self, message: str) -> None:
        """Handle chat messages with state tracking."""
        try:
            response = await self._process_agent_command(message)
            self.view_state.add_message("user", message)
            self.view_state.add_message("assistant", response)
        except Exception as e:
            error_msg = f"Error processing message: {str(e)}"
            self.view_state.add_message("assistant", error_msg)
            
    async def _process_agent_command(self, message: str) -> str:
        """Process agent management commands with state tracking."""
        try:
            command = message.lower().strip()
            
            if "create agent" in command:
                name = command.split("create agent")[-1].strip()
                if not name:
                    raise StateValidationError("Agent name is required")
                    
                agent = await self._create_agent(name)
                if self.agent_state:
                    self.agent_state.active_agents.append(agent.id)
                    await self.state_manager._persist_specialized_state(self.agent_state)
                return f"Created agent: {agent.name}"
                
            elif "list agents" in command:
                agents = await self._get_active_agents()
                if not agents:
                    return "No active agents found"
                return "Active agents:\n" + "\n".join(f"- {a.name}" for a in agents)
                
            elif "help" in command:
                return """Available commands:
- create agent <name>
- list agents
- help"""
                
            return f"Unknown command. Type 'help' for available commands."
            
        except StateError as e:
            raise
        except Exception as e:
            print(f"Command processing error: {str(e)}")
            raise StateError(f"Failed to process command: {str(e)}")
            
    async def _create_agent(self, name: str) -> Agent:
        """Create an agent with state tracking."""
        try:
            agent = Agent(name=name)
            created = self.persistence_model.agents.create(agent)
            
            if self.agent_state:
                await self.state_manager.update_state(
                    self.agent_state.id,
                    {
                        "last_created_agent": created.id,
                        "total_agents": len(self.agent_state.active_agents) + 1
                    }
                )
            
            return created
            
        except Exception as e:
            raise StateError(f"Failed to create agent: {str(e)}")
            
    async def _get_active_agents(self) -> List[Agent]:
        """Get active agents from state."""
        if not self.agent_state:
            raise StateNotFoundError("Agent state not initialized")
            
        try:
            return [
                self.persistence_model.agents.get(agent_id)
                for agent_id in self.agent_state.active_agents
                if self.persistence_model.agents.get(agent_id)
            ]
        except Exception as e:
            raise StateError(f"Failed to get active agents: {str(e)}")
            
    def show_agent_dialog(self) -> Optional[Dict[str, Any]]:
        """Show dialog for creating/editing agents."""
        dialog = AgentDialog(self.view_state)
        return dialog.render()