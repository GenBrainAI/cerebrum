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
    data: Optional[Dict[str, Any]] = None

    def add_child(self, child: 'TreeNode') -> None:
        """Add a child node to this node."""
        child.parent_id = self.id
        self.children.append(child)

    def remove_child(self, child_id: UUID) -> bool:
        """Remove a child node by its ID."""
        for i, child in enumerate(self.children):
            if child.id == child_id:
                self.children.pop(i)
                return True
        return False

    def find_child(self, child_id: UUID) -> Optional['TreeNode']:
        """Find a child node by its ID."""
        for child in self.children:
            if child.id == child_id:
                return child
            found = child.find_child(child_id)
            if found:
                return found
        return None

    def to_dict(self) -> Dict[str, Any]:
        """Convert the node to a dictionary representation."""
        return {
            "id": str(self.id),
            "name": self.name,
            "type": self.type,
            "parent_id": str(self.parent_id) if self.parent_id else None,
            "children": [child.to_dict() for child in self.children],
            "metadata": self.metadata,
            "expanded": self.expanded,
            "data": self.data
        }