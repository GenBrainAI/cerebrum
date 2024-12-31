from typing import Dict, Any, List, Optional
from pathlib import Path
import logging

from src.server.context.vector_store import VectorStore, VectorStoreConfig
from src.server.context.knowledge_base import KnowledgeBase
from src.server.context.code_catalog import CodeCatalog
from src.server.context.context_provider import ContextProvider

logger = logging.getLogger(__name__)

class ContextConfig:
    """Configuration for context handling across different frameworks."""
    
    def __init__(self):
        self.vector_config = {
            "batch_size": 100,
            "max_retries": 3,
            "retry_delay": 1,
            "connection_timeout": 30,
            "max_concurrent_requests": 10,
            "chunk_size": 1000,
            "chunk_overlap": 100,
            "embedding_model": "text-embedding-3-small",
            "embeddings_provider": "openai"
        }
        
        self.knowledge_config = {
            "base_path": "persistent_state/context/knowledge_base",
            "domains": ["langchain", "tools", "patterns", "system"],
            "default_tags": ["documentation", "tools", "patterns"]
        }
        
        self.code_config = {
            "analyze_deps": True,
            "parse_docs": True,
            "deep_scan": False,
            "exclude_dirs": ["venv", "__pycache__", ".git", "node_modules"]
        }
        
        self.framework_configs = {
            "cerebrum": {
                "default_context_types": ["vector", "knowledge", "code"],
                "context_weights": {
                    "vector": 1.0,
                    "knowledge": 0.8,
                    "code": 0.6
                }
            },
            "crew_ai": {
                "default_context_types": ["vector", "knowledge"],
                "context_weights": {
                    "vector": 0.8,
                    "knowledge": 1.0
                },
                "min_relevance": 0.7
            }
        }

class UnifiedContextState:
    """Manages different types of contexts and their assignments to various agent frameworks."""
    
    def __init__(self, base_path: str = "persistent_state/context", config: Optional[ContextConfig] = None):
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)
        
        # Use provided config or create default
        self.config = config or ContextConfig()
        
        # Initialize different context stores with config
        self.vector_store = VectorStore(
            config=VectorStoreConfig(**self.config.vector_config),
            base_path=str(self.base_path / "vector_store")
        )
        self.knowledge_base = KnowledgeBase(
            base_path=str(self.base_path / "knowledge_base")
        )
        self.code_catalog = CodeCatalog()
        
        # Initialize context assignments
        self.context_assignments = {
            "cerebrum": {
                "tasks": {},
                "task_managers": {}
            },
            "crew_ai": {
                "agents": {},
                "tasks": {},
                "crews": {}
            }
        }
        
        # Initialize context bridges
        self.crew_bridge = None
        self.context_provider = None
        
    async def initialize(self):
        """Initialize context provider and bridges."""
        self.context_provider = ContextProvider()
        
    async def assign_context_to_cerebrum_task(
        self,
        task_id: str,
        context_types: List[str],
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Assign context to a Cerebrum task."""
        self.context_assignments["cerebrum"]["tasks"][task_id] = {
            "types": context_types,
            "metadata": metadata or {}
        }
        
    async def assign_context_to_crew_agent(
        self,
        agent_id: str,
        context_types: List[str],
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Assign context to a CrewAI agent."""
        self.context_assignments["crew_ai"]["agents"][agent_id] = {
            "types": context_types,
            "metadata": metadata or {}
        }
        
    async def get_context_for_entity(
        self,
        entity_type: str,
        framework: str,
        entity_id: str,
        query: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get assigned context for a specific entity with framework-specific weights."""
        assignments = self.context_assignments.get(framework, {}).get(entity_type, {})
        entity_context = assignments.get(entity_id, {})
        
        if not entity_context:
            # Use default context types from framework config
            framework_config = self.config.framework_configs.get(framework, {})
            context_types = framework_config.get("default_context_types", [])
        else:
            context_types = entity_context["types"]
            
        if not context_types:
            return []
            
        # Get framework-specific weights and minimum relevance
        framework_config = self.config.framework_configs.get(framework, {})
        context_weights = framework_config.get("context_weights", {})
        min_relevance = framework_config.get("min_relevance", 0.0)
        
        contexts = []
        for context_type in context_types:
            weight = context_weights.get(context_type, 1.0)
            
            # Get raw contexts without weights
            if context_type == "vector":
                raw_contexts = await self.context_provider._get_vector_contexts(
                    entity_id, query or ""
                )
            elif context_type == "knowledge":
                raw_contexts = await self.context_provider._get_knowledge_contexts(
                    entity_id
                )
            elif context_type == "code":
                raw_contexts = await self.context_provider._get_code_contexts(
                    entity_id
                )
            else:
                continue
                
            # Apply weights to raw contexts
            for ctx in raw_contexts:
                ctx["type"] = context_type  # Ensure type is set
                raw_relevance = ctx.get("relevance", 0)
                ctx["weighted_relevance"] = raw_relevance * weight
            contexts.extend(raw_contexts)
            
        # Filter by minimum relevance and sort by weighted relevance
        filtered_contexts = [
            ctx for ctx in contexts 
            if ctx.get("weighted_relevance", 0) >= min_relevance
        ]
        filtered_contexts.sort(key=lambda x: x.get("weighted_relevance", 0), reverse=True)
        
        return filtered_contexts
        
    async def create_specialized_state(
        self,
        state_type: str,
        config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create a specialized state for different frameworks."""
        if state_type == "crew_ai":
            return await self._create_crew_ai_state(config)
        elif state_type == "cerebrum":
            return await self._create_cerebrum_state(config)
        else:
            raise ValueError(f"Unsupported state type: {state_type}")
            
    async def _create_crew_ai_state(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Create specialized state for CrewAI."""
        from src.server.models.agent import CrewConfiguration
        from src.server.context.crew_ai_knowledge_bridge import CrewAIKnowledgeBridge
        
        crew_config = CrewConfiguration(**config)
        
        # Create bridge if not exists
        if self.crew_bridge is None:
            self.crew_bridge = CrewAIKnowledgeBridge(self)
        
        # Enhance agents with context
        for agent in crew_config.agents:
            contexts = await self.get_context_for_entity(
                "agents", "crew_ai", agent.role, None
            )
            agent.backstory = self._enhance_backstory(agent.backstory, contexts)
            
        return {
            "crew_config": crew_config,
            "context_provider": self.context_provider,
            "crew_bridge": self.crew_bridge
        }
        
    async def _create_cerebrum_state(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Create specialized state for Cerebrum."""
        return {
            "context_provider": self.context_provider,
            "vector_store": self.vector_store,
            "knowledge_base": self.knowledge_base,
            "code_catalog": self.code_catalog
        }
        
    def _enhance_backstory(self, original_backstory: str, contexts: List[Dict[str, Any]]) -> str:
        """Enhance agent backstory with context."""
        if not contexts:
            return original_backstory
            
        enhanced = f"{original_backstory}\n\nRelevant Context:\n"
        for context in contexts:
            enhanced += f"\n• [{context['type']}] {context['content']}"
            if 'metadata' in context:
                enhanced += f" (Source: {context['metadata'].get('source', 'unknown')})"
                
        return enhanced 