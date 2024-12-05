from typing import List, Dict, Optional, Union
from pydantic import BaseModel, Field
from datetime import datetime
from uuid import UUID, uuid4

class ContextReference(BaseModel):
    """Reference to a specific context source."""
    id: UUID = Field(default_factory=uuid4)
    type: str  # "vector", "knowledge", "system"
    source_id: str
    metadata: Dict = Field(default_factory=dict)
    priority: int = Field(default=0)  # Higher number = higher priority
    created_at: datetime = Field(default_factory=datetime.now)

class TaskContext(BaseModel):
    """Collection of context references for a task."""
    id: UUID = Field(default_factory=uuid4)
    task_id: str
    contexts: List[ContextReference] = Field(default_factory=list)
    active: bool = True
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    def add_context(self, type: str, source_id: str, priority: int = 0, metadata: Dict = None) -> ContextReference:
        """Add a new context reference."""
        context = ContextReference(
            type=type,
            source_id=source_id,
            priority=priority,
            metadata=metadata or {}
        )
        self.contexts.append(context)
        self.updated_at = datetime.now()
        return context

    def remove_context(self, context_id: UUID) -> bool:
        """Remove a context reference by ID."""
        initial_length = len(self.contexts)
        self.contexts = [c for c in self.contexts if c.id != context_id]
        removed = len(self.contexts) < initial_length
        if removed:
            self.updated_at = datetime.now()
        return removed

    def get_contexts_by_type(self, type: str) -> List[ContextReference]:
        """Get all contexts of a specific type."""
        return [c for c in self.contexts if c.type == type]

    def get_sorted_contexts(self) -> List[ContextReference]:
        """Get contexts sorted by priority (highest first)."""
        return sorted(self.contexts, key=lambda x: x.priority, reverse=True)

class TaskContextManager(BaseModel):
    """Manager for task contexts."""
    id: UUID = Field(default_factory=uuid4)
    task_contexts: Dict[str, TaskContext] = Field(default_factory=dict)
    
    def create_task_context(self, task_id: str) -> TaskContext:
        """Create a new task context."""
        if task_id in self.task_contexts:
            raise ValueError(f"Task context already exists for task {task_id}")
            
        context = TaskContext(task_id=task_id)
        self.task_contexts[task_id] = context
        return context
    
    def get_task_context(self, task_id: str) -> Optional[TaskContext]:
        """Get task context by task ID."""
        return self.task_contexts.get(task_id)
    
    def delete_task_context(self, task_id: str) -> bool:
        """Delete a task context."""
        if task_id in self.task_contexts:
            del self.task_contexts[task_id]
            return True
        return False
    
    def get_active_contexts(self) -> List[TaskContext]:
        """Get all active task contexts."""
        return [tc for tc in self.task_contexts.values() if tc.active]