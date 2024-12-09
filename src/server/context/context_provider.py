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


class ContextProvider:
    """Provides context for tasks by managing different context sources."""
    
    def __init__(self):
        self.context_db = ContextDatabase()
        self.knowledge_base = KnowledgeBase()
        self.system_context = SystemContextManager()
        self.task_context_manager = TaskContextManager()
        self.persistence_model = PersistenceModelFactory.persistence_model()

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

    async def get_task_contexts(self, task_id: str, context_types: List[str] = None) -> List[Dict]:
        """Get contexts for a task, including inherited contexts from the manager."""
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
                            context_data = await self._get_context_data(context_ref)
                            if context_data:
                                # Ensure context_data is a dictionary
                                if hasattr(context_data, 'dict'):
                                    context_data = context_data.dict()
                                contexts.append(context_data)

        # Add task-specific contexts
        for context_ref in task_context.contexts:
            if not context_types or context_ref.type in context_types:
                context_data = await self._get_context_data(context_ref)
                if context_data:
                    # Ensure context_data is a dictionary
                    if hasattr(context_data, 'dict'):
                        context_data = context_data.dict()
                    contexts.append(context_data)

        # Sort by priority (highest first)
        contexts.sort(key=lambda x: x.get('priority', 0), reverse=True)
        return contexts

    async def _get_context_data(self, context_ref: ContextReference) -> Optional[Dict]:
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
                    context_ref.source_id, 
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
        task_context = self.task_context_manager.get_task_context(task_id)
        if not task_context or not task_context.use_context:
            return messages

        # Get contexts based on task settings
        contexts = await self.get_task_contexts(task_id=task_id)
        
        if not contexts:
            return messages

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
        
        task_context = self.task_context_manager.get_task_context(task_id)
        if not task_context:
            print(f"Debug - Creating new task context for {task_id}")  # Debug print
            task_context = self.create_task_context(task_id)
        
        context_ref = task_context.add_context(
            type=type,
            source_id=source_id,
            priority=priority,
            metadata=metadata
        )
        print(f"Debug - Added context reference: {context_ref}")  # Debug print
        return context_ref

    async def update_task_context(
        self,
        task_id: str,
        context_id: UUID,
        priority: Optional[int] = None,
        metadata: Optional[Dict] = None
    ) -> bool:
        """Update a task's context reference."""
        task_context = self.task_context_manager.get_task_context(task_id)
        if not task_context:
            return False

        updated = False
        if priority is not None:
            updated |= task_context.update_context_priority(context_id, priority)
        if metadata is not None:
            updated |= task_context.update_context_metadata(context_id, metadata)
        
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