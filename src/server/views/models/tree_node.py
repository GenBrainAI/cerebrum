from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from uuid import UUID, uuid4

class TreeNode(BaseModel):
    """Generic tree node model for all views."""
    id: UUID = Field(default_factory=uuid4)
    name: str
    type: str
    parent_id: Optional[UUID] = None
    children: List['TreeNode'] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    expanded: bool = False