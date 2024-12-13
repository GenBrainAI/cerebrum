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

class TaskContext:
    def __init__(self, task_id: str):
        self.task_id = task_id
        self.contexts: List[ContextReference] = []
        self.use_context: bool = True
        self.inherit_manager_context: bool = True

    def add_context(self, type: str, source_id: str, priority: int = 50, metadata: Dict = None) -> ContextReference:
        """Add a context reference to this task context."""
        context_ref = ContextReference(
            task_id=self.task_id,
            type=type,
            source_id=source_id,
            priority=priority,
            metadata=metadata or {}
        )
        self.contexts.append(context_ref)
        return context_ref

    def remove_context(self, context_id: UUID) -> bool:
        """Remove a context reference by its ID.
        
        Args:
            context_id: UUID of the context to remove
            
        Returns:
            bool: True if context was found and removed, False otherwise
        """
        initial_length = len(self.contexts)
        self.contexts = [ctx for ctx in self.contexts if ctx.id != context_id]
        return len(self.contexts) < initial_length

    def dict(self) -> Dict:
        """Convert to dictionary for serialization."""
        return {
            "task_id": self.task_id,
            "use_context": self.use_context,
            "inherit_manager_context": self.inherit_manager_context,
            "contexts": [
                ctx.dict() if hasattr(ctx, 'dict') else ctx 
                for ctx in self.contexts
            ]
        }

    def update_context_config(
        self,
        use_context: Optional[bool] = None,
        inherit_manager_context: Optional[bool] = None
    ) -> bool:
        """Update context configuration."""
        updated = False
        if use_context is not None and use_context != self.use_context:
            self.use_context = use_context
            updated = True
        if inherit_manager_context is not None and inherit_manager_context != self.inherit_manager_context:
            self.inherit_manager_context = inherit_manager_context
            updated = True
        return updated

    def update_context_priority(self, context_id: UUID, priority: int) -> bool:
        """Update priority of a specific context."""
        for ctx in self.contexts:
            if ctx.id == context_id:
                ctx.priority = priority
                return True
        return False

    def update_context_metadata(self, context_id: UUID, metadata: Dict) -> bool:
        """Update metadata of a specific context."""
        for ctx in self.contexts:
            if ctx.id == context_id:
                ctx.metadata.update(metadata)
                return True
        return False

class TaskContextManager:
    def __init__(self):
        self.task_contexts: Dict[str, TaskContext] = {}

    def get_task_context(self, task_id: str) -> Optional[TaskContext]:
        return self.task_contexts.get(task_id)

    def create_task_context(self, task_id: str) -> TaskContext:
        context = TaskContext(task_id)
        self.task_contexts[task_id] = context
        return context