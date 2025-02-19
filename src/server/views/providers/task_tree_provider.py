from typing import Optional, List, Dict, Any
from uuid import UUID, uuid4
from ...models.task import Task
from ..models.tree_node import TreeNode
from ..components.tree_component import TreeComponent

class TaskTreeProvider:
    """Converts task hierarchies to TreeNode structures."""
    
    def __init__(self, persistence_model):
        self.persistence_model = persistence_model
        
    def get_task_tree(self, root_task_id: Optional[str] = None) -> TreeNode:
        """Build tree structure from tasks."""
        # Get all tasks
        tasks = self.persistence_model.tasks.list()
        
        # Create root node if not specified
        if not root_task_id:
            root = TreeNode(
                id=uuid4(),
                name="All Tasks",
                node_type="root"
            )
        else:
            task = self.persistence_model.tasks.read(root_task_id)
            root = self._task_to_node(task)
            
        # Build tree structure
        self._build_task_tree(root, tasks)
        return root
        
    def _task_to_node(self, task: Task) -> TreeNode:
        """Convert a task to a TreeNode."""
        return TreeNode(
            id=UUID(task.id) if isinstance(task.id, str) else task.id,
            name=task.name,
            node_type="task",
            metadata={
                "description": task.description,
                "status": getattr(task, "status", "pending"),
                "priority": getattr(task, "priority", "medium")
            }
        )
        
    def _build_task_tree(self, parent: TreeNode, tasks: List[Task]):
        """Recursively build task tree structure."""
        for task in tasks:
            if getattr(task, "parent_id", None) == str(parent.id):
                node = self._task_to_node(task)
                parent.children.append(node)
                self._build_task_tree(node, tasks) 