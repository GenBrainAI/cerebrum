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

@dataclass
class DecompositionTemplate:
    """Template for goal decomposition."""
    id: str
    name: str
    description: str
    goal_type: GoalType
    subgoal_structure: List[Dict[str, Any]]
    resource_estimates: Dict[str, Any]
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert template to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "goal_type": self.goal_type.name,
            "subgoal_structure": self.subgoal_structure,
            "resource_estimates": self.resource_estimates,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DecompositionTemplate':
        """Create template from dictionary."""
        return cls(
            id=data["id"],
            name=data["name"],
            description=data["description"],
            goal_type=GoalType[data["goal_type"]],
            subgoal_structure=data["subgoal_structure"],
            resource_estimates=data["resource_estimates"],
            metadata=data.get("metadata", {})
        )

class GoalDecompositionEngine:
    """
    Engine for decomposing high-level goals into manageable subgoals.
    
    This engine provides methods for breaking down goals, estimating resources,
    prioritizing subgoals, and validating decompositions.
    """
    
    def __init__(self, knowledge_system=None, templates_dir: Optional[str] = None):
        """Initialize the goal decomposition engine."""
        # Dictionary to store decomposed goals by ID
        self.decomposed_goals: Dict[str, DecomposedGoal] = {}
        
        # Dictionary to store decomposition templates by ID
        self.templates: Dict[str, DecompositionTemplate] = {}
        
        # Reference to a knowledge system for semantic queries
        self.knowledge_system = knowledge_system
        
        # Directory for template storage
        self.templates_dir = templates_dir or os.path.join(
            os.path.dirname(os.path.abspath(__file__)), 
            "templates"
        )
        
        # Track decomposition history
        self.decomposition_history: List[Dict[str, Any]] = []
        
        # Load templates
        self._load_templates()
    
    def _load_templates(self) -> None:
        """Load decomposition templates from the templates directory."""
        os.makedirs(self.templates_dir, exist_ok=True)
        
        try:
            for filename in os.listdir(self.templates_dir):
                if filename.endswith(".json"):
                    file_path = os.path.join(self.templates_dir, filename)
                    with open(file_path, "r") as f:
                        try:
                            template_data = json.load(f)
                            template = DecompositionTemplate.from_dict(template_data)
                            self.templates[template.id] = template
                            logger.info(f"Loaded template: {template.name}")
                        except Exception as e:
                            logger.error(f"Error loading template from {filename}: {e}")
        except Exception as e:
            logger.error(f"Error loading templates: {e}")
            
        # Create default templates if none exist
        if not self.templates:
            self._create_default_templates()

    def _create_default_templates(self) -> None:
        """Create default decomposition templates."""
        # Research goal template
        research_template = DecompositionTemplate(
            id=str(uuid.uuid4()),
            name="Standard Research Project",
            description="Template for standard research goals",
            goal_type=GoalType.RESEARCH,
            subgoal_structure=[
                {
                    "name": "Background Research",
                    "description": "Analyze existing knowledge and research",
                    "priority": 10,
                    "children": []
                },
                {
                    "name": "Research Question Formulation",
                    "description": "Define specific research questions",
                    "priority": 9,
                    "children": []
                },
                {
                    "name": "Methodology Design",
                    "description": "Design research methodology",
                    "priority": 8,
                    "dependencies": ["Background Research", "Research Question Formulation"],
                    "children": []
                },
                {
                    "name": "Data Collection",
                    "description": "Collect necessary data",
                    "priority": 7,
                    "dependencies": ["Methodology Design"],
                    "children": []
                },
                {
                    "name": "Data Analysis",
                    "description": "Analyze collected data",
                    "priority": 6,
                    "dependencies": ["Data Collection"],
                    "children": []
                },
                {
                    "name": "Conclusion Formulation",
                    "description": "Draw conclusions from analysis",
                    "priority": 5,
                    "dependencies": ["Data Analysis"],
                    "children": []
                },
                {
                    "name": "Research Documentation",
                    "description": "Document research findings",
                    "priority": 4,
                    "dependencies": ["Conclusion Formulation"],
                    "children": []
                }
            ],
            resource_estimates={
                "Background Research": {"time_hours": 10, "complexity": 6, "risk_level": 3},
                "Research Question Formulation": {"time_hours": 5, "complexity": 8, "risk_level": 7},
                "Methodology Design": {"time_hours": 8, "complexity": 7, "risk_level": 6},
                "Data Collection": {"time_hours": 15, "complexity": 5, "risk_level": 4},
                "Data Analysis": {"time_hours": 12, "complexity": 8, "risk_level": 5},
                "Conclusion Formulation": {"time_hours": 6, "complexity": 9, "risk_level": 7},
                "Research Documentation": {"time_hours": 8, "complexity": 4, "risk_level": 2}
            }
        )
        
        # Development goal template
        development_template = DecompositionTemplate(
            id=str(uuid.uuid4()),
            name="Software Development Project",
            description="Template for software development goals",
            goal_type=GoalType.DEVELOPMENT,
            subgoal_structure=[
                {
                    "name": "Requirements Analysis",
                    "description": "Analyze requirements and specifications",
                    "priority": 10,
                    "children": []
                },
                {
                    "name": "System Design",
                    "description": "Design system architecture",
                    "priority": 9,
                    "dependencies": ["Requirements Analysis"],
                    "children": []
                },
                {
                    "name": "Implementation",
                    "description": "Implement the designed system",
                    "priority": 8,
                    "dependencies": ["System Design"],
                    "children": []
                },
                {
                    "name": "Testing",
                    "description": "Test the implementation",
                    "priority": 7,
                    "dependencies": ["Implementation"],
                    "children": []
                },
                {
                    "name": "Deployment",
                    "description": "Deploy the system",
                    "priority": 6,
                    "dependencies": ["Testing"],
                    "children": []
                },
                {
                    "name": "Documentation",
                    "description": "Document the system",
                    "priority": 5,
                    "dependencies": ["Implementation"],
                    "children": []
                }
            ],
            resource_estimates={
                "Requirements Analysis": {"time_hours": 8, "complexity": 7, "risk_level": 5},
                "System Design": {"time_hours": 12, "complexity": 9, "risk_level": 8},
                "Implementation": {"time_hours": 20, "complexity": 8, "risk_level": 7},
                "Testing": {"time_hours": 10, "complexity": 6, "risk_level": 4},
                "Deployment": {"time_hours": 5, "complexity": 7, "risk_level": 9},
                "Documentation": {"time_hours": 6, "complexity": 4, "risk_level": 2}
            }
        )
        
        # Analysis goal template
        analysis_template = DecompositionTemplate(
            id=str(uuid.uuid4()),
            name="System Analysis Project",
            description="Template for analysis goals",
            goal_type=GoalType.ANALYSIS,
            subgoal_structure=[
                {
                    "name": "Problem Definition",
                    "description": "Define the problem to be analyzed",
                    "priority": 10,
                    "children": []
                },
                {
                    "name": "Data Collection",
                    "description": "Collect data for analysis",
                    "priority": 9,
                    "dependencies": ["Problem Definition"],
                    "children": []
                },
                {
                    "name": "Data Preprocessing",
                    "description": "Clean and prepare data",
                    "priority": 8,
                    "dependencies": ["Data Collection"],
                    "children": []
                },
                {
                    "name": "Model Selection",
                    "description": "Select appropriate analysis models",
                    "priority": 7,
                    "dependencies": ["Problem Definition"],
                    "children": []
                },
                {
                    "name": "Model Implementation",
                    "description": "Implement selected models",
                    "priority": 6,
                    "dependencies": ["Model Selection", "Data Preprocessing"],
                    "children": []
                },
                {
                    "name": "Result Analysis",
                    "description": "Analyze model results",
                    "priority": 5,
                    "dependencies": ["Model Implementation"],
                    "children": []
                },
                {
                    "name": "Report Generation",
                    "description": "Generate analysis report",
                    "priority": 4,
                    "dependencies": ["Result Analysis"],
                    "children": []
                }
            ],
            resource_estimates={
                "Problem Definition": {"time_hours": 5, "complexity": 8, "risk_level": 6},
                "Data Collection": {"time_hours": 10, "complexity": 6, "risk_level": 5},
                "Data Preprocessing": {"time_hours": 8, "complexity": 7, "risk_level": 4},
                "Model Selection": {"time_hours": 6, "complexity": 9, "risk_level": 8},
                "Model Implementation": {"time_hours": 12, "complexity": 8, "risk_level": 7},
                "Result Analysis": {"time_hours": 8, "complexity": 9, "risk_level": 6},
                "Report Generation": {"time_hours": 5, "complexity": 5, "risk_level": 3}
            }
        )
        
        # Save and add templates
        self.templates[research_template.id] = research_template
        self.templates[development_template.id] = development_template
        self.templates[analysis_template.id] = analysis_template
        
        self._save_templates()
    
    def _save_templates(self) -> None:
        """Save templates to disk."""
        os.makedirs(self.templates_dir, exist_ok=True)
        
        for template_id, template in self.templates.items():
            file_path = os.path.join(self.templates_dir, f"{template.id}.json")
            with open(file_path, "w") as f:
                json.dump(template.to_dict(), f, indent=2)
        
    async def decompose_goal(
        self, 
        goal: Dict[str, Any],
        strategy: DecompositionStrategy = DecompositionStrategy.TOP_DOWN,
        template_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> DecomposedGoal:
        """
        Decompose a high-level goal into subgoals.
        
        Args:
            goal: Dictionary with goal details (name, description, type, etc.)
            strategy: The decomposition strategy to use
            template_id: Optional ID of a template to use
            context: Optional additional context for decomposition
        
        Returns:
            A DecomposedGoal object representing the decomposed goal
        
        Raises:
            InvalidGoalError: If the goal is invalid
        """
        # Validate goal
        if not isinstance(goal, dict):
            raise InvalidGoalError("Goal must be a dictionary")
        
        if not goal.get("name"):
            raise InvalidGoalError("Goal must have a name")
        
        # Determine goal type
        goal_type = None
        if "type" in goal:
            try:
                goal_type = GoalType.from_str(goal["type"])
            except ValueError:
                logger.warning(f"Invalid goal type '{goal['type']}', using GENERAL instead")
                goal_type = GoalType.GENERAL
        else:
            goal_type = GoalType.GENERAL
            
        # Set description if not provided
        description = goal.get("description", f"Goal: {goal['name']}")
        
        # Get knowledge context if available
        knowledge_context = None
        if self.knowledge_system and context:
            knowledge_context = await self._get_knowledge_context(goal, context)
        
        # Apply decomposition strategy
        if strategy == DecompositionStrategy.TOP_DOWN:
            logger.info("Applying top-down decomposition strategy")
            if template_id and template_id in self.templates:
                template = self.templates[template_id]
                subgoals, root_ids = await self._apply_template(goal, template, knowledge_context)
            else:
                subgoals, root_ids = await self._apply_top_down_strategy(goal, knowledge_context)
        elif strategy == DecompositionStrategy.BOTTOM_UP:
            logger.info("Applying bottom-up decomposition strategy")
            subgoals, root_ids = await self._apply_bottom_up_strategy(goal, knowledge_context)
        elif strategy == DecompositionStrategy.ITERATIVE:
            logger.info("Applying iterative decomposition strategy")
            subgoals, root_ids = await self._apply_iterative_strategy(goal, knowledge_context)
        elif strategy == DecompositionStrategy.DOMAIN_SPECIFIC:
            logger.info("Applying domain-specific decomposition strategy")
            subgoals, root_ids = await self._apply_domain_specific_strategy(goal, knowledge_context)
        else:
            logger.warning(f"Unknown strategy '{strategy}', falling back to top-down")
            subgoals, root_ids = await self._apply_top_down_strategy(goal, knowledge_context)
        
        # Calculate total resources
        total_resources = await self._calculate_total_resources(subgoals)
        
        # Create the decomposed goal
        goal_id = str(uuid.uuid4())
        
        # Capture metadata if provided
        metadata = goal.get("metadata", {})
        
        decomposed_goal = DecomposedGoal(
            id=goal_id,
            name=goal["name"],
            description=description,
            goal_type=goal_type,
            strategy=strategy,
            subgoals=subgoals,
            root_subgoal_ids=root_ids,
            total_resources=total_resources,
            creation_time=datetime.now().isoformat(),
            metadata=metadata
        )
        
        # Store the decomposed goal
        self.decomposed_goals[goal_id] = decomposed_goal
        
        # Record in decomposition history
        self.decomposition_history.append({
            "goal_id": goal_id,
            "strategy": strategy.name,
            "timestamp": datetime.now().isoformat(),
            "subgoal_count": len(subgoals),
            "template_used": template_id if template_id else None,
            "validation": {"is_valid": True, "goal_type": goal_type.name}
        })
        
        return decomposed_goal
    
    async def _apply_template(
        self, 
        goal: Dict[str, Any],
        template: DecompositionTemplate,
        knowledge_context: Optional[Dict[str, Any]] = None
    ) -> Tuple[Dict[str, SubGoal], List[str]]:
        """
        Apply a decomposition template to a goal.
        
        Args:
            goal: Goal to decompose
            template: Template to apply
            knowledge_context: Knowledge context for decomposition
            
        Returns:
            Tuple of (subgoals_dict, root_subgoal_ids)
        """
        subgoals = {}
        root_subgoal_ids = []
        name_to_id_map = {}
        
        # Create subgoals from template structure
        for subgoal_template in template.subgoal_structure:
            subgoal_id = str(uuid.uuid4())
            name_to_id_map[subgoal_template["name"]] = subgoal_id
            
            # Get resource estimates from template
            template_resources = template.resource_estimates.get(subgoal_template["name"], {})
            resource_estimate = ResourceEstimate(
                time_hours=template_resources.get("time_hours", 5.0),
                complexity=template_resources.get("complexity", 5),
                knowledge_requirements=template_resources.get("knowledge_requirements", []),
                dependencies=template_resources.get("dependencies", []),
                risk_level=template_resources.get("risk_level", 5)
            )
            
            # Create subgoal
            subgoal = SubGoal(
                id=subgoal_id,
                name=subgoal_template["name"],
                description=subgoal_template["description"],
                goal_type=template.goal_type,
                priority=subgoal_template.get("priority", 5),
                resources=resource_estimate,
                parent_id=None,  # Will be set later
                children_ids=[],  # Will be set later
                status="pending",
                metadata={}
            )
            
            subgoals[subgoal_id] = subgoal
            
            # Track root subgoals
            if not subgoal_template.get("dependencies"):
                root_subgoal_ids.append(subgoal_id)
        
        # Set up dependencies and parent-child relationships
        for subgoal_template in template.subgoal_structure:
            subgoal_id = name_to_id_map[subgoal_template["name"]]
            dependencies = subgoal_template.get("dependencies", [])
            
            # Convert dependency names to IDs and update resources
            dependency_ids = [name_to_id_map[dep] for dep in dependencies if dep in name_to_id_map]
            subgoals[subgoal_id].resources.dependencies = dependency_ids
            
            # Set parent-child relationships
            for dep_id in dependency_ids:
                subgoals[dep_id].children_ids.append(subgoal_id)
                subgoals[subgoal_id].parent_id = dep_id  # Note: Multiple dependencies will override
        
        # Further decompose each subgoal if needed
        goal_type = GoalType[goal.get("type", "GENERAL").upper()]
        for subgoal_id, subgoal in list(subgoals.items()):
            if "decompose_further" in subgoal.metadata and subgoal.metadata["decompose_further"]:
                child_subgoals = await self._further_decompose_subgoal(subgoal, goal_type, knowledge_context)
                subgoals.update(child_subgoals)
        
        return subgoals, root_subgoal_ids
    
    async def _apply_domain_specific_strategy(
        self, 
        goal: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> Tuple[Dict[str, SubGoal], List[str]]:
        """
        Apply domain-specific decomposition strategy.
        
        Args:
            goal: Goal to decompose
            context: Knowledge context for decomposition
            
        Returns:
            Tuple of (subgoals_dict, root_subgoal_ids)
        """
        goal_type_str = goal.get("type", "GENERAL").upper()
        
        try:
            goal_type = GoalType[goal_type_str]
        except KeyError:
            logger.warning(f"Unknown goal type {goal_type_str}, using GENERAL")
            goal_type = GoalType.GENERAL
        
        # Select template based on goal type
        matching_templates = [t for t in self.templates.values() if t.goal_type == goal_type]
        
        if matching_templates:
            # Use the first matching template
            template = matching_templates[0]
            return await self._apply_template(goal, template, context)
        else:
            # Fall back to top-down strategy
            logger.info(f"No domain-specific template for {goal_type.name}, using top-down strategy")
            return await self._apply_top_down_strategy(goal, context)
    
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
    
    async def get_available_templates(self, goal_type: Optional[GoalType] = None) -> Dict[str, DecompositionTemplate]:
        """
        Get available decomposition templates.
        
        Args:
            goal_type: Optional filter by goal type
            
        Returns:
            Dictionary of template_id -> template
        """
        if goal_type:
            return {tid: t for tid, t in self.templates.items() if t.goal_type == goal_type}
        return self.templates
    
    async def create_template(
        self,
        name: str,
        description: str,
        goal_type: GoalType,
        subgoal_structure: List[Dict[str, Any]],
        resource_estimates: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Create a new decomposition template.
        
        Args:
            name: Template name
            description: Template description
            goal_type: Goal type for this template
            subgoal_structure: Structure of subgoals
            resource_estimates: Resource estimates for subgoals
            metadata: Optional metadata
            
        Returns:
            Template ID
        """
        template_id = str(uuid.uuid4())
        
        template = DecompositionTemplate(
            id=template_id,
            name=name,
            description=description,
            goal_type=goal_type,
            subgoal_structure=subgoal_structure,
            resource_estimates=resource_estimates,
            metadata=metadata or {}
        )
        
        self.templates[template_id] = template
        self._save_templates()
        
        return template_id
    
    async def delete_template(self, template_id: str) -> bool:
        """
        Delete a decomposition template.
        
        Args:
            template_id: ID of template to delete
            
        Returns:
            True if deleted, False if not found
        """
        if template_id in self.templates:
            del self.templates[template_id]
            
            # Remove from disk
            template_path = os.path.join(self.templates_dir, f"{template_id}.json")
            if os.path.exists(template_path):
                os.remove(template_path)
            
            return True
        return False 