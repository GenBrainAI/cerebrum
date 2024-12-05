import asyncio
from typing import List, Dict, Any, Optional
from uuid import UUID
from datetime import datetime

from src.server.context.context_database import ContextDatabase
from src.server.context.knowledge_base import KnowledgeBase
from src.server.models.message import Message
from src.server.models.task_context_model import TaskContextManager, TaskContext, ContextReference
from src.server.context.system_context import SystemContextManager
class ContextProvider:
    """Provides context for tasks by managing different context sources."""
    
    def __init__(self):
        self.context_db = ContextDatabase()
        self.knowledge_base = KnowledgeBase()
        self.system_context = SystemContextManager()
        self.task_context_manager = TaskContextManager()

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
        query: Optional[str] = None,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """Get all relevant contexts for a task."""
        task_context = self.task_context_manager.get_task_context(task_id)
        if not task_context:
            return []

        # Get sorted contexts by priority
        contexts = task_context.get_sorted_contexts()
        results = []

        for context_ref in contexts:
            if context_ref.type == "vector":
                # Search vector store
                vector_results = await self.context_db.search_context(
                    query=query or "",
                    limit=limit,
                    filters=context_ref.metadata.get("filters", {})
                )
                results.extend([
                    {
                        "type": "vector",
                        "content": r["content"],
                        "metadata": r["metadata"],
                        "relevance": r["relevance"],
                        "context_id": str(context_ref.id)
                    }
                    for r in vector_results
                ])
            
            elif context_ref.type == "knowledge":
                # Get knowledge base entries
                kb_results = self.knowledge_base.get_knowledge(
                    domain=context_ref.metadata.get("domain"),
                    tags=context_ref.metadata.get("tags")
                )
                results.extend([
                    {
                        "type": "knowledge",
                        "content": r["content"],
                        "metadata": r["metadata"],
                        "context_id": str(context_ref.id)
                    }
                    for r in kb_results
                ])
            
            elif context_ref.type == "system":
                # Get system context
                system_content = self.get_system_context(context_ref.source_id)
                if system_content:
                    results.append({
                        "type": "system",
                        "content": system_content,
                        "metadata": context_ref.metadata,
                        "context_id": str(context_ref.id)
                    })

        return results[:limit]  # Limit total results

    async def prepare_task_messages(
        self,
        task_id: str,
        messages: List[Message],
        query: Optional[str] = None
    ) -> List[Message]:
        """Prepare messages for a task by injecting relevant context."""
        task_context = self.task_context_manager.get_task_context(task_id)
        if not task_context:
            return messages

        context_parts = []
        
        # Get contexts by type
        for context_ref in task_context.get_sorted_contexts():
            if context_ref.type == "system":
                # Format system context entries
                system_content = self.system_context.format_task_context(
                    task_id=task_id,
                    context_ids=[UUID(context_ref.source_id)],
                    query=query
                )
                if system_content:
                    context_parts.append(system_content)
                    
            elif context_ref.type == "vector":
                # Search vector store
                vector_results = await self.context_db.search_context(
                    query=query or "",
                    limit=5,
                    filters=context_ref.metadata.get("filters", {})
                )
                if vector_results:
                    content = "\n\n".join([
                        f"Vector Context {i+1}:\n{r['content']}"
                        for i, r in enumerate(vector_results)
                    ])
                    context_parts.append(content)
            
            elif context_ref.type == "knowledge":
                # Get knowledge base entries
                kb_results = self.knowledge_base.get_knowledge(
                    domain=context_ref.metadata.get("domain"),
                    tags=context_ref.metadata.get("tags")
                )
                if kb_results:
                    content = "\n\n".join([
                        f"Knowledge Context {i+1}:\n{r['content']}"
                        for i, r in enumerate(kb_results)
                    ])
                    context_parts.append(content)

        if not context_parts:
            return messages

        # Create a system message with all context
        context_message = Message(
            role="system",
            content="Using the following context to inform your responses:\n\n" + 
                    "\n\n---\n\n".join(context_parts)
        )

        # Add context as system message at the start
        return [context_message] + messages

    def create_task_context(self, task_id: str) -> TaskContext:
        """Create a new task context."""
        return self.task_context_manager.create_task_context(task_id)

    async def add_context_to_task(
        self,
        task_id: str,
        type: str,
        source_id: str,
        priority: int = 0,
        metadata: Dict = None
    ) -> ContextReference:
        """Add a context reference to a task."""
        task_context = self.task_context_manager.get_task_context(task_id)
        if not task_context:
            task_context = self.create_task_context(task_id)
        
        return task_context.add_context(
            type=type,
            source_id=source_id,
            priority=priority,
            metadata=metadata
        )