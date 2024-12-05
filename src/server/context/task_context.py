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
    crewai_info_id: Optional[str] = None
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

async def prepare_task_messages(
    context_provider,
    task: TaskContext,
    tasksmanager: TaskManagerContext,
    messages: List[Dict[str, Any]],
    query: Optional[str] = None
) -> List[Dict[str, Any]]:
    """Prepare messages with context from ContextProvider."""
    # Start with any system messages
    system_messages = []
    
    # Get system contexts if enabled
    if task.context_config.include_system_context:
        # Combine global and task-specific system contexts
        all_context_ids = []
        if tasksmanager.context_config.enable_global_context:
            all_context_ids.extend(tasksmanager.global_system_context_ids)
        all_context_ids.extend(task.system_context_ids)
        
        # Get system context content
        for context_id in all_context_ids:
            system_content = await context_provider.get_system_context(str(context_id))
            if system_content:
                system_messages.append({
                    "role": "system",
                    "content": system_content
                })
    
    # Get vector contexts if enabled
    vector_contexts = []
    if task.context_config.include_vector_context:
        # Use task-specific query if available, otherwise use provided query
        search_query = task.vector_context_query or query or task.description
        if search_query:
            vector_results = await context_provider.search_context(
                query=search_query,
                limit=task.context_config.max_contexts,
                min_relevance=task.context_config.min_relevance
            )
            
            if vector_results:
                vector_contexts = [
                    {
                        "role": "system",
                        "content": f"Relevant Context (similarity: {result['relevance']:.2f}):\n{result['content']}"
                    }
                    for result in vector_results
                ]
    
    # Combine all messages in proper order
    return system_messages + vector_contexts + messages