from typing import List, Dict, Any, Optional
from uuid import UUID
from .view_types import ViewType
from ...models.agent import Agentic

class ViewState:
    """State for view components."""
    
    def __init__(self, view_type: ViewType):
        self.view_type = view_type
        self.expanded_nodes = set()
        self.selected_node_id: Optional[UUID] = None
        self.selected_agentic: Optional[Agentic] = None
        self.selected_group: Optional[Dict[str, Any]] = None
        self.chat_history: List[Dict[str, Any]] = []
        self.show_dialog = False
        self.dialog_type = None
        self.template = None
        self.task_id: Optional[str] = None
        self.task_name: Optional[str] = None
        self.tasksmanager_id: Optional[str] = None
        self.tasksmanager_name: Optional[str] = None
        self.metadata: Dict[str, Any] = {}
        self.tree_data = None
        self.agent_status = {
            "loaded": False,
            "error": "No agent selected"
        }
        
    @property
    def task_status(self) -> Dict[str, Any]:
        """Get the current task status information."""
        if not self.task_id or not self.tasksmanager_id:
            return {
                "loaded": False,
                "error": "No task selected"
            }
        return {
            "loaded": True,
            "task_id": self.task_id,
            "task_name": self.task_name,
            "tasksmanager_id": self.tasksmanager_id,
            "tasksmanager_name": self.tasksmanager_name,
            "error": None
        }
        
    def set_active_task(self, task_id: str, task_name: str, manager_id: str, manager_name: str):
        """Set the active task and manager information."""
        self.task_id = task_id
        self.task_name = task_name
        self.tasksmanager_id = manager_id
        self.tasksmanager_name = manager_name
        
    def add_message(self, role: str, content: str):
        """Add a message to the chat history."""
        self.chat_history.append({
            "role": role,
            "content": content
        })
        
    def clear_chat(self):
        """Clear the chat history."""
        self.chat_history = []
        
    def set_selected_node(self, node_id: UUID):
        """Set the selected node ID."""
        self.selected_node_id = node_id
        
    def toggle_node_expansion(self, node_id: UUID):
        """Toggle node expansion state."""
        if node_id in self.expanded_nodes:
            self.expanded_nodes.remove(node_id)
        else:
            self.expanded_nodes.add(node_id)

    def set_active_agent(self, agent_id: str, agent_name: str):
        """Set the active agent information."""
        self.agent_status = {
            "loaded": True,
            "agent_id": agent_id,
            "agent_name": agent_name
        }

    def clear_active_agent(self):
        """Clear the active agent information."""
        self.agent_status = {
            "loaded": False,
            "error": "No agent selected"
        }
