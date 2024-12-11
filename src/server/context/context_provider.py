import asyncio
from typing import List, Dict, Any, Optional
from uuid import UUID
from datetime import datetime
import traceback

from src.server.context.context_database import ContextDatabase
from src.server.context.knowledge_base import KnowledgeBase
from src.server.models.message import Message
from src.server.models.task_context_model import TaskContextManager, TaskContext, ContextReference
from src.server.context.system_context import SystemContextManager
from src.server.persistence.persistence_model_factory import PersistenceModelFactory
from src.server.models.tasks_manager import TasksManager
from src.server.models.task import Task
from src.server.context.context_analytics import ContextAnalytics
from src.server.context.vector_store import VectorStore

class ContextProvider:
    """Provides context for tasks by managing different context sources."""
    
    def __init__(self):
        self.context_db = None  # Initialize when needed
        self._vector_store = None  # Initialize when needed
        self._persistence_model = None  # Add private storage
        self.knowledge_base = KnowledgeBase()
        self.system_context = SystemContextManager()
        self.task_context_manager = TaskContextManager()
        self.context_analytics = ContextAnalytics()

    @property
    def persistence_model(self):
        """Get persistence model instance when needed"""
        if self._persistence_model is not None:
            return self._persistence_model
        return PersistenceModelFactory.persistence_model()

    @persistence_model.setter
    def persistence_model(self, value):
        """Set persistence model - mainly for testing purposes"""
        self._persistence_model = value

    async def add_system_context(
        self,
        task_id: str,
        name: str,
        content: str,
        description: Optional[str] = None,
        tags: Optional[List[str]] = None,
        format: str = "text",
        category: str = "general",
        priority: int = 0
    ) -> ContextReference:
        """Add a system context to a task."""
        # Create system context entry
        entry = self.system_context.add_context(
            name=name,
            content=content,
            description=description,
            tags=tags,
            format=format,
            category=category
        )
        
        # Add to task context
        return await self.add_context_to_task(
            task_id=task_id,
            type="system",
            source_id=str(entry.id),
            priority=priority,
            metadata={"category": category}
        )

    async def get_task_contexts(
        self, 
        task_id: str, 
        context_types: List[str] = None,
        query: Optional[str] = None
    ) -> List[Dict]:
        """Get contexts for a task, including inherited contexts from the manager.
        
        Args:
            task_id: ID of the task
            context_types: Optional list of context types to filter by
            query: Optional query string for semantic search
        """
        contexts = []
        
        # Get task context
        task_context = self.task_context_manager.get_task_context(task_id)
        if not task_context or not task_context.use_context:
            return []

        # If task inherits from manager, get manager contexts first
        if task_context.inherit_manager_context:
            # Get the task to find manager ID
            task = self.persistence_model.tasks.read(task_id)
            if task and hasattr(task, 'tasksmanager_id'):
                manager_id = task.tasksmanager_id
                manager_context_id = f"manager_{manager_id}"
                manager_context = self.task_context_manager.get_task_context(manager_context_id)
                
                if manager_context:
                    # Add manager contexts
                    for context_ref in manager_context.contexts:
                        if not context_types or context_ref.type in context_types:
                            context_data = await self._get_context_data(context_ref, query)
                            if context_data:
                                # Ensure context_data is a dictionary
                                if hasattr(context_data, 'dict'):
                                    context_data = context_data.dict()
                                contexts.append(context_data)

        # Add task-specific contexts
        for context_ref in task_context.contexts:
            if not context_types or context_ref.type in context_types:
                context_data = await self._get_context_data(context_ref, query)
                if context_data:
                    # Ensure context_data is a dictionary
                    if hasattr(context_data, 'dict'):
                        context_data = context_data.dict()
                    contexts.append(context_data)

        # Sort by priority (highest first)
        contexts.sort(key=lambda x: x.get('priority', 0), reverse=True)
        return contexts

    async def _get_context_data(
        self, 
        context_ref: ContextReference,
        query: Optional[str] = None
    ) -> Optional[Dict]:
        """Get the actual context data based on the reference type."""
        try:
            if context_ref.type == "system":
                return {
                    "id": str(context_ref.id),
                    "type": "system",
                    "content": self.system_context.get_context(context_ref.source_id),
                    "priority": context_ref.priority
                }
            elif context_ref.type == "vector":
                # For vector type, we should use the file_ids from metadata
                if context_ref.metadata and 'filters' in context_ref.metadata:
                    if query:
                        # If query provided, use semantic search
                        results = await self.context_db.search_context(
                            query,
                            filters=context_ref.metadata.get('filters'),
                            limit=1
                        )
                    else:
                        # Otherwise use direct file access
                        results = await self.context_db.vector_store.get_filtered_items(
                            filters=context_ref.metadata,
                            limit=1
                        )
                    if results:
                        return {
                            "id": str(context_ref.id),
                            "type": "vector",
                            "content": results[0]["content"],
                            "metadata": context_ref.metadata,
                            "priority": context_ref.priority
                        }
                # Fallback to search if no filters
                results = await self.context_db.search_context(
                    query or context_ref.source_id, 
                    limit=1,
                    filters=context_ref.metadata.get('filters') if context_ref.metadata else None
                )
                if results:
                    return {
                        "id": str(context_ref.id),
                        "type": "vector",
                        "content": results[0]["content"],
                        "metadata": results[0]["metadata"],
                        "priority": context_ref.priority
                    }
            elif context_ref.type == "knowledge":
                knowledge = self.knowledge_base.get_knowledge(
                    domain=context_ref.source_id
                )
                if knowledge:
                    return {
                        "id": str(context_ref.id),
                        "type": "knowledge",
                        "content": knowledge[0]["content"],
                        "metadata": knowledge[0]["metadata"],
                        "priority": context_ref.priority
                    }
            return None
        except Exception:
            return None

    def _get_manager_id(self, task_id: str) -> Optional[str]:
        """Get the manager ID for a task."""
        try:
            task = self.persistence_model.tasks.read(task_id)
            if task and task.tasksmanager_id:
                return f"manager_{task.tasksmanager_id}"
            return None
        except Exception as e:
            print(f"Error getting manager ID for task {task_id}: {str(e)}")
            return None

    async def update_task_context_config(
        self,
        task_id: str,
        use_context: Optional[bool] = None,
        inherit_manager_context: Optional[bool] = None
    ) -> bool:
        """Update task's context configuration."""
        task_context = self.task_context_manager.get_task_context(task_id)
        if not task_context:
            task_context = self.task_context_manager.create_task_context(task_id)
        
        return task_context.update_context_config(
            use_context=use_context,
            inherit_manager_context=inherit_manager_context
        )

    async def prepare_task_messages(
        self,
        task_id: str,
        messages: List[Message],
        query: Optional[str] = None
    ) -> List[Message]:
        """Prepare messages for a task by injecting relevant context."""
        try:
            # Ensure we're synced with persistence model
            task = self.persistence_model.tasks.read(task_id)
            if task:
                self.sync_task_contexts(task_id, task)
            
            # Get task context
            task_context = self.task_context_manager.get_task_context(task_id)
            if not task_context or not task_context.use_context:
                return messages

            # Get contexts based on task settings
            contexts = await self.get_task_contexts(task_id=task_id, query=query)
            
            if not contexts:
                return messages

            # Record context usage if there's a caller_id in the last message
            caller_id = None
            if messages and hasattr(messages[-1], 'metadata'):
                caller_id = messages[-1].metadata.get('caller_id')
            
            if caller_id:
                for ctx in contexts:
                    self.context_analytics.record_context_usage(
                        context_id=ctx['id'],
                        caller_id=caller_id,
                        context_type=ctx['type']
                    )

            # Format contexts by type
            context_parts = []
            for ctx in contexts:
                if ctx["type"] == "system":
                    context_parts.append(f"System Context:\n{ctx['content']}")
                elif ctx["type"] == "vector":
                    context_parts.append(f"Related Context:\n{ctx['content']}")
                elif ctx["type"] == "knowledge":
                    context_parts.append(f"Domain Knowledge:\n{ctx['content']}")

            # Create context message
            if context_parts:
                context_message = Message(
                    role="system",
                    content="Using the following context to inform your responses:\n\n" + 
                            "\n\n---\n\n".join(context_parts)
                )
                return [context_message] + messages
            
            return messages
            
        except Exception as e:
            print(f"Error preparing task messages: {str(e)}")
            return messages  # Return original messages if there's an error

    def create_task_context(self, task_id: str) -> TaskContext:
        """Create a new task context."""
        return self.task_context_manager.create_task_context(task_id)

    async def add_context_to_task(
        self,
        task_id: str,
        type: str,
        source_id: str,
        priority: int,
        metadata: Dict
    ) -> ContextReference:
        """Add a context reference to a task.
        
        Args:
            task_id: ID of the task
            type: Type of context (vector, knowledge, system)
            source_id: ID of the source content
            priority: Priority level (0-100)
            metadata: Additional metadata for the context
        """
        print(f"Debug - Adding context to task {task_id}:")  # Debug print
        print(f"Type: {type}")
        print(f"Source ID: {source_id}")
        print(f"Priority: {priority}")
        print(f"Metadata: {metadata}")
        
        # Get or create task context
        task_context = self.task_context_manager.get_task_context(task_id)
        if not task_context:
            print(f"Debug - Creating new task context for {task_id}")  # Debug print
            task_context = self.create_task_context(task_id)
        
        # Add context to task context manager
        context_ref = task_context.add_context(
            type=type,
            source_id=source_id,
            priority=priority,
            metadata=metadata
        )
        print(f"Debug - Added context reference: {context_ref}")  # Debug print

        # Update the task model in persistence
        task = self.persistence_model.tasks.read(task_id)
        if task:
            # Convert context reference to dict for task model
            context_dict = context_ref.dict()
            
            # Initialize contexts list if needed
            if not hasattr(task, 'contexts') or task.contexts is None:
                task.contexts = []
            
            # Add the new context to task's contexts
            task.contexts.append(context_dict)
            
            # Save updated task
            self.persistence_model.tasks.update(task_id, task)
            print(f"Debug - Updated task model with contexts: {task.contexts}")  # Debug print
        else:
            print(f"Warning: Task {task_id} not found in persistence model")

        return context_ref

    async def update_task_context(
        self,
        task_id: str,
        context_id: UUID,
        priority: Optional[int] = None,
        metadata: Optional[Dict] = None
    ) -> bool:
        """Update a task's context reference."""
        # Get task context from manager
        task_context = self.task_context_manager.get_task_context(task_id)
        if not task_context:
            return False

        # Update in task context manager
        updated = False
        if priority is not None:
            updated |= task_context.update_context_priority(context_id, priority)
        if metadata is not None:
            updated |= task_context.update_context_metadata(context_id, metadata)
        
        # If updated, sync with persistence model
        if updated:
            task = self.persistence_model.tasks.read(task_id)
            if task:
                # Find and update the context in task.contexts
                for ctx in task.contexts:
                    if ctx.get('id') == str(context_id):
                        if priority is not None:
                            ctx['priority'] = priority
                        if metadata is not None:
                            ctx['metadata'].update(metadata)
                        break
                
                # Save updated task
                self.persistence_model.tasks.update(task_id, task)
                print(f"Debug - Updated task context in persistence model: {task.contexts}")
        
        return updated

    async def inherit_task_contexts(
        self,
        source_task_id: str,
        target_task_id: str,
        context_types: Optional[List[str]] = None,
        override_existing: bool = False
    ) -> List[ContextReference]:
        """Inherit contexts from one task to another."""
        return await self.task_context_manager.inherit_contexts(
            source_task_id=source_task_id,
            target_task_id=target_task_id,
            context_types=context_types,
            override_existing=override_existing
        )

    async def inherit_from_parent(
        self,
        parent_id: str,
        task_id: str,
        parent_type: str = "task",
        context_types: Optional[List[str]] = None,
        override_existing: bool = False
    ) -> List[ContextReference]:
        """
        Inherit contexts from a parent (task or task manager).
        
        Args:
            parent_id: ID of parent task or task manager
            task_id: ID of target task
            parent_type: Type of parent ("task" or "manager")
            context_types: Optional list of context types to inherit
            override_existing: Whether to override existing contexts
        """
        if parent_type == "manager":
            # For task managers, use a special context ID format
            source_id = f"manager_{parent_id}"
        else:
            source_id = parent_id
            
        return await self.inherit_task_contexts(
            source_task_id=source_id,
            target_task_id=task_id,
            context_types=context_types,
            override_existing=override_existing
        )

    async def enhance_task_context(
        self,
        task_id: str,
        base_context: Dict
    ) -> Dict:
        """Enhance context with task-specific information"""
        enhanced_context = base_context.copy()
        
        # Get task contexts
        task_contexts = await self.get_task_contexts(task_id)
        
        # Add to context
        enhanced_context["task_contexts"] = task_contexts
        
        return enhanced_context

    def load_state(self, state_data: Dict):
        """Load context state from saved state data."""
        if 'task_contexts' in state_data:
            for task_id, context_data in state_data['task_contexts'].items():
                task_context = self.task_context_manager.create_task_context(task_id)
                task_context.use_context = context_data.get('use_context', True)
                task_context.inherit_manager_context = context_data.get('inherit_manager_context', True)
                task_context.contexts = [
                    ContextReference(**ctx) if isinstance(ctx, dict) else ctx 
                    for ctx in context_data.get('contexts', [])
                ]

    def get_state(self) -> Dict:
        """Get current context state for saving."""
        return {
            'task_contexts': {
                task_id: {
                    'use_context': context.use_context,
                    'inherit_manager_context': context.inherit_manager_context,
                    'contexts': [ctx.dict() if hasattr(ctx, 'dict') else ctx for ctx in context.contexts]
                }
                for task_id, context in self.task_context_manager.task_contexts.items()
            }
        }

    def sync_task_contexts(self, task_id: str, task: Task) -> None:
        """Sync contexts between task model and context manager."""
        # Get or create task context
        task_context = self.task_context_manager.get_task_context(task_id)
        if not task_context:
            task_context = self.task_context_manager.create_task_context(task_id)
        
        # Sync configuration
        task_context.use_context = task.use_context
        task_context.inherit_manager_context = task.inherit_manager_context
        
        # Sync contexts from task model to context manager
        if task.contexts:
            task_context.contexts = [
                ContextReference(**ctx) if isinstance(ctx, dict) else ctx 
                for ctx in task.contexts
            ]

    def sync_manager_contexts(self, manager_id: str, manager: TasksManager) -> None:
        """Sync contexts between task manager model and context manager."""
        # Get or create manager context
        manager_context_id = f"manager_{manager_id}"
        manager_context = self.task_context_manager.get_task_context(manager_context_id)
        if not manager_context:
            manager_context = self.task_context_manager.create_task_context(manager_context_id)
        
        # Sync configuration
        manager_context.use_context = manager.use_context
        
        # Sync contexts from manager model to context manager
        if manager.contexts:
            manager_context.contexts = [
                ContextReference(**ctx) if isinstance(ctx, dict) else ctx 
                for ctx in manager.contexts
            ]

    def update_task_model(self, task_id: str, task: Task) -> None:
        """Update task model with current context state."""
        task_context = self.task_context_manager.get_task_context(task_id)
        if task_context:
            print(f"Debug - Updating task model {task_id}")  # Debug print
            print(f"Context count: {len(task_context.contexts)}")
            
            task.use_context = task_context.use_context
            task.inherit_manager_context = task_context.inherit_manager_context
            
            # Convert contexts to dictionaries
            contexts = [
                ctx.dict() if hasattr(ctx, 'dict') else ctx 
                for ctx in task_context.contexts
            ]
            print(f"Debug - Converted contexts: {contexts}")  # Debug print
            
            task.contexts = contexts
            print(f"Debug - Task contexts after update: {task.contexts}")  # Debug print

    def update_manager_model(self, manager_id: str, manager: TasksManager) -> None:
        """Update task manager model with current context state."""
        manager_context_id = f"manager_{manager_id}"
        manager_context = self.task_context_manager.get_task_context(manager_context_id)
        if manager_context:
            manager.use_context = manager_context.use_context
            manager.contexts = [
                ctx.dict() if hasattr(ctx, 'dict') else ctx 
                for ctx in manager_context.contexts
            ]

    async def remove_context_from_task(self, task_id: str, context_id: str) -> bool:
        """
        Remove a context from a task.
        
        Args:
            task_id (str): The ID of the task
            context_id (str): The ID of the context to remove
            
        Returns:
            bool: True if context was removed successfully, False otherwise
        """
        try:
            # Get the persistence model
            persistence_model = PersistenceModelFactory.persistence_model()
            
            # Get the task
            task = persistence_model.tasks.read(task_id)
            if not task:
                raise ValueError(f"Task {task_id} not found")
            
            # Convert task to dictionary if needed
            task_dict = task.dict() if hasattr(task, 'dict') else task
            
            # Initialize contexts list if it doesn't exist
            if 'contexts' not in task_dict:
                task_dict['contexts'] = []
            
            # Find and remove the context
            task_dict['contexts'] = [
                ctx for ctx in task_dict['contexts'] 
                if str(ctx.get('id', '')) != str(context_id)
            ]
            
            # Update the task
            persistence_model.tasks.update(task_id, task_dict)
            
            # Also remove from vector store if it's a vector context
            try:
                vector_store = VectorStore()
                await vector_store.remove_context(context_id)
            except Exception as e:
                print(f"Warning: Could not remove from vector store: {e}")
            
            return True
            
        except Exception as e:
            print(f"Error removing context: {e}")
            raise Exception(f"Failed to remove context: {str(e)}")

    async def initialize(self):
        """Initialize context provider and sync with persistence model."""
        try:
            # Initialize context DB if needed
            if self.context_db is None:
                self.context_db = ContextDatabase()
            
            # Get persistence model
            persistence_model = self.persistence_model
            
            # Sync task contexts
            tasks = persistence_model.tasks.list()
            for task in tasks:
                self.sync_task_contexts(task.id, task)
            
            # Sync manager contexts
            managers = persistence_model.tasksmanagers.list()
            for manager in managers:
                self.sync_manager_contexts(manager.id, manager)
            
            print("Context provider initialized and synced with persistence model")
        except Exception as e:
            print(f"Error initializing context provider: {str(e)}")
            raise