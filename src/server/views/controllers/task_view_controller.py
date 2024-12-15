from typing import Optional
from uuid import UUID
from ...models.task import Task
from ..models.view_state import ViewState
from ..models.view_types import ViewType
from ..data.task_tree_provider import TaskTreeProvider
from ..components.dialogs.task_dialog import TaskDialog
from ..state.state_manager import ViewStateManager
from ..components.tree_component import TreeNode

class TaskHierarchyController:
    """Controller for task hierarchy view."""
    
    def __init__(self, persistence_model):
        self.persistence_model = persistence_model
        self.view_state = ViewState(view_type=ViewType.TASK_HIERARCHY)
        self.tree_provider = TaskTreeProvider(persistence_model)
        self.state_manager = ViewStateManager(persistence_model)
        
    async def get_task_tree(self) -> Optional[TreeNode]:
        """Get task hierarchy as tree structure."""
        try:
            # Get all tasks from persistence model
            tasks = self.persistence_model.tasks.list()
            
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
            
            # TODO: Implement task management logic
            response = await self._process_task_command(message)
            
            # Add response to chat history
            self.view_state.chat_history.append({
                "role": "assistant",
                "content": response
            })
            
            # Save state
            self.state_manager.save_state(ViewType.TASK_HIERARCHY, self.view_state)
            
            return response
            
        except Exception as e:
            return f"Error processing message: {str(e)}"
            
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
        """Process task management commands."""
        # TODO: Implement natural language command processing
        return "Task management commands not yet implemented"
        
    def handle_node_click(self, node: TreeNode):
        """Handle tree node click events."""
        self.view_state.selected_node = node.id
        if node.type == "task":
            # Update task details or show task dialog
            self.show_task_dialog(str(node.id))
        elif node.type == "group":
            # Toggle node expansion
            node.expanded = not node.expanded
