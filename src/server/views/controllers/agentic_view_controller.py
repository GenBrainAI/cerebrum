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

class AgenticViewController:
    """Controller for agentic configuration view with specialized state support."""
    
    def __init__(self, persistence_model):
        self.global_persistence = persistence_model
        self.view_state = ViewState(view_type=ViewType.AGENTIC_CONFIG)
        self.state_manager = ViewStateManager(persistence_model)
        self.local_persistence = None
        self.agent_state = None
        
    async def initialize(self):
        """Initialize controller with specialized state."""
        try:
            print("Starting controller initialization...")
            state_file = StateLoader.get_state_file("agentic_framework_state.json")
            print(f"Checking state file path: {state_file}")
            
            if not state_file or not state_file.exists():
                print(f"🔴 Specialized state file not found at {state_file}")
                # Create initial state file
                root_dir = StateLoader.get_project_root()
                state_dir = root_dir / "state" / "specialized"
                state_dir.mkdir(parents=True, exist_ok=True)
                
                initial_state = {
                    "type": "agent_framework",
                    "task_context": None,
                    "frameworks": [],
                    "tasks": [],
                    "tasksmanagers": []
                }
                
                state_file = state_dir / "agent_framework_state.json"
                with open(state_file, 'w') as f:
                    json.dump(initial_state, f, indent=2)
                print(f"Created initial state file at: {state_file}")

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
                        
                        # Set agent state using task context
                        self.agent_state = AgentFrameworkState(
                            state_type=StateType.AGENT_FRAMEWORK,
                            name=f"{agentic_manager.name}-{agentic_task.name}",
                            data={},
                            metadata=StateMetadata(),
                            frameworks=[],
                            task_context={
                                "task_id": agentic_task.id,
                                "manager_id": agentic_manager.id
                            }
                        )
                        
                        # Check for framework configuration in task
                        if hasattr(agentic_task, 'crewai_info_id') and agentic_task.crewai_info_id:
                            print("Found CrewAI configuration in task")
                            # TODO: Load framework configuration from CrewAI info
                        elif hasattr(agentic_task, 'autogen_config_id') and agentic_task.autogen_config_id:
                            print("Found Autogen configuration in task")
                            # TODO: Load framework configuration from Autogen config
                        
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
            if not self.local_persistence:
                return None
            
            # Get frameworks from local persistence
            frameworks = self.local_persistence.agents.list()
            if not frameworks:
                print("No frameworks found in local persistence")
                return None
            
            # Create root node
            root = TreeNode(UUID('00000000-0000-0000-0000-000000000000'), "Frameworks", "root")
            
            # Add framework nodes
            for framework in frameworks:
                try:
                    node = TreeNode(
                        UUID(framework.id), 
                        framework.name, 
                        "agentic"
                    )
                    root.children.append(node)
                except Exception as e:
                    print(f"Error adding framework node: {str(e)}")
            
            return root
            
        except Exception as e:
            print(f"Error building frameworks tree: {str(e)}")
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
        """Process agentic management commands with state tracking."""
        try:
            command = message.lower().strip()
            
            if "create agentic" in command:
                name = command.split("create agentic")[-1].strip()
                if not name:
                    raise StateValidationError("Agent name is required")
                    
                agentic = await self._create_agent(name)
                if self.agent_state:
                    self.agent_state.active_agents.append(agentic.id)
                    await self.state_manager._persist_specialized_state(self.agent_state)
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
                
            return f"Unknown command. Type 'help' for available commands."
            
        except StateError as e:
            raise
        except Exception as e:
            print(f"Command processing error: {str(e)}")
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