from typing import List, Dict, Any, Optional, Tuple
import traceback
import logging
import uuid
import os
import re
from unittest.mock import AsyncMock  # Add this import for test compatibility

# Initialize logger
logger = logging.getLogger(__name__)

from ..context.context_database import ContextDatabase
from ..context.knowledge_base import KnowledgeBase
from ..models.message import Message
from ..models.task_context_model import TaskContextManager, ContextReference
from ..persistence.persistence_model_factory import PersistenceModelFactory
from ..context.vector_store import VectorStore
from ..context.code_catalog import CodeCatalog
from src.server.context.system_context import SystemContextManager
from src.server.persistence.persistence_model import PersistenceModelBase

# Re-export ContextReference for backwards compatibility
__all__ = ['ContextProvider', 'ContextReference']

class ContextProvider:
    """Provider for managing and accessing different types of context."""
    
    def __init__(self):
        """Initialize context provider."""
        self.task_context_manager = TaskContextManager()
        # Initialize vector store with the correct path
        self.vector_store = VectorStore(base_path="persistent_state/chroma_db")
        self.code_catalog = CodeCatalog()
        self.knowledge_base = KnowledgeBase("persistent_state/knowledge_base")
        # Initialize context database with the same path
        self.context_db = ContextDatabase(persist_directory="persistent_state/chroma_db")
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
        print(f"🔍 DEBUG: get_task_contexts called for task_id={task_id}, context_types={context_types}")
        contexts = await self.task_context_manager.get_task_contexts(task_id, context_types)
        print(f"🔍 DEBUG: Retrieved {len(contexts)} contexts for task_id={task_id}")
        return contexts
        
    def get_task_context(self, task_id: str) -> Optional[Any]:
        """Get the TaskContext object for a task.
        
        Args:
            task_id: ID of the task to get context for
            
        Returns:
            Optional[TaskContext]: The task context object or None if not found
        """
        print(f"🔍 DEBUG: get_task_context called for task_id={task_id}")
        context = self.task_context_manager.get_task_context(task_id)
        print(f"🔍 DEBUG: Task context found: {context is not None}")
        return context
        
    async def get_manager_contexts(self, manager_id: str) -> List[Dict[str, Any]]:
        """Get all contexts associated with a tasks manager."""
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
        return await self.task_context_manager.remove_context_from_manager(manager_id, context_id)
        
    async def get_contexts_by_source(
        self,
        source_id: str,
        type: str
    ) -> List[Dict[str, Any]]:
        """Get all contexts that reference a particular source."""
        return await self.task_context_manager.get_contexts_by_source(source_id, type)
        
    async def remove_contexts_by_source(
        self,
        source_id: str,
        type: str
    ) -> bool:
        """Remove all contexts that reference a particular source."""
        return await self.task_context_manager.remove_contexts_by_source(source_id, type)
        
    async def update_task_context_config(
        self,
        task_id: str,
        use_context: bool = True,
        inherit_manager_context: bool = True
    ) -> bool:
        """Update task context configuration."""
        return await self.task_context_manager.update_task_context_config(
            task_id=task_id,
            use_context=use_context,
            inherit_manager_context=inherit_manager_context
        )
        
    def sync_task_contexts(self, task_id: str, task: Any) -> None:
        """Sync task contexts with the task_context_manager."""
        print(f"\n🔄 DEBUG: sync_task_contexts called for task_id={task_id}")
        
        if not task:
            print(f"⚠️ DEBUG: No task provided for sync_task_contexts")
            return
            
        try:
            # Delegate to task_context_manager
            self.task_context_manager.sync_task_contexts(task_id, task)
            
            # Verify sync was successful
            task_context = self.task_context_manager.get_task_context(task_id)
            if task_context:
                print(f"✅ DEBUG: Task context synced successfully. Context has {len(task_context.contexts)} contexts")
                
                # Log context details for debugging
                for i, ctx in enumerate(task_context.contexts):
                    print(f"📄 DEBUG: Context {i+1}:")
                    print(f"  - Type: {getattr(ctx, 'type', 'unknown')}")
                    print(f"  - Source ID: {getattr(ctx, 'source_id', 'unknown')}")
                    print(f"  - Priority: {getattr(ctx, 'priority', 0)}")
                    metadata = getattr(ctx, 'metadata', {})
                    print(f"  - Metadata: {metadata}")
                    if hasattr(metadata, 'get'):
                        index_name = metadata.get('index_name')
                        if index_name:
                            print(f"  - Index Name: {index_name}")
            else:
                print(f"⚠️ DEBUG: Task context not found after sync")
        except Exception as e:
            print(f"❌ DEBUG: Error in sync_task_contexts: {str(e)}")
            import traceback
            print(f"❌ DEBUG: Traceback: {traceback.format_exc()}")
            
    def sync_manager_contexts(self, manager_id: str, manager: Any) -> None:
        """Sync manager contexts with the task_context_manager."""
        print(f"\n🔄 DEBUG: sync_manager_contexts called for manager_id={manager_id}")
        
        if not manager:
            print(f"⚠️ DEBUG: No manager provided for sync_manager_contexts")
            return
            
        try:
            # Delegate to task_context_manager
            self.task_context_manager.sync_task_contexts(manager_id, manager)
            
            # Verify sync was successful
            manager_context = self.task_context_manager.get_task_context(manager_id)
            if manager_context:
                print(f"✅ DEBUG: Manager context synced successfully. Context has {len(manager_context.contexts)} contexts")
                
                # Log context details for debugging
                for i, ctx in enumerate(manager_context.contexts):
                    print(f"📄 DEBUG: Context {i+1}:")
                    print(f"  - Type: {getattr(ctx, 'type', 'unknown')}")
                    print(f"  - Source ID: {getattr(ctx, 'source_id', 'unknown')}")
                    print(f"  - Priority: {getattr(ctx, 'priority', 0)}")
                    metadata = getattr(ctx, 'metadata', {})
                    print(f"  - Metadata: {metadata}")
                    if hasattr(metadata, 'get'):
                        index_name = metadata.get('index_name')
                        if index_name:
                            print(f"  - Index Name: {index_name}")
            else:
                print(f"⚠️ DEBUG: Manager context not found after sync")
        except Exception as e:
            print(f"❌ DEBUG: Error in sync_manager_contexts: {str(e)}")
            import traceback
            print(f"❌ DEBUG: Traceback: {traceback.format_exc()}")
            
    async def get_all_contexts(self) -> List[Dict[str, Any]]:
        """Get all contexts in the system."""
        print("\n🔍 Getting all contexts from the system")
        contexts = []
        
        # Get vector store contexts first
        try:
            print("  Getting vector store contexts...")
            # Force reload indices to ensure we have the latest
            self.vector_store._reload_indices()
            print(f"  Vector store indices after reload: {self.vector_store.indices}")
            
            # Get all indices
            indices = await self.vector_store.list_indices()
            print(f"  Raw indices from list_indices: {[idx['name'] for idx in indices]}")
            
            # Check ChromaDB collections directly
            collections = self.vector_store.client.list_collections()
            print(f"  Raw ChromaDB collections: {[c.name for c in collections]}")
            
            # Check if there are any collections with vs_ prefix
            vs_collections = [c for c in collections if c.name.startswith('vs_')]
            print(f"  ChromaDB collections with vs_ prefix: {[c.name for c in vs_collections]}")
            
            # If we have vs_ collections but no indices, try to add them manually
            if vs_collections and not indices:
                print("  Adding missing vs_ collections to indices...")
                for collection in vs_collections:
                    try:
                        # Add to indices dictionary
                        self.vector_store.indices[collection.name] = self.vector_store.client.get_collection(
                            name=collection.name,
                            embedding_function=self.vector_store.embedding_function
                        )
                        # Add to contexts list
                        contexts.append({
                            "id": collection.name,
                            "type": "vector",
                            "content": f"Vector store index with documents",
                            "metadata": {
                                "name": collection.name.replace("vs_", ""),
                                "description": collection.metadata.get("description", ""),
                                "document_count": collection.count()
                            }
                        })
                        print(f"    Added missing vector store: {collection.name}")
                    except Exception as e:
                        print(f"    Error adding collection {collection.name}: {str(e)}")
            
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

    async def get_contexts(
        self,
        query: str,
        task_id: str,
        model: Optional[str] = None,
        max_tokens: Optional[int] = None,
        message_history: Optional[List[Dict[str, Any]]] = None
    ) -> List[Dict[str, Any]]:
        """Get all contexts relevant to a query for a task."""
        # Calculate available tokens based on model and message history
        available_tokens = self._calculate_available_tokens(model=model, max_tokens=max_tokens, message_history=message_history)
        print(f"📊 DEBUG: Available tokens for context: {available_tokens}")
        remaining_tokens = available_tokens
        
        # Get task-specific contexts
        task_contexts = await self._get_task_specific_contexts(task_id)
        
        # Add task contexts to final contexts list
        contexts = []
        contexts, task_contexts, available_tokens, used_tokens = self._add_contexts_within_limit(
            contexts, task_contexts, available_tokens, 0
        )
        remaining_tokens = available_tokens - used_tokens
        print(f"📊 DEBUG: After adding task contexts: {used_tokens} tokens used, {remaining_tokens} remaining")
        
        # Search for relevant contexts in the context database
        try:
            vector_context_dicts = []
            if query:
                # Get the appropriate vector index name
                if task_id:
                    index_name = self._get_vector_index_name_from_task(task_id)
                    if not index_name:
                        index_name = self._find_relevant_index_name()
                else:
                    index_name = self._find_relevant_index_name()
                
                # Search for relevant contexts
                vector_contexts = await self.context_db.search_context(query, limit=5, index_name=index_name)
                if vector_contexts:
                    vector_context_dicts = self._convert_vector_results_to_contexts(vector_contexts)
            
            # Add vector contexts to final contexts list based on priority and token limit
            contexts, vector_context_dicts, available_tokens, used_tokens = self._add_contexts_within_limit(
                contexts, vector_context_dicts, available_tokens, used_tokens
            )
            print(f"📊 DEBUG: After adding vector contexts: {used_tokens} tokens used, {available_tokens - used_tokens} remaining")
            
        except Exception as e:
            print(f"❌ ERROR in get_contexts: {str(e)}")
            import traceback
            print(traceback.format_exc())
        
        # Sort contexts by priority (highest first)
        contexts.sort(key=lambda x: x.get('priority', 0), reverse=True)
        
        return contexts
    
    def _calculate_available_tokens(
        self,
        model: Optional[str] = None,
        max_tokens: Optional[int] = None,
        message_history: Optional[List[Dict[str, Any]]] = None
    ) -> int:
        """Backward compatibility method for tests.
        
        Calls _calculate_token_budget and returns just the available_tokens value.
        
        Args:
            model: The model to use for token calculation
            max_tokens: Maximum tokens to use for contexts
            message_history: Optional message history for token calculation
            
        Returns:
            int: Available tokens for context
        """
        token_info = self._calculate_token_budget(model=model, max_tokens=max_tokens, message_history=message_history)
        return token_info['available_tokens']
    
    def _calculate_token_budget(
        self,
        model: Optional[str] = None,
        max_tokens: Optional[int] = None,
        message_history: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, int]:
        """Calculate token budget for context based on model and message history."""
        # Default token limits by model
        model_limits = {
            "gpt-3.5-turbo": 4096,
            "gpt-3.5-turbo-16k": 16384,
            "gpt-4": 8192,
            "gpt-4-32k": 32768,
            "gpt-4-turbo": 128000,
            "gpt-4o": 128000,
            "gpt-4o-mini": 128000,
            "claude-3-opus-20240229": 200000,
            "claude-3-sonnet-20240229": 180000,
            "claude-3-haiku-20240307": 150000,
            "default": 4096
        }
        
        # If max_tokens is provided, use it
        if max_tokens is not None:
            total_tokens = max_tokens
        # Otherwise, use model-based limit
        elif model and model in model_limits:
            total_tokens = model_limits[model]
        else:
            total_tokens = model_limits["default"]
        
        print(f"📊 DEBUG: Total tokens for model: {total_tokens}")
        
        # Subtract tokens used by message history if provided
        if message_history:
            message_tokens = sum(self._estimate_token_count(msg.get("content", "")) for msg in message_history)
            # Reserve some tokens for the response
            response_tokens = 1000
            available_tokens = max(0, total_tokens - message_tokens - response_tokens)
            print(f"📊 DEBUG: Message history uses {message_tokens} tokens, reserving {response_tokens} for response")
        else:
            # If no message history, reserve a portion for other parts of the context
            available_tokens = int(total_tokens * 0.7)  # Use 70% of available tokens for context
            print(f"📊 DEBUG: No message history, using 70% of total tokens: {available_tokens}")
        
        return {
            'total_tokens': total_tokens,
            'available_tokens': available_tokens
        }
    
    async def _get_task_specific_contexts(self, task_id: str) -> List[Dict[str, Any]]:        
        """Get task-specific contexts for a task."""
        print(f"🔍 DEBUG: Getting task-specific contexts for task_id={task_id}")
        
        if not task_id:
            print("⚠️ DEBUG: No task_id provided, returning empty contexts")
            return []
                        
        # Check if the task exists in the persistence model
        if self.persistence_model:
            try:
                task = self.persistence_model.tasks.read(task_id)
                if task:
                    print(f"✅ DEBUG: Found task {task_id} in persistence model: {task.name}")
                    # Task contexts should already be synced in get_contexts
                else:
                    print(f"⚠️ DEBUG: Task {task_id} not found in persistence model")
            except Exception as e:
                print(f"❌ DEBUG: Error checking task in persistence model: {str(e)}")
        else:
            print("⚠️ DEBUG: No persistence model available")
            
        # Get contexts from task context manager
        contexts = await self.get_task_contexts(task_id)
        print(f"📊 DEBUG: Retrieved {len(contexts)} contexts from task context manager")
        
        # Log context details for debugging
        for i, ctx in enumerate(contexts):
            print(f"📄 DEBUG: Context {i+1}:")
            print(f"  - Type: {ctx.get('type')}")
            print(f"  - Source ID: {ctx.get('source_id')}")
            print(f"  - Priority: {ctx.get('priority')}")
            print(f"  - Metadata: {ctx.get('metadata', {})}")
            
        return contexts
    
    def _get_vector_index_name_from_task(self, task_id: str) -> Optional[str]:
        """Extract vector index name from task contexts."""
        try:
            print(f"🔍 DEBUG: Looking for vector index name in task with ID {task_id}")
            
            if not task_id:
                print("⚠️ DEBUG: No task_id provided")
                return None
                
            if not self.persistence_model:
                print(f"⚠️ DEBUG: No persistence model available")
                return None
            
            # Try to get the task from persistence model
            try:
                task = self.persistence_model.tasks.read(task_id)
            except Exception as e:
                print(f"❌ DEBUG: Error reading task from persistence model: {str(e)}")
                return None
                
            if not task:
                print(f"⚠️ DEBUG: Task {task_id} not found")
                return None
                
            print(f"📄 DEBUG: Retrieved task: {task.name}")
            
            # If task has contexts, look for vector contexts
            if hasattr(task, 'contexts') and task.contexts:
                print(f"📊 DEBUG: Task has {len(task.contexts)} contexts")
                
                # Log all contexts for debugging
                for i, ctx in enumerate(task.contexts):
                    if isinstance(ctx, dict):
                        print(f"📄 DEBUG: Context {i+1} (dict):")
                        print(f"  - Type: {ctx.get('type')}")
                        print(f"  - Metadata: {ctx.get('metadata', {})}")
                    else:
                        print(f"📄 DEBUG: Context {i+1} (object):")
                        print(f"  - Type: {getattr(ctx, 'type', 'unknown')}")
                        print(f"  - Metadata: {getattr(ctx, 'metadata', {})}")
                
                # Look for vector contexts
                for ctx in task.contexts:
                    if isinstance(ctx, dict) and ctx.get('type') == 'vector':
                        # Extract index name from metadata
                        metadata = ctx.get('metadata', {})
                        if 'index_name' in metadata:
                            index_name = metadata['index_name']
                            print(f"✅ DEBUG: Found vector index {index_name} associated with task {task_id}")
                            return index_name
                        else:
                            print(f"⚠️ DEBUG: Vector context found but no index_name in metadata: {metadata}")
                    elif hasattr(ctx, 'type') and ctx.type == 'vector':
                        # Extract index name from metadata for object-style contexts
                        metadata = getattr(ctx, 'metadata', {})
                        if hasattr(metadata, 'get'):
                            index_name = metadata.get('index_name')
                            if index_name:
                                print(f"✅ DEBUG: Found vector index {index_name} associated with task {task_id}")
                                return index_name
                        elif isinstance(metadata, dict) and 'index_name' in metadata:
                            index_name = metadata['index_name']
                            print(f"✅ DEBUG: Found vector index {index_name} associated with task {task_id}")
                            return index_name
                        else:
                            print(f"⚠️ DEBUG: Vector context found but no index_name in metadata: {metadata}")
            else:
                print(f"⚠️ DEBUG: Task has no contexts or contexts attribute")
                                
            print("⚠️ DEBUG: No vector index name found")
            return None
        except Exception as e:
            print(f"❌ DEBUG: Error retrieving vector index name: {str(e)}")
            import traceback
            print(f"❌ DEBUG: Traceback: {traceback.format_exc()}")
            return None
    
    def _find_relevant_index_name(self) -> Optional[str]:
        """Find a relevant index name when no specific one is found in task."""
        try:
            print("🔍 DEBUG: Finding relevant index name")
            
            # Check if we have a context database
            if not hasattr(self, 'context_db') or not self.context_db:
                print("⚠️ DEBUG: No context database available")
                return None
                
            # Check if we have a vector store
            if not hasattr(self.context_db, 'vector_store') or not self.context_db.vector_store:
                print("⚠️ DEBUG: No vector store available")
                return None
                
            # Get available indices
            vector_store = self.context_db.vector_store
            if hasattr(vector_store, 'list_indices'):
                try:
                    indices = vector_store.indices
                    if not indices:
                        print("⚠️ DEBUG: No indices available in vector store")
                        return None
                        
                    print(f"📊 DEBUG: Available indices: {list(indices.keys())}")
                    
                    # Prioritize certain indices if they exist
                    priority_indices = ["brain", "code", "documentation"]
                    for index_name in priority_indices:
                        prefixed_name = f"vs_{index_name}" if not index_name.startswith("vs_") else index_name
                        if prefixed_name in indices:
                            print(f"✅ DEBUG: Found priority index: {prefixed_name}")
                            return prefixed_name
                    
                    # If no priority index found, return the first one
                    first_index = next(iter(indices.keys()))
                    print(f"✅ DEBUG: Using first available index: {first_index}")
                    return first_index
                except Exception as e:
                    print(f"❌ DEBUG: Error listing indices: {str(e)}")
            else:
                print("⚠️ DEBUG: Vector store doesn't have list_indices method")
            
            # Fallback to default
            print("🔄 DEBUG: Falling back to default 'brain' index")
            return "brain"  # Default to "brain" index
        except Exception as e:
            print(f"❌ DEBUG: Error finding relevant index: {str(e)}")
            import traceback
            print(f"❌ DEBUG: Traceback: {traceback.format_exc()}")
            return None
    
    def _convert_vector_results_to_contexts(self, vector_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Convert vector search results to context dictionaries."""
        contexts = []
        for ctx in vector_results:
            relevance = ctx.get("relevance", 0.5)
            contexts.append({
                "type": "vector",
                "source_id": ctx.get("metadata", {}).get("id", str(uuid.uuid4())),
                "content": ctx.get("content", ""),
                "metadata": ctx.get("metadata", {}),
                "priority": int(relevance * 100)  # Convert relevance to priority
            })
        return contexts
    
    def _add_contexts_within_limit(
        self, 
        existing_contexts: List[Dict[str, Any]], 
        new_contexts: List[Dict[str, Any]], 
        available_tokens: int, 
        used_tokens: int
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], int, int]:
        """Add contexts within the token limit.
        
        Args:
            existing_contexts: List of contexts already selected
            new_contexts: List of new contexts to potentially add
            available_tokens: Total available tokens
            used_tokens: Tokens already used
            
        Returns:
            Tuple containing:
            - updated list of contexts
            - remaining new contexts not added
            - updated available tokens
            - updated used tokens
        """
        remaining_contexts = []
        for ctx in new_contexts:
            content = ctx.get("content", "")
            token_count = self._estimate_token_count(content)
            
            if used_tokens + token_count <= available_tokens:
                print(f"✅ DEBUG: Adding context: type={ctx.get('type')}, source={ctx.get('source_id')}")
                existing_contexts.append(ctx)
                used_tokens += token_count
            else:
                print(f"⚠️ DEBUG: Skipping context due to token limit: {token_count} tokens needed, {available_tokens - used_tokens} remaining")
                remaining_contexts.append(ctx)
        
        return existing_contexts, remaining_contexts, available_tokens, used_tokens
    
    def _estimate_token_count(self, text: str) -> int:
        """Estimate token count for a text string.
        
        This is a simple approximation. For more accurate counts,
        consider using a tokenizer like tiktoken.
        """
        if not text:
            return 0
            
        # Simple approximation: 4 characters per token
        return len(text) // 4 + 1
    
    def _is_code_related(self, query: str) -> bool:
        """Determine if a query is related to code."""
        code_keywords = [
            "code", "function", "class", "method", "variable", "import",
            "module", "library", "api", "syntax", "error", "bug", "debug",
            "implement", "algorithm", "data structure", "programming"
        ]
        
        query_lower = query.lower()
        return any(keyword in query_lower for keyword in code_keywords)