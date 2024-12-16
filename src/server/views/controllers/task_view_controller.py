from typing import Optional, Dict, Any
from uuid import UUID
from datetime import datetime
from ...models.exceptions import StateError, StateNotFoundError
from ...models.task import Task
from ..models.view_state import ViewState
from ..models.view_types import ViewType
from ...models.specialized_state import StateType, TaskGenerationState
from ..data.task_tree_provider import TaskTreeProvider
from ..components.dialogs.task_dialog import TaskDialog
from ..state.state_manager import ViewStateManager
from ..components.tree_component import TreeNode
from ...utils.state_loader import StateLoader

class TaskHierarchyController:
    """Controller for task hierarchy view with specialized state support."""
    
    def __init__(self, persistence_model):
        self.persistence_model = persistence_model
        self.view_state = ViewState(view_type=ViewType.TASK_HIERARCHY)
        self.tree_provider = TaskTreeProvider(persistence_model)
        self.state_manager = ViewStateManager(persistence_model)
        self.task_state: Optional[TaskGenerationState] = None
        
        # Load existing state
        state_ids = StateLoader.get_state_ids("task_management")
        if state_ids:
            self.task_manager_id = state_ids["task_manager_id"]
            self.task_id = state_ids["task_id"]
        
    async def initialize(self):
        """Initialize controller with specialized state."""
        # Try to load existing state first
        state_file = StateLoader.get_state_file("task_management")
        if state_file and state_file.exists():
            self.task_state = await self.state_manager.load_specialized_state(state_file)
        
        # Create new state if none exists
        if not self.task_state:
            self.task_state = await self.state_manager.create_specialized_state(
                state_type=StateType.TASK_GENERATION,
                name="Task Generation State",
                initial_data={
                    "active_view": ViewType.TASK_HIERARCHY.value,
                    "selected_task": None
                }
            )

    async def get_task_tree(self) -> Optional[TreeNode]:
        """Get task hierarchy as tree structure with state tracking."""
        try:
            tasks = self.persistence_model.tasks.list()
            
            # Update task state
            if self.task_state:
                self.task_state.active_tasks = [task.id for task in tasks]
                await self.state_manager._persist_specialized_state(self.task_state)
            
            # Create root node
            root = TreeNode(UUID('00000000-0000-0000-0000-000000000000'), "Tasks", "root")
            
            # Build tree structure
            task_map = {task.id: task for task in tasks}
            for task in tasks:
                node = TreeNode(UUID(task.id), task.name, "task")
                if task.parent_id and task.parent_id in task_map:
                    # Find parent node
                    parent_id = UUID(task.parent_id)
                    parent_node = next(
                        (n for n in root.traverse() if n.id == parent_id), 
                        None
                    )
                    if parent_node:
                        parent_node.children.append(node)
                else:
                    # Add to root if no parent
                    root.children.append(node)
                    
            return root
        except Exception as e:
            print(f"Error building task tree: {str(e)}")
            return None
        
    async def handle_chat(self, message: str) -> str:
        """Process chat messages for task management."""
        try:
            # Add message to chat history
            self.view_state.chat_history.append({
                "role": "user",
                "content": message
            })
            
            # Update task state
            if self.task_state:
                await self.task_state.update({
                    "last_message": message,
                    "timestamp": datetime.now().isoformat()
                })
            
            # Process command
            try:
                response = await self._process_task_command(message)
            except StateError as e:
                response = f"State error: {str(e)}"
            except Exception as e:
                response = f"Error processing command: {str(e)}"
                self.logger.error(f"Command processing error: {str(e)}")
            
            # Add response to history
            self.view_state.chat_history.append({
                "role": "assistant",
                "content": response
            })
            
            # Save state
            try:
                await self.state_manager.save_state(ViewType.TASK_HIERARCHY, self.view_state)
            except StateError as e:
                self.logger.error(f"Failed to save state: {str(e)}")
                return f"Command processed but state save failed: {str(e)}"
            
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
        """Process task management commands with state tracking."""
        try:
            command = message.lower().strip()
            
            if "create task" in command:
                name = command.split("create task")[-1].strip()
                if not name:
                    raise StateValidationError("Task name is required")
                    
                task = await self._create_task(name)
                if self.task_state:
                    self.task_state.active_tasks.append(task.id)
                    await self.state_manager._persist_specialized_state(self.task_state)
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
                
            return f"Unknown command. Type 'help' for available commands."
            
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
