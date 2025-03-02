from typing import List, Dict, Any, Optional
import traceback
import logging
import os

# Initialize logger
logger = logging.getLogger(__name__)

from ..context.context_database import ContextDatabase
from ..context.knowledge_base import KnowledgeBase
from ..models.message import Message
from ..models.task_context_model import TaskContextManager, ContextReference
from ..persistence.persistence_model_factory import PersistenceModelFactory
from ..context.chroma_vector_store import ChromaVectorStore, VectorStoreConfig
from ..context.code_catalog import CodeCatalog

# Define standard paths for vector store
GLOBAL_VECTOR_STORE_PATH = "persistent_state/global_context/vector_store"
CONTEXT_VECTOR_STORE_PATH = "persistent_state/context/vector_store"
CODEBASE_VECTOR_STORE_PATH = "persistent_state/codebase/vector_store"

# Re-export ContextReference for backwards compatibility
__all__ = ['ContextProvider', 'ContextReference']

class ContextProvider:
    """Provider for managing and accessing different types of context."""
    
    def __init__(self, is_global: bool = False):
        """Initialize context provider."""
        self.is_global = is_global
        self.task_context_manager = TaskContextManager()
        
        # Use standardized paths for vector store
        vector_store_path = get_vector_store_path("global" if is_global else "default")
            
        self.vector_store = ChromaVectorStore(
            config=VectorStoreConfig(
                persist_directory=vector_store_path,
                collection_name="context",
                embedding_model="text-embedding-3-small"
            ),
            base_path=vector_store_path
        )
        
        self.code_catalog = CodeCatalog()
        self.knowledge_base = KnowledgeBase(
            base_path="persistent_state/global_knowledge_base" if is_global else "persistent_state/knowledge_base"
        )
        self.context_db = ContextDatabase()
        self._persistence_model = None
        
    @property
    def persistence_model(self):
        """Get persistence model instance when needed."""
        if self._persistence_model is None:
            self._persistence_model = PersistenceModelFactory.persistence_model()
        return self._persistence_model

    @persistence_model.setter
    def persistence_model(self, value):
        """Set persistence model - mainly for testing purposes."""
        self._persistence_model = value
        
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
        if self.is_global:
            return []  # Global provider doesn't track task associations
        return await self.task_context_manager.get_task_contexts(task_id, context_types)
        
    async def get_manager_contexts(self, manager_id: str) -> List[Dict[str, Any]]:
        """Get all contexts associated with a tasks manager."""
        if self.is_global:
            return []  # Global provider doesn't track manager associations
        return await self.task_context_manager.get_manager_contexts(manager_id)
        
    async def add_context_to_task(
        self,
        task_id: str,
        type: str,
        source_id: str,
        metadata: Optional[Dict[str, Any]] = None,
        priority: int = 50
    ) -> str:
        """Add a context to a task."""
        if self.is_global:
            raise ValueError("Cannot add task associations to global context")
        return await self.task_context_manager.add_context_to_task(
            task_id=task_id,
            type=type,
            source_id=source_id,
            metadata=metadata,
            priority=priority
        )
        
    async def add_context_to_manager(
        self,
        manager_id: str,
        type: str,
        source_id: str,
        metadata: Optional[Dict[str, Any]] = None,
        priority: int = 50
    ) -> str:
        """Add a context to a tasks manager."""
        if self.is_global:
            raise ValueError("Cannot add manager associations to global context")
        return await self.task_context_manager.add_context_to_manager(
            manager_id=manager_id,
            type=type,
            source_id=source_id,
            metadata=metadata,
            priority=priority
        )
        
    async def remove_context_from_task(self, task_id: str, context_id: str) -> bool:
        """Remove a context from a task.
        
        Args:
            task_id: ID of the task to remove context from
            context_id: ID of the context to remove
            
        Returns:
            bool: True if context was removed successfully, False otherwise
        """
        try:
            # 1. Remove from task context manager
            removed = await self.task_context_manager.remove_context_from_task(task_id, context_id)
            if not removed:
                return False
                
            # 2. Remove from persistence model
            task = self.persistence_model.tasks.read(task_id)
            if task:
                # Remove context from task's contexts list
                if hasattr(task, 'contexts') and task.contexts:
                    task.contexts = [
                        ctx for ctx in task.contexts 
                        if str(ctx.get('id', '')) != str(context_id)
                    ]
                    
                    # Update task in persistence model
                    self.persistence_model.tasks.update(task_id, task)
                
            # 3. Remove from context database if it exists
            if self.context_db:
                await self.context_db.remove_context(task_id, context_id)
                
            # 4. Remove from vector store if it's a vector context
            try:
                if self.vector_store:
                    await self.vector_store.remove_context(context_id)
            except Exception as e:
                print(f"Warning: Could not remove from vector store: {e}")
                
            # 5. Save state to ensure persistence
            if hasattr(self.persistence_model, 'save_state'):
                await self.persistence_model.save_state()
                
            return True
                
        except Exception as e:
            logging.error(f"Error removing context from task: {str(e)}")
            traceback.print_exc()
            return False
        
    async def remove_context_from_manager(self, manager_id: str, context_id: str) -> bool:
        """Remove a context from a tasks manager."""
        if self.is_global:
            raise ValueError("Cannot remove manager associations from global context")
        return await self.task_context_manager.remove_context_from_manager(manager_id, context_id)
        
    async def get_contexts_by_source(
        self,
        source_id: str,
        type: str
    ) -> List[Dict[str, Any]]:
        """Get all contexts that reference a particular source."""
        if self.is_global:
            return []  # Global provider doesn't track associations
        return await self.task_context_manager.get_contexts_by_source(source_id, type)
        
    async def remove_contexts_by_source(
        self,
        source_id: str,
        type: str
    ) -> bool:
        """Remove all contexts that reference a particular source."""
        if self.is_global:
            return True  # No associations to remove in global context
        return await self.task_context_manager.remove_contexts_by_source(source_id, type)
        
    async def update_task_context_config(
        self,
        task_id: str,
        use_context: bool = True,
        inherit_manager_context: bool = True
    ) -> bool:
        """Update task context configuration."""
        if self.is_global:
            raise ValueError("Cannot update task configuration in global context")
        return await self.task_context_manager.update_task_context_config(
            task_id=task_id,
            use_context=use_context,
            inherit_manager_context=inherit_manager_context
        )
        
    def sync_task_contexts(self, task_id: str, task: Any) -> None:
        """Sync task contexts with persistence model."""
        if not self.is_global:
            self.task_context_manager.sync_task_contexts(task_id, task)
            
    def sync_manager_contexts(self, manager_id: str, manager: Any) -> None:
        """Sync manager contexts with persistence model."""
        if not self.is_global:
            self.task_context_manager.sync_manager_contexts(manager_id, manager)
            
    async def get_all_contexts(self) -> List[Dict[str, Any]]:
        """Get all contexts in the system."""
        print("\n🔍 Getting all contexts from the system")
        contexts = []
        
        # Get vector store contexts first
        try:
            print("  Getting vector store contexts...")
            # Force reload indices to ensure we have the latest
            self.vector_store._reload_indices()
            
            # Get all indices
            indices = await self.vector_store.list_indices()
            
            # Process indices from list_indices
            for idx in indices:
                if idx["name"].startswith("vs_"):
                    print(f"    Found vector store: {idx['name']}")
                    contexts.append({
                        "id": idx["name"],
                        "type": "vector",
                        "content": f"Vector store index with {idx['count']} documents",
                        "metadata": {
                            "name": idx["name"].replace("vs_", ""),
                            "description": idx["description"],
                            "document_count": idx["count"]
                        }
                    })
        except Exception as e:
            print(f"❌ Error getting vector store contexts: {str(e)}")
            logging.error(f"Error getting vector store contexts: {str(e)}")
            
        # Get knowledge base contexts
        try:
            print("  Getting knowledge base contexts...")
            kb_contexts = await self.knowledge_base.get_knowledge()
            for ctx in kb_contexts:
                # print(f"    Found knowledge base context: {ctx['id']}")
                contexts.append({
                    "id": ctx["id"],
                    "type": "knowledge",
                    "content": ctx["content"],
                    "metadata": ctx["metadata"],
                    "created_at": ctx["created_at"]
                })
        except Exception as e:
            print(f"❌ Error getting knowledge base contexts: {str(e)}")
            logging.error(f"Error getting knowledge base contexts: {str(e)}")
            
        # Get code catalog contexts
        try:
            print("  Getting code catalog contexts...")
            code_contexts = self.code_catalog.get_all_files()
            for ctx in code_contexts:
                print(f"    Found code context: {ctx['path']}")
                contexts.append({
                    "id": ctx["path"],
                    "type": "code",
                    "content": ctx["content"],
                    "metadata": {
                        "path": ctx["path"],
                        "size": ctx["size"],
                        "last_modified": ctx["last_modified"]
                    }
                })
        except Exception as e:
            print(f"❌ Error getting code catalog contexts: {str(e)}")
            logging.error(f"Error getting code catalog contexts: {str(e)}")
            
        print(f"\n✅ Found total of {len(contexts)} contexts")
        return contexts

    async def add_system_context(
        self,
        task_id: str,
        name: str,
        content: str,
        description: Optional[str] = None,
        tags: Optional[List[str]] = None,
        priority: int = 90
    ) -> str:
        """Add system context to a task.
        
        Args:
            task_id: ID of the task to add context to
            name: Name of the context
            content: Content of the context
            description: Optional description of the context
            tags: Optional list of tags
            priority: Priority of the context (default: 90 for system context)
            
        Returns:
            str: ID of the created context
        """
        try:
            # Add to knowledge base first
            source_id = await self.knowledge_base.add_entry(
                content=content,
                domain="system",
                metadata={
                    "name": name,
                    "description": description,
                    "tags": tags or [],
                    "type": "system"
                }
            )
            
            # Add context reference
            await self.add_context_to_task(
                task_id=task_id,
                type="system",
                source_id=source_id,
                metadata={
                    "name": name,
                    "description": description,
                    "tags": tags or []
                },
                priority=priority
            )
            
            return source_id
            
        except Exception as e:
            logger.error(f"Error adding system context: {str(e)}")
            raise

    async def prepare_task_messages(
        self,
        task_id: str,
        messages: List[Message]
    ) -> List[Message]:
        """Prepare messages for a task by incorporating relevant context.
        
        Args:
            task_id: ID of the task to prepare messages for
            messages: List of messages to prepare
            
        Returns:
            List[Message]: List of prepared messages with context
        """
        # Get task context
        task_context = self.task_context_manager.get_task_context(task_id)
        if not task_context or not task_context.use_context:
            return messages
            
        # Get all contexts for the task
        contexts = await self.get_task_contexts(task_id)
        if not contexts:
            return messages
            
        # Sort contexts by priority (higher priority first)
        contexts.sort(key=lambda x: x.get("priority", 0), reverse=True)
            
        # Prepare system message with context
        context_content = "\n\n".join([
            f"{ctx.get('metadata', {}).get('content', '')}"
            for ctx in contexts
            if ctx.get('metadata', {}).get('content')
        ])
            
        if context_content:
            # Add context as a system message at the start
            prepared_messages = [Message(role="system", content=context_content)]
            prepared_messages.extend(messages)
            return prepared_messages
            
        return messages

def get_vector_store_path(context_type: str = "default") -> str:
    """Get the appropriate vector store path based on context type."""
    if context_type == "global":
        return GLOBAL_VECTOR_STORE_PATH
    elif context_type == "codebase":
        return CODEBASE_VECTOR_STORE_PATH
    else:
        return os.path.join(CONTEXT_VECTOR_STORE_PATH, context_type)