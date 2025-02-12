from typing import List, Dict, Optional, Union, Any
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

    async def add_context_to_task(
        self,
        task_id: str,
        type: str,
        source_id: str,
        metadata: Optional[Dict[str, Any]] = None,
        priority: int = 50
    ) -> str:
        """Add a context to a task.
        
        Args:
            task_id: ID of the task to add context to
            type: Type of context (knowledge, vector, system, etc.)
            source_id: ID of the source content
            metadata: Additional metadata about the context
            priority: Priority of the context (default: 50)
            
        Returns:
            str: ID of the created context reference
        """
        # Get or create task context
        task_context = self.get_task_context(task_id)
        if not task_context:
            task_context = self.create_task_context(task_id)
            
        # Add context reference
        context_ref = task_context.add_context(
            type=type,
            source_id=source_id,
            priority=priority,
            metadata=metadata or {}
        )
        
        return str(context_ref.id)
        
    async def get_contexts_by_source(
        self,
        source_id: str,
        type: str
    ) -> List[Dict[str, Any]]:
        """Get all contexts that reference a particular source."""
        contexts = []
        for task_context in self.task_contexts.values():
            for context in task_context.contexts:
                if context.source_id == source_id and context.type == type:
                    contexts.append({
                        "id": str(context.id),
                        "task_id": task_context.task_id,
                        "type": context.type,
                        "source_id": context.source_id,
                        "metadata": context.metadata,
                        "priority": context.priority
                    })
        return contexts
        
    async def remove_contexts_by_source(
        self,
        source_id: str,
        type: str
    ) -> bool:
        """Remove all contexts that reference a particular source."""
        removed = False
        for task_context in self.task_contexts.values():
            initial_length = len(task_context.contexts)
            task_context.contexts = [
                ctx for ctx in task_context.contexts 
                if not (ctx.source_id == source_id and ctx.type == type)
            ]
            if len(task_context.contexts) < initial_length:
                removed = True
        return removed

    async def get_task_contexts(
        self,
        task_id: str,
        context_types: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """Get all contexts associated with a task.
        
        Args:
            task_id: ID of the task to get contexts for
            context_types: Optional list of context types to filter by
            
        Returns:
            List[Dict[str, Any]]: List of context dictionaries with their metadata
        """
        task_context = self.get_task_context(task_id)
        if not task_context:
            return []
            
        # Get task's own contexts
        contexts = []
        for context in task_context.contexts:
            if context_types and context.type not in context_types:
                continue
            contexts.append({
                "id": str(context.id),
                "type": context.type,
                "source_id": context.source_id,
                "metadata": context.metadata,
                "priority": context.priority,
                "created_at": context.created_at
            })
            
        # If inheritance is enabled, get manager contexts
        if task_context.inherit_manager_context and task_id.startswith("task"):
            # Extract manager ID from task ID (e.g., "task1" -> "manager1")
            manager_id = task_id.replace("task", "manager")
            manager_context = self.get_task_context(manager_id)
            if manager_context:
                for context in manager_context.contexts:
                    if context_types and context.type not in context_types:
                        continue
                    contexts.append({
                        "id": str(context.id),
                        "type": context.type,
                        "source_id": context.source_id,
                        "metadata": context.metadata,
                        "priority": context.priority,
                        "created_at": context.created_at
                    })
                    
        # Sort contexts by priority (highest first)
        contexts.sort(key=lambda x: x["priority"], reverse=True)
        return contexts