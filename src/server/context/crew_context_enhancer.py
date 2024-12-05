from typing import List, Dict, Any, Optional, Set
from pydantic import BaseModel, Field
from datetime import datetime
from crewai import Agent, Crew
import asyncio
import hashlib
import math
import re

from src.server.context.context_provider import ContextProvider

class ContextMetrics(BaseModel):
    """Metrics for context enhancement."""
    total_contexts: int = 0
    relevant_contexts: int = 0
    code_contexts: int = 0
    domain_contexts: int = 0
    average_relevance: float = 0.0
    enhancement_time_ms: float = 0.0

class ContextSource(BaseModel):
    """Track a context source's usage and relevance."""
    source_id: str
    source_type: str  # "code" or "knowledge"
    use_count: int = 0
    total_relevance: float = 0.0
    last_used: datetime = Field(default_factory=datetime.now)

    @property
    def average_relevance(self) -> float:
        """Calculate average relevance score."""
        return self.total_relevance / self.use_count if self.use_count > 0 else 0.0


class CrewContextConfig(BaseModel):
    """Enhanced configuration for crew context."""
    task_id: Optional[str] = None
    include_code_context: bool = True
    include_domain_context: bool = True
    context_max_length: int = 2000
    relevance_threshold: float = 0.7
    max_contexts_per_type: int = 5
    
    # New features
    enable_context_caching: bool = False
    cache_ttl_minutes: int = 30
    enable_context_deduplication: bool = True
    enable_relevance_feedback: bool = True
    enable_metrics: bool = True
    
    # Context weighting
    code_context_weight: float = 1.0
    domain_context_weight: float = 1.0
    recency_weight: float = 0.5

class CrewContextEnhancer:
    """Enhanced context enhancer with additional features."""
    
    def __init__(self, context_provider: ContextProvider):
        self.context_provider = context_provider
        self.context_cache: Dict[str, Dict[str, Any]] = {}
        self.context_sources: Dict[str, ContextSource] = {}
        self.used_contexts: Set[str] = set()

    async def enhance_crew(self, crew: Crew, config: CrewContextConfig) -> tuple[Crew, Optional[ContextMetrics]]:
        """Enhanced crew context enhancement with metrics and advanced features."""
        start_time = datetime.now()
        metrics = ContextMetrics() if config.enable_metrics else None
        
        try:
            for agent in crew.agents:
                print(f"Getting contexts for agent {agent.role}")
                # Get contexts
                contexts = await self.context_provider.get_task_contexts(
                    task_id=config.task_id,
                    query=f"role:{agent.role}",
                    limit=config.max_contexts_per_type
                )
                print(f"Received contexts: {contexts}")

                # Filter and process contexts
                filtered_contexts = []
                for context in contexts:
                    context_type = context.get('type', '').lower()
                    if ((context_type == 'vector' and config.include_code_context) or
                        (context_type == 'knowledge' and config.include_domain_context) or
                        (context_type == 'system')):
                        filtered_contexts.append(context)

                if config.enable_context_deduplication:
                    filtered_contexts = self._deduplicate_contexts(filtered_contexts)

                # Build the enhanced backstory
                backstory_parts = [agent.backstory or ""]
                if filtered_contexts:
                    backstory_parts.append("\n\nRelevant Contexts:")
                    
                    for context in filtered_contexts:
                        # Track context usage here
                        self._track_context_usage(context)
                        
                        relevance = context.get('relevance', 0)
                        context_str = f"\n\nContext ({context['type']}, relevance: {relevance:.2f}):\n"
                        context_str += context['content']
                        
                        # Check length limit
                        current_length = sum(len(part) for part in backstory_parts)
                        if current_length + len(context_str) > config.context_max_length:
                            break
                            
                        backstory_parts.append(context_str)

                # Update agent's backstory
                agent.backstory = "".join(backstory_parts)

                # Update metrics
                if metrics:
                    metrics.total_contexts += len(filtered_contexts)
                    metrics.code_contexts += sum(1 for c in filtered_contexts if c['type'].lower() == 'vector')
                    metrics.domain_contexts += sum(1 for c in filtered_contexts if c['type'].lower() == 'knowledge')
                    if filtered_contexts:
                        metrics.average_relevance = sum(c.get('relevance', 0) for c in filtered_contexts) / len(filtered_contexts)

            if metrics:
                metrics.enhancement_time_ms = (datetime.now() - start_time).total_seconds() * 1000

            return crew, metrics

        except Exception as e:
            print(f"Error enhancing crew with context: {str(e)}")
            return crew, None    
        
    def _truncate_context(self, content: str, max_length: int) -> str:
        """
        Truncate context content to fit within max_length while preserving readability.
        
        Args:
            content: The content to truncate
            max_length: Maximum allowed length
            
        Returns:
            Truncated content with ellipsis if needed
        """
        if len(content) <= max_length:
            return content
            
        # Reserve space for ellipsis
        max_length = max(max_length - 3, 0)
        
        # If very short length, just truncate
        if max_length < 10:
            return content[:max_length] + "..."
            
        # Try to truncate at a sensible boundary
        truncated = content[:max_length]
        
        # Look for last sentence or line break
        last_sentence = truncated.rfind('.')
        last_linebreak = truncated.rfind('\n')
        
        # Use the latest sensible breaking point
        break_point = max(last_sentence, last_linebreak)
        if break_point > max_length * 0.5:  # Only use if it's not too far back
            truncated = truncated[:break_point + 1]
        
        return truncated + "..."
    
    def _deduplicate_contexts(self, contexts: List[Dict[str, Any]], similarity_threshold: float = 0.8) -> List[Dict[str, Any]]:
        """
        Deduplicate contexts based on content similarity.
        
        Args:
            contexts: List of context dictionaries
            similarity_threshold: Threshold for considering contexts similar (0-1)
            
        Returns:
            List of deduplicated contexts
        """
        deduplicated_contexts = []
        content_hashes = set()
        
        # Sort contexts by relevance to keep most relevant versions
        sorted_contexts = sorted(contexts, key=lambda x: x.get('relevance', 0), reverse=True)
        
        for context in sorted_contexts:
            content = context.get('content', '')
            content_normalized = self._normalize_content(content)
            content_hash = self._get_content_hash(content_normalized)
            
            # Check if similar content exists
            is_duplicate = False
            for existing_hash in content_hashes:
                if self._calculate_similarity(content_hash, existing_hash) >= similarity_threshold:
                    is_duplicate = True
                    break
                    
            if not is_duplicate:
                deduplicated_contexts.append(context)
                content_hashes.add(content_hash)
                
        return deduplicated_contexts

    def _normalize_content(self, content: str) -> str:
        """Normalize content for comparison by removing whitespace and comments."""
        content = content.lower()
        # Remove single-line comments
        content = re.sub(r'//.*$', '', content, flags=re.MULTILINE)
        # Remove multi-line comments
        content = re.sub(r'/\*.*?\*/', '', content, flags=re.DOTALL)
        # Remove extra whitespace
        content = re.sub(r'\s+', ' ', content)
        return content.strip()

    def _weight_contexts(self, contexts: List[Dict[str, Any]], config: CrewContextConfig) -> List[Dict[str, Any]]:
        """Weight contexts based on their type and configuration."""
        weighted_contexts = []
        for context in contexts:
            context_type = context.get('type', '').lower()
            weight = 1.0

            if context_type == 'vector':
                weight = config.code_context_weight if config.include_code_context else 0.0
            elif context_type == 'knowledge':
                weight = config.domain_context_weight if config.include_domain_context else 0.0
            elif context_type == 'system':
                weight = 1.0  # System contexts are always included with normal weight

            weighted_relevance = context.get('relevance', 0.0) * weight
            if weighted_relevance > 0:  # Only include contexts with non-zero weight
                weighted_context = context.copy()
                weighted_context['weighted_relevance'] = weighted_relevance
                weighted_contexts.append(weighted_context)

        return sorted(weighted_contexts, key=lambda x: x.get('weighted_relevance', 0), reverse=True)

    async def _enhance_agent_backstory(
        self,
        agent: Agent,
        config: CrewContextConfig
    ) -> tuple[str, Optional[ContextMetrics]]:
        """Add relevant context to an agent's backstory."""
        # Initialize metrics
        metrics = ContextMetrics() if config.enable_metrics else None
        code_contexts = []
        domain_contexts = []
        
        try:
            # Get code contexts if enabled
            if config.include_code_context:
                code_contexts = await self.context_provider.get_task_contexts(
                    task_id=config.task_id,
                    query=f"role:{agent.role}",
                    context_type="code",
                    limit=config.max_contexts_per_type
                )
                if metrics:
                    metrics.code_contexts = len(code_contexts)
            
            # Get domain knowledge if enabled
            if config.include_domain_context:
                domain_contexts = await self.context_provider.get_task_contexts(
                    task_id=config.task_id,
                    query=f"role:{agent.role}",
                    context_type="knowledge",
                    limit=config.max_contexts_per_type
                )
                if metrics:
                    metrics.domain_contexts = len(domain_contexts)

            # Create weighted contexts list
            contexts = []
            for ctx in code_contexts:
                ctx['weighted_relevance'] = ctx.get('relevance', 0) * config.code_context_weight
                contexts.append(ctx)
            for ctx in domain_contexts:
                ctx['weighted_relevance'] = ctx.get('relevance', 0) * config.domain_context_weight
                contexts.append(ctx)

            # Sort contexts by weighted relevance
            contexts.sort(key=lambda x: x.get('weighted_relevance', 0), reverse=True)

            # Update metrics
            if metrics:
                metrics.total_contexts = len(contexts)
                metrics.relevant_contexts = len([c for c in contexts 
                    if c.get('relevance', 0) >= config.min_relevance])
                if contexts:
                    metrics.average_relevance = sum(c.get('relevance', 0) 
                        for c in contexts) / len(contexts)

            # Build enhanced backstory - Start fresh with original backstory
            enhanced = agent.backstory

            # Add contexts if available
            if contexts:
                enhanced += "\n\nRelevant Context:\n"
                for context in contexts:
                    # Track context usage
                    self._track_context_usage(context)
                    
                    base_relevance = context.get('relevance', 0)
                    weight = (config.code_context_weight if context['type'] == 'code' 
                            else config.domain_context_weight)
                    weighted_relevance = base_relevance * weight

                    enhanced += f"\n• [{context['type']}] {context['content']}"
                    if 'metadata' in context:
                        enhanced += f" (Source: {context['metadata'].get('source', 'unknown')}"
                    enhanced += f", Base: {base_relevance:.2f}, Weighted: {weighted_relevance:.2f})"

            return enhanced, metrics

        except Exception as e:
            print(f"Error enhancing agent backstory: {str(e)}")
            return agent.backstory, metrics    
    
    async def _get_cached_contexts(
        self,
        task_id: str,
        query: str,
        context_type: str,
        config: CrewContextConfig
    ) -> List[Dict[str, Any]]:
        """Get contexts with caching support."""
        cache_key = f"{task_id}:{query}:{context_type}"
        
        if config.enable_context_caching:
            cached = self.context_cache.get(cache_key)
            if cached:
                cache_age = (datetime.now() - cached['timestamp']).total_seconds() / 60
                if cache_age < config.cache_ttl_minutes:
                    return cached['contexts']
        
        # Fetch fresh contexts
        contexts = await self.context_provider.get_task_contexts(
            task_id=task_id,
            query=query,
            context_type=context_type,
            limit=config.max_contexts_per_type
        )
        
        # Cache results
        if config.enable_context_caching:
            self.context_cache[cache_key] = {
                'contexts': contexts,
                'timestamp': datetime.now()
            }
            
        return contexts
    
    def _get_content_hash(self, content: str) -> str:
        """Create a hash of content for comparison."""
        # Normalize content before hashing
        normalized = ' '.join(content.lower().split())
        return hashlib.sha256(normalized.encode()).hexdigest()

    def _calculate_similarity(self, hash1: str, hash2: str) -> float:
        """Calculate similarity between two content hashes."""
        # Simple Hamming distance based similarity
        differences = sum(c1 != c2 for c1, c2 in zip(hash1, hash2))
        return 1 - (differences / len(hash1))

    def _get_context_source_id(self, context: Dict[str, Any]) -> str:
        """Generate a unique identifier for a context source."""
        metadata = context.get('metadata', {})
        source_type = context.get('type', 'unknown')
        source = metadata.get('source', 'unknown')
        return f"{source_type}:{source}"

    def _track_context_usage(self, context: Dict[str, Any]) -> None:
        """Track usage and relevance of a context."""
        # Generate a unique source ID from metadata
        metadata = context.get('metadata', {})
        source_id = f"{context['type']}:{metadata.get('source', 'unknown')}"

        print(f"Tracking context usage: {source_id}")  # Debug print

        if source_id not in self.context_sources:
            self.context_sources[source_id] = ContextSource(
                source_id=source_id,
                source_type=context['type']
            )

        source = self.context_sources[source_id]
        source.use_count += 1
        source.total_relevance += context.get('relevance', 0.0)
        source.last_used = datetime.now()
        
        # Track globally used contexts
        self.used_contexts.add(source_id)

    def _calculate_recency_score(self, source: ContextSource) -> float:
        """Calculate a recency score for a context source."""
        if not source or not source.last_used:
            return 0.5
            
        # Calculate hours since last use
        hours_since_use = (datetime.now() - source.last_used).total_seconds() / 3600
        
        # Exponential decay with 24-hour half-life
        decay_rate = 0.029  # ln(2)/24
        recency_score = max(0.1, min(1.0, pow(2, -decay_rate * hours_since_use)))
        return recency_score

    def _create_context_summary(self, context: Dict[str, Any]) -> str:
        """Create an enhanced context summary with metadata."""
        content = context.get('content', '')
        metadata = context.get('metadata', {})
        relevance = context.get('weighted_relevance', 0)
        
        # Truncate content
        max_length = 200
        if len(content) > max_length:
            content = content[:max_length] + "..."
            
        # Format source information
        source_type = context.get('type', 'unknown')
        source = metadata.get('source', 'unknown')
        
        # Add relevance score
        relevance_str = f"{relevance:.2f}"
        
        return f"[{source_type}] {content} (Source: {source}, Relevance: {relevance_str})"

    async def get_enhancement_stats(self) -> Dict[str, Any]:
        """Get statistics about context enhancement."""
        stats = {
            "total_sources": len(self.context_sources),
            "used_sources": len(self.used_contexts),
            "source_stats": {
                source_id: {
                    "type": source.source_type,
                    "use_count": source.use_count,
                    "average_relevance": source.average_relevance,
                    "last_used": source.last_used.isoformat()
                }
                for source_id, source in self.context_sources.items()
            }
        }
        return stats

    def clear_context_cache(self) -> None:
        """Clear the context cache."""
        self.context_cache.clear()
