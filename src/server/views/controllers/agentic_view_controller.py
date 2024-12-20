# src/server/views/controllers/agentic_view_controller.py
from typing import Optional, Dict, Any, List
from uuid import UUID
from datetime import datetime
import json
from ...models.exceptions import StateError, StateNotFoundError, StateValidationError
from ...models.agent import Agentic
from ..models.view_state import ViewState
from ..models.view_types import ViewType
from ...models.specialized_state import StateType, AgentFrameworkState, StateMetadata
from ..state.state_manager import ViewStateManager
from ..components.tree_component import TreeNode
from ...utils.state_loader import StateLoader
from ...persistence.in_memory_persistence import InMemoryPersistenceModel
from ..components.tree_select_component import TreeSelectComponent
import logging
from pathlib import Path

class AgenticViewController:
    """Controller for agentic configuration view with specialized state support."""
    
    def __init__(self, persistence_model):
        self.global_persistence = persistence_model
        self.view_state = ViewState(view_name="agentic_config")
        self.state_manager = ViewStateManager(persistence_model)
        self.local_persistence = None
        self.agent_state = None
        self.tree_component = TreeSelectComponent(self.handle_node_click)
        self.logger = logging.getLogger(__name__)
        
    async def initialize(self):
        """Initialize controller with specialized state."""
        try:
            await self.state_manager.initialize()
            
            # Load existing state if available
            try:
                session_dir = Path("state/sessions")
                state_file = session_dir / "agentic_config_view_default.json"
                if state_file.exists():
                    with open(state_file) as f:
                        state_data = json.load(f)
                        self.view_state.chat_history = state_data.get('chat_history', [])
                        if 'task_status' in state_data:
                            self.view_state.task_status = state_data['task_status']
                        print(f"Loaded chat history: {len(self.view_state.chat_history)} messages")
            except Exception as e:
                self.logger.error(f"Failed to load existing state: {str(e)}")
            
            # Initialize task context
            task_managers = self.global_persistence.tasksmanagers.list()
            tasks = self.global_persistence.tasks.list()
            
            if task_managers and tasks:
                # Find agentic framework task
                agentic_manager = next(
                    (m for m in task_managers if "Agentic Framework" in m.name),
                    task_managers[0]
                )
                agentic_task = next(
                    (t for t in tasks if t.tasksmanager_id == agentic_manager.id),
                    None
                )
                
                if agentic_task:
                    # Set active task context
                    self.view_state.set_active_task(
                        task_id=agentic_task.id,
                        task_name=agentic_task.name,
                        manager_id=agentic_manager.id,
                        manager_name=agentic_manager.name
                    )
                    print(f"Set active task: {agentic_manager.name}-{agentic_task.name}")
            
            # Initialize other components
            self.local_persistence = InMemoryPersistenceModel()
            print("Local persistence model initialized")
            
        except Exception as e:
            self.logger.error(f"Error in controller initialization: {str(e)}")
            raise

    async def get_agent_tree(self) -> Optional[TreeNode]:
        """Get agentic frameworks as tree structure."""
        try:
            # Use global persistence to get crewai configs
            crewai_configs = self.global_persistence.crewai_config.list()
            if not crewai_configs:
                print("No CrewAI configurations found")
                return None
            
            # Create root node
            root = TreeNode(UUID('00000000-0000-0000-0000-000000000000'), "Agentic Frameworks", "root")
            
            # Create framework type nodes
            framework_types = {
                "crewai": TreeNode(
                    UUID('11111111-1111-1111-1111-111111111111'), 
                    "CrewAI", 
                    "group"
                ),
                "autogen": TreeNode(
                    UUID('22222222-2222-2222-2222-222222222222'), 
                    "AutoGen", 
                    "group"
                ),
                "other": TreeNode(
                    UUID('33333333-3333-3333-3333-333333333333'), 
                    "Other", 
                    "group"
                )
            }
            
            # Add framework type nodes to root
            for type_node in framework_types.values():
                root.children.append(type_node)
            
            # Process CrewAI configurations
            for config in crewai_configs:
                try:
                    # Get agents from the CrewAI config
                    if hasattr(config, 'agents') and config.agents:
                        for agent in config.agents:
                            agent_node = TreeNode(
                                UUID(agent.id), 
                                agent.name,
                                "agentic"
                            )
                            
                            # Add agent details if available
                            if hasattr(agent, 'role'):
                                agent_node.description = f"Role: {agent.role}"
                            if hasattr(agent, 'goal'):
                                agent_node.metadata = {"goal": agent.goal}
                            if hasattr(agent, 'backstory'):
                                agent_node.metadata = {
                                    **agent_node.metadata, 
                                    "backstory": agent.backstory
                                }
                            
                            # Add to CrewAI group
                            framework_types['crewai'].children.append(agent_node)
                
                except Exception as e:
                    print(f"Error processing CrewAI config {config.id}: {str(e)}")
            
            # Sort agents within each framework type
            for framework in framework_types.values():
                framework.children.sort(key=lambda x: x.name)
            
            # Remove empty framework types
            root.children = [
                framework for framework in root.children 
                if framework.children or framework.node_type == "group"
            ]
            
            return root
            
        except Exception as e:
            print(f"Error building frameworks tree: {str(e)}")
            return None
            
    async def handle_chat(self, message: str) -> str:
        """Process chat messages."""
        try:
            # Process message and get response
            response = await self._process_agent_command(message)
            
            # Add messages to chat history
            self.view_state.chat_history.append({
                "role": "user",
                "content": message
            })
            self.view_state.chat_history.append({
                "role": "assistant",
                "content": response
            })
            
            # Save state after chat update
            try:
                state_data = self.view_state.dict()
                await self.state_manager.save_state("agentic_config", state_data)
            except Exception as e:
                self.logger.error(f"Failed to save state: {str(e)}")
            
            return response
            
        except Exception as e:
            self.logger.error(f"Chat handling error: {str(e)}")
            return f"An error occurred: {str(e)}"
            
    async def _process_agent_command(self, message: str) -> str:
        """Process agentic management commands or run active task."""
        try:
            command = message.lower().strip()
            
            # Check for specific commands
            if "create agentic" in command:
                name = command.split("create agentic")[-1].strip()
                if not name:
                    raise StateValidationError("Agent name is required")
                    
                agentic = await self._create_agent(name)
                if self.agent_state:
                    self.agent_state.active_agents.append(agentic.id)
                return f"Created agentic: {agentic.name}"
                
            elif "list agents" in command:
                agents = await self._get_active_agents()
                if not agents:
                    return "No active agents found"
                return "Active agents:\n" + "\n".join(f"- {a.name}" for a in agents)
                
            elif "help" in command:
                return """Available commands:
- create agentic <name>
- list agents
- help"""
                
            # If no command matched, run the active task
            if self.view_state.task_status and self.view_state.task_status.get("loaded"):
                task_id = self.view_state.task_status.get("task_id")
                manager_id = self.view_state.task_status.get("tasksmanager_id")
                
                if task_id and manager_id:
                    response = await self.state_manager.task_runner.run_task(
                        tasksmanager_id=manager_id,
                        task_id=task_id,
                        running_extra_params={'messages': [{'role': 'user', 'content': message}]}
                    )
                    return response.get('response', str(response))
                    
            return "No active task to process message. Try 'help' for available commands."
            
        except StateError as e:
            raise
        except Exception as e:
            self.logger.error(f"Command processing error: {str(e)}")
            raise StateError(f"Failed to process command: {str(e)}")
            
    async def _create_agent(self, name: str) -> Agentic:
        """Create an agentic with state tracking."""
        try:
            agentic = Agentic(name=name)
            created = self.persistence_model.agents.create(agentic)
            
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
            raise StateError(f"Failed to create agentic: {str(e)}")
            
    async def _get_active_agents(self) -> List[Agentic]:
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
            
    
    async def handle_node_click(self, node: TreeNode):
        """Handle click events on tree nodes."""
        try:
            if not node:
                return
                
            # Update selected node in view state
            self.view_state.selected_node_id = node.id
            
            # Handle different node types
            if node.node_type == "agentic":
                # Load agentic details in the main content area
                agentic = await self.persistence_model.agents.read(node.id)
                if agentic:
                    self.view_state.selected_agentic = agentic
                    
            elif node.node_type == "group":
                # Clear selected agentic when group is selected
                self.view_state.selected_agentic = None
                # Load group details if needed
                group = await self.persistence_model.agent_groups.read(node.id)
                if group:
                    self.view_state.selected_group = group
                    
            # Update state
            if self.agent_state:
                await self.state_manager.update_state(
                    self.agent_state.id,
                    {"selected_node": node.id}
                )
                
        except Exception as e:
            import streamlit as st
            st.error(f"Error handling node click: {str(e)}")
            
    async def refresh_view(self):
        """Refresh the view state."""
        try:
            # Reload tree data
            tree_data = await self.tree_provider.get_tree_data()
            self.view_state.tree_data = tree_data
            
            # Reload selected items if any
            if self.view_state.selected_node_id:
                node = next(
                    (n for n in tree_data if n.id == self.view_state.selected_node_id),
                    None
                )
                if node:
                    await self.handle_node_click(node)
                    
        except Exception as e:
            import streamlit as st
            st.error(f"Error refreshing view: {str(e)}")
            
    async def handle_agent_save(self, agentic: Agentic):
        """Handle saving of agentic configuration."""
        try:
            if not agentic.id:
                # Create new agentic
                agent_id = await self.persistence_model.agents.create(agentic)
                agentic.id = agent_id
            else:
                # Update existing agentic
                await self.persistence_model.agents.update(agentic.id, agentic)
                
            # Refresh view
            await self.refresh_view()
            
            # Update state
            if self.agent_state:
                await self.state_manager.update_state(
                    self.agent_state.id,
                    {"last_modified_agent": str(agentic.id)}
                )
                
        except Exception as e:
            import streamlit as st
            st.error(f"Error saving agentic: {str(e)}")
            
    def handle_agent_cancel(self):
        """Handle cancellation of agentic configuration."""
        self.view_state.selected_agentic = None
        self.view_state.selected_node_id = None