from typing import List, Dict, Any, Optional
from pydantic import BaseModel

class ViewState(BaseModel):
    """View state model."""
    view_name: str
    task_status: Dict[str, Any] = {
        "loaded": False,
        "task_id": None,
        "task_name": None,
        "tasksmanager_id": None,
        "tasksmanager_name": None
    }
    chat_history: List[Dict[str, Any]] = []
    selected_node: Optional[str] = None
    expanded_nodes: List[str] = []

    def set_active_task(self, task_id: str, task_name: str, manager_id: str, manager_name: str):
        """Set active task context."""
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
