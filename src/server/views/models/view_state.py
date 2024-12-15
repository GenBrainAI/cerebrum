from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field
from .view_types import ViewType

class ViewState(BaseModel):
    """Base model for view state."""
    view_type: ViewType
    expanded_nodes: set[str] = Field(default_factory=set)
    selected_node: Optional[str] = None
    chat_history: List[Dict[str, Any]] = Field(default_factory=list)
    task_id: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
