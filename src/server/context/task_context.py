from datetime import datetime
from typing import List, Optional, Dict, Any, Union
from pydantic import BaseModel, Field
from uuid import UUID

class TaskContextConfig(BaseModel):
    """Configuration for task's context handling."""
    include_vector_context: bool = True
    include_system_context: bool = True
    max_contexts: int = 5
    min_relevance: float = 0.7
    context_priority: int = 0

class TaskContext(BaseModel):
    """Task model with vector and system context support."""
    id: str
    name: str
    tasksmanager_id: str
    description: Optional[str] = None
    
    # Context configuration
    context_config: TaskContextConfig = Field(default_factory=TaskContextConfig)
    system_context_ids: List[UUID] = Field(default_factory=list)
    vector_context_query: Optional[str] = None  # Custom query for vector search
    
    # Regular task fields (unchanged)
    messages: Optional[List[Dict[str, Any]]] = None
    chat_sessions: Dict[str, List[Dict[str, Any]]] = Field(default_factory=dict)
    toolsets: Optional[List[str]] = None
    curried_tools: Optional[List[str]] = None
    curried_proxy_id: Optional[str] = None
    crewai_config_id: Optional[str] = None
    created_at: Optional[datetime] = Field(default_factory=datetime.now)
    updated_at: Optional[datetime] = Field(default_factory=datetime.now)
    
    def add_system_context(self, context_id: UUID) -> None:
        """Add a system context reference."""
        if context_id not in self.system_context_ids:
            self.system_context_ids.append(context_id)
            self.updated_at = datetime.now()
    
    def remove_system_context(self, context_id: UUID) -> bool:
        """Remove a system context reference."""
        if context_id in self.system_context_ids:
            self.system_context_ids.remove(context_id)
            self.updated_at = datetime.now()
            return True
        return False

class TaskManagerContextConfig(BaseModel):
    """Configuration for TaskManager's context handling."""
    enable_global_context: bool = True
    global_vector_query: Optional[str] = None
    max_global_contexts: int = 10

class TaskManagerContext(BaseModel):
    """TaskManager model with context support."""
    id: str
    name: str
    model: Optional[str] = None
    description: Optional[str] = None
    
    # Context configuration
    context_config: TaskManagerContextConfig = Field(default_factory=TaskManagerContextConfig)
    global_system_context_ids: List[UUID] = Field(default_factory=list)
    
    # Regular fields (unchanged)
    status: Optional[str] = None
    configurations: Optional[Dict[str, Any]] = None
    messages: Optional[List[Dict[str, Any]]] = Field(default_factory=list)
    toolsets: Optional[List[str]] = Field(default_factory=list)
    created_at: Optional[datetime] = Field(default_factory=datetime.now)
    updated_at: Optional[datetime] = Field(default_factory=datetime.now)

async def extract_context_messages_by_task(
    context_provider,
    task: TaskContext,
    tasksmanager: TaskManagerContext,
    messages: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    Extract and format context messages for a task based on its configuration.
    Combines system contexts, knowledge base, and vector search results.
    """
    # Start with empty context collections
    context_messages = []
    
    # Skip if task doesn't want context
    if not task.context_config.include_system_context:
        return messages

    # Build query from messages and task description
    query_text = _build_search_query(messages, task.description)
    
    # Get all contexts through context provider
    contexts = await context_provider.get_task_contexts(
        task_id=task.id,
        query=query_text if task.context_config.include_vector_context else None,
        limit=task.context_config.max_contexts
    )
    
    if not contexts:
        return messages

    # Group contexts by type
    context_by_type = {
        "knowledge": [],
        "code": [],
        "vector": [],
        "system": []
    }
    
    for ctx in contexts:
        ctx_type = ctx.get("type", "")
        if ctx_type in context_by_type:
            # Add relevance score for vector contexts
            if ctx_type == "vector" and "relevance" in ctx:
                content = f"Relevance ({ctx['relevance']:.2f}): {ctx['content']}"
            else:
                content = ctx["content"]
            context_by_type[ctx_type].append(content)

    # Build context messages in specific order
    # 1. System and Knowledge (constant context)
    for ctx_type in ["system", "knowledge"]:
        if context_by_type[ctx_type]:
            context_messages.append({
                "role": "system",
                "content": f"{ctx_type.title()} Context:\n" + 
                          "\n---\n".join(context_by_type[ctx_type])
            })
    
    # 2. Code Context (full files)
    if context_by_type["code"]:
        context_messages.append({
            "role": "system",
            "content": "Code Context:\n" + "\n---\n".join(context_by_type["code"])
        })
    
    # 3. Vector Context (relevant chunks)
    if context_by_type["vector"]:
        context_messages.append({
            "role": "system",
            "content": "Relevant Context:\n" + "\n---\n".join(context_by_type["vector"])
        })

    # Return context messages followed by user messages
    return context_messages + messages

def _build_search_query(messages: List[Dict[str, Any]], task_description: Optional[str] = None) -> str:
    """Build search query from messages and task description."""
    query_parts = []
    
    # Add task description if available
    if task_description:
        query_parts.append(task_description)
    
    # Add system messages
    system_messages = [msg["content"] for msg in messages 
                      if msg.get("role") == "system"]
    if system_messages:
        query_parts.extend(system_messages)
    
    # Add last user message
    user_messages = [msg["content"] for msg in messages 
                    if msg.get("role") == "user"]
    if user_messages:
        query_parts.append(user_messages[-1])
    
    return " ".join(query_parts)