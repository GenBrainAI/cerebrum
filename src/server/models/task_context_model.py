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
        self.use_context = True
        self.inherit_manager_context = True
        self.contexts: List[ContextReference] = []

class TaskContextManager:
    def __init__(self):
        self.task_contexts: Dict[str, TaskContext] = {}

    def get_task_context(self, task_id: str) -> Optional[TaskContext]:
        return self.task_contexts.get(task_id)

    def create_task_context(self, task_id: str) -> TaskContext:
        context = TaskContext(task_id)
        self.task_contexts[task_id] = context
        return context