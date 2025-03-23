"""
Research Planner for the Self-Aware Cerebrum system.

This module provides capabilities for planning research activities,
analyzing knowledge gaps, and generating research strategies.
"""

from typing import Dict, List, Optional, Any, Tuple
import logging
import asyncio
import json
import os
import uuid
import re
from datetime import datetime
from enum import Enum, auto
from dataclasses import dataclass, field
from collections import defaultdict

from src.server.context.knowledge_integration import KnowledgeIntegrationSystem

logger = logging.getLogger(__name__)

class ResearchStrategyType(Enum):
    """Strategies for conducting research."""
    EXPLORATORY = auto()  # Broad research to discover unknown unknowns
    TARGETED = auto()     # Focused research to answer specific questions
    COMPARATIVE = auto()  # Compare different approaches or solutions
    SYSTEMATIC = auto()   # Systematic review of existing knowledge

@dataclass
class KnowledgeGap:
    """Representation of a knowledge gap."""
    id: str
    topic: str
    description: str
    confidence: float  # 0.0-1.0 scale of confidence in our understanding
    importance: int    # 1-10 scale of importance
    sources: List[str] = field(default_factory=list)
    related_gaps: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        """Validate knowledge gap attributes."""
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("Confidence must be between 0.0 and 1.0")
        if not 1 <= self.importance <= 10:
            raise ValueError("Importance must be between 1 and 10")
            
    def to_dict(self) -> Dict[str, Any]:
        """Convert knowledge gap to dictionary."""
        return {
            "id": self.id,
            "topic": self.topic,
            "description": self.description,
            "confidence": self.confidence,
            "importance": self.importance,
            "sources": self.sources,
            "related_gaps": self.related_gaps
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'KnowledgeGap':
        """Create knowledge gap from dictionary."""
        return cls(
            id=data["id"],
            topic=data["topic"],
            description=data["description"],
            confidence=data["confidence"],
            importance=data["importance"],
            sources=data.get("sources", []),
            related_gaps=data.get("related_gaps", [])
        )
    
@dataclass
class ResearchTask:
    """A specific research task to address knowledge gaps."""
    id: str
    title: str
    description: str
    strategy: ResearchStrategyType
    estimated_time_hours: float
    knowledge_gaps: List[str]
    priority: int  # 1-10 scale
    sources: List[Dict[str, Any]] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    status: str = "pending"
    
    def __post_init__(self):
        """Validate research task attributes."""
        if not 1 <= self.priority <= 10:
            raise ValueError("Priority must be between 1 and 10")
        if self.estimated_time_hours <= 0:
            raise ValueError("Estimated time must be positive")
        if self.status not in {"pending", "in_progress", "completed", "blocked", "failed"}:
            raise ValueError("Invalid status")
            
    def to_dict(self) -> Dict[str, Any]:
        """Convert research task to dictionary."""
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "strategy": self.strategy.name,
            "estimated_time_hours": self.estimated_time_hours,
            "knowledge_gaps": self.knowledge_gaps,
            "priority": self.priority,
            "sources": self.sources,
            "dependencies": self.dependencies,
            "status": self.status
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ResearchTask':
        """Create research task from dictionary."""
        return cls(
            id=data["id"],
            title=data["title"],
            description=data["description"],
            strategy=ResearchStrategyType[data["strategy"]],
            estimated_time_hours=data["estimated_time_hours"],
            knowledge_gaps=data["knowledge_gaps"],
            priority=data["priority"],
            sources=data.get("sources", []),
            dependencies=data.get("dependencies", []),
            status=data.get("status", "pending")
        )
    
@dataclass
class ResearchPlan:
    """Complete research plan for addressing knowledge gaps."""
    id: str
    title: str
    description: str
    knowledge_gaps: Dict[str, KnowledgeGap]
    tasks: Dict[str, ResearchTask]
    total_estimated_time: float
    creation_time: str
    task_sequence: List[str] = field(default_factory=list)
    status: str = "pending"
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate research plan attributes."""
        if not self.title:
            raise ValueError("Title cannot be empty")
        if not self.description:
            raise ValueError("Description cannot be empty")
        if self.status not in {"pending", "in_progress", "completed", "blocked", "failed"}:
            raise ValueError("Invalid status")
            
    def to_dict(self) -> Dict[str, Any]:
        """Convert research plan to dictionary."""
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "knowledge_gaps": {k: v.to_dict() for k, v in self.knowledge_gaps.items()},
            "tasks": {k: v.to_dict() for k, v in self.tasks.items()},
            "total_estimated_time": self.total_estimated_time,
            "creation_time": self.creation_time,
            "task_sequence": self.task_sequence,
            "status": self.status,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ResearchPlan':
        """Create research plan from dictionary."""
        return cls(
            id=data["id"],
            title=data["title"],
            description=data["description"],
            knowledge_gaps={k: KnowledgeGap.from_dict(v) for k, v in data["knowledge_gaps"].items()},
            tasks={k: ResearchTask.from_dict(v) for k, v in data["tasks"].items()},
            total_estimated_time=data["total_estimated_time"],
            creation_time=data["creation_time"],
            task_sequence=data.get("task_sequence", []),
            status=data.get("status", "pending"),
            metadata=data.get("metadata", {})
        )
    
class ResearchPlanner:
    """Plans research activities to address knowledge gaps."""
    
    def __init__(self, knowledge_system: Optional[KnowledgeIntegrationSystem] = None, storage_dir: Optional[str] = None):
        """
        Initialize the Research Planner.
        
        Args:
            knowledge_system: Knowledge integration system for context
            storage_dir: Directory to store research plans
        """
        self.knowledge_system = knowledge_system
        self.storage_dir = storage_dir or os.path.join(os.path.dirname(__file__), "../../..", "data/research_plans")
        os.makedirs(self.storage_dir, exist_ok=True)
        
        self.research_plans = {}
        self.knowledge_gaps = {}
        
        self._load_plans()
        
    def _load_plans(self) -> None:
        """Load research plans from storage."""
        try:
            for filename in os.listdir(self.storage_dir):
                if filename.endswith(".json"):
                    file_path = os.path.join(self.storage_dir, filename)
                    with open(file_path, "r") as f:
                        try:
                            plan_data = json.load(f)
                            plan = ResearchPlan.from_dict(plan_data)
                            self.research_plans[plan.id] = plan
                            
                            # Also load knowledge gaps
                            for gap_id, gap in plan.knowledge_gaps.items():
                                self.knowledge_gaps[gap_id] = gap
                                
                            logger.info(f"Loaded research plan: {plan.title}")
                        except Exception as e:
                            logger.error(f"Error loading research plan from {filename}: {e}")
        except Exception as e:
            logger.error(f"Error loading research plans: {e}")
    
    def _save_plan(self, plan_id: str) -> None:
        """Save a research plan to storage."""
        if plan_id not in self.research_plans:
            logger.warning(f"Cannot save non-existent plan: {plan_id}")
            return
            
        plan = self.research_plans[plan_id]
        file_path = os.path.join(self.storage_dir, f"{plan_id}.json")
        
        with open(file_path, "w") as f:
            json.dump(plan.to_dict(), f, indent=2)
        
        logger.info(f"Saved research plan: {plan.title}")
        
    async def identify_knowledge_gaps(
        self, 
        topic: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, KnowledgeGap]:
        """
        Identify knowledge gaps in a given topic.
        
        Args:
            topic: Topic to analyze for knowledge gaps
            context: Additional context information
            
        Returns:
            Dictionary of knowledge gap ID to KnowledgeGap
        """
        if not self.knowledge_system:
            raise ValueError("Knowledge integration system required")
            
        # Get existing knowledge on the topic
        existing_knowledge = await self.knowledge_system.query_knowledge(
            topic=topic,
            depth=2,
            context=context or {}
        )
        
        # Extract concepts from existing knowledge
        concepts = set()
        for item in existing_knowledge.get("semantic_items", []):
            concepts.add(item.get("concept", "").lower())
            # Add related concepts
            for related in item.get("related_concepts", []):
                concepts.add(related.lower())
        
        # Extract key terms from topic
        key_terms = self._extract_key_terms(topic)
        
        # Identify missing concepts
        missing_concepts = set()
        for term in key_terms:
            if not any(term in concept for concept in concepts):
                missing_concepts.add(term)
        
        # Calculate confidence for each potential gap
        gaps = {}
        
        # First, check for missing concepts
        for concept in missing_concepts:
            gap_id = str(uuid.uuid4())
            gap = KnowledgeGap(
                id=gap_id,
                topic=concept,
                description=f"Limited knowledge about {concept} in the context of {topic}",
                confidence=0.2,  # Low confidence since concept is missing
                importance=self._estimate_importance(concept, topic, existing_knowledge),
                sources=[],
                related_gaps=[]
            )
            gaps[gap_id] = gap
            self.knowledge_gaps[gap_id] = gap
        
        # Second, check for concepts with limited information
        for concept in concepts:
            # Skip if already identified as a gap
            if any(gap.topic.lower() == concept for gap in gaps.values()):
                continue
                
            # Calculate confidence based on amount of information
            concept_items = [
                item for item in existing_knowledge.get("semantic_items", [])
                if item.get("concept", "").lower() == concept
            ]
            
            if concept_items:
                confidence = min(len(concept_items) * 0.1, 0.9)  # Scale by number of items, cap at 0.9
                
                # If confidence is low, create a gap
                if confidence < 0.7 and concept in key_terms:
                    gap_id = str(uuid.uuid4())
                    gap = KnowledgeGap(
                        id=gap_id,
                        topic=concept,
                        description=f"Incomplete knowledge about {concept} in {topic}",
                        confidence=confidence,
                        importance=self._estimate_importance(concept, topic, existing_knowledge),
                        sources=[item.get("id", "") for item in concept_items],
                        related_gaps=[]
                    )
                    gaps[gap_id] = gap
                    self.knowledge_gaps[gap_id] = gap
        
        # Connect related gaps
        self._connect_related_gaps(gaps)
        
        return gaps
    
    def _extract_key_terms(self, text: str) -> List[str]:
        """Extract key terms from text."""
        # Simple implementation - split by spaces and common punctuation
        terms = re.split(r'[\s,.;:!?()\[\]{}"]', text.lower())
        
        # Filter out common words and empty strings
        common_words = {"the", "a", "an", "of", "in", "on", "and", "or", "for", "to", "with", "by", "at", "from"}
        filtered_terms = [term for term in terms if term and term not in common_words and len(term) > 2]
        
        return filtered_terms
    
    def _estimate_importance(self, concept: str, topic: str, knowledge_context: Dict[str, Any]) -> int:
        """Estimate importance of a concept in the given topic context."""
        # Simple heuristic - concepts directly in the topic are more important
        if concept.lower() in topic.lower():
            base_importance = 8
        else:
            base_importance = 5
            
        # Adjust based on how many related items there are
        related_items = sum(
            1 for item in knowledge_context.get("semantic_items", [])
            if concept.lower() in item.get("related_concepts", [])
        )
        
        importance_modifier = min(related_items, 4)  # Cap at +/- 2
        
        # Final importance
        importance = base_importance + importance_modifier
        
        # Ensure it's in the valid range
        return max(1, min(importance, 10))
    
    def _connect_related_gaps(self, gaps: Dict[str, KnowledgeGap]) -> None:
        """Connect related knowledge gaps."""
        gap_list = list(gaps.values())
        
        for i, gap1 in enumerate(gap_list):
            for j, gap2 in enumerate(gap_list[i+1:], i+1):
                # Check if topics are related
                if (gap1.topic.lower() in gap2.topic.lower() or 
                    gap2.topic.lower() in gap1.topic.lower() or
                    self._share_words(gap1.topic, gap2.topic)):
                    
                    # Add bidirectional relation
                    if gap2.id not in gap1.related_gaps:
                        gap1.related_gaps.append(gap2.id)
                    if gap1.id not in gap2.related_gaps:
                        gap2.related_gaps.append(gap1.id)
    
    def _share_words(self, text1: str, text2: str) -> bool:
        """Check if two texts share significant words."""
        words1 = set(self._extract_key_terms(text1))
        words2 = set(self._extract_key_terms(text2))
        
        common_words = words1.intersection(words2)
        
        # Consider related if they share at least 2 significant words
        return len(common_words) >= 2
    
    async def create_research_plan(
        self,
        title: str,
        description: str,
        knowledge_gaps: List[str],
        context: Optional[Dict[str, Any]] = None
    ) -> ResearchPlan:
        """
        Create a research plan to address knowledge gaps.
        
        Args:
            title: Plan title
            description: Plan description
            knowledge_gaps: List of knowledge gap IDs to address
            context: Additional context
            
        Returns:
            Created ResearchPlan
        """
        # Validate knowledge gaps
        valid_gaps = {}
        for gap_id in knowledge_gaps:
            if gap_id in self.knowledge_gaps:
                valid_gaps[gap_id] = self.knowledge_gaps[gap_id]
            else:
                logger.warning(f"Knowledge gap not found: {gap_id}")
        
        if not valid_gaps:
            raise ValueError("No valid knowledge gaps provided")
        
        # Create research tasks for each gap
        tasks = {}
        
        for gap_id, gap in valid_gaps.items():
            # Select appropriate research strategy
            strategy = await self._select_research_strategy(gap, context)
            
            # Estimate time required
            estimated_time = await self._estimate_research_time(gap, strategy)
            
            # Create task
            task_id = str(uuid.uuid4())
            task = ResearchTask(
                id=task_id,
                title=f"Research {gap.topic}",
                description=f"Address knowledge gap: {gap.description}",
                strategy=strategy,
                estimated_time_hours=estimated_time,
                knowledge_gaps=[gap_id],
                priority=gap.importance,
                sources=[]
            )
            
            tasks[task_id] = task
        
        # Set up dependencies between tasks
        self._set_task_dependencies(tasks, valid_gaps)
        
        # Calculate total time
        total_time = sum(task.estimated_time_hours for task in tasks.values())
        
        # Create plan ID
        plan_id = str(uuid.uuid4())
        
        # Create task sequence
        task_sequence = await self.prioritize_research_tasks(tasks)
        
        # Create the plan
        plan = ResearchPlan(
            id=plan_id,
            title=title,
            description=description,
            knowledge_gaps=valid_gaps,
            tasks=tasks,
            total_estimated_time=total_time,
            creation_time=datetime.now().isoformat(),
            task_sequence=task_sequence,
            metadata={}
        )
        
        # Store the plan
        self.research_plans[plan_id] = plan
        
        # Save to disk
        self._save_plan(plan_id)
        
        return plan
    
    async def _select_research_strategy(
        self, 
        gap: KnowledgeGap,
        context: Optional[Dict[str, Any]] = None
    ) -> ResearchStrategyType:
        """
        Select appropriate research strategy for a knowledge gap.
        
        Args:
            gap: Knowledge gap to address
            context: Additional context
            
        Returns:
            Selected research strategy
        """
        # Default strategy
        strategy = ResearchStrategyType.EXPLORATORY
        
        # If confidence is very low, use exploratory
        if gap.confidence < 0.3:
            strategy = ResearchStrategyType.EXPLORATORY
        # If confidence is moderate, use targeted
        elif gap.confidence < 0.6:
            strategy = ResearchStrategyType.TARGETED
        # If confidence is high but still a gap, use systematic
        else:
            strategy = ResearchStrategyType.SYSTEMATIC
            
        # If there are related gaps, consider comparative
        if len(gap.related_gaps) > 2:
            # For related gaps, comparative might be better
            strategy = ResearchStrategyType.COMPARATIVE
            
        return strategy
    
    async def _estimate_research_time(
        self, 
        gap: KnowledgeGap,
        strategy: ResearchStrategyType
    ) -> float:
        """
        Estimate time required for research.
        
        Args:
            gap: Knowledge gap to address
            strategy: Research strategy
            
        Returns:
            Estimated time in hours
        """
        # Base time based on strategy
        if strategy == ResearchStrategyType.EXPLORATORY:
            base_time = 8.0  # Exploratory takes longest
        elif strategy == ResearchStrategyType.COMPARATIVE:
            base_time = 6.0
        elif strategy == ResearchStrategyType.SYSTEMATIC:
            base_time = 5.0
        else:  # TARGETED
            base_time = 4.0
            
        # Adjust based on confidence (lower confidence needs more time)
        confidence_factor = 1.0 + (1.0 - gap.confidence)
        
        # Adjust based on importance (higher importance needs more thorough research)
        importance_factor = 0.8 + (gap.importance / 10) * 0.4
        
        # Calculate final time
        estimated_time = base_time * confidence_factor * importance_factor
        
        return estimated_time
    
    def _set_task_dependencies(
        self,
        tasks: Dict[str, ResearchTask],
        gaps: Dict[str, KnowledgeGap]
    ) -> None:
        """
        Set up dependencies between research tasks.
        
        Args:
            tasks: Dictionary of task ID to ResearchTask
            gaps: Dictionary of gap ID to KnowledgeGap
        """
        # Map gaps to tasks
        gap_to_task = {}
        for task_id, task in tasks.items():
            for gap_id in task.knowledge_gaps:
                gap_to_task[gap_id] = task_id
        
        # Set dependencies based on related gaps
        for gap_id, gap in gaps.items():
            if gap_id in gap_to_task:
                task_id = gap_to_task[gap_id]
                
                # Get related gaps' tasks
                for related_gap_id in gap.related_gaps:
                    if related_gap_id in gap_to_task:
                        related_task_id = gap_to_task[related_gap_id]
                        
                        # Only set dependency if related gap has higher importance
                        related_gap = gaps.get(related_gap_id)
                        if related_gap and related_gap.importance > gap.importance:
                            if related_task_id not in tasks[task_id].dependencies:
                                tasks[task_id].dependencies.append(related_task_id)
    
    async def prioritize_research_tasks(
        self, 
        tasks: Optional[Dict[str, ResearchTask]] = None,
        plan_id: Optional[str] = None
    ) -> List[str]:
        """
        Prioritize research tasks in a plan.
        
        Args:
            tasks: Dictionary of tasks to prioritize (if not using plan_id)
            plan_id: ID of research plan (if not providing tasks directly)
            
        Returns:
            List of task IDs in priority order
        """
        if plan_id:
            if plan_id not in self.research_plans:
                raise ValueError(f"Research plan not found: {plan_id}")
            tasks = self.research_plans[plan_id].tasks
        
        if not tasks:
            raise ValueError("No tasks provided")
        
        # First, identify all independent tasks and sort by priority
        independent_tasks = sorted(
            [task_id for task_id, task in tasks.items() if not task.dependencies],
            key=lambda tid: tasks[tid].priority,
            reverse=True  # Highest priority first
        )
        
        # Next, identify all dependent tasks
        dependent_tasks = {task_id: task for task_id, task in tasks.items() if task.dependencies}
        
        # Create a dependency graph
        dependency_graph = {}
        for task_id, task in dependent_tasks.items():
            dependency_graph[task_id] = task.dependencies
        
        # Sort tasks according to dependencies and priority
        result = []
        
        # Add independent tasks in priority order
        for task_id in independent_tasks:
            result.append(task_id)
        
        # Process dependent tasks
        processed = set(independent_tasks)
        
        # Keep processing until all tasks are processed or we can't make progress
        while len(processed) < len(tasks):
            # Find tasks whose dependencies are all processed
            ready_tasks = []
            for task_id, dependencies in dependency_graph.items():
                if task_id not in processed and all(dep in processed for dep in dependencies):
                    ready_tasks.append(task_id)
            
            if not ready_tasks:
                # We have a circular dependency or missing dependency
                logger.warning("Detected circular dependency or missing dependency in tasks")
                # Add remaining tasks in priority order
                remaining = sorted(
                    [tid for tid in tasks if tid not in processed],
                    key=lambda tid: tasks[tid].priority,
                    reverse=True
                )
                result.extend(remaining)
                break
            
            # Sort ready tasks by priority
            ready_tasks.sort(key=lambda tid: tasks[tid].priority, reverse=True)
            
            # Add to result and mark as processed
            for task_id in ready_tasks:
                result.append(task_id)
                processed.add(task_id)
        
        # Update plan if necessary
        if plan_id:
            self.research_plans[plan_id].task_sequence = result
            self._save_plan(plan_id)
        
        return result
    
    async def evaluate_information_sources(
        self,
        topic: str,
        context: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Evaluate potential information sources for a topic.
        
        Args:
            topic: Topic to find sources for
            context: Additional context
            
        Returns:
            List of information sources with metadata
        """
        if not self.knowledge_system:
            raise ValueError("Knowledge integration system required")
            
        # Get existing knowledge context
        knowledge_context = await self.knowledge_system.get_knowledge_context(topic, max_items=10)
        
        # Extract potential sources
        sources = []
        
        # Extract from semantic memory
        for item in knowledge_context.get("semantic_memory", []):
            if "source" in item and item["source"]:
                source_info = {
                    "type": "reference",
                    "name": item.get("source", ""),
                    "description": f"Source for concept: {item.get('concept', 'Unknown')}",
                    "relevance": 0.8,
                    "confidence": item.get("confidence", 0.5)
                }
                if source_info not in sources:
                    sources.append(source_info)
        
        # Extract from episodic memory
        for item in knowledge_context.get("episodic_memory", []):
            if "actors" in item and item["actors"]:
                source_info = {
                    "type": "person",
                    "name": ", ".join(item.get("actors", [])),
                    "description": f"Involved in: {item.get('title', 'Unknown event')}",
                    "relevance": 0.7,
                    "confidence": item.get("confidence", 0.5)
                }
                if source_info not in sources:
                    sources.append(source_info)
        
        # Extract from procedural memory
        for item in knowledge_context.get("procedural_memory", []):
            source_info = {
                "type": "procedure",
                "name": item.get("task_name", "Unknown procedure"),
                "description": item.get("description", ""),
                "relevance": 0.6,
                "confidence": item.get("success_rate", 0.5)
            }
            if source_info not in sources:
                sources.append(source_info)
        
        # Sort by combined relevance and confidence
        sources.sort(key=lambda s: s["relevance"] * s["confidence"], reverse=True)
        
        return sources
    
    async def get_research_plan(
        self, 
        plan_id: str
    ) -> Optional[ResearchPlan]:
        """
        Get a research plan by ID.
        
        Args:
            plan_id: Research plan ID
            
        Returns:
            ResearchPlan if found, None otherwise
        """
        return self.research_plans.get(plan_id)
    
    async def get_all_research_plans(self) -> Dict[str, ResearchPlan]:
        """
        Get all research plans.
        
        Returns:
            Dictionary of plan ID to ResearchPlan
        """
        return self.research_plans
    
    async def get_knowledge_gap(
        self, 
        gap_id: str
    ) -> Optional[KnowledgeGap]:
        """
        Get a knowledge gap by ID.
        
        Args:
            gap_id: Knowledge gap ID
            
        Returns:
            KnowledgeGap if found, None otherwise
        """
        return self.knowledge_gaps.get(gap_id)
    
    async def estimate_confidence_gain(
        self,
        knowledge_gap_id: str,
        research_task_ids: List[str]
    ) -> float:
        """
        Estimate confidence gain from completing research tasks.
        
        Args:
            knowledge_gap_id: Knowledge gap ID
            research_task_ids: List of research task IDs
            
        Returns:
            Estimated confidence gain (0.0-1.0)
        """
        if knowledge_gap_id not in self.knowledge_gaps:
            raise ValueError(f"Knowledge gap not found: {knowledge_gap_id}")
            
        gap = self.knowledge_gaps[knowledge_gap_id]
        
        # Get all tasks that address this gap
        relevant_tasks = []
        for task_id in research_task_ids:
            for plan in self.research_plans.values():
                if task_id in plan.tasks and knowledge_gap_id in plan.tasks[task_id].knowledge_gaps:
                    relevant_tasks.append(plan.tasks[task_id])
        
        if not relevant_tasks:
            return 0.0
        
        # Base gain depends on current confidence
        base_gain = 0.3 * (1 - gap.confidence)
        
        # Adjust based on number of tasks
        task_factor = min(len(relevant_tasks) * 0.2, 0.6)
        
        # Adjust based on task strategies
        strategy_factor = 0.0
        for task in relevant_tasks:
            if task.strategy == ResearchStrategyType.EXPLORATORY:
                strategy_factor += 0.2
            elif task.strategy == ResearchStrategyType.TARGETED:
                strategy_factor += 0.3
            elif task.strategy == ResearchStrategyType.COMPARATIVE:
                strategy_factor += 0.25
            elif task.strategy == ResearchStrategyType.SYSTEMATIC:
                strategy_factor += 0.35
                
        strategy_factor = min(strategy_factor, 0.5)
        
        # Total confidence gain (capped at 1.0 - current confidence)
        total_gain = min(base_gain + task_factor + strategy_factor, 1.0 - gap.confidence)
        
        return total_gain
    
    async def update_research_task(
        self,
        plan_id: str,
        task_id: str,
        **updates
    ) -> bool:
        """
        Update a research task.
        
        Args:
            plan_id: Research plan ID
            task_id: Research task ID
            **updates: Attributes to update
            
        Returns:
            True if successful, False otherwise
        """
        if plan_id not in self.research_plans:
            logger.warning(f"Research plan not found: {plan_id}")
            return False
            
        plan = self.research_plans[plan_id]
        
        if task_id not in plan.tasks:
            logger.warning(f"Research task not found: {task_id}")
            return False
            
        task = plan.tasks[task_id]
        
        # Update attributes
        for key, value in updates.items():
            if hasattr(task, key):
                setattr(task, key, value)
        
        # Save the plan
        self._save_plan(plan_id)
        
        return True
    
    async def delete_research_plan(
        self,
        plan_id: str
    ) -> bool:
        """
        Delete a research plan.
        
        Args:
            plan_id: Research plan ID
            
        Returns:
            True if successful, False otherwise
        """
        if plan_id not in self.research_plans:
            logger.warning(f"Research plan not found: {plan_id}")
            return False
            
        # Remove from memory
        plan = self.research_plans.pop(plan_id)
        
        # Don't delete gaps in case they're used by other plans
        
        # Remove file
        file_path = os.path.join(self.storage_dir, f"{plan_id}.json")
        if os.path.exists(file_path):
            os.remove(file_path)
            
        logger.info(f"Deleted research plan: {plan.title}")
        
        return True 