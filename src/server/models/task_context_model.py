from typing import Dict, List, Optional, Any
from uuid import UUID
import logging
from datetime import datetime
from crewai import Task
from pydantic import BaseModel, Field
from uuid import uuid4
import traceback

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

    def sync_task_contexts(self, task_id: str, task: Task) -> None:
        """Sync task contexts with persistence model."""
        try:
            print(f"\n🔄 Syncing task contexts for {task_id}")
            # Get or create task context
            task_context = self.get_task_context(task_id)
            if not task_context:
                print("  Creating new task context")
                task_context = self.create_task_context(task_id)
            else:
                print("  Using existing task context")
            
            # Update context configuration from task
            print("  Checking task attributes:")
            print(f"    has use_context: {hasattr(task, 'use_context')}")
            print(f"    has inherit_manager_context: {hasattr(task, 'inherit_manager_context')}")
            task_context.use_context = getattr(task, 'use_context', True)
            task_context.inherit_manager_context = getattr(task, 'inherit_manager_context', True)
            print(f"    use_context: {task_context.use_context}")
            print(f"    inherit_manager_context: {task_context.inherit_manager_context}")
            
            # Sync contexts from task if they exist
            print("  Checking task contexts:")
            print(f"    has contexts attribute: {hasattr(task, 'contexts')}")
            if hasattr(task, 'contexts'):
                print(f"    contexts value: {task.contexts}")
            
            if hasattr(task, 'contexts') and task.contexts:
                print(f"  Found {len(task.contexts)} contexts to sync")
                task_context.contexts = [
                    ContextReference(**ctx) if isinstance(ctx, dict) else ctx 
                    for ctx in task.contexts
                ]
                print("  Contexts synced successfully")
            else:
                print("  No contexts found to sync")
            
        except Exception as e:
            print(f"❌ Error syncing task contexts: {str(e)}")
            print(f"  Stack trace: {traceback.format_exc()}")
            logging.error(f"Error syncing task contexts: {str(e)}")

    def sync_manager_contexts(self, manager_id: str, manager: Any) -> None:
        """Sync manager contexts with persistence model."""
        try:
            # Get or create manager context
            manager_context = self.get_task_context(manager_id)
            if not manager_context:
                manager_context = self.create_task_context(manager_id)
            
            # Sync contexts from manager if they exist
            if hasattr(manager, 'contexts') and manager.contexts:
                manager_context.contexts = [
                    ContextReference(**ctx) if isinstance(ctx, dict) else ctx 
                    for ctx in manager.contexts
                ]
            
        except Exception as e:
            logging.error(f"Error syncing manager contexts: {str(e)}")

    async def get_manager_contexts(self, manager_id: str) -> List[Dict[str, Any]]:
        """Get all contexts associated with a tasks manager."""
        try:
            manager_context = self.get_task_context(manager_id)
            if not manager_context:
                return []
            
            return [{
                "id": str(ctx.id),
                "type": ctx.type,
                "source_id": ctx.source_id,
                "metadata": ctx.metadata,
                "priority": ctx.priority,
                "created_at": ctx.created_at,
                "manager_id": manager_id
            } for ctx in manager_context.contexts]
            
        except Exception as e:
            logging.error(f"Error getting manager contexts: {str(e)}")
            return []

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

        # Get task from persistence model and update its contexts
        try:
            from ..persistence.persistence_model_factory import PersistenceModelFactory
            persistence_model = PersistenceModelFactory.persistence_model()
            if persistence_model:
                task = persistence_model.tasks.read(task_id)
                if task:
                    # Initialize contexts list if needed
                    if not hasattr(task, 'contexts') or task.contexts is None:
                        task.contexts = []
                    
                    # Add context reference to task
                    task.contexts.append(context_ref.dict())
                    
                    # Update task in persistence model
                    persistence_model.tasks.update(task_id, task)
                    print(f"✅ Added context {context_ref.id} to task {task_id} in persistence model")
        except Exception as e:
            print(f"❌ Error updating task in persistence model: {str(e)}")
            print(f"Stack trace: {traceback.format_exc()}")
        
        return str(context_ref.id)
        
    async def get_contexts_by_source(
        self,
        source_id: str,
        type: str
    ) -> List[Dict[str, Any]]:
        """Get all contexts that reference a particular source."""
        # print(f"\n🔍 Looking for contexts with source_id={source_id}, type={type}")
        contexts = []
        for task_id, task_context in self.task_contexts.items():
            # print(f"  Checking task {task_id}")
            for context in task_context.contexts:
                # print(f"    Checking context: source_id={context.source_id}, type={context.type}")
                if context.source_id == source_id and context.type == type:
                    # print(f"    ✅ Found matching context")
                    contexts.append({
                        "id": str(context.id),
                        "task_id": task_context.task_id,
                        "type": context.type,
                        "source_id": context.source_id,
                        "metadata": context.metadata,
                        "priority": context.priority
                    })
                else:
                    # print(f"    ❌ No match")
                    pass
        # print(f"  Found {len(contexts)} matching contexts")
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

    async def remove_context_from_task(self, task_id: str, context_id: str) -> bool:
        """Remove a context from a task.
        
        Args:
            task_id: ID of the task to remove context from
            context_id: ID of the context to remove
            
        Returns:
            bool: True if context was removed successfully, False otherwise
        """
        try:
            # Get task context
            task_context = self.get_task_context(task_id)
            if not task_context:
                return False

            # Convert context_id to UUID if it's a string
            context_uuid = UUID(context_id) if isinstance(context_id, str) else context_id
                
            # Remove from task context
            return task_context.remove_context(context_uuid)
            
        except Exception as e:
            logging.error(f"Error removing context from task: {str(e)}")
            return False