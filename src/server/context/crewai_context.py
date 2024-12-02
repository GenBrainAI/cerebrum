from typing import List, Dict, Any, Optional
from uuid import UUID

from crewai import Agent, Task, Crew, Process
from crewai.knowledge.source.string_knowledge_source import StringKnowledgeSource
from crewai.knowledge.source.text_file_knowledge_source import TextFileKnowledgeSource
from crewai.knowledge.source.base_knowledge_source import BaseKnowledgeSource

from src.server.models.task import Task as CerebrumTask

class CrewAIKnowledgeBridge:
    """Bridge between Cerebrum's context system and CrewAI's knowledge system."""
    
    def __init__(self, context_provider):
        self.context_provider = context_provider

    async def create_crew_knowledge(
        self,
        task: CerebrumTask,
        query: Optional[str] = None
    ) -> List[BaseKnowledgeSource]:
        """Create CrewAI knowledge sources from Cerebrum context."""
        task_context = self.context_provider.task_context_manager.get_task_context(task.id)
        if not task_context:
            return []
            
        knowledge_sources = []
        
        # Get contexts sorted by priority
        for context_ref in task_context.get_sorted_contexts():
            if context_ref.type == "system":
                # Convert system context to string knowledge source
                entry = self.context_provider.system_context.get_context(UUID(context_ref.source_id))
                if entry:
                    content = await entry.get_content()
                    knowledge_sources.append(
                        StringKnowledgeSource(
                            content=content,
                            metadata={
                                "name": entry.name,
                                "category": entry.category,
                                **entry.source.dict()
                            }
                        )
                    )
            
            elif context_ref.type == "vector":
                # Search vector store and create knowledge sources
                vector_results = await self.context_provider.context_db.search_context(
                    query=query or "",
                    limit=5,
                    filters=context_ref.metadata.get("filters", {})
                )
                
                for result in vector_results:
                    knowledge_sources.append(
                        StringKnowledgeSource(
                            content=result["content"],
                            metadata={
                                "relevance": result["relevance"],
                                **result["metadata"]
                            }
                        )
                    )
            
            elif context_ref.type == "knowledge":
                # Get knowledge base entries
                kb_results = self.context_provider.knowledge_base.get_knowledge(
                    domain=context_ref.metadata.get("domain"),
                    tags=context_ref.metadata.get("tags")
                )
                
                for result in kb_results:
                    knowledge_sources.append(
                        StringKnowledgeSource(
                            content=result["content"],
                            metadata=result["metadata"]
                        )
                    )

        return knowledge_sources

    async def run_crew_task(
        self,
        task: CerebrumTask,
        crew_request: Dict[str, Any],
        running_extra_params: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Run a CrewAI task with context integration."""
        try:
            # Create knowledge sources
            query = running_extra_params.get("query") if running_extra_params else None
            knowledge_sources = await self.create_crew_knowledge(task, query)
            
            # Create CrewAI crew configuration
            crew_config = crew_request["create_crew"]
            
            # Create agents with knowledge
            agents = []
            for agent_config in crew_config.agents:
                agent = Agent(
                    role=agent_config.role,
                    goal=agent_config.goal,
                    backstory=agent_config.backstory,
                    tools=agent_config.tools or [],
                    knowledge_sources=knowledge_sources,  # Add knowledge sources to each agent
                    verbose=True
                )
                agents.append(agent)
            
            # Create tasks
            tasks = []
            for task_config in crew_config.tasks:
                agent = next(
                    (a for a in agents if a.role == task_config.agent_role),
                    None
                )
                if not agent:
                    raise ValueError(f"Agent role '{task_config.agent_role}' not found.")
                    
                crew_task = Task(
                    description=task_config.description,
                    expected_output=task_config.expected_output,
                    agent=agent
                )
                tasks.append(crew_task)
            
            # Create and run crew
            crew = Crew(
                agents=agents,
                tasks=tasks,
                verbose=True,
                process=Process.sequential
            )
            
            # Run with extra parameters
            result = crew.kickoff(**(running_extra_params or {}))
            return {"response": str(result)}
            
        except Exception as e:
            return {"error": f"CrewAI task execution failed: {str(e)}"}

class CrewAIContextProvider:
    """Context provider specifically for CrewAI integration."""
    
    def __init__(self, bridge: CrewAIKnowledgeBridge):
        self.bridge = bridge

    async def prepare_crew_context(
        self,
        task: CerebrumTask,
        query: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Prepare context for CrewAI usage."""
        knowledge_sources = await self.bridge.create_crew_knowledge(task, query)
        
        # Convert to serializable format
        contexts = []
        for source in knowledge_sources:
            if isinstance(source, StringKnowledgeSource):
                contexts.append({
                    "type": "string",
                    "content": source.content,
                    "metadata": source.metadata
                })
            elif isinstance(source, TextFileKnowledgeSource):
                contexts.append({
                    "type": "text",
                    "file_path": source.file_path,
                    "metadata": source.metadata
                })
        
        return contexts