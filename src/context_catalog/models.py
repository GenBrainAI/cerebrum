"""Core data models for the Context Catalog System."""

from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any, Union
from pydantic import BaseModel, Field

from .metadata import (
    ContextMetadata,
    StorageInfo
)


class SourceType(str, Enum):
    """Types of context sources."""
    KNOWLEDGE = "knowledge"
    CODE = "code"
    VECTOR = "vector"
    SYSTEM = "system"


class AccessRecord(BaseModel):
    """Record of context access."""
    
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    user_id: str
    operation: str
    metadata: Dict[str, Any] = Field(default_factory=dict)


class UsageStats(BaseModel):
    """Statistics for context usage."""
    
    access_count: int = 0
    last_accessed: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    operation_counts: Dict[str, int] = Field(default_factory=dict)


class ContextRelationships(BaseModel):
    """Tracks relationships between context entries."""
    
    dependencies: List[str] = Field(default_factory=list)  # IDs of contexts this entry depends on
    dependents: List[str] = Field(default_factory=list)    # IDs of contexts that depend on this
    related: List[str] = Field(default_factory=list)       # IDs of related contexts
    derived_from: Optional[str] = None                     # ID of parent context if derived
    versions: List[str] = Field(default_factory=list)      # IDs of other versions


class ValidationStatus(BaseModel):
    """Validation status for a context entry."""
    
    is_valid: bool = True
    last_validated: datetime = Field(default_factory=datetime.utcnow)
    validation_errors: List[str] = Field(default_factory=list)
    validation_warnings: List[str] = Field(default_factory=list)


class TreeNode(BaseModel):
    """Tree node structure for hierarchical organization."""
    
    name: str
    data: Optional[Any] = None
    children: List['TreeNode'] = Field(default_factory=list)
    parent: Optional['TreeNode'] = None
    
    def add_child(self, child: 'TreeNode') -> None:
        """Add a child node."""
        child.parent = self
        self.children.append(child)
    
    def find_child(self, name: str) -> Optional['TreeNode']:
        """Find a child node by name."""
        for child in self.children:
            if child.name == name:
                return child
        return None
    
    def get_path(self) -> List[str]:
        """Get the path from root to this node."""
        path = []
        current = self
        while current:
            path.insert(0, current.name)
            current = current.parent
        return path
    
    class Config:
        arbitrary_types_allowed = True


class ContextEntry(BaseModel):
    """A context entry in the catalog."""
    id: str
    metadata: ContextMetadata
    content: Optional[str] = None
    embeddings: Optional[List[float]] = None
    storage_info: StorageInfo
    relationships: Dict[str, List[str]] = Field(default_factory=dict)
    usage_stats: UsageStats = Field(default_factory=UsageStats)
    access_history: List[AccessRecord] = Field(default_factory=list)
    task_managers: List[Any] = Field(default_factory=list)  # Type will be TaskManager
    tasks: List[Any] = Field(default_factory=list)  # Type will be Task
    
    class Config:
        arbitrary_types_allowed = True


# Rebuild models to ensure proper initialization
AccessRecord.model_rebuild()
UsageStats.model_rebuild()
ContextRelationships.model_rebuild()
ContextEntry.model_rebuild() 