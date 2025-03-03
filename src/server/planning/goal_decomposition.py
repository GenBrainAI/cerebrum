"""
Goal Decomposition Engine for the Self-Aware Cerebrum system.

This module provides capabilities for breaking down high-level goals into
manageable subgoals and tasks, with resource estimation and prioritization.
"""

from typing import Dict, List, Optional, Any, Tuple, Set
import logging
import asyncio
import json
import os
import uuid
from datetime import datetime
from enum import Enum, auto
from dataclasses import dataclass, field
from collections import defaultdict

logger = logging.getLogger(__name__)

class GoalDecompositionError(Exception):
    """Base exception for goal decomposition errors."""
    pass

class InvalidGoalError(GoalDecompositionError):
    """Raised when a goal is invalid."""
    pass

class CircularDependencyError(GoalDecompositionError):
    """Raised when circular dependencies are detected."""
    pass

class ResourceValidationError(GoalDecompositionError):
    """Raised when resource validation fails."""
    pass

class GoalType(Enum):
    """Types of goals that can be decomposed."""
    RESEARCH = auto()
    DEVELOPMENT = auto()
    ANALYSIS = auto()
    INTEGRATION = auto()
    OPTIMIZATION = auto()
    TESTING = auto()
    DOCUMENTATION = auto()
    GENERAL = auto()

    @classmethod
    def from_str(cls, value: str) -> 'GoalType':
        """Convert string to GoalType, with validation."""
        try:
            return cls[value.upper()]
        except KeyError:
            raise ValueError(f"Invalid goal type: {value}")

class DecompositionStrategy(Enum):
    """Strategies for decomposing goals."""
    TOP_DOWN = auto()
    BOTTOM_UP = auto()
    ITERATIVE = auto()
    DOMAIN_SPECIFIC = auto()

    @classmethod
    def from_str(cls, value: str) -> 'DecompositionStrategy':
        """Convert string to DecompositionStrategy, with validation."""
        try:
            return cls[value.upper()]
        except KeyError:
            raise ValueError(f"Invalid decomposition strategy: {value}")

@dataclass
class ResourceEstimate:
    """Resource estimates for a goal or subgoal."""
    time_hours: float
    complexity: int  # 1-10 scale
    knowledge_requirements: List[str]
    dependencies: List[str]
    risk_level: int  # 1-10 scale

    def __post_init__(self):
        """Validate resource estimates."""
        if not 0 <= self.time_hours:
            raise ValueError("Time hours must be non-negative")
        if not 1 <= self.complexity <= 10:
            raise ValueError("Complexity must be between 1 and 10")
        if not 1 <= self.risk_level <= 10:
            raise ValueError("Risk level must be between 1 and 10")
        
        # Ensure lists are unique
        self.knowledge_requirements = list(set(self.knowledge_requirements))
        self.dependencies = list(set(self.dependencies))

    def merge(self, other: 'ResourceEstimate') -> 'ResourceEstimate':
        """Merge two resource estimates."""
        return ResourceEstimate(
            time_hours=self.time_hours + other.time_hours,
            complexity=max(self.complexity, other.complexity),
            knowledge_requirements=list(set(self.knowledge_requirements + other.knowledge_requirements)),
            dependencies=list(set(self.dependencies + other.dependencies)),
            risk_level=max(self.risk_level, other.risk_level)
        )

@dataclass
class SubGoal:
    """Representation of a subgoal within a decomposed goal."""
    id: str
    name: str
    description: str
    goal_type: GoalType
    priority: int  # 1-10 scale
    resources: ResourceEstimate
    parent_id: Optional[str] = None
    children_ids: List[str] = field(default_factory=list)
    status: str = "pending"
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate subgoal attributes."""
        if not 1 <= self.priority <= 10:
            raise ValueError("Priority must be between 1 and 10")
        if not self.name:
            raise ValueError("Name cannot be empty")
        if not isinstance(self.goal_type, GoalType):
            raise ValueError("Invalid goal type")
        if self.status not in {"pending", "in_progress", "completed", "blocked", "failed"}:
            raise ValueError("Invalid status")

    def to_dict(self) -> Dict[str, Any]:
        """Convert subgoal to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "goal_type": self.goal_type.name,
            "priority": self.priority,
            "resources": {
                "time_hours": self.resources.time_hours,
                "complexity": self.resources.complexity,
                "knowledge_requirements": self.resources.knowledge_requirements,
                "dependencies": self.resources.dependencies,
                "risk_level": self.resources.risk_level
            },
            "parent_id": self.parent_id,
            "children_ids": self.children_ids,
            "status": self.status,
            "metadata": self.metadata
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SubGoal':
        """Create subgoal from dictionary."""
        resources = ResourceEstimate(
            time_hours=data["resources"]["time_hours"],
            complexity=data["resources"]["complexity"],
            knowledge_requirements=data["resources"]["knowledge_requirements"],
            dependencies=data["resources"]["dependencies"],
            risk_level=data["resources"]["risk_level"]
        )
        
        return cls(
            id=data["id"],
            name=data["name"],
            description=data["description"],
            goal_type=GoalType[data["goal_type"]],
            priority=data["priority"],
            resources=resources,
            parent_id=data.get("parent_id"),
            children_ids=data.get("children_ids", []),
            status=data.get("status", "pending"),
            metadata=data.get("metadata", {})
        )

@dataclass
class DecomposedGoal:
    """Representation of a fully decomposed goal."""
    id: str
    name: str
    description: str
    goal_type: GoalType
    strategy: DecompositionStrategy
    subgoals: Dict[str, SubGoal]
    root_subgoal_ids: List[str]
    total_resources: ResourceEstimate
    creation_time: str
    status: str = "pending"
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Validate decomposed goal attributes."""
        if not self.name:
            raise ValueError("Name cannot be empty")
        if not isinstance(self.goal_type, GoalType):
            raise ValueError("Invalid goal type")
        if not isinstance(self.strategy, DecompositionStrategy):
            raise ValueError("Invalid decomposition strategy")
        if self.status not in {"pending", "in_progress", "completed", "blocked", "failed"}:
            raise ValueError("Invalid status")

    def to_dict(self) -> Dict[str, Any]:
        """Convert decomposed goal to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "goal_type": self.goal_type.name,
            "strategy": self.strategy.name,
            "subgoals": {k: v.to_dict() for k, v in self.subgoals.items()},
            "root_subgoal_ids": self.root_subgoal_ids,
            "total_resources": {
                "time_hours": self.total_resources.time_hours,
                "complexity": self.total_resources.complexity,
                "knowledge_requirements": self.total_resources.knowledge_requirements,
                "dependencies": self.total_resources.dependencies,
                "risk_level": self.total_resources.risk_level
            },
            "creation_time": self.creation_time,
            "status": self.status,
            "metadata": self.metadata
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DecomposedGoal':
        """Create decomposed goal from dictionary."""
        total_resources = ResourceEstimate(
            time_hours=data["total_resources"]["time_hours"],
            complexity=data["total_resources"]["complexity"],
            knowledge_requirements=data["total_resources"]["knowledge_requirements"],
            dependencies=data["total_resources"]["dependencies"],
            risk_level=data["total_resources"]["risk_level"]
        )
        
        subgoals = {
            k: SubGoal.from_dict(v) for k, v in data["subgoals"].items()
        }
        
        return cls(
            id=data["id"],
            name=data["name"],
            description=data["description"],
            goal_type=GoalType[data["goal_type"]],
            strategy=DecompositionStrategy[data["strategy"]],
            subgoals=subgoals,
            root_subgoal_ids=data["root_subgoal_ids"],
            total_resources=total_resources,
            creation_time=data["creation_time"],
            status=data.get("status", "pending"),
            metadata=data.get("metadata", {})
        )

    def get_subgoal_tree(self) -> Dict[str, List[str]]:
        """Get the subgoal tree structure."""
        tree = defaultdict(list)
        for subgoal_id, subgoal in self.subgoals.items():
            parent_id = subgoal.parent_id or "root"
            tree[parent_id].append(subgoal_id)
        return dict(tree)

    def get_critical_path(self) -> List[str]:
        """Get the critical path through the subgoals."""
        # Build dependency graph
        graph = defaultdict(list)
        weights = {}
        for subgoal_id, subgoal in self.subgoals.items():
            weights[subgoal_id] = subgoal.resources.time_hours
            for dep in subgoal.resources.dependencies:
                graph[dep].append(subgoal_id)

        # Find longest path
        def dfs(node: str, visited: Set[str]) -> float:
            if node in visited:
                raise CircularDependencyError(f"Circular dependency detected at {node}")
            if node not in graph:
                return weights.get(node, 0)
            
            visited.add(node)
            max_path = 0
            for neighbor in graph[node]:
                path_length = dfs(neighbor, visited.copy()) + weights[node]
                max_path = max(max_path, path_length)
            return max_path

        # Find critical path starting from each root node
        critical_path = []
        max_length = 0
        for root in self.root_subgoal_ids:
            try:
                path_length = dfs(root, set())
                if path_length > max_length:
                    max_length = path_length
                    critical_path = [root]
                    current = root
                    while current in graph and graph[current]:
                        next_node = max(graph[current], key=lambda x: weights[x])
                        critical_path.append(next_node)
                        current = next_node
            except CircularDependencyError as e:
                logger.warning(f"Skipping path due to circular dependency: {e}")

        return critical_path

class GoalDecompositionEngine:
    """Engine for decomposing high-level goals into manageable subgoals."""
    
    def __init__(self, knowledge_system=None):
        """Initialize the Goal Decomposition Engine.
        
        Args:
            knowledge_system: Knowledge Integration System for context.
        """
        self.knowledge_system = knowledge_system
        self.decomposed_goals = {}
        self.decomposition_history = []
        
    async def decompose_goal(
        self, 
        goal: Dict[str, Any],
        strategy: DecompositionStrategy = DecompositionStrategy.TOP_DOWN,
        context: Optional[Dict[str, Any]] = None
    ) -> DecomposedGoal:
        """Decompose a high-level goal into subgoals."""
        try:
            # Validate input
            if not isinstance(goal, dict):
                raise InvalidGoalError("Goal must be a dictionary")
            if not goal.get("name"):
                raise InvalidGoalError("Goal must have a name")
            
            goal_id = goal.get("id", str(uuid.uuid4()))
            logger.info(f"Decomposing goal with ID: {goal_id}")
            
            # Extract goal information
            goal_name = goal.get("name", "Unnamed Goal")
            goal_description = goal.get("description", "")
            goal_type_str = goal.get("type", "GENERAL")
            
            try:
                goal_type = GoalType.from_str(goal_type_str)
            except ValueError as e:
                logger.warning(f"Invalid goal type: {e}, using GENERAL")
                goal_type = GoalType.GENERAL
            
            # Apply the appropriate decomposition strategy
            if strategy == DecompositionStrategy.TOP_DOWN:
                subgoals, root_ids = await self._apply_top_down_strategy(goal, context)
            elif strategy == DecompositionStrategy.BOTTOM_UP:
                subgoals, root_ids = await self._apply_bottom_up_strategy(goal, context)
            elif strategy == DecompositionStrategy.ITERATIVE:
                subgoals, root_ids = await self._apply_iterative_strategy(goal, context)
            elif strategy == DecompositionStrategy.DOMAIN_SPECIFIC:
                subgoals, root_ids = await self._apply_domain_specific_strategy(goal, context)
            else:
                # Default to top-down
                subgoals, root_ids = await self._apply_top_down_strategy(goal, context)
            
            # Calculate total resources
            total_resources = await self._calculate_total_resources(subgoals)
            
            # Create the decomposed goal
            decomposed_goal = DecomposedGoal(
                id=goal_id,
                name=goal_name,
                description=goal_description,
                goal_type=goal_type,
                strategy=strategy,
                subgoals=subgoals,
                root_subgoal_ids=root_ids,
                total_resources=total_resources,
                creation_time=datetime.now().isoformat(),
                status="pending",
                metadata=goal.get("metadata", {})
            )
            
            # Store the decomposed goal
            self.decomposed_goals[goal_id] = decomposed_goal
            
            # Validate the decomposition
            validation = await self.validate_decomposition(decomposed_goal.id)
            if not validation["valid"]:
                # Remove the goal if validation fails
                del self.decomposed_goals[goal_id]
                raise GoalDecompositionError(f"Invalid decomposition: {validation['errors']}")
            
            # Record in history
            self.decomposition_history.append({
                "goal_id": goal_id,
                "strategy": strategy.name,
                "timestamp": datetime.now().isoformat(),
                "subgoal_count": len(subgoals),
                "validation": validation
            })
            
            logger.info(f"Goal decomposition completed with {len(subgoals)} subgoals")
            return decomposed_goal
            
        except Exception as e:
            logger.error(f"Error decomposing goal: {str(e)}")
            raise
    
    async def _apply_top_down_strategy(
        self, 
        goal: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> Tuple[Dict[str, SubGoal], List[str]]:
        """Apply top-down decomposition strategy."""
        logger.info(f"Applying top-down decomposition strategy")
        
        subgoals = {}
        root_ids = []
        
        # Create the initial breakdown based on goal type
        goal_type_str = goal.get("type", "GENERAL")
        goal_type = GoalType[goal_type_str] if goal_type_str in GoalType.__members__ else GoalType.GENERAL
        
        # Get knowledge context if available
        knowledge_context = None
        if self.knowledge_system and context:
            knowledge_context = await self._get_knowledge_context(goal, context)
        
        # Create initial breakdown based on goal type and knowledge
        initial_breakdown = await self._create_initial_breakdown(goal, goal_type, knowledge_context)
        
        # Create root subgoals
        for i, subgoal_info in enumerate(initial_breakdown):
            subgoal_id = str(uuid.uuid4())
            
            # Create resource estimate
            resources = ResourceEstimate(
                time_hours=subgoal_info.get("time_hours", 1.0),
                complexity=subgoal_info.get("complexity", 5),
                knowledge_requirements=subgoal_info.get("knowledge_requirements", []),
                dependencies=subgoal_info.get("dependencies", []),
                risk_level=subgoal_info.get("risk_level", 3)
            )
            
            # Create subgoal
            subgoal = SubGoal(
                id=subgoal_id,
                name=subgoal_info.get("name", f"Subgoal {i+1}"),
                description=subgoal_info.get("description", ""),
                goal_type=goal_type,
                priority=subgoal_info.get("priority", 5),
                resources=resources,
                parent_id=None,
                children_ids=[],
                status="pending"
            )
            
            subgoals[subgoal_id] = subgoal
            root_ids.append(subgoal_id)
            
            # Further decompose if needed
            if subgoal_info.get("needs_further_decomposition", False):
                child_subgoals = await self._further_decompose_subgoal(subgoal, goal_type, knowledge_context)
                
                for child_id, child_subgoal in child_subgoals.items():
                    subgoals[child_id] = child_subgoal
                    subgoal.children_ids.append(child_id)
        
        return subgoals, root_ids
    
    async def _apply_bottom_up_strategy(
        self, 
        goal: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> Tuple[Dict[str, SubGoal], List[str]]:
        """Apply bottom-up decomposition strategy."""
        # For now, delegate to top-down as a fallback
        logger.info(f"Bottom-up strategy not yet implemented, falling back to top-down")
        return await self._apply_top_down_strategy(goal, context)
    
    async def _apply_iterative_strategy(
        self, 
        goal: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> Tuple[Dict[str, SubGoal], List[str]]:
        """Apply iterative decomposition strategy."""
        # For now, delegate to top-down as a fallback
        logger.info(f"Iterative strategy not yet implemented, falling back to top-down")
        return await self._apply_top_down_strategy(goal, context)
    
    async def _apply_domain_specific_strategy(
        self, 
        goal: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> Tuple[Dict[str, SubGoal], List[str]]:
        """Apply domain-specific decomposition strategy."""
        # For now, delegate to top-down as a fallback
        logger.info(f"Domain-specific strategy not yet implemented, falling back to top-down")
        return await self._apply_top_down_strategy(goal, context)
    
    async def _create_initial_breakdown(
        self, 
        goal: Dict[str, Any],
        goal_type: GoalType,
        knowledge_context: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Create initial breakdown of a goal based on its type."""
        if goal_type == GoalType.RESEARCH:
            return [
                {
                    "name": "Background Research",
                    "description": "Gather and analyze existing knowledge on the topic",
                    "priority": 8,
                    "time_hours": 4.0,
                    "complexity": 6,
                    "knowledge_requirements": ["research_methodology"],
                    "dependencies": [],
                    "risk_level": 2,
                    "needs_further_decomposition": True
                },
                {
                    "name": "Gap Analysis",
                    "description": "Identify gaps in current knowledge",
                    "priority": 7,
                    "time_hours": 3.0,
                    "complexity": 7,
                    "knowledge_requirements": ["analytical_thinking"],
                    "dependencies": ["Background Research"],
                    "risk_level": 3,
                    "needs_further_decomposition": False
                },
                {
                    "name": "Research Planning",
                    "description": "Plan specific research activities",
                    "priority": 6,
                    "time_hours": 2.0,
                    "complexity": 5,
                    "knowledge_requirements": ["project_planning"],
                    "dependencies": ["Gap Analysis"],
                    "risk_level": 4,
                    "needs_further_decomposition": True
                }
            ]
        elif goal_type == GoalType.DEVELOPMENT:
            return [
                {
                    "name": "Requirements Analysis",
                    "description": "Analyze and document requirements",
                    "priority": 9,
                    "time_hours": 3.0,
                    "complexity": 6,
                    "knowledge_requirements": ["requirements_engineering"],
                    "dependencies": [],
                    "risk_level": 4,
                    "needs_further_decomposition": True
                },
                {
                    "name": "Architecture Design",
                    "description": "Design the system architecture",
                    "priority": 8,
                    "time_hours": 4.0,
                    "complexity": 8,
                    "knowledge_requirements": ["software_architecture"],
                    "dependencies": ["Requirements Analysis"],
                    "risk_level": 7,
                    "needs_further_decomposition": True
                },
                {
                    "name": "Implementation",
                    "description": "Implement the designed solution",
                    "priority": 10,
                    "time_hours": 10.0,
                    "complexity": 7,
                    "knowledge_requirements": ["programming"],
                    "dependencies": ["Architecture Design"],
                    "risk_level": 6,
                    "needs_further_decomposition": True
                }
            ]
        else:
            # Generic breakdown for other goal types
            return [
                {
                    "name": "Analysis",
                    "description": "Analyze the problem or goal",
                    "priority": 8,
                    "time_hours": 2.0,
                    "complexity": 6,
                    "knowledge_requirements": ["analytical_thinking"],
                    "dependencies": [],
                    "risk_level": 3,
                    "needs_further_decomposition": False
                },
                {
                    "name": "Planning",
                    "description": "Plan the approach",
                    "priority": 7,
                    "time_hours": 2.0,
                    "complexity": 5,
                    "knowledge_requirements": ["project_planning"],
                    "dependencies": ["Analysis"],
                    "risk_level": 4,
                    "needs_further_decomposition": False
                },
                {
                    "name": "Execution",
                    "description": "Execute the plan",
                    "priority": 9,
                    "time_hours": 6.0,
                    "complexity": 7,
                    "knowledge_requirements": [],
                    "dependencies": ["Planning"],
                    "risk_level": 5,
                    "needs_further_decomposition": True
                }
            ]
    
    async def _further_decompose_subgoal(
        self, 
        subgoal: SubGoal,
        goal_type: GoalType,
        knowledge_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, SubGoal]:
        """Further decompose a subgoal into smaller subgoals."""
        logger.info(f"Further decomposing subgoal: {subgoal.name}")
        
        child_subgoals = {}
        
        if "Research" in subgoal.name:
            children = [
                {
                    "name": f"{subgoal.name} - Literature Review",
                    "description": "Review existing literature on the topic",
                    "priority": subgoal.priority,
                    "time_hours": subgoal.resources.time_hours * 0.4,
                    "complexity": max(subgoal.resources.complexity - 1, 1),
                    "knowledge_requirements": subgoal.resources.knowledge_requirements + ["literature_review"],
                    "dependencies": [],
                    "risk_level": max(subgoal.resources.risk_level - 1, 1)
                },
                {
                    "name": f"{subgoal.name} - Data Collection",
                    "description": "Collect relevant data for analysis",
                    "priority": subgoal.priority,
                    "time_hours": subgoal.resources.time_hours * 0.3,
                    "complexity": subgoal.resources.complexity,
                    "knowledge_requirements": subgoal.resources.knowledge_requirements + ["data_collection"],
                    "dependencies": [f"{subgoal.name} - Literature Review"],
                    "risk_level": subgoal.resources.risk_level
                }
            ]
        elif "Implementation" in subgoal.name:
            children = [
                {
                    "name": f"{subgoal.name} - Core Functionality",
                    "description": "Implement core functionality",
                    "priority": subgoal.priority,
                    "time_hours": subgoal.resources.time_hours * 0.5,
                    "complexity": subgoal.resources.complexity,
                    "knowledge_requirements": subgoal.resources.knowledge_requirements,
                    "dependencies": [],
                    "risk_level": subgoal.resources.risk_level
                },
                {
                    "name": f"{subgoal.name} - Edge Cases",
                    "description": "Handle edge cases and error conditions",
                    "priority": subgoal.priority - 1,
                    "time_hours": subgoal.resources.time_hours * 0.3,
                    "complexity": subgoal.resources.complexity + 1,
                    "knowledge_requirements": subgoal.resources.knowledge_requirements + ["error_handling"],
                    "dependencies": [f"{subgoal.name} - Core Functionality"],
                    "risk_level": subgoal.resources.risk_level + 1
                }
            ]
        else:
            # Generic decomposition for other subgoals
            children = [
                {
                    "name": f"{subgoal.name} - Planning",
                    "description": f"Plan the {subgoal.name} activities",
                    "priority": subgoal.priority,
                    "time_hours": subgoal.resources.time_hours * 0.2,
                    "complexity": max(subgoal.resources.complexity - 1, 1),
                    "knowledge_requirements": subgoal.resources.knowledge_requirements,
                    "dependencies": [],
                    "risk_level": max(subgoal.resources.risk_level - 1, 1)
                },
                {
                    "name": f"{subgoal.name} - Execution",
                    "description": f"Execute the {subgoal.name} activities",
                    "priority": subgoal.priority,
                    "time_hours": subgoal.resources.time_hours * 0.6,
                    "complexity": subgoal.resources.complexity,
                    "knowledge_requirements": subgoal.resources.knowledge_requirements,
                    "dependencies": [f"{subgoal.name} - Planning"],
                    "risk_level": subgoal.resources.risk_level
                }
            ]
        
        # Create child subgoals
        for child_info in children:
            child_id = str(uuid.uuid4())
            
            # Create resource estimate
            resources = ResourceEstimate(
                time_hours=child_info.get("time_hours", 1.0),
                complexity=child_info.get("complexity", 5),
                knowledge_requirements=child_info.get("knowledge_requirements", []),
                dependencies=child_info.get("dependencies", []),
                risk_level=child_info.get("risk_level", 3)
            )
            
            # Create subgoal
            child_subgoal = SubGoal(
                id=child_id,
                name=child_info.get("name", "Unnamed Subgoal"),
                description=child_info.get("description", ""),
                goal_type=goal_type,
                priority=child_info.get("priority", 5),
                resources=resources,
                parent_id=subgoal.id,
                children_ids=[],
                status="pending"
            )
            
            child_subgoals[child_id] = child_subgoal
        
        return child_subgoals
    
    async def _calculate_total_resources(self, subgoals: Dict[str, SubGoal]) -> ResourceEstimate:
        """Calculate total resources for all subgoals."""
        total_time = 0.0
        max_complexity = 0
        all_knowledge_requirements = set()
        all_dependencies = set()
        max_risk_level = 0
        
        for subgoal in subgoals.values():
            total_time += subgoal.resources.time_hours
            max_complexity = max(max_complexity, subgoal.resources.complexity)
            all_knowledge_requirements.update(subgoal.resources.knowledge_requirements)
            all_dependencies.update(subgoal.resources.dependencies)
            max_risk_level = max(max_risk_level, subgoal.resources.risk_level)
        
        return ResourceEstimate(
            time_hours=total_time,
            complexity=max_complexity,
            knowledge_requirements=list(all_knowledge_requirements),
            dependencies=list(all_dependencies),
            risk_level=max_risk_level
        )
    
    async def _get_knowledge_context(
        self, 
        goal: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Get knowledge context for a goal."""
        if not self.knowledge_system:
            return None
        
        try:
            # Extract relevant keywords from the goal
            keywords = [
                goal.get("name", ""),
                goal.get("description", ""),
                goal.get("type", "GENERAL")
            ]
            
            # Add context keywords if available
            if context and "keywords" in context:
                keywords.extend(context["keywords"])
            
            # Query the knowledge system
            knowledge_items = await self.knowledge_system.query_semantic_memory(
                query=" ".join(keywords),
                limit=5
            )
            
            # Extract relevant information
            knowledge_context = {
                "relevant_items": knowledge_items,
                "domain_knowledge": {}
            }
            
            # Extract domain-specific knowledge if available
            if goal.get("domain"):
                domain_knowledge = await self.knowledge_system.query_semantic_memory(
                    query=f"domain:{goal.get('domain')}",
                    limit=3
                )
                knowledge_context["domain_knowledge"] = domain_knowledge
            
            return knowledge_context
        
        except Exception as e:
            logger.error(f"Error getting knowledge context: {str(e)}")
            return None
    
    async def prioritize_subgoals(self, goal_id: str) -> List[str]:
        """Prioritize subgoals within a decomposed goal."""
        if goal_id not in self.decomposed_goals:
            logger.error(f"Goal with ID {goal_id} not found")
            return []
        
        decomposed_goal = self.decomposed_goals[goal_id]
        subgoals = decomposed_goal.subgoals
        
        # Create a list of (subgoal_id, priority) tuples
        priority_list = []
        for subgoal_id, subgoal in subgoals.items():
            # Calculate effective priority based on multiple factors
            effective_priority = subgoal.priority
            
            # Adjust for dependencies
            if not subgoal.parent_id:  # Root subgoals
                effective_priority += 1
            
            # Adjust for complexity
            if subgoal.resources.complexity > 7:
                effective_priority += 1
            
            # Adjust for risk
            if subgoal.resources.risk_level > 7:
                effective_priority += 2
            
            priority_list.append((subgoal_id, effective_priority))
        
        # Sort by priority (descending)
        priority_list.sort(key=lambda x: x[1], reverse=True)
        
        # Extract subgoal IDs
        prioritized_ids = [item[0] for item in priority_list]
        
        return prioritized_ids
    
    async def estimate_resources(self, goal_id: str) -> ResourceEstimate:
        """Estimate resources for a decomposed goal."""
        if goal_id not in self.decomposed_goals:
            logger.error(f"Goal with ID {goal_id} not found")
            return ResourceEstimate(
                time_hours=0.0,
                complexity=1,  # Changed from 0 to 1 to meet the validation requirement
                knowledge_requirements=[],
                dependencies=[],
                risk_level=1  # Changed from 0 to 1 to meet the validation requirement
            )
        
        decomposed_goal = self.decomposed_goals[goal_id]
        return decomposed_goal.total_resources
    
    async def validate_decomposition(self, goal_id: str) -> Dict[str, Any]:
        """Validate a goal decomposition for completeness and consistency."""
        if goal_id not in self.decomposed_goals:
            logger.error(f"Goal with ID {goal_id} not found")
            return {
                "valid": False,
                "errors": ["Goal not found"],
                "warnings": []
            }
        
        decomposed_goal = self.decomposed_goals[goal_id]
        subgoals = decomposed_goal.subgoals
        
        errors = []
        warnings = []
        
        # Check for orphaned subgoals
        for subgoal_id, subgoal in subgoals.items():
            if subgoal.parent_id and subgoal.parent_id not in subgoals:
                errors.append(f"Subgoal {subgoal_id} has invalid parent {subgoal.parent_id}")
        
        # Check for circular dependencies
        dependency_graph = {}
        for subgoal_id, subgoal in subgoals.items():
            dependency_graph[subgoal_id] = subgoal.children_ids
        
        # Simple cycle detection
        visited = set()
        path = set()
        
        def check_cycle(node):
            visited.add(node)
            path.add(node)
            
            for neighbor in dependency_graph.get(node, []):
                if neighbor not in visited:
                    if check_cycle(neighbor):
                        return True
                elif neighbor in path:
                    errors.append(f"Circular dependency detected involving {node} and {neighbor}")
                    return True
            
            path.remove(node)
            return False
        
        for node in dependency_graph:
            if node not in visited:
                check_cycle(node)
        
        # Check for resource consistency
        total_time = 0.0
        for subgoal_id, subgoal in subgoals.items():
            total_time += subgoal.resources.time_hours
        
        if abs(total_time - decomposed_goal.total_resources.time_hours) > 0.1:
            warnings.append(f"Total time inconsistency: {total_time} vs {decomposed_goal.total_resources.time_hours}")
        
        # Check for coverage
        if len(subgoals) < 2:
            warnings.append("Goal decomposition has fewer than 2 subgoals")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings
        }
    
    async def get_decomposed_goal(self, goal_id: str) -> Optional[DecomposedGoal]:
        """Get a decomposed goal by ID."""
        return self.decomposed_goals.get(goal_id)
    
    async def get_all_decomposed_goals(self) -> Dict[str, DecomposedGoal]:
        """Get all decomposed goals."""
        return self.decomposed_goals
    
    async def delete_decomposed_goal(self, goal_id: str) -> bool:
        """Delete a decomposed goal."""
        if goal_id in self.decomposed_goals:
            del self.decomposed_goals[goal_id]
            return True
        return False 