from typing import Dict, Any, Optional, List
import streamlit as st
import logging
from datetime import datetime
from pathlib import Path
import json
from uuid import UUID, uuid4
from ...models.exceptions import StateError, StateNotFoundError, StateValidationError
from ..models.view_state import ViewState
from ..models.view_types import ViewType
from ...models.specialized_state import StateType, TaskGenerationState, StateMetadata
from ..state.state_manager import ViewStateManager
from ..models.tree_node import TreeNode
from ...utils.state_loader import StateLoader
from ...persistence.in_memory_persistence import InMemoryPersistenceModel
from ..components.tree_select_component import TreeSelectComponent
from ...models.message import Message
from ...controllers.task_runner import TaskRunner
from ...models.task import Task
from ...models.tasks_manager import TasksManager

class TaskHierarchyController:
    """Controller for task hierarchy view with task management capabilities."""
    
    def __init__(self, persistence_model):
        self.global_persistence = persistence_model
        self.persistence_model = persistence_model  # For compatibility with task management
        self.logger = logging.getLogger(__name__)
        self.view_state = ViewState(view_name="task_hierarchy")
        self.state_manager = ViewStateManager(persistence_model)
        self.tree_component = TreeSelectComponent(self.handle_node_click)
        self.local_persistence = None
        self.task_runner = None  # Will be initialized after local persistence is loaded
        self.view_state.task_status = {
            "loaded": False,
            "tasksmanager_name": "",
            "task_name": ""
        }
        self.view_state.chat_history = []
        
        # Initialize available models for task management
        self.view_state.available_models = [
            "gpt-4",
            "gpt-4-turbo",
            "gpt-3.5-turbo",
            "claude-3-opus",
            "claude-3-sonnet",
            "claude-3-haiku",
            "ollama/llama3"
        ]

    def handle_node_click(self, node_id: UUID):
        """Handle tree node selection."""
        self.view_state.selected_node = node_id
        # TODO: Implement task selection logic

    async def get_task_tree(self):
        """Get the task hierarchy as a tree structure."""
        try:
            self.logger.info("Building task hierarchy tree...")
            
            # Create root node
            root = TreeNode(
                id=UUID('00000000-0000-0000-0000-000000000000'),
                name="Task Hierarchy",
                type="root",
                children=[]
            )
            
            # Get all task managers
            task_managers = self.get_task_managers()
            self.logger.info(f"Found {len(task_managers)} task managers")
            
            # Create task manager nodes
            for tm in task_managers:
                tm_node = TreeNode(
                    id=UUID(tm.id),
                    name=f"{tm.name}",
                    type="tasksmanager",
                    data={"id": tm.id, "model": tm.model},
                    children=[]
                )
                
                # Get tasks for this task manager
                tasks = self.get_tasks(tm.id)
                self.logger.info(f"Found {len(tasks)} tasks for manager {tm.name}")
                
                # Create task nodes
                for task in tasks:
                    task_node = TreeNode(
                        id=UUID(task.id),
                        name=f"{task.name}",
                        type="task",
                        data={"id": task.id, "model": task.model, "tasksmanager_id": tm.id},
                        children=[]
                    )
                    tm_node.children.append(task_node)
                
                # Always add the manager node even if it has no tasks
                # This allows users to see the manager in the tree and add tasks to it
                root.children.append(tm_node)
            
            # Log the tree structure for debugging
            self.logger.info(f"Task tree generated with {len(root.children)} task managers")
            
            return root
        except Exception as e:
            self.logger.error(f"Error building task tree: {str(e)}")
            import traceback
            self.logger.error(f"Stack trace: {traceback.format_exc()}")
            return None
            
    # Task Management methods
    
    def get_task_managers(self) -> List[TasksManager]:
        """Get all task managers from persistence."""
        try:
            return self.persistence_model.tasksmanagers.list()
        except Exception as e:
            self.logger.error(f"Error getting task managers: {str(e)}")
            return []
            
    def get_tasks(self, tasksmanager_id: Optional[str] = None) -> List[Task]:
        """Get tasks for a specific task manager or all tasks."""
        try:
            all_tasks = self.persistence_model.tasks.list()
            if tasksmanager_id:
                return [task for task in all_tasks if task.tasksmanager_id == tasksmanager_id]
            return all_tasks
        except Exception as e:
            self.logger.error(f"Error getting tasks: {str(e)}")
            return []
            
    def create_task_manager(self, name: str, model: Optional[str] = None, 
                          description: Optional[str] = None, 
                          system_message: Optional[str] = None) -> Optional[TasksManager]:
        """Create a new task manager."""
        try:
            messages = []
            if system_message:
                messages.append(Message(role="system", content=system_message))
                
            task_manager = TasksManager(
                name=name,
                model=model,
                description=description,
                messages=messages
            )
            
            # Save to persistence
            created_manager = self.persistence_model.tasksmanagers.create(task_manager)
            return created_manager
        except Exception as e:
            self.logger.error(f"Error creating task manager: {str(e)}")
            return None
            
    def update_task_manager(self, task_manager_id: str, name: Optional[str] = None, 
                          model: Optional[str] = None, description: Optional[str] = None, 
                          system_message: Optional[str] = None) -> Optional[TasksManager]:
        """Update an existing task manager."""
        try:
            # Get existing task manager
            task_manager = self.persistence_model.tasksmanagers.read(task_manager_id)
            if not task_manager:
                self.logger.error(f"Task manager not found: {task_manager_id}")
                return None
                
            # Update fields if provided
            if name:
                task_manager.name = name
            if model is not None:  # Allow setting to None
                task_manager.model = model
            if description is not None:  # Allow setting to None
                task_manager.description = description
                
            # Update system message if provided
            if system_message is not None:
                # Find existing system message or create new one
                system_messages = [msg for msg in task_manager.messages if msg.role == "system"]
                if system_messages:
                    system_messages[0].content = system_message
                else:
                    task_manager.messages.append(Message(role="system", content=system_message))
                    
            # Update in persistence
            updated_manager = self.persistence_model.tasksmanagers.update(task_manager_id, task_manager)
            return updated_manager
        except Exception as e:
            self.logger.error(f"Error updating task manager: {str(e)}")
            return None
            
    def delete_task_manager(self, task_manager_id: str) -> bool:
        """Delete a task manager and its associated tasks."""
        try:
            # Get all tasks for this manager
            tasks = self.get_tasks(task_manager_id)
            
            # Delete all tasks first
            for task in tasks:
                self.persistence_model.tasks.delete(task.id)
                
            # Delete the task manager
            return self.persistence_model.tasksmanagers.delete(task_manager_id)
        except Exception as e:
            self.logger.error(f"Error deleting task manager: {str(e)}")
            return False
            
    def create_task(self, name: str, tasksmanager_id: str, model: Optional[str] = None,
                  description: Optional[str] = None, system_message: Optional[str] = None,
                  inherit_manager_context: bool = False) -> Optional[Task]:
        """Create a new task associated with a task manager."""
        try:
            messages = []
            if system_message:
                messages.append(Message(role="system", content=system_message))
                
            task = Task(
                name=name,
                tasksmanager_id=tasksmanager_id,
                model=model,
                description=description,
                messages=messages,
                inherit_manager_context=inherit_manager_context
            )
            
            # Save to persistence
            created_task = self.persistence_model.tasks.create(task)
            return created_task
        except Exception as e:
            self.logger.error(f"Error creating task: {str(e)}")
            return None
            
    def update_task(self, task_id: str, name: Optional[str] = None, 
                  tasksmanager_id: Optional[str] = None, model: Optional[str] = None,
                  description: Optional[str] = None, system_message: Optional[str] = None,
                  inherit_manager_context: Optional[bool] = None) -> Optional[Task]:
        """Update an existing task."""
        try:
            # Get existing task
            task = self.persistence_model.tasks.read(task_id)
            if not task:
                self.logger.error(f"Task not found: {task_id}")
                return None
                
            # Update fields if provided
            if name:
                task.name = name
            if tasksmanager_id:
                task.tasksmanager_id = tasksmanager_id
            if model is not None:  # Allow setting to None
                task.model = model
            if description is not None:  # Allow setting to None
                task.description = description
            if inherit_manager_context is not None:
                task.inherit_manager_context = inherit_manager_context
                
            # Update system message if provided
            if system_message is not None:
                # Find existing system message or create new one
                system_messages = [msg for msg in task.messages if msg.role == "system"]
                if system_messages:
                    system_messages[0].content = system_message
                else:
                    task.messages.append(Message(role="system", content=system_message))
                    
            # Update in persistence
            updated_task = self.persistence_model.tasks.update(task_id, task)
            return updated_task
        except Exception as e:
            self.logger.error(f"Error updating task: {str(e)}")
            return None
            
    def delete_task(self, task_id: str) -> bool:
        """Delete a task."""
        try:
            return self.persistence_model.tasks.delete(task_id)
        except Exception as e:
            self.logger.error(f"Error deleting task: {str(e)}")
            return False
            
    def get_system_message(self, obj: Any) -> Optional[str]:
        """Extract system message from a task or task manager."""
        if not obj or not hasattr(obj, 'messages'):
            return None
            
        system_messages = [msg.content for msg in obj.messages if msg.role == "system"]
        return system_messages[0] if system_messages else None

    async def initialize(self):
        """Initialize controller with specialized state."""
        try:
            print("\n🚀 Starting task controller initialization...")
            
            state_file = StateLoader.get_state_file("task_management_state.json")
            print(f"📁 Checking state file path: {state_file}")
            
            if not state_file or not state_file.exists():
                print(f"🔴 Specialized state file not found at {state_file}")
                return

            print(f"📖 Loading state from: {state_file}")
            
            # Read state file content as string
            with open(state_file, 'r', encoding='utf-8') as f:
                json_str = f.read()
            
            # Create local persistence model and load state from string
            self.local_persistence = InMemoryPersistenceModel()
            self.local_persistence.from_json(json_str=json_str)
            
            if self.local_persistence:
                print("✅ Local persistence model created")
                
                # Initialize task runner with local persistence
                self.task_runner = TaskRunner(self.local_persistence)
                await self.task_runner.initialize()
                print("✅ Task runner initialized with local persistence")
                
                # Get task context from local persistence
                task_managers = self.local_persistence.tasksmanagers.list()
                tasks = self.local_persistence.tasks.list()
                
                print(f"Found {len(task_managers)} task managers and {len(tasks)} tasks")
                
                if task_managers and tasks:
                    # Find the task management manager and task
                    task_manager = next(
                        (m for m in task_managers if "Task Management" in m.name),
                        task_managers[0]
                    )
                    main_task = next(
                        (t for t in tasks if t.tasksmanager_id == task_manager.id),
                        None
                    )
                    
                    if main_task:
                        # Update view state with task context
                        self.view_state.set_active_task(
                            task_id=main_task.id,
                            task_name=main_task.name,
                            manager_id=task_manager.id,
                            manager_name=task_manager.name
                        )
                        
                        print(f"🟢 Loaded state for {task_manager.name}-{main_task.name}")
                    else:
                        print("🔴 No task management task found")
                else:
                    print("🔴 No task context found in state file")
            else:
                print("🔴 Failed to create local persistence model")
                
        except Exception as e:
            print(f"Error initializing task controller: {str(e)}")
            raise

    async def handle_chat(self, prompt: str):
        """Handle chat messages."""
        try:
            # Add user message to chat history
            user_message = {
                "role": "user",
                "content": prompt,
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            }
            self.view_state.chat_history.append(user_message)
            
            # Save chat history to session state immediately after adding user message
            if 'task_controller' in st.session_state:
                st.session_state.task_controller.view_state.chat_history = self.view_state.chat_history
            
            # Process the message if we have an active task
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
                    
                    # Run task with message context
                    print("\n🔄 Using existing persistence model from session state")
                    print("Context provider initialized and synced with persistence model")
                    
                    # Use the task runner with local persistence
                    if not self.task_runner:
                        print("🔄 Initializing task runner with local persistence")
                        self.task_runner = TaskRunner(self.local_persistence)
                        await self.task_runner.initialize()
                    
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
                    
                    # Add assistant response to chat history
                    assistant_message = {
                        "role": "assistant",
                        "content": response_text,
                        "created_at": datetime.now().isoformat(),
                        "updated_at": datetime.now().isoformat()
                    }
                    self.view_state.chat_history.append(assistant_message)
                    
                    # Save updated chat history to session state
                    if 'task_controller' in st.session_state:
                        st.session_state.task_controller.view_state.chat_history = self.view_state.chat_history
                    
                    # Save chat history to persistence
                    if self.local_persistence and task_id:
                        task = self.local_persistence.tasks.read(task_id)
                        if task:
                            if not hasattr(task, 'chat_sessions'):
                                task.chat_sessions = {}
                            session_id = str(uuid4())
                            task.chat_sessions[session_id] = self.view_state.chat_history
                            self.local_persistence.tasks.update(task_id, task)
                else:
                    # Add simple response if no active task
                    response_message = {
                        "role": "assistant",
                        "content": "No active task to process message.",
                        "created_at": datetime.now().isoformat(),
                        "updated_at": datetime.now().isoformat()
                    }
                    self.view_state.chat_history.append(response_message)
            else:
                # Add simple response if no task loaded
                response_message = {
                    "role": "assistant",
                    "content": "Task management not loaded. Please initialize first.",
                    "created_at": datetime.now().isoformat(),
                    "updated_at": datetime.now().isoformat()
                }
                self.view_state.chat_history.append(response_message)
            
            # Final save of chat history to session state
            if 'task_controller' in st.session_state:
                st.session_state.task_controller.view_state.chat_history = self.view_state.chat_history
                
        except Exception as e:
            self.logger.error(f"Error handling chat: {str(e)}")
            st.error(f"Error handling chat: {str(e)}")
            # Add error message to chat history
            error_message = {
                "role": "assistant",
                "content": f"Error processing message: {str(e)}",
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            }
            self.view_state.chat_history.append(error_message)
            
            # Save error message to session state
            if 'task_controller' in st.session_state:
                st.session_state.task_controller.view_state.chat_history = self.view_state.chat_history
