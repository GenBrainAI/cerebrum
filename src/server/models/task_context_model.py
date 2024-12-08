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
    use_context: bool = Field(
        default=True, 
        description="Whether to use context enhancement"
    )
    inherit_manager_context: bool = Field(
        default=True,
        description="Whether to use manager context as fallback"
    )
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    def add_context(self, type: str, source_id: str, priority: int = 0, metadata: Dict = None) -> ContextReference:
        """Add a new context reference."""
        print(f"Debug - Adding context to task {self.task_id}:")
        print(f"  Type: {type}")
        print(f"  Source ID: {source_id}")
        print(f"  Priority: {priority}")
        print(f"  Metadata: {metadata}")
        
        context = ContextReference(
            type=type,
            source_id=source_id,
            priority=priority,
            metadata=metadata or {}
        )
        self.contexts.append(context)
        self.updated_at = datetime.now()
        
        print(f"Debug - Current contexts after adding:")
        for ctx in self.contexts:
            print(f"  - {ctx}")
        
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

    def update_context_priority(self, context_id: UUID, new_priority: int) -> bool:
        """Update the priority of a context reference."""
        for context in self.contexts:
            if context.id == context_id:
                context.priority = new_priority
                self.updated_at = datetime.now()
                return True
        return False

    def update_context_metadata(self, context_id: UUID, metadata: Dict) -> bool:
        """Update the metadata of a context reference."""
        for context in self.contexts:
            if context.id == context_id:
                context.metadata.update(metadata)
                self.updated_at = datetime.now()
                return True
        return False

    def get_context_by_id(self, context_id: UUID) -> Optional[ContextReference]:
        """Get a specific context reference by ID."""
        for context in self.contexts:
            if context.id == context_id:
                return context
        return None

    def update_context_config(
        self,
        use_context: Optional[bool] = None,
        inherit_manager_context: Optional[bool] = None
    ) -> bool:
        """Update context configuration."""
        updated = False
        if use_context is not None:
            self.use_context = use_context
            updated = True
        if inherit_manager_context is not None:
            self.inherit_manager_context = inherit_manager_context
            updated = True
        if updated:
            self.updated_at = datetime.now()
        return updated

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
        """Get or create task context."""
        if task_id not in self.task_contexts:
            print(f"Debug - Creating new task context for {task_id}")
            self.task_contexts[task_id] = TaskContext(task_id=task_id)
        return self.task_contexts[task_id]
    
    def delete_task_context(self, task_id: str) -> bool:
        """Delete a task context."""
        if task_id in self.task_contexts:
            del self.task_contexts[task_id]
            return True
        return False
    
    def get_active_contexts(self) -> List[TaskContext]:
        """Get all active task contexts."""
        return [tc for tc in self.task_contexts.values() if tc.active]

    async def inherit_contexts(
        self, 
        source_task_id: str, 
        target_task_id: str,
        context_types: Optional[List[str]] = None,
        override_existing: bool = False
    ) -> List[ContextReference]:
        """
        Inherit contexts from one task to another.
        
        Args:
            source_task_id: Task to inherit from
            target_task_id: Task to inherit to
            context_types: Optional list of context types to inherit
            override_existing: Whether to override existing contexts
        """
        source_context = self.get_task_context(source_task_id)
        if not source_context:
            raise ValueError(f"Source task {source_task_id} not found")
            
        target_context = self.get_task_context(target_task_id)
        if not target_context:
            target_context = self.create_task_context(target_task_id)
            
        inherited_refs = []
        
        for context_ref in source_context.contexts:
            # Skip if context type not in requested types
            if context_types and context_ref.type not in context_types:
                continue
                
            # Skip if context already exists and not overriding
            if not override_existing and any(
                ref.source_id == context_ref.source_id and 
                ref.type == context_ref.type 
                for ref in target_context.contexts
            ):
                continue
                
            # Create new reference with same properties
            new_ref = target_context.add_context(
                type=context_ref.type,
                source_id=context_ref.source_id,
                priority=context_ref.priority,
                metadata=context_ref.metadata.copy()
            )
            inherited_refs.append(new_ref)
            
        return inherited_refs

    def get_or_create_task_context(self, task_id: str) -> TaskContext:
        """Get existing task context or create new one."""
        task_context = self.get_task_context(task_id)
        if not task_context:
            task_context = self.create_task_context(task_id)
        return task_context