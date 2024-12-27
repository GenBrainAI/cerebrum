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
from ...models.message import Message
from ...controllers.task_runner import TaskRunner

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
        self.task_runner = TaskRunner(persistence_model)
        
    async def initialize(self):
        """Initialize controller with specialized state."""
        try:
            print("Starting agentic controller initialization...")
            # Initialize task runner
            await self.task_runner.initialize()
            
            state_file = StateLoader.get_state_file("agentic_framework_state.json")
            print(f"Checking state file path: {state_file}")
            
            if not state_file or not state_file.exists():
                print(f"🔴 Specialized state file not found at {state_file}")
                return

            print(f"Loading state from: {state_file}")
            
            # Read state file content as string
            with open(state_file, 'r', encoding='utf-8') as f:
                json_str = f.read()
            
            # Create local persistence model and load state from string
            self.local_persistence = InMemoryPersistenceModel()
            self.local_persistence.from_json(json_str=json_str)
            
            if self.local_persistence:
                print("Local persistence model created")
                # Get task context from local persistence
                task_managers = self.local_persistence.tasksmanagers.list()
                tasks = self.local_persistence.tasks.list()
                
                print(f"Found {len(task_managers)} task managers and {len(tasks)} tasks")
                
                if task_managers and tasks:
                    # Find the agentic framework manager and task
                    agentic_manager = next(
                        (m for m in task_managers if "Agentic Framework" in m.name),
                        task_managers[0]
                    )
                    agentic_task = next(
                        (t for t in tasks if t.tasksmanager_id == agentic_manager.id),
                        None
                    )
                    
                    if agentic_task:
                        # Update view state with task context
                        self.view_state.set_active_task(
                            task_id=agentic_task.id,
                            task_name=agentic_task.name,
                            manager_id=agentic_manager.id,
                            manager_name=agentic_manager.name
                        )
                        
                        print(f"🟢 Loaded state for {agentic_manager.name}-{agentic_task.name}")
                    else:
                        print("🔴 No agentic framework task found")
                else:
                    print("🔴 No task context found in state file")
            else:
                print("🔴 Failed to create local persistence model")
                
        except Exception as e:
            print(f"Error initializing agentic controller: {str(e)}")
            raise

    async def get_agent_tree(self) -> Optional[TreeNode]:
        """Get agentic frameworks as tree structure."""
        try:
            # Use global persistence to get crewai configs
            crewai_configs = self.global_persistence.crewai_config.list()
            if not crewai_configs:
                # print("No CrewAI configurations found")
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
            
            # Save session state after chat update
            try:
                state_data = self.view_state.dict()
                await self.state_manager.save_session_state("agentic_config", state_data)
            except Exception as e:
                self.logger.error(f"Failed to save session state: {str(e)}")
            
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
                    # Prepare messages context
                    current_messages = []
                    
                    # Add existing chat history
                    for msg in self.view_state.chat_history:
                        if isinstance(msg, Message):
                            current_messages.append(msg)
                        elif isinstance(msg, dict):
                            current_messages.append(Message(**msg))
                        else:
                            current_messages.append(Message(
                                role=getattr(msg, 'role', 'user'),
                                content=str(msg),
                                file_ids=getattr(msg, 'file_ids', None),
                                created_at=getattr(msg, 'created_at', None),
                                updated_at=getattr(msg, 'updated_at', None)
                            ))
                    
                    # Add current message
                    user_message = Message(
                        role="user",
                        content=message,
                        file_ids=None,
                        created_at=None,
                        updated_at=None
                    )
                    current_messages.append(user_message)
                    
                    # Run task with message context
                    response = await self.task_runner.run_task(
                        tasksmanager_id=manager_id,
                        task_id=task_id,
                        running_extra_params={'messages': current_messages}
                    )
                    
                    # Process response
                    if isinstance(response, dict) and 'response' in response:
                        response_text = response['response']
                    else:
                        response_text = str(response)
                    
                    return response_text
            
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