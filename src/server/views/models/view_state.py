from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from .view_types import ViewType

@dataclass
class TaskContext:
    """Task context information."""
    task_id: str
    task_name: str
    manager_id: str
    manager_name: str

@dataclass
class ViewState:
    """State for view components."""
    view_type: ViewType
    chat_history: List[Dict[str, str]] = field(default_factory=list)
    selected_node_id: Optional[str] = None
    active_task: Optional[TaskContext] = None
    task_status: Dict[str, Any] = field(default_factory=lambda: {
        "loaded": False,
        "task_id": None,
        "task_name": None,
        "tasksmanager_id": None,
        "tasksmanager_name": None
    })

    def set_active_task(self, task_id: str, task_name: str, manager_id: str, manager_name: str):
        """Set the active task context."""
        self.active_task = TaskContext(
            task_id=task_id,
            task_name=task_name,
            manager_id=manager_id,
            manager_name=manager_name
        )
        self.task_status = {
            "loaded": True,
            "task_id": task_id,
            "task_name": task_name,
            "tasksmanager_id": manager_id,
            "tasksmanager_name": manager_name
        }

    def add_message(self, role: str, content: str):
        """Add a message to chat history."""
        self.chat_history.append({
            "role": role,
            "content": content
        })
