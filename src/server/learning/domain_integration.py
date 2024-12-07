# src/server/learning/domain_integration.py

import asyncio
from typing import Dict, Any, List
from pydantic import BaseModel
from datetime import datetime
from ..context.context_provider import ContextProvider
from ..context.vector_store import VectorStore
from ..context.knowledge_base import KnowledgeBase

class DomainKnowledgeResult(BaseModel):
    """Results from domain knowledge processing."""
    processed_segments: int
    valid_segments: int
    new_concepts: int
    integration_metrics: Dict[str, Any]
    timestamp: datetime = Field(default_factory=datetime.now)

class DomainKnowledgeIntegrator:
    """Manages integration of domain knowledge into Cerebrum's context system."""
    
    def __init__(self, 
                 context_provider: ContextProvider, 
                 vector_store: VectorStore,
                 knowledge_base: KnowledgeBase):
        self.context_provider = context_provider
        self.vector_store = vector_store
        self.knowledge_base = knowledge_base
        self.logger = logging.getLogger(__name__)

    def _segment_knowledge(self, content: str) -> List[str]:
        """Break down content into logical segments."""
        # Simple segmentation by paragraphs for now
        segments = [s.strip() for s in content.split("\n\n") if s.strip()]
        return segments

    async def _extract_concepts(self, segments: List[str]) -> List[Dict[str, Any]]:
        """Extract key concepts from knowledge segments."""
        concepts = []
        for segment in segments:
            # Basic concept extraction
            concept = {
                "content": segment,
                "timestamp": datetime.now(),
                "keywords": self._extract_keywords(segment),
                "type": "domain_knowledge"
            }
            concepts.append(concept)
        return concepts

    def _extract_keywords(self, text: str) -> List[str]:
        """Extract keywords from text using simple frequency analysis."""
        # Basic keyword extraction
        words = text.lower().split()
        # Filter stop words and short words
        keywords = [w for w in words if len(w) > 3]
        return list(set(keywords))

    async def process_domain_source(self, 
                                  source_content: str,
                                  domain_type: str,
                                  metadata: Dict[str, Any]) -> DomainKnowledgeResult:
        """Process domain knowledge through integration pipeline."""
        try:
            # Segment content
            segments = self._segment_knowledge(source_content)
            
            # Extract concepts
            concepts = await self._extract_concepts(segments)
            
            # Store in knowledge base
            valid_segments = 0
            new_concepts = 0
            
            for concept in concepts:
                try:
                    await self.knowledge_base.add_knowledge(
                        content=concept["content"],
                        domain=domain_type,
                        metadata={**metadata, **concept}
                    )
                    valid_segments += 1
                    new_concepts += 1
                except Exception as e:
                    self.logger.error(f"Error storing concept: {str(e)}")

            return DomainKnowledgeResult(
                processed_segments=len(segments),
                valid_segments=valid_segments,
                new_concepts=new_concepts,
                integration_metrics={
                    "success_rate": valid_segments / len(segments) if segments else 0,
                    "domain": domain_type,
                    "timestamp": datetime.now().isoformat()
                }
            )

        except Exception as e:
            self.logger.error(f"Error processing domain source: {str(e)}")
            raise