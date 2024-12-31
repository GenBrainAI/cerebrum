from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import logging

from crewai.knowledge.source.string_knowledge_source import StringKnowledgeSource
from crewai.knowledge.source.text_file_knowledge_source import TextFileKnowledgeSource
from crewai.knowledge.source.base_knowledge_source import BaseKnowledgeSource

from src.server.models.task import Task as CerebrumTask
from src.server.context.unified_context import UnifiedContextState

logger = logging.getLogger(__name__)

class CrewAIKnowledgeBridge:
    """Bridge between Cerebrum's unified context system and CrewAI's knowledge system."""
    
    def __init__(self, unified_state: UnifiedContextState):
        self.unified_state = unified_state
        
    async def create_crew_knowledge(
        self,
        task: CerebrumTask,
        query: Optional[str] = None
    ) -> List[BaseKnowledgeSource]:
        """Create knowledge sources for CrewAI from unified context state."""
        try:
            logger.info(f"Creating CrewAI knowledge for task: {task.id}")
            
            # Get contexts from unified state with CrewAI-specific weights
            contexts = await self.unified_state.get_context_for_entity(
                entity_type="tasks",
                framework="crew_ai",
                entity_id=task.id,
                query=query
            )
            
            logger.info(f"Found {len(contexts)} contexts for task")
            
            # Convert contexts to CrewAI knowledge sources
            knowledge_sources = []
            for context in contexts:
                # Only use contexts that meet the minimum relevance threshold
                if context.get("weighted_relevance", 0) >= self.unified_state.config.framework_configs["crew_ai"]["min_relevance"]:
                    knowledge_sources.append(
                        StringKnowledgeSource(
                            content=context["content"],
                            metadata={
                                "type": context["type"],
                                "weighted_relevance": context.get("weighted_relevance", 0),
                                **context.get("metadata", {})
                            }
                        )
                    )
            
            logger.info(f"Created {len(knowledge_sources)} knowledge sources")
            return knowledge_sources
            
        except Exception as e:
            logger.error(f"Error creating CrewAI knowledge: {str(e)}", exc_info=True)
            return []
            
    async def prepare_crew_context(
        self,
        task: CerebrumTask,
        query: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Prepare context for CrewAI usage."""
        try:
            logger.info(f"Preparing CrewAI context for task: {task.id}")
            knowledge_sources = await self.create_crew_knowledge(task, query)
            
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
            
            logger.info(f"Prepared {len(contexts)} contexts")
            return contexts
            
        except Exception as e:
            logger.error(f"Error preparing CrewAI context: {str(e)}", exc_info=True)
            return [] 