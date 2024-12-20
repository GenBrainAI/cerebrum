from typing import Optional, Dict, Any, List
from uuid import UUID
from datetime import datetime
from ...models.exceptions import StateError, StateNotFoundError, StateValidationError
from ...models.task import Task
from ..models.view_state import ViewState
from ..models.view_types import ViewType
from ...models.specialized_state import StateType, TaskGenerationState, StateMetadata
from ..data.task_tree_provider import TaskTreeProvider
from ..components.dialogs.task_dialog import TaskDialog
from ..state.state_manager import ViewStateManager
from ..components.tree_component import TreeNode
from ...utils.state_loader import StateLoader
from ...persistence.in_memory_persistence import InMemoryPersistenceModel
from ..components.tree_select_component import TreeSelectComponent
from ...models.message import Message
import logging
import json
from pathlib import Path

class TaskHierarchyController:
    """Controller for task hierarchy view with specialized state support."""
    
    def __init__(self, persistence_model):
        self.global_persistence = persistence_model
        self.view_state = ViewState(view_name="task_hierarchy")
        self.state_manager = ViewStateManager(persistence_model)
        self.task_state = None
        self.tree_component = TreeSelectComponent(self.handle_node_click)
        self.logger = logging.getLogger(__name__)
        
    async def initialize(self):
        """Initialize controller with specialized state."""
        try:
            await self.state_manager.initialize()
            
            # Load existing state if available
            try:
                session_dir = Path("state/sessions")
                state_file = session_dir / "task_hierarchy_view_default.json"
                if state_file.exists():
                    with open(state_file) as f:
                        state_data = json.load(f)
                        self.view_state.chat_history = state_data.get('chat_history', [])
                        if 'task_status' in state_data:
                            self.view_state.task_status = state_data['task_status']
                        print(f"Loaded chat history: {len(self.view_state.chat_history)} messages")
            except Exception as e:
                self.logger.error(f"Failed to load existing state: {str(e)}")
            
            print("🔍 Starting task controller initialization...")
            
            # Initialize task context
            task_managers = self.global_persistence.tasksmanagers.list()
            tasks = self.global_persistence.tasks.list()
            
            # Create default task manager and task if none exist
            if not task_managers:
                print("Creating default task manager and tasks...")
                # Create Task Management manager
                task_manager = self.global_persistence.tasksmanagers.create({
                    "name": "Task Management",
                    "description": "Default task management system"
                })
                
                # Create default task
                main_task = self.global_persistence.tasks.create({
                    "name": "Task Management",
                    "description": "Main task management task",
                    "tasksmanager_id": task_manager.id
                })
                
                # Refresh lists
                task_managers = [task_manager]
                tasks = [main_task]
                print(f"Created default task manager: {task_manager.name}")
                print(f"Created default task: {main_task.name}")
            
            print(f"Found {len(task_managers)} managers and {len(tasks)} tasks")
            
            if task_managers and tasks:
                # Find task management task
                task_manager = next(
                    (m for m in task_managers if "Task Management" in m.name),
                    task_managers[0]
                )
                main_task = next(
                    (t for t in tasks if t.tasksmanager_id == task_manager.id),
                    None
                )
                
                if main_task:
                    # Set active task context
                    self.view_state.set_active_task(
                        task_id=main_task.id,
                        task_name=main_task.name,
                        manager_id=task_manager.id,
                        manager_name=task_manager.name
                    )
                    print(f"🟢 Set active task: {task_manager.name}-{main_task.name}")
                    
                    # Set task state
                    self.task_state = {
                        "active_tasks": [t.id for t in tasks if t.tasksmanager_id == task_manager.id],
                        "total_tasks": len(tasks),
                        "manager_id": task_manager.id,
                        "task_id": main_task.id
                    }
                else:
                    print("🔴 No main task found for task manager")
            else:
                print("🔴 No task managers found")
                
        except Exception as e:
            self.logger.error(f"Error in controller initialization: {str(e)}")
            raise

    async def get_task_tree(self) -> Optional[TreeNode]:
        """Get task hierarchy as tree structure."""
        try:
            # Debug persistence state when building tree
            print("\n🌳 Building task tree...")
            task_managers = self.global_persistence.tasksmanagers.list()
            tasks = self.global_persistence.tasks.list()
            print(f"Found {len(task_managers)} managers and {len(tasks)} tasks")
            
            if not task_managers:
                print("No task managers found")
                return None
                
            # Create root node
            root = TreeNode(UUID('00000000-0000-0000-0000-000000000000'), "Tasks", "root")
            
            # Create nodes for each task manager
            for manager in task_managers:
                try:
                    manager_node = TreeNode(
                        UUID(manager.id),
                        manager.name,
                        "manager"
                    )
                    
                    # Add tasks belonging to this manager
                    manager_tasks = [t for t in tasks if t.tasksmanager_id == manager.id]
                    print(f"Adding {len(manager_tasks)} tasks for manager {manager.name}")
                    
                    for task in manager_tasks:
                        try:
                            task_node = TreeNode(
                                UUID(task.id),
                                task.name,
                                "task"
                            )
                            manager_node.children.append(task_node)
                        except Exception as e:
                            print(f"Error adding task node {task.name}: {str(e)}")
                    
                    root.children.append(manager_node)
                except Exception as e:
                    print(f"Error processing manager {manager.name}: {str(e)}")
            
            return root
            
        except Exception as e:
            print(f"Error building task tree: {str(e)}")
            return None
        
    async def handle_chat(self, message: str) -> str:
        """Process chat messages for task management."""
        try:
            # Process message and get response
            response = await self._process_task_command(message)
            
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
                await self.state_manager.save_state("task_hierarchy", state_data)
            except Exception as e:
                self.logger.error(f"Failed to save state: {str(e)}")
            
            return response
            
        except Exception as e:
            self.logger.error(f"Chat handling error: {str(e)}")
            return f"An error occurred: {str(e)}"
            
    def show_task_dialog(self, parent_id: Optional[str] = None) -> Optional[Task]:
        """Show dialog for creating/editing tasks."""
        dialog = TaskDialog(self.view_state, self.persistence_model)
        result = dialog.render(parent_id)
        
        if result:
            # Create new task
            task = Task(
                name=result["name"],
                description=result["description"],
                parent_id=parent_id,
                metadata={
                    "status": result["status"],
                    "priority": result["priority"]
                }
            )
            return self.persistence_model.tasks.create(task)
        return None
        
    async def _process_task_command(self, message: str) -> str:
        """Process task management commands or run active task."""
        try:
            command = message.lower().strip()
            
            # Check for specific commands
            if "create task" in command:
                name = command.split("create task")[-1].strip()
                if not name:
                    raise StateValidationError("Task name is required")
                    
                task = await self._create_task(name)
                if self.task_state:
                    self.task_state["active_tasks"].append(task.id)
                return f"Created task: {task.name}"
                
            elif "list tasks" in command:
                tasks = await self._get_active_tasks()
                if not tasks:
                    return "No active tasks found"
                return "Active tasks:\n" + "\n".join(f"- {t.name}" for t in tasks)
                
            elif "help" in command:
                return """Available commands:
- create task <name>
- list tasks
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
                    response = await self.state_manager.task_runner.run_task(
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
                
            return "No active task to process message."
            
        except StateError as e:
            raise
        except Exception as e:
            self.logger.error(f"Command processing error: {str(e)}")
            raise StateError(f"Failed to process command: {str(e)}")

    async def _create_task(self, name: str) -> Task:
        """Create a task with state tracking."""
        try:
            task = Task(name=name)
            created = self.persistence_model.tasks.create(task)
            
            if self.task_state:
                await self.state_manager.update_state(
                    self.task_state.id,
                    {
                        "last_created_task": created.id,
                        "total_tasks": len(self.task_state.active_tasks) + 1
                    }
                )
            
            return created
            
        except Exception as e:
            raise StateError(f"Failed to create task: {str(e)}")

    async def _get_active_tasks(self) -> List[Task]:
        """Get active tasks from state."""
        if not self.task_state:
            raise StateNotFoundError("Task state not initialized")
            
        try:
            return [
                self.persistence_model.tasks.get(task_id)
                for task_id in self.task_state.active_tasks
                if self.persistence_model.tasks.get(task_id)
            ]
        except Exception as e:
            raise StateError(f"Failed to get active tasks: {str(e)}")
        
    def handle_node_click(self, node: TreeNode):
        """Handle tree node click events."""
        self.view_state.selected_node = node.id
        if node.type == "task":
            # Update task details or show task dialog
            self.show_task_dialog(str(node.id))
        elif node.type == "group":
            # Toggle node expansion
            node.expanded = not node.expanded
