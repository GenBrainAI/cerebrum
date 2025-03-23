
# Detailed Implementation Instructions: Work Unit 2.5 - Planning Engine Integration

## Overview

This work unit focuses on integrating all Planning Engine components (Goal Decomposition Engine, Research Planner, Implementation Planner, and Resource Allocation Manager) into a cohesive system. You'll create a central `PlanningEngine` class that orchestrates these components, establish cross-component workflows, implement versioning, and build metrics collection.

## Implementation Steps

### 1. Create Planning Engine Core Class

**File to create**: `src/server/planning/planning_engine.py`

```python
"""
Planning Engine for the Self-Aware Cerebrum system.

This module integrates all planning components (Goal Decomposition,
Research Planning, Implementation Planning, Resource Allocation)
into a unified planning system.
"""

from typing import Dict, List, Optional, Any, Tuple, Set, Union
import logging
import asyncio
import json
import os
import uuid
from datetime import datetime
from enum import Enum, auto
from dataclasses import dataclass, field
from pathlib import Path

from src.server.planning.goal_decomposition import (
    GoalDecompositionEngine, 
    GoalType, 
    DecompositionStrategy,
    DecomposedGoal,
    ResourceEstimate
)
from src.server.planning.research_planner import (
    ResearchPlanner,
    ResearchPlan,
    KnowledgeGap
)
from src.server.planning.implementation_planner import (
    ImplementationPlanner,
    ImplementationPlan,
    SolutionDesignSystem,
    SolutionDesign
)
from src.server.planning.resource_allocation import (
    ResourceAllocationManager,
    ResourcePool,
    AllocationPlan,
    AllocationStrategy
)
from src.server.context.knowledge_integration import KnowledgeIntegrationSystem

logger = logging.getLogger(__name__)

class PlanType(Enum):
    """Types of plans that can be created and managed."""
    GOAL_DECOMPOSITION = auto()
    RESEARCH = auto()
    IMPLEMENTATION = auto()
    RESOURCE_ALLOCATION = auto()
    INTEGRATED = auto()

@dataclass
class PlanVersion:
    """Version information for a plan."""
    version_id: str
    plan_id: str
    plan_type: PlanType
    timestamp: str
    changes: List[str]
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class PlanningMetrics:
    """Metrics for planning activities."""
    planning_time: float
    complexity_score: int
    confidence_score: float
    resource_efficiency: float
    adaptability_score: float
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class IntegratedPlan:
    """An integrated plan that combines multiple planning components."""
    id: str
    name: str
    description: str
    goal_decomposition_id: Optional[str] = None
    research_plan_ids: List[str] = field(default_factory=list)
    implementation_plan_id: Optional[str] = None
    resource_allocation_id: Optional[str] = None
    metrics: Optional[PlanningMetrics] = None
    version_history: List[PlanVersion] = field(default_factory=list)
    creation_time: str = field(default_factory=lambda: datetime.now().isoformat())
    status: str = "draft"
    metadata: Dict[str, Any] = field(default_factory=dict)

class PlanningEngine:
    """
    Central engine that integrates all planning components.
    
    This class provides a unified interface to the planning subsystems,
    coordinates cross-component workflows, and manages plan versioning.
    """
    
    def __init__(
        self,
        goal_decomposition_engine: Optional[GoalDecompositionEngine] = None,
        research_planner: Optional[ResearchPlanner] = None,
        implementation_planner: Optional[ImplementationPlanner] = None,
        solution_design_system: Optional[SolutionDesignSystem] = None,
        resource_allocation_manager: Optional[ResourceAllocationManager] = None,
        knowledge_system: Optional[KnowledgeIntegrationSystem] = None,
        storage_path: Optional[str] = None
    ):
        """
        Initialize the Planning Engine.
        
        Args:
            goal_decomposition_engine: Engine for decomposing goals
            research_planner: Planner for research activities
            implementation_planner: Planner for implementation activities
            solution_design_system: System for solution design
            resource_allocation_manager: Manager for resource allocation
            knowledge_system: Knowledge integration system
            storage_path: Path to store planning data
        """
        self.goal_decomposition_engine = goal_decomposition_engine
        self.research_planner = research_planner
        self.implementation_planner = implementation_planner
        self.solution_design_system = solution_design_system
        self.resource_allocation_manager = resource_allocation_manager
        self.knowledge_system = knowledge_system
        
        self.storage_path = storage_path or os.path.join(os.path.expanduser("~"), ".cerebrum", "planning_engine")
        os.makedirs(self.storage_path, exist_ok=True)
        
        # Create subdirectories
        self.integrated_plans_path = os.path.join(self.storage_path, "integrated_plans")
        self.versions_path = os.path.join(self.storage_path, "versions")
        self.metrics_path = os.path.join(self.storage_path, "metrics")
        
        os.makedirs(self.integrated_plans_path, exist_ok=True)
        os.makedirs(self.versions_path, exist_ok=True)
        os.makedirs(self.metrics_path, exist_ok=True)
        
        self.integrated_plans: Dict[str, IntegratedPlan] = {}
        self.plan_versions: Dict[str, PlanVersion] = {}
        
        # Load existing data
        self._load_integrated_plans()
        self._load_plan_versions()
    
    async def create_complete_plan(
        self,
        name: str,
        description: str,
        goal_requirements: Dict[str, Any],
        goal_type: GoalType,
        decomposition_strategy: DecompositionStrategy = DecompositionStrategy.TOP_DOWN,
        include_research: bool = True,
        include_implementation: bool = True,
        include_resource_allocation: bool = True,
        context: Optional[Dict[str, Any]] = None
    ) -> IntegratedPlan:
        """
        Create a complete integrated plan starting from goal decomposition.
        
        This method orchestrates the entire planning process across all components.
        
        Args:
            name: Name of the integrated plan
            description: Description of the plan
            goal_requirements: Requirements for the goal
            goal_type: Type of goal
            decomposition_strategy: Strategy for goal decomposition
            include_research: Whether to include research planning
            include_implementation: Whether to include implementation planning
            include_resource_allocation: Whether to include resource allocation
            context: Additional context information
            
        Returns:
            A complete integrated plan
        """
        start_time = datetime.now()
        
        # Create the integrated plan
        plan_id = str(uuid.uuid4())
        
        # Step 1: Goal Decomposition
        logger.info(f"Creating goal decomposition for plan: {name}")
        decomposed_goal = await self.goal_decomposition_engine.decompose_goal(
            goal=goal_requirements,
            strategy=decomposition_strategy,
            context=context
        )
        
        # Initialize the integrated plan
        integrated_plan = IntegratedPlan(
            id=plan_id,
            name=name,
            description=description,
            goal_decomposition_id=decomposed_goal.id,
            metadata={"goal_type": goal_type.name}
        )
        
        # Step 2: Research Planning (if needed)
        if include_research and self.research_planner:
            logger.info(f"Creating research plans for goal: {decomposed_goal.id}")
            research_plan_ids = await self._create_research_plans_for_goal(decomposed_goal, context)
            integrated_plan.research_plan_ids = research_plan_ids
        
        # Step 3: Implementation Planning (if needed)
        if include_implementation and self.implementation_planner and self.solution_design_system:
            logger.info(f"Creating implementation plan for goal: {decomposed_goal.id}")
            implementation_plan = await self._create_implementation_plan_for_goal(decomposed_goal, context)
            integrated_plan.implementation_plan_id = implementation_plan.id
        
        # Step 4: Resource Allocation (if needed)
        if include_resource_allocation and self.resource_allocation_manager:
            logger.info(f"Creating resource allocation for goal: {decomposed_goal.id}")
            allocation_plan = await self._create_resource_allocation_for_goal(
                decomposed_goal, 
                integrated_plan.implementation_plan_id,
                context
            )
            integrated_plan.resource_allocation_id = allocation_plan.id
        
        # Calculate metrics
        end_time = datetime.now()
        planning_time = (end_time - start_time).total_seconds()
        
        metrics = await self._calculate_planning_metrics(
            integrated_plan,
            planning_time,
            context
        )
        integrated_plan.metrics = metrics
        
        # Create initial version
        version = PlanVersion(
            version_id=str(uuid.uuid4()),
            plan_id=plan_id,
            plan_type=PlanType.INTEGRATED,
            timestamp=datetime.now().isoformat(),
            changes=["Initial plan creation"]
        )
        integrated_plan.version_history.append(version)
        
        # Save the integrated plan
        self.integrated_plans[plan_id] = integrated_plan
        self._save_integrated_plan(plan_id)
        
        return integrated_plan
    
    async def update_plan(
        self,
        plan_id: str,
        updates: Dict[str, Any],
        change_description: str,
        context: Optional[Dict[str, Any]] = None
    ) -> IntegratedPlan:
        """
        Update an existing integrated plan and create a new version.
        
        Args:
            plan_id: ID of the plan to update
            updates: Dictionary of updates to apply
            change_description: Description of the changes
            context: Additional context information
            
        Returns:
            The updated integrated plan
        """
        # Implementation logic
    
    async def _create_research_plans_for_goal(
        self,
        decomposed_goal: DecomposedGoal,
        context: Optional[Dict[str, Any]] = None
    ) -> List[str]:
        """
        Create research plans for a decomposed goal.
        
        Args:
            decomposed_goal: The decomposed goal
            context: Additional context information
            
        Returns:
            List of research plan IDs
        """
        research_plan_ids = []
        
        # Identify knowledge gaps for each subgoal
        for subgoal_id, subgoal in decomposed_goal.subgoals.items():
            topic = subgoal.name
            
            # Skip if subgoal doesn't need research
            if not any(req.lower().startswith("research") for req in subgoal.resources.knowledge_requirements):
                continue
                
            # Identify knowledge gaps
            knowledge_gaps = await self.research_planner.identify_knowledge_gaps(
                topic=topic,
                context=context
            )
            
            if knowledge_gaps:
                # Create a research plan
                plan = await self.research_planner.create_research_plan(
                    title=f"Research Plan for {topic}",
                    description=f"Research plan to address knowledge gaps for {topic}",
                    knowledge_gaps=list(knowledge_gaps.keys()),
                    context={
                        **(context or {}),
                        "subgoal_id": subgoal_id,
                        "goal_id": decomposed_goal.id
                    }
                )
                research_plan_ids.append(plan.id)
        
        return research_plan_ids
    
    async def _create_implementation_plan_for_goal(
        self,
        decomposed_goal: DecomposedGoal,
        context: Optional[Dict[str, Any]] = None
    ) -> ImplementationPlan:
        """
        Create an implementation plan for a decomposed goal.
        
        Args:
            decomposed_goal: The decomposed goal
            context: Additional context information
            
        Returns:
            An implementation plan
        """
        # Create a solution design
        requirements = []
        constraints = []
        
        for subgoal in decomposed_goal.subgoals.values():
            requirements.append(subgoal.description)
            
            # Extract constraints from metadata if available
            if "constraints" in subgoal.metadata:
                constraints.extend(subgoal.metadata["constraints"])
        
        # Create solution design
        solution_design = await self.solution_design_system.create_solution_design(
            name=f"Design for {decomposed_goal.name}",
            description=f"Solution design for {decomposed_goal.description}",
            requirements=requirements,
            constraints=constraints,
            context={
                **(context or {}),
                "goal_id": decomposed_goal.id
            }
        )
        
        # Create implementation plan
        implementation_plan = await self.implementation_planner.create_implementation_plan(
            name=f"Implementation for {decomposed_goal.name}",
            description=f"Implementation plan for {decomposed_goal.description}",
            solution_design_id=solution_design.id,
            context={
                **(context or {}),
                "goal_id": decomposed_goal.id
            }
        )
        
        return implementation_plan
    
    async def _create_resource_allocation_for_goal(
        self,
        decomposed_goal: DecomposedGoal,
        implementation_plan_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> AllocationPlan:
        """
        Create a resource allocation plan for a decomposed goal.
        
        Args:
            decomposed_goal: The decomposed goal
            implementation_plan_id: Optional ID of an implementation plan
            context: Additional context information
            
        Returns:
            A resource allocation plan
        """
        # Get the default resource pool
        # In a real implementation, you'd have logic to select the appropriate pool
        pools = list(self.resource_allocation_manager.resource_pools.values())
        if not pools:
            raise ValueError("No resource pools available")
        
        pool = pools[0]
        
        # Collect task requirements
        task_requirements = {}
        task_priorities = {}
        
        if implementation_plan_id and implementation_plan_id in self.implementation_planner.plans:
            # Use implementation tasks if available
            implementation_plan = self.implementation_planner.plans[implementation_plan_id]
            
            for task_id, task in implementation_plan.tasks.items():
                # Convert task resource needs to resource types
                task_requirements[task_id] = {
                    #... convert task requirements to resource types
                }
                task_priorities[task_id] = task.priority
        else:
            # Fall back to using subgoals
            for subgoal_id, subgoal in decomposed_goal.subgoals.items():
                # Convert subgoal resource needs to resource types
                task_requirements[subgoal_id] = {
                    #... convert subgoal requirements to resource types
                }
                task_priorities[subgoal_id] = subgoal.priority
        
        # Create allocation plan
        allocation_plan = await self.resource_allocation_manager.create_allocation_plan(
            name=f"Resources for {decomposed_goal.name}",
            description=f"Resource allocation for {decomposed_goal.description}",
            pool_id=pool.id,
            task_requirements=task_requirements,
            task_priorities=task_priorities,
            strategy=AllocationStrategy.PRIORITY_BASED,
            context={
                **(context or {}),
                "goal_id": decomposed_goal.id,
                "implementation_plan_id": implementation_plan_id
            }
        )
        
        return allocation_plan
    
    async def _calculate_planning_metrics(
        self,
        integrated_plan: IntegratedPlan,
        planning_time: float,
        context: Optional[Dict[str, Any]] = None
    ) -> PlanningMetrics:
        """
        Calculate metrics for an integrated plan.
        
        Args:
            integrated_plan: The integrated plan
            planning_time: Time taken for planning
            context: Additional context information
            
        Returns:
            Planning metrics
        """
        # Implementation logic
    
    async def get_integrated_plan(self, plan_id: str) -> Optional[IntegratedPlan]:
        """Get an integrated plan by ID."""
        return self.integrated_plans.get(plan_id)
    
    async def list_integrated_plans(self) -> List[Dict[str, Any]]:
        """List all integrated plans with summary information."""
        return [
            {
                "id": plan_id,
                "name": plan.name,
                "description": plan.description,
                "creation_time": plan.creation_time,
                "status": plan.status,
                "components": {
                    "goal_decomposition": plan.goal_decomposition_id is not None,
                    "research_plans": len(plan.research_plan_ids),
                    "implementation_plan": plan.implementation_plan_id is not None,
                    "resource_allocation": plan.resource_allocation_id is not None
                }
            }
            for plan_id, plan in self.integrated_plans.items()
        ]
    
    def _load_integrated_plans(self) -> None:
        """Load existing integrated plans from storage."""
        # Implementation logic
    
    def _load_plan_versions(self) -> None:
        """Load existing plan versions from storage."""
        # Implementation logic
    
    def _save_integrated_plan(self, plan_id: str) -> None:
        """Save an integrated plan to storage."""
        # Implementation logic
```

### 2. Create Planning Engine Configuration Manager

**File to create**: `src/server/planning/planning_config.py`

```python
"""
Planning Engine Configuration Manager.

This module provides configuration management for the Planning Engine,
including default settings, configuration loading, and validation.
"""

from typing import Dict, List, Optional, Any
import os
import json
import logging
from dataclasses import dataclass, field, asdict
from enum import Enum, auto

logger = logging.getLogger(__name__)

class OptimizationGoal(Enum):
    """Goals for planning optimization."""
    SPEED = auto()        # Optimize for faster planning
    QUALITY = auto()      # Optimize for higher quality plans
    EFFICIENCY = auto()   # Optimize for resource efficiency
    ADAPTABILITY = auto() # Optimize for plan flexibility
    BALANCED = auto()     # Balance all factors

@dataclass
class PlanningConfig:
    """Configuration for the Planning Engine."""
    
    # General settings
    default_storage_path: str = os.path.join(os.path.expanduser("~"), ".cerebrum", "planning_engine")
    optimization_goal: OptimizationGoal = OptimizationGoal.BALANCED
    max_plan_versions: int = 10
    
    # Goal Decomposition settings
    default_decomposition_strategy: str = "TOP_DOWN"
    max_decomposition_depth: int = 5
    min_subgoal_size: int = 2
    
    # Research Planning settings
    enable_auto_research: bool = True
    min_confidence_threshold: float = 0.6
    max_research_tasks: int = 20
    
    # Implementation Planning settings
    enable_auto_implementation: bool = True
    default_architecture_pattern: str = "MODULAR_MONOLITH"
    component_complexity_threshold: int = 7
    
    # Resource Allocation settings
    enable_auto_allocation: bool = True
    default_allocation_strategy: str = "PRIORITY_BASED"
    resource_buffer_percentage: float = 0.2
    
    # Performance settings
    enable_caching: bool = True
    cache_ttl_seconds: int = 3600
    parallel_planning: bool = True
    
    # Integration settings
    auto_integrate_plans: bool = True
    default_metrics_collection: bool = True
    
    # Custom settings
    custom_settings: Dict[str, Any] = field(default_factory=dict)

class PlanningConfigManager:
    """Manages configuration for the Planning Engine."""
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize the Planning Config Manager.
        
        Args:
            config_path: Path to the configuration file
        """
        self.config_path = config_path or os.path.join(
            os.path.expanduser("~"), 
            ".cerebrum", 
            "config", 
            "planning_engine.json"
        )
        self.config = PlanningConfig()
        
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
        
        # Load existing configuration if available
        if os.path.exists(self.config_path):
            self.load_config()
        else:
            # Save default configuration
            self.save_config()
    
    def load_config(self) -> PlanningConfig:
        """
        Load configuration from file.
        
        Returns:
            The loaded configuration
        """
        try:
            with open(self.config_path, "r") as f:
                config_dict = json.load(f)
            
            # Convert enum strings to enum values
            if "optimization_goal" in config_dict:
                config_dict["optimization_goal"] = OptimizationGoal[config_dict["optimization_goal"]]
            
            # Update configuration
            for key, value in config_dict.items():
                if hasattr(self.config, key):
                    setattr(self.config, key, value)
            
            logger.info(f"Loaded planning configuration from {self.config_path}")
            return self.config
        except Exception as e:
            logger.error(f"Error loading planning configuration: {e}")
            return self.config
    
    def save_config(self) -> bool:
        """
        Save configuration to file.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            # Convert to dictionary
            config_dict = asdict(self.config)
            
            # Convert enums to strings
            if "optimization_goal" in config_dict:
                config_dict["optimization_goal"] = self.config.optimization_goal.name
            
            with open(self.config_path, "w") as f:
                json.dump(config_dict, f, indent=4)
            
            logger.info(f"Saved planning configuration to {self.config_path}")
            return True
        except Exception as e:
            logger.error(f"Error saving planning configuration: {e}")
            return False
    
    def update_config(self, updates: Dict[str, Any]) -> PlanningConfig:
        """
        Update configuration with new values.
        
        Args:
            updates: Dictionary of updates to apply
            
        Returns:
            The updated configuration
        """
        try:
            # Handle enum conversions
            if "optimization_goal" in updates and isinstance(updates["optimization_goal"], str):
                updates["optimization_goal"] = OptimizationGoal[updates["optimization_goal"]]
            
            # Update configuration
            for key, value in updates.items():
                if hasattr(self.config, key):
                    setattr(self.config, key, value)
                else:
                    self.config.custom_settings[key] = value
            
            # Save updated configuration
            self.save_config()
            
            return self.config
        except Exception as e:
            logger.error(f"Error updating planning configuration: {e}")
            return self.config
    
    def get_component_config(self, component: str) -> Dict[str, Any]:
        """
        Get configuration specific to a component.
        
        Args:
            component: Component name (goal_decomposition, research, implementation, resource)
            
        Returns:
            Dictionary of component-specific configuration
        """
        config_dict = asdict(self.config)
        result = {}
        
        # Extract component-specific settings
        for key, value in config_dict.items():
            if key.startswith(component):
                result[key] = value
        
        # Include any custom settings
        for key, value in self.config.custom_settings.items():
            if key.startswith(component):
                result[key] = value
        
        return result
```

### 3. Create Planning Engine Factory

**File to create**: `src/server/planning/planning_factory.py`

```python
"""
Planning Engine Factory.

This module provides factory methods for creating Planning Engine instances
with various configurations and component combinations.
"""

from typing import Dict, List, Optional, Any
import os
import logging

from src.server.planning.planning_engine import PlanningEngine
from src.server.planning.planning_config import PlanningConfigManager, PlanningConfig
from src.server.planning.goal_decomposition import GoalDecompositionEngine
from src.server.planning.research_planner import ResearchPlanner
from src.server.planning.implementation_planner import ImplementationPlanner, SolutionDesignSystem
from src.server.planning.resource_allocation import ResourceAllocationManager
from src.server.context.knowledge_integration import KnowledgeIntegrationSystem
from src.server.observability.resource_monitor import ResourceMonitor
from src.server.system.codebase_vector_store import CodebaseVectorStore

logger = logging.getLogger(__name__)

class PlanningEngineFactory:
    """Factory for creating Planning Engine instances."""
    
    @staticmethod
    async def create_planning_engine(
        config_path: Optional[str] = None,
        knowledge_system: Optional[KnowledgeIntegrationSystem] = None,
        include_components: Optional[List[str]] = None,
        storage_path: Optional[str] = None
    ) -> PlanningEngine:
        """
        Create a Planning Engine with the specified components.
        
        Args:
            config_path: Path to configuration file
            knowledge_system: Knowledge Integration System instance
            include_components: List of components to include (all by default)
            storage_path: Path for storing planning data
            
        Returns:
            A configured Planning Engine instance
        """
        # Load configuration
        config_manager = PlanningConfigManager(config_path)
        config = config_manager.config
        
        # Determine which components to include
        include_all = include_components is None
        components = set(include_components or [])
        
        # Determine storage path
        storage_path = storage_path or config.default_storage_path
        
        # Create component instances
        goal_decomposition_engine = None
        research_planner = None
        implementation_planner = None
        solution_design_system = None
        resource_allocation_manager = None
        
        # Create Knowledge System if not provided
        if knowledge_system is None:
            knowledge_path = os.path.join(storage_path, "knowledge")
            knowledge_system = KnowledgeIntegrationSystem(storage_path=knowledge_path)
            await knowledge_system.initialize()
        
        # Create Goal Decomposition Engine
        if include_all or "goal_decomposition" in components:
            logger.info("Creating Goal Decomposition Engine")
            goal_decomposition_engine = GoalDecompositionEngine(
                knowledge_system=knowledge_system,
                storage_path=os.path.join(storage_path, "goal_decomposition")
            )
        
        # Create Research Planner
        if include_all or "research" in components:
            logger.info("Creating Research Planner")
            research_planner = ResearchPlanner(
                knowledge_system=knowledge_system,
                storage_path=os.path.join(storage_path, "research")
            )
        
        # Create Solution Design System and Implementation Planner
        if include_all or "implementation" in components:
            logger.info("Creating Implementation Planning components")
            
            # Create Codebase Vector Store
            codebase_store = CodebaseVectorStore()
            
            # Create Solution Design System
            solution_design_system = SolutionDesignSystem(
                knowledge_system=knowledge_system,
                codebase_store=codebase_store,
                storage_path=os.path.join(storage_path, "solution_designs")
            )
            
            # Create Implementation Planner
            implementation_planner = ImplementationPlanner(
                solution_design_system=solution_design_system,
                storage_path=os.path.join(storage_path, "implementation")
            )
        
        # Create Resource Allocation Manager
        if include_all or "resource" in components:
            logger.info("Creating Resource Allocation Manager")
            
            # Create Resource Monitor
            resource_monitor = ResourceMonitor()
            
            # Create Resource Allocation Manager
            resource_allocation_manager = ResourceAllocationManager(
                resource_monitor=resource_monitor,
                storage_path=os.path.join(storage_path, "resources")
            )
        
        # Create Planning Engine
        planning_engine = PlanningEngine(
            goal_decomposition_engine=goal_decomposition_engine,
            research_planner=research_planner,
            implementation_planner=implementation_planner,
            solution_design_system=solution_design_system,
            resource_allocation_manager=resource_allocation_manager,
            knowledge_system=knowledge_system,
            storage_path=storage_path
        )
        
        logger.info("Planning Engine created successfully")
        return planning_engine
```

### 4. Create Planning Engine Workflow Manager

**File to create**: `src/server/planning/planning_workflow.py`

```python
"""
Planning Engine Workflow Manager.

This module provides workflow management for the Planning Engine,
orchestrating cross-component workflows and managing their execution.
"""

from typing import Dict, List, Optional, Any, Union, Callable, Awaitable
import logging
import asyncio
import json
from enum import Enum, auto
from datetime import datetime
import uuid

from src.server.planning.planning_engine import (
    PlanningEngine, 
    IntegratedPlan,
    PlanType
)

logger = logging.getLogger(__name__)

class WorkflowStepStatus(Enum):
    """Status of a workflow step."""
    PENDING = auto()
    IN_PROGRESS = auto()
    COMPLETED = auto()
    FAILED = auto()
    SKIPPED = auto()

class WorkflowStatus(Enum):
    """Status of a workflow."""
    PENDING = auto()
    IN_PROGRESS = auto()
    COMPLETED = auto()
    FAILED = auto()
    CANCELLED = auto()

class PlanningWorkflow:
    """
    Manages workflows that span multiple planning components.
    
    This class orchestrates complex workflows across planning components,
    tracks their execution, and manages state transitions.
    """
    
    def __init__(self, planning_engine: PlanningEngine):
        """
        Initialize the Planning Workflow.
        
        Args:
            planning_engine: The Planning Engine instance
        """
        self.planning_engine = planning_engine
        self.workflows: Dict[str, Dict[str, Any]] = {}
    
    async def create_research_driven_workflow(
        self,
        name: str,
        description: str,
        initial_goal: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Create a research-driven workflow that adapts based on research findings.
        
        This workflow first decomposes a goal, conducts research, and then
        iteratively refines the goal and planning based on findings.
        
        Args:
            name: Name of the workflow
            description: Description of the workflow
            initial_goal: Initial goal definition
            context: Additional context information
            
        Returns:
            Workflow ID
        """
        workflow_id = str(uuid.uuid4())
        
        # Define workflow steps
        steps = [
            {
                "id": "goal_decomposition",
                "name": "Initial Goal Decomposition",
                "function": self._execute_goal_decomposition,
                "params": {
                    "goal": initial_goal,
                    "context": context
                },
                "status": WorkflowStepStatus.PENDING,
                "result": None,
                "dependencies": []
            },
            {
                "id": "research_planning",
                "name": "Research Planning",
                "function": self._execute_research_planning,
                "params": {
                    "context": context
                },
                "status": WorkflowStepStatus.PENDING,
                "result": None,
                "dependencies": ["goal_decomposition"]
            },
            {
                "id": "research_analysis",
                "name": "Research Analysis",
                "function": self._execute_research_analysis,
                "params": {
                    "context": context
                },
                "status": WorkflowStepStatus.PENDING,
                "result": None,
                "dependencies": ["research_planning"]
            },
            {
                "id": "goal_refinement",
                "name": "Goal Refinement",
                "function": self._execute_goal_refinement,
                "params": {
                    "context": context
                },
                "status": WorkflowStepStatus.PENDING,
                "result": None,
                "dependencies": ["research_analysis"]
            },
            {
                "id": "implementation_planning",
                "name": "Implementation Planning",
                "function": self._execute_implementation_planning,
                "params": {
                    "context": context
                },
                "status": WorkflowStepStatus.PENDING,
                "result": None,
                "dependencies": ["goal_refinement"]
            },
            {
                "id": "resource_allocation",
                "name": "Resource Allocation",
                "function": self._execute_resource_allocation,
                "params": {
                    "context": context
                },
                "status": WorkflowStepStatus.PENDING,
                "result": None,
                "dependencies": ["implementation_planning"]
            },
            {
                "id": "plan_integration",
                "name": "Plan Integration",
                "function": self._execute_plan_integration,
                "params": {
                    "name": name,
                    "description": description,
                    "context": context
                },
                "status": WorkflowStepStatus.PENDING,
                "result": None,
                "dependencies": ["resource_allocation"]
            }
        ]
        
        # Create the workflow
        workflow = {
            "id": workflow_id,
            "name": name,
            "description": description,
            "type": "research_driven",
            "steps": {step["id"]: step for step in steps},
            "step_order": [step["id"] for step in steps],
            "status": WorkflowStatus.PENDING,
            "start_time": None,
            "end_time": None,
            "result": None,
            "context": context or {}
        }
        
        self.workflows[workflow_id] = workflow
        logger.info(f"Created research-driven workflow: {workflow_id}")
        
        return workflow_id
    
    async def create_implementation_focused_workflow(
        self,
        name: str,
        description: str,
        implementation_requirements: List[str],
        constraints: List[str],
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Create an implementation-focused workflow that emphasizes solution design.
        
        This workflow focuses on solution design and implementation planning,
        with resource allocation and dependency management.
        
        Args:
            name: Name of the workflow
            description: Description of the workflow
            implementation_requirements: Implementation requirements
            constraints: Implementation constraints
            context: Additional context information
            
        Returns:
            Workflow ID
        """
        # Implementation logic
    
    async def execute_workflow(self, workflow_id: str) -> Dict[str, Any]:
        """
        Execute a workflow by processing its steps in order.
        
        Args:
            workflow_id: ID of the workflow to execute
            
        Returns:
            Workflow execution result
        """
        if workflow_id not in self.workflows:
            raise ValueError(f"Workflow not found: {workflow_id}")
        
        workflow = self.workflows[workflow_id]
        
        # Update workflow status
        workflow["status"] = WorkflowStatus.IN_PROGRESS
        workflow["start_time"] = datetime.now().isoformat()
        
        logger.info(f"Executing workflow: {workflow_id}")
        
        # Create shared workflow context
        workflow_context = {
            "workflow_id": workflow_id,
            "intermediate_results": {},
            **(workflow["context"] or {})
        }
        
        # Process steps in order, respecting dependencies
        for step_id in workflow["step_order"]:
            step = workflow["steps"][step_id]
            
            # Check dependencies
            dependencies_met = all(
                workflow["steps"][dep_id]["status"] == WorkflowStepStatus.COMPLETED
                for dep_id in step["dependencies"]
            )
            
            if not dependencies_met:
                step["status"] = WorkflowStepStatus.SKIPPED
                logger.warning(f"Skipping step {step_id} due to unmet dependencies")
                continue
            
            # Execute step
            try:
                logger.info(f"Executing workflow step: {step_id}")
                step["status"] = WorkflowStepStatus.IN_PROGRESS
                
                # Merge workflow context with step params
                step_params = {
                    **step["params"],
                    "workflow_context": workflow_context
                }
                
                # Execute the step function
                step_result = await step["function"](**step_params)
                
                # Update step status and result
                step["status"] = WorkflowStepStatus.COMPLETED
                step["result"] = step_result
                
                # Update workflow context with step result
                workflow_context["intermediate_results"][step_id] = step_result
                
                logger.info(f"Completed workflow step: {step_id}")
            except Exception as e:
                logger.error(f"Error executing workflow step {step_id}: {e}")
                step["status"] = WorkflowStepStatus.FAILED
                step["error"] = str(e)
                
                # Mark workflow as failed
                workflow["status"] = WorkflowStatus.FAILED
                workflow["end_time"] = datetime.now().isoformat()
                workflow["error"] = f"Failed on step {step_id}: {e}"
                
                return {
                    "workflow_id": workflow_id,
                    "status": "failed",
                    "error": str(e),
                    "completed_steps": [
                        s for s in workflow["step_order"] 
                        if workflow["steps"][s]["status"] == WorkflowStepStatus.COMPLETED
                    ]
                }
        
        # Check if all steps completed successfully
        all_completed = all(
            workflow["steps"][step_id]["status"] == WorkflowStepStatus.COMPLETED
            for step_id in workflow["step_order"]
        )
        
        if all_completed:
            # Mark workflow as completed
            workflow["status"] = WorkflowStatus.COMPLETED
            workflow["end_time"] = datetime.now().isoformat()
            
            # Set workflow result
            final_step_id = workflow["step_order"][-1]
            workflow["result"] = workflow["steps"][final_step_id]["result"]
            
            logger.info(f"Workflow completed successfully: {workflow_id}")
        else:
            # Mark workflow as failed
            workflow["status"] = WorkflowStatus.FAILED
            workflow["end_time"] = datetime.now().isoformat()
            
            logger.warning(f"Workflow did not complete all steps: {workflow_id}")
        
        return {
            "workflow_id": workflow_id,
            "status": workflow["status"].name.lower(),
            "result": workflow["result"],
            "completed_steps": [
                step_id for step_id in workflow["step_order"] 
                if workflow["steps"][step_id]["status"] == WorkflowStepStatus.COMPLETED
            ]
        }
    
    async def get_workflow_status(self, workflow_id: str) -> Dict[str, Any]:
        """
        Get the current status of a workflow.
        
        Args:
            workflow_id: ID of the workflow
            
        Returns:
            Workflow status information
        """
        if workflow_id not in self.workflows:
            raise ValueError(f"Workflow not found: {workflow_id}")
        
        workflow = self.workflows[workflow_id]
        
        return {
            "id": workflow_id,
            "name": workflow["name"],
            "status": workflow["status"].name,
            "start_time": workflow["start_time"],
            "end_time": workflow["end_time"],
            "steps": {
                step_id: {
                    "name": step["name"],
                    "status": step["status"].name,
                    "dependencies": step["dependencies"]
                }
                for step_id, step in workflow["steps"].items()
            },
            "step_order": workflow["step_order"]
        }
    
    # Implementation of step functions
    
    async def _execute_goal_decomposition(
        self,
        goal: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
        workflow_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Execute goal decomposition step."""
        if not self.planning_engine.goal_decomposition_engine:
            raise ValueError("Goal Decomposition Engine not available")
        
        # Merge contexts
        merged_context = {**(context or {}), **(workflow_context or {})}
        
        decomposed_goal = await self.planning_engine.goal_decomposition_engine.decompose_goal(
            goal=goal,
            context=merged_context
        )
        
        return {
            "goal_id": decomposed_goal.id,
            "subgoal_count": len(decomposed_goal.subgoals)
        }
    
    async def _execute_research_planning(
        self,
        context: Optional[Dict[str, Any]] = None,
        workflow_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Execute research planning step."""
        if not self.planning_engine.research_planner:
            raise ValueError("Research Planner not available")
        
        # Get the decomposed goal from previous step
        if "goal_decomposition" not in workflow_context.get("intermediate_results", {}):
            raise ValueError("Goal decomposition result not found in workflow context")
        
        goal_result = workflow_context["intermediate_results"]["goal_decomposition"]
        goal_id = goal_result["goal_id"]
        
        # Get the decomposed goal
        decomposed_goal = await self.planning_engine.goal_decomposition_engine.get_decomposed_goal(goal_id)
        if not decomposed_goal:
            raise ValueError(f"Decomposed goal not found: {goal_id}")
        
        # Create research plans
        research_plan_ids = await self.planning_engine._create_research_plans_for_goal(
            decomposed_goal=decomposed_goal,
            context=context
        )
        
        return {
            "research_plan_ids": research_plan_ids,
            "research_plan_count": len(research_plan_ids)
        }
    
    # Add implementations for other step functions:
    # - _execute_research_analysis
    # - _execute_goal_refinement
    # - _execute_implementation_planning
    # - _execute_resource_allocation
    # - _execute_plan_integration
```

### 5. Create Planning Engine Metrics Collector

**File to create**: `src/server/planning/planning_metrics.py`

```python
"""
Planning Engine Metrics Collector.

This module provides metrics collection and analysis for the Planning Engine,
tracking performance, quality, and efficiency metrics.
"""

from typing import Dict, List, Optional, Any, Union
import logging
import time
import json
import os
from datetime import datetime
import statistics
from dataclasses import dataclass, field, asdict
import uuid

logger = logging.getLogger(__name__)

@dataclass
class PlanningMetric:
    """A single planning metric measurement."""
    id: str
    name: str
    value: float
    timestamp: str
    category: str
    plan_id: Optional[str] = None
    component: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class MetricSummary:
    """Summary statistics for a metric."""
    count: int
    min: float
    max: float
    mean: float
    median: float
    std_dev: Optional[float] = None
    percentiles: Dict[str, float] = field(default_factory=dict)

class PlanningMetricsCollector:
    """Collects and analyzes metrics for the Planning Engine."""
    
    def __init__(self, storage_path: Optional[str] = None):
        """
        Initialize the Planning Metrics Collector.
        
        Args:
            storage_path: Path to store metrics data
        """
        self.storage_path = storage_path or os.path.join(
            os.path.expanduser("~"), 
            ".cerebrum", 
            "planning_engine", 
            "metrics"
        )
        os.makedirs(self.storage_path, exist_ok=True)
        
        # Create category directories
        self.categories = [
            "performance", "quality", "efficiency", 
            "adaptability", "resource_usage"
        ]
        
        for category in self.categories:
            os.makedirs(os.path.join(self.storage_path, category), exist_ok=True)
        
        self.metrics: Dict[str, PlanningMetric] = {}
        self.load_recent_metrics()
        
        # Performance timing
        self.timing_starts: Dict[str, float] = {}
    
    def start_timing(self, operation_name: str) -> str:
        """
        Start timing an operation.
        
        Args:
            operation_name: Name of the operation
            
        Returns:
            Timing ID
        """
        timing_id = f"{operation_name}_{str(uuid.uuid4())}"
        self.timing_starts[timing_id] = time.time()
        return timing_id
    
    def end_timing(
        self,
        timing_id: str,
        category: str = "performance",
        plan_id: Optional[str] = None,
        component: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[PlanningMetric]:
        """
        End timing an operation and record the metric.
        
        Args:
            timing_id: Timing ID from start_timing
            category: Metric category
            plan_id: Optional plan ID
            component: Optional component name
            metadata: Additional metadata
            
        Returns:
            The recorded metric, or None if timing ID not found
        """
        if timing_id not in self.timing_starts:
            logger.warning(f"Timing ID not found: {timing_id}")
            return None
        
        elapsed_time = time.time() - self.timing_starts[timing_id]
        del self.timing_starts[timing_id]
        
        # Extract operation name from timing ID
        operation_name = timing_id.split('_')[0]
        
        # Record the metric
        return self.record_metric(
            name=f"{operation_name}_time",
            value=elapsed_time,
            category=category,
            plan_id=plan_id,
            component=component,
            metadata=metadata
        )
    
    def record_metric(
        self,
        name: str,
        value: float,
        category: str,
        plan_id: Optional[str] = None,
        component: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> PlanningMetric:
        """
        Record a planning metric.
        
        Args:
            name: Metric name
            value: Metric value
            category: Metric category
            plan_id: Optional plan ID
            component: Optional component name
            metadata: Additional metadata
            
        Returns:
            The recorded metric
        """
        if category not in self.categories:
            logger.warning(f"Unknown metric category: {category}, using 'performance' instead")
            category = "performance"
        
        metric_id = str(uuid.uuid4())
        timestamp = datetime.now().isoformat()
        
        metric = PlanningMetric(
            id=metric_id,
            name=name,
            value=value,
            timestamp=timestamp,
            category=category,
            plan_id=plan_id,
            component=component,
            metadata=metadata or {}
        )
        
        # Store the metric
        self.metrics[metric_id] = metric
        self._save_metric(metric)
        
        return metric
    
    def get_metrics(
        self,
        category: Optional[str] = None,
        name: Optional[str] = None,
        plan_id: Optional[str] = None,
        component: Optional[str] = None,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None
    ) -> List[PlanningMetric]:
        """
        Get metrics matching the specified filters.
        
        Args:
            category: Filter by category
            name: Filter by name
            plan_id: Filter by plan ID
            component: Filter by component
            start_time: Filter by start time (ISO format)
            end_time: Filter by end time (ISO format)
            
        Returns:
            List of matching metrics
        """
        result = []
        
        for metric in self.metrics.values():
            # Apply filters
            if category and metric.category != category:
                continue
            if name and metric.name != name:
                continue
            if plan_id and metric.plan_id != plan_id:
                continue
            if component and metric.component != component:
                continue
            if start_time and metric.timestamp < start_time:
                continue
            if end_time and metric.timestamp > end_time:
                continue
            
            result.append(metric)
        
        return result
    
    def get_metric_summary(
        self,
        name: str,
        category: Optional[str] = None,
        plan_id: Optional[str] = None,
        component: Optional[str] = None
    ) -> Optional[MetricSummary]:
        """
        Get summary statistics for a metric.
        
        Args:
            name: Metric name
            category: Filter by category
            plan_id: Filter by plan ID
            component: Filter by component
            
        Returns:
            Summary statistics, or None if no matching metrics
        """
        metrics = self.get_metrics(
            name=name,
            category=category,
            plan_id=plan_id,
            component=component
        )
        
        if not metrics:
            return None
        
        values = [metric.value for metric in metrics]
        
        summary = MetricSummary(
            count=len(values),
            min=min(values),
            max=max(values),
            mean=statistics.mean(values),
            median=statistics.median(values)
        )
        
        # Calculate standard deviation if we have enough data
        if len(values) > 1:
            summary.std_dev = statistics.stdev(values)
        
        # Calculate percentiles
        if len(values) >= 10:
            sorted_values = sorted(values)
            size = len(sorted_values)
            summary.percentiles = {
                "p25": sorted_values[int(size * 0.25)],
                "p50": sorted_values[int(size * 0.5)],
                "p75": sorted_values[int(size * 0.75)],
                "p90": sorted_values[int(size * 0.9)],
                "p95": sorted_values[int(size * 0.95)],
                "p99": sorted_values[int(size * 0.99)] if size >= 100 else sorted_values[-1]
            }
        
        return summary
    
    def get_component_performance(self, component: str) -> Dict[str, Any]:
        """
        Get performance metrics for a component.
        
        Args:
            component: Component name
            
        Returns:
            Dictionary of performance metrics
        """
        metrics = self.get_metrics(component=component, category="performance")
        
        if not metrics:
            return {"component": component, "metrics": {}}
        
        # Group metrics by name
        grouped = {}
        for metric in metrics:
            if metric.name not in grouped:
                grouped[metric.name] = []
            grouped[metric.name].append(metric.value)
        
        # Calculate statistics for each metric
        result = {"component": component, "metrics": {}}
        
        for name, values in grouped.items():
            result["metrics"][name] = {
                "count": len(values),
                "min": min(values),
                "max": max(values),
                "mean": statistics.mean(values),
                "median": statistics.median(values),
                "latest": values[-1] if values else None
            }
        
        return result
    
    def load_recent_metrics(self, max_age_days: int = 7) -> None:
        """
        Load recent metrics from storage.
        
        Args:
            max_age_days: Maximum age of metrics to load, in days
        """
        cutoff_date = (datetime.now() - timedelta(days=max_age_days)).isoformat()
        
        for category in self.categories:
            category_dir = os.path.join(self.storage_path, category)
            
            if not os.path.exists(category_dir):
                continue
            
            for filename in os.listdir(category_dir):
                if not filename.endswith('.json'):
                    continue
                
                file_path = os.path.join(category_dir, filename)
                
                try:
                    with open(file_path, 'r') as f:
                        metric_data = json.load(f)
                    
                    # Skip if older than cutoff
                    if metric_data.get("timestamp", "") < cutoff_date:
                        continue
                    
                    metric = PlanningMetric(
                        id=metric_data["id"],
                        name=metric_data["name"],
                        value=metric_data["value"],
                        timestamp=metric_data["timestamp"],
                        category=metric_data["category"],
                        plan_id=metric_data.get("plan_id"),
                        component=metric_data.get("component"),
                        metadata=metric_data.get("metadata", {})
                    )
                    
                    self.metrics[metric.id] = metric
                except Exception as e:
                    logger.warning(f"Error loading metric file {file_path}: {e}")
        
        logger.info(f"Loaded {len(self.metrics)} recent metrics")
    
    def _save_metric(self, metric: PlanningMetric) -> None:
        """
        Save a metric to storage.
        
        Args:
            metric: The metric to save
        """
        category_dir = os.path.join(self.storage_path, metric.category)
        file_path = os.path.join(category_dir, f"{metric.id}.json")
        
        try:
            with open(file_path, 'w') as f:
                json.dump(asdict(metric), f, indent=2)
        except Exception as e:
            logger.error(f"Error saving metric {metric.id}: {e}")
```

### 6. Create Planning Engine Visualization

**File to create**: `src/server/planning/planning_visualization.py`

```python
"""
Planning Engine Visualization.

This module provides visualization capabilities for the Planning Engine,
generating diagrams and charts for plans, workflows, and metrics.
"""

from typing import Dict, List, Optional, Any, Union
import logging
import os
import json
from datetime import datetime
import uuid

logger = logging.getLogger(__name__)

class PlanningVisualizer:
    """Generates visualizations for planning components."""
    
    def __init__(self, storage_path: Optional[str] = None):
        """
        Initialize the Planning Visualizer.
        
        Args:
            storage_path: Path to store visualization data
        """
        self.storage_path = storage_path or os.path.join(
            os.path.expanduser("~"), 
            ".cerebrum", 
            "planning_engine", 
            "visualizations"
        )
        os.makedirs(self.storage_path, exist_ok=True)
    
    def generate_goal_tree(self, decomposed_goal: Any) -> Dict[str, Any]:
        """
        Generate a tree visualization for a decomposed goal.
        
        Args:
            decomposed_goal: The decomposed goal
            
        Returns:
            Visualization data
        """
        # Generate nodes and edges for the goal tree
        nodes = []
        edges = []
        
        # Add root node
        root_id = "root"
        nodes.append({
            "id": root_id,
            "label": decomposed_goal.name,
            "type": "goal",
            "data": {
                "description": decomposed_goal.description,
                "goal_type": decomposed_goal.goal_type.name if hasattr(decomposed_goal.goal_type, 'name') else str(decomposed_goal.goal_type)
            }
        })
        
        # Add subgoal nodes
        for subgoal_id, subgoal in decomposed_goal.subgoals.items():
            nodes.append({
                "id": subgoal_id,
                "label": subgoal.name,
                "type": "subgoal",
                "data": {
                    "description": subgoal.description,
                    "priority": subgoal.priority,
                    "status": subgoal.status
                }
            })
            
            # Add edge from parent to child
            if subgoal.parent_id:
                edges.append({
                    "source": subgoal.parent_id,
                    "target": subgoal_id
                })
            else:
                # Connect to root if no parent
                edges.append({
                    "source": root_id,
                    "target": subgoal_id
                })
        
        return {
            "type": "tree",
            "nodes": nodes,
            "edges": edges,
            "metadata": {
                "goal_id": decomposed_goal.id,
                "goal_name": decomposed_goal.name,
                "strategy": decomposed_goal.strategy.name if hasattr(decomposed_goal.strategy, 'name') else str(decomposed_goal.strategy)
            }
        }
    
    def generate_workflow_diagram(self, workflow: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate a diagram visualization for a workflow.
        
        Args:
            workflow: The workflow data
            
        Returns:
            Visualization data
        """
        nodes = []
        edges = []
        
        # Add nodes for each step
        for step_id, step in workflow["steps"].items():
            # Determine node color based on status
            color = "#cccccc"  # default gray
            if step["status"] == "COMPLETED":
                color = "#8bc34a"  # green
            elif step["status"] == "FAILED":
                color = "#f44336"  # red
            elif step["status"] == "IN_PROGRESS":
                color = "#2196f3"  # blue
            elif step["status"] == "SKIPPED":
                color = "#ff9800"  # orange
            
            nodes.append({
                "id": step_id,
                "label": step["name"],
                "color": color,
                "data": {
                    "status": step["status"],
                    "dependencies": step["dependencies"]
                }
            })
        
        # Add edges for dependencies
        for step_id, step in workflow["steps"].items():
            for dep_id in step["dependencies"]:
                edges.append({
                    "source": dep_id,
                    "target": step_id,
                    "label": "depends on"
                })
        
        return {
            "type": "workflow",
            "nodes": nodes,
            "edges": edges,
            "metadata": {
                "workflow_id": workflow["id"],
                "workflow_name": workflow["name"],
                "status": workflow["status"],
                "start_time": workflow["start_time"],
                "end_time": workflow["end_time"]
            }
        }
    
    def generate_metrics_chart(
        self,
        metrics: List[Any],
        chart_type: str = "line"
    ) -> Dict[str, Any]:
        """
        Generate a chart visualization for metrics.
        
        Args:
            metrics: List of metrics
            chart_type: Type of chart (line, bar, etc.)
            
        Returns:
            Visualization data
        """
        # Group metrics by name
        grouped = {}
        for metric in metrics:
            if metric.name not in grouped:
                grouped[metric.name] = []
            
            grouped[metric.name].append({
                "timestamp": metric.timestamp,
                "value": metric.value
            })
        
        # Sort data points by timestamp
        for name in grouped:
            grouped[name].sort(key=lambda x: x["timestamp"])
        
        # Generate chart data
        series = []
        for name, data_points in grouped.items():
            series.append({
                "name": name,
                "data": data_points
            })
        
        return {
            "type": "chart",
            "chart_type": chart_type,
            "series": series,
            "metadata": {
                "metric_count": len(metrics),
                "series_count": len(series),
                "generated_at": datetime.now().isoformat()
            }
        }
    
    def generate_resource_allocation_chart(
        self,
        allocation_plan: Any
    ) -> Dict[str, Any]:
        """
        Generate a chart visualization for resource allocation.
        
        Args:
            allocation_plan: The resource allocation plan
            
        Returns:
            Visualization data
        """
        # Extract resource types
        resource_types = set()
        for allocation in allocation_plan.allocations.values():
            resource_types.update(allocation.resources.keys())
        
        # Create series for each resource type
        series = []
        for resource_type in resource_types:
            data = []
            
            for task_id, allocation in allocation_plan.allocations.items():
                if resource_type in allocation.resources:
                    data.append({
                        "task_id": task_id,
                        "value": allocation.resources[resource_type]
                    })
            
            series.append({
                "name": str(resource_type),
                "data": data
            })
        
        return {
            "type": "resource_allocation",
            "chart_type": "bar",
            "series": series,
            "metadata": {
                "plan_id": allocation_plan.id,
                "plan_name": allocation_plan.name,
                "strategy": str(allocation_plan.strategy),
                "total_cost": allocation_plan.total_cost
            }
        }
    
    def save_visualization(
        self,
        visualization: Dict[str, Any],
        name: Optional[str] = None
    ) -> str:
        """
        Save a visualization to storage.
        
        Args:
            visualization: The visualization data
            name: Optional name for the visualization
            
        Returns:
            The visualization ID
        """
        vis_id = str(uuid.uuid4())
        
        # Create visualization metadata
        metadata = {
            "id": vis_id,
            "name": name or f"Visualization_{vis_id[:8]}",
            "type": visualization["type"],
            "created_at": datetime.now().isoformat(),
            "visualization": visualization
        }
        
        # Save to file
        file_path = os.path.join(self.storage_path, f"{vis_id}.json")
        
        try:
            with open(file_path, 'w') as f:
                json.dump(metadata, f, indent=2)
            
            logger.info(f"Saved visualization to {file_path}")
            return vis_id
        except Exception as e:
            logger.error(f"Error saving visualization: {e}")
            return vis_id
```

### 7. Create Planning Engine Integration for Self-Aware System

**File to create**: `src/server/self_aware_integration.py` (update)

```python
# Add to imports at the top
from src.server.planning.planning_engine import PlanningEngine
from src.server.planning.planning_factory import PlanningEngineFactory
from src.server.planning.planning_workflow import PlanningWorkflow
from src.server.planning.planning_metrics import PlanningMetricsCollector
from src.server.planning.planning_visualization import PlanningVisualizer

# Add to SelfAwareSystem.__init__
# In the existing SelfAwareSystem class, add the planning_engine field
self.planning_engine = None

# Add new method to SelfAwareSystem
async def initialize_planning_engine(self):
    """Initialize the Planning Engine."""
    logger.info("Initializing Planning Engine")
    
    storage_path = os.path.join(self.storage_path, "planning_engine")
    
    # Create the Planning Engine using the factory
    self.planning_engine = await PlanningEngineFactory.create_planning_engine(
        knowledge_system=self.knowledge_system,
        storage_path=storage_path
    )
    
    # Create Planning Workflow
    self.planning_workflow = PlanningWorkflow(self.planning_engine)
    
    # Create Metrics Collector
    self.planning_metrics_collector = PlanningMetricsCollector(
        storage_path=os.path.join(storage_path, "metrics")
    )
    
    # Create Visualizer
    self.planning_visualizer = PlanningVisualizer(
        storage_path=os.path.join(storage_path, "visualizations")
    )
    
    logger.info("Planning Engine initialized")

# Update the initialize method to call initialize_planning_engine
async def initialize(self):
    """Initialize the Self-Aware System."""
    # ... existing initialization code ...
    
    # Initialize Planning Engine
    await self.initialize_planning_engine()
    
    # ... rest of existing initialization code ...

# Add planning-related methods to SelfAwareSystem
async def create_goal_plan(
    self,
    name: str,
    description: str,
    goal_requirements: Dict[str, Any],
    goal_type: Any,
    include_research: bool = True,
    include_implementation: bool = True,
    include_resources: bool = True
) -> Dict[str, Any]:
    """
    Create a comprehensive plan for a goal.
    
    Args:
        name: Name of the plan
        description: Description of the plan
        goal_requirements: Requirements for the goal
        goal_type: Type of goal
        include_research: Whether to include research planning
        include_implementation: Whether to include implementation planning
        include_resources: Whether to include resource allocation
        
    Returns:
        The created plan
    """
    if not self.planning_engine:
        await self.initialize_planning_engine()
    
    # Record planning start time for metrics
    timing_id = self.planning_metrics_collector.start_timing("goal_planning")
    
    # Create the integrated plan
    integrated_plan = await self.planning_engine.create_complete_plan(
        name=name,
        description=description,
        goal_requirements=goal_requirements,
        goal_type=goal_type,
        include_research=include_research,
        include_implementation=include_implementation,
        include_resource_allocation=include_resources,
        context={"source": "self_aware_system"}
    )
    
    # Record planning time metric
    self.planning_metrics_collector.end_timing(
        timing_id=timing_id,
        category="performance",
        plan_id=integrated_plan.id,
        metadata={"plan_name": name}
    )
    
    # Generate visualization if available
    if self.planning_engine.goal_decomposition_engine and integrated_plan.goal_decomposition_id:
        decomposed_goal = await self.planning_engine.goal_decomposition_engine.get_decomposed_goal(
            integrated_plan.goal_decomposition_id
        )
        
        if decomposed_goal:
            visualization = self.planning_visualizer.generate_goal_tree(decomposed_goal)
            self.planning_visualizer.save_visualization(
                visualization,
                name=f"Goal Tree: {name}"
            )
    
    # Return plan information
    return {
        "id": integrated_plan.id,
        "name": integrated_plan.name,
        "description": integrated_plan.description,
        "components": {
            "goal_decomposition": integrated_plan.goal_decomposition_id,
            "research_plans": integrated_plan.research_plan_ids,
            "implementation_plan": integrated_plan.implementation_plan_id,
            "resource_allocation": integrated_plan.resource_allocation_id
        },
        "metrics": integrated_plan.metrics
    }

async def execute_research_driven_workflow(
    self,
    name: str,
    description: str,
    initial_goal: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Execute a research-driven workflow.
    
    Args:
        name: Name of the workflow
        description: Description of the workflow
        initial_goal: Initial goal definition
        
    Returns:
        Workflow execution result
    """
    if not self.planning_engine:
        await self.initialize_planning_engine()
    
    # Create workflow
    workflow_id = await self.planning_workflow.create_research_driven_workflow(
        name=name,
        description=description,
        initial_goal=initial_goal
    )
    
    # Execute workflow
    result = await self.planning_workflow.execute_workflow(workflow_id)
    
    # Generate visualization
    workflow_status = await self.planning_workflow.get_workflow_status(workflow_id)
    visualization = self.planning_visualizer.generate_workflow_diagram(workflow_status)
    self.planning_visualizer.save_visualization(
        visualization,
        name=f"Workflow: {name}"
    )
    
    return result

async def get_planning_component_performance(self) -> Dict[str, Any]:
    """
    Get performance metrics for planning components.
    
    Returns:
        Dictionary of performance metrics by component
    """
    if not self.planning_metrics_collector:
        await self.initialize_planning_engine()
    
    components = [
        "goal_decomposition",
        "research_planner",
        "implementation_planner",
        "resource_allocation"
    ]
    
    result = {}
    for component in components:
        performance = self.planning_metrics_collector.get_component_performance(component)
        result[component] = performance
    
    return result
```

### 8. Create Planning Engine Integration Tests

**File to create**: `tests/self_aware/planning/test_planning_integration.py`

```python
"""
Tests for Planning Engine integration.

This module tests the integration of Planning Engine components.
"""

import os
import pytest
import asyncio
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock

from src.server.planning.planning_engine import PlanningEngine, IntegratedPlan, PlanType
from src.server.planning.planning_factory import PlanningEngineFactory
from src.server.planning.planning_workflow import PlanningWorkflow
from src.server.planning.planning_metrics import PlanningMetricsCollector
from src.server.planning.planning_visualization import PlanningVisualizer

from src.server.planning.goal_decomposition import GoalDecompositionEngine, GoalType, DecompositionStrategy
from src.server.planning.research_planner import ResearchPlanner
from src.server.planning.implementation_planner import ImplementationPlanner, SolutionDesignSystem
from src.server.planning.resource_allocation import ResourceAllocationManager

from src.server.context.knowledge_integration import KnowledgeIntegrationSystem

@pytest.fixture
def temp_dir():
    """Create a temporary directory for testing."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)

@pytest.fixture
async def mock_components(temp_dir):
    """Create mock components for testing."""
    # Create mock components
    mock_knowledge_system = MagicMock(spec=KnowledgeIntegrationSystem)
    mock_knowledge_system.initialize = AsyncMock()
    
    mock_goal_decomposition = MagicMock(spec=GoalDecompositionEngine)
    mock_goal_decomposition.decompose_goal = AsyncMock()
    mock_goal_decomposition.get_decomposed_goal = AsyncMock()
    
    mock_research_planner = MagicMock(spec=ResearchPlanner)
    mock_research_planner.identify_knowledge_gaps = AsyncMock()
    mock_research_planner.create_research_plan = AsyncMock()
    
    mock_solution_design = MagicMock(spec=SolutionDesignSystem)
    mock_solution_design.create_solution_design = AsyncMock()
    
    mock_implementation_planner = MagicMock(spec=ImplementationPlanner)
    mock_implementation_planner.create_implementation_plan = AsyncMock()
    mock_implementation_planner.plans = {}
    
    mock_resource_allocation = MagicMock(spec=ResourceAllocationManager)
    mock_resource_allocation.create_allocation_plan = AsyncMock()
    mock_resource_allocation.resource_pools = {"pool1": MagicMock()}
    
    return {
        "knowledge_system": mock_knowledge_system,
        "goal_decomposition": mock_goal_decomposition,
        "research_planner": mock_research_planner,
        "solution_design": mock_solution_design,
        "implementation_planner": mock_implementation_planner,
        "resource_allocation": mock_resource_allocation
    }

@pytest.mark.asyncio
async def test_planning_engine_initialization(temp_dir, mock_components):
    """Test initializing the Planning Engine."""
    # Create a Planning Engine instance
    planning_engine = PlanningEngine(
        goal_decomposition_engine=mock_components["goal_decomposition"],
        research_planner=mock_components["research_planner"],
        implementation_planner=mock_components["implementation_planner"],
        solution_design_system=mock_components["solution_design"],
        resource_allocation_manager=mock_components["resource_allocation"],
        knowledge_system=mock_components["knowledge_system"],
        storage_path=temp_dir
    )
    
    # Check that the planning engine was initialized properly
    assert planning_engine.goal_decomposition_engine == mock_components["goal_decomposition"]
    assert planning_engine.research_planner == mock_components["research_planner"]
    assert planning_engine.implementation_planner == mock_components["implementation_planner"]
    assert planning_engine.solution_design_system == mock_components["solution_design"]
    assert planning_engine.resource_allocation_manager == mock_components["resource_allocation"]
    assert planning_engine.knowledge_system == mock_components["knowledge_system"]
    assert planning_engine.storage_path == temp_dir
    
    # Check that subdirectories were created
    assert os.path.exists(os.path.join(temp_dir, "integrated_plans"))
    assert os.path.exists(os.path.join(temp_dir, "versions"))
    assert os.path.exists(os.path.join(temp_dir, "metrics"))

@pytest.mark.asyncio
async def test_planning_engine_factory(temp_dir, mock_components):
    """Test creating a Planning Engine using the factory."""
    # Patch component creation
    with patch('src.server.planning.planning_factory.KnowledgeIntegrationSystem', return_value=mock_components["knowledge_system"]), \
         patch('src.server.planning.planning_factory.GoalDecompositionEngine', return_value=mock_components["goal_decomposition"]), \
         patch('src.server.planning.planning_factory.ResearchPlanner', return_value=mock_components["research_planner"]), \
         patch('src.server.planning.planning_factory.SolutionDesignSystem', return_value=mock_components["solution_design"]), \
         patch('src.server.planning.planning_factory.ImplementationPlanner', return_value=mock_components["implementation_planner"]), \
         patch('src.server.planning.planning_factory.ResourceAllocationManager', return_value=mock_components["resource_allocation"]), \
         patch('src.server.planning.planning_factory.CodebaseVectorStore'):
        
        # Create a Planning Engine using the factory
        planning_engine = await PlanningEngineFactory.create_planning_engine(
            storage_path=temp_dir
        )
        
        # Check that the planning engine was created properly
        assert planning_engine is not None
        assert isinstance(planning_engine, PlanningEngine)
        assert planning_engine.storage_path == temp_dir

@pytest.mark.asyncio
async def test_planning_workflow_creation(temp_dir, mock_components):
    """Test creating a Planning Workflow."""
    # Create a Planning Engine instance
    planning_engine = PlanningEngine(
        goal_decomposition_engine=mock_components["goal_decomposition"],
        research_planner=mock_components["research_planner"],
        implementation_planner=mock_components["implementation_planner"],
        solution_design_system=mock_components["solution_design"],
        resource_allocation_manager=mock_components["resource_allocation"],
        knowledge_system=mock_components["knowledge_system"],
        storage_path=temp_dir
    )
    
    # Create a Planning Workflow
    workflow = PlanningWorkflow(planning_engine)

    # Mock workflow step results
    mock_components["goal_decomposition"].decompose_goal.return_value = MagicMock(
        id="goal-123",
        subgoals={"sub1": MagicMock(), "sub2": MagicMock()}
    )
    
    # Create a research-driven workflow
    workflow_id = await workflow.create_research_driven_workflow(
        name="Test Research Workflow",
        description="A test workflow",
        initial_goal={"name": "Test Goal", "description": "A test goal"}
    )
    
    # Check that workflow was created properly
    assert workflow_id is not None
    assert workflow_id in workflow.workflows
    assert workflow.workflows[workflow_id]["name"] == "Test Research Workflow"
    assert workflow.workflows[workflow_id]["description"] == "A test workflow"
    assert len(workflow.workflows[workflow_id]["steps"]) > 0

@pytest.mark.asyncio
async def test_planning_metrics_collector(temp_dir):
    """Test the Planning Metrics Collector."""
    # Create a Planning Metrics Collector
    metrics_collector = PlanningMetricsCollector(storage_path=temp_dir)
    
    # Test timing functionality
    timing_id = metrics_collector.start_timing("test_operation")
    await asyncio.sleep(0.1)  # Wait a bit
    metric = metrics_collector.end_timing(
        timing_id=timing_id,
        category="performance",
        plan_id="plan-123",
        component="test_component"
    )
    
    # Check that metric was recorded properly
    assert metric is not None
    assert metric.name == "test_operation_time"
    assert metric.value > 0
    assert metric.category == "performance"
    assert metric.plan_id == "plan-123"
    assert metric.component == "test_component"
    
    # Test metric summarization
    summary = metrics_collector.get_metric_summary(
        name="test_operation_time",
        category="performance"
    )
    
    assert summary is not None
    assert summary.count == 1
    assert summary.min == metric.value
    assert summary.max == metric.value
    assert summary.mean == metric.value
    assert summary.median == metric.value

@pytest.mark.asyncio
async def test_planning_visualizer(temp_dir, mock_components):
    """Test the Planning Visualizer."""
    # Create a Planning Visualizer
    visualizer = PlanningVisualizer(storage_path=temp_dir)
    
    # Create mock decomposed goal
    mock_goal = MagicMock(
        id="goal-123",
        name="Test Goal",
        description="A test goal",
        goal_type=MagicMock(name="DEVELOPMENT"),
        strategy=MagicMock(name="TOP_DOWN"),
        subgoals={
            "sub1": MagicMock(
                name="Subgoal 1",
                description="First subgoal",
                parent_id=None,
                priority=1,
                status="IN_PROGRESS"
            ),
            "sub2": MagicMock(
                name="Subgoal 2",
                description="Second subgoal",
                parent_id="sub1",
                priority=2,
                status="PENDING"
            )
        }
    )
    
    # Generate goal tree visualization
    visualization = visualizer.generate_goal_tree(mock_goal)
    
    # Check visualization structure
    assert visualization["type"] == "tree"
    assert len(visualization["nodes"]) == 3  # Root + 2 subgoals
    assert len(visualization["edges"]) == 2  # Root->Sub1, Sub1->Sub2
    
    # Save visualization
    vis_id = visualizer.save_visualization(visualization, name="Test Goal Tree")
    
    # Check that visualization was saved
    assert vis_id is not None
    assert os.path.exists(os.path.join(temp_dir, f"{vis_id}.json"))

@pytest.mark.asyncio
async def test_create_complete_plan(temp_dir, mock_components):
    """Test creating a complete plan."""
    # Create a Planning Engine instance
    planning_engine = PlanningEngine(
        goal_decomposition_engine=mock_components["goal_decomposition"],
        research_planner=mock_components["research_planner"],
        implementation_planner=mock_components["implementation_planner"],
        solution_design_system=mock_components["solution_design"],
        resource_allocation_manager=mock_components["resource_allocation"],
        knowledge_system=mock_components["knowledge_system"],
        storage_path=temp_dir
    )
    
    # Mock component responses
    mock_components["goal_decomposition"].decompose_goal.return_value = MagicMock(
        id="goal-123",
        subgoals={"sub1": MagicMock(), "sub2": MagicMock()}
    )
    
    mock_components["research_planner"].create_research_plan.return_value = "research-123"
    
    mock_components["implementation_planner"].create_implementation_plan.return_value = "impl-123"
    
    mock_components["resource_allocation"].create_allocation_plan.return_value = MagicMock(
        id="resource-123"
    )
    
    # Create a complete plan
    plan = await planning_engine.create_complete_plan(
        name="Test Complete Plan",
        description="A test plan",
        goal_requirements={"key": "value"},
        goal_type=GoalType.DEVELOPMENT,
        include_research=True,
        include_implementation=True,
        include_resource_allocation=True
    )
    
    # Check that plan was created properly
    assert plan is not None
    assert plan.name == "Test Complete Plan"
    assert plan.description == "A test plan"
    assert plan.goal_decomposition_id == "goal-123"
    assert "research-123" in plan.research_plan_ids
    assert plan.implementation_plan_id == "impl-123"
    assert plan.resource_allocation_id == "resource-123"
    assert plan.plan_type == PlanType.COMPLETE
```

### 9. Create Documentation for Planning Engine Integration

**File to create**: `docs/planning_engine_integration.md`

```markdown
# Planning Engine Integration

This document provides an overview of the Planning Engine integration in the Self-Aware Cerebrum System.

## Architecture Overview

The Planning Engine serves as the central planning and coordination mechanism for the Self-Aware system,
integrating several specialized components:

1. **Goal Decomposition Engine**: Breaks down high-level goals into manageable subgoals
2. **Research Planner**: Plans research activities to address knowledge gaps
3. **Implementation Planner**: Creates detailed implementation plans
4. **Resource Allocation Manager**: Optimizes resource usage across tasks

These components work together through the Planning Engine, which provides:
- Integrated planning workflows
- Cross-component orchestration
- Metrics collection and analysis
- Visualization capabilities

## Core Components

### PlanningEngine

The central orchestrator that integrates all planning components. It provides:
- Management of integrated plans
- Cross-component workflows
- Version control for plans
- Configuration management

```python
# Example: Creating a complete plan
integrated_plan = await planning_engine.create_complete_plan(
    name="New Feature Development",
    description="Develop a new feature for the system",
    goal_requirements=requirements,
    goal_type=GoalType.DEVELOPMENT,
    include_research=True,
    include_implementation=True,
    include_resource_allocation=True
)
```

### PlanningWorkflow

Manages end-to-end planning workflows, including:
- Research-driven workflows
- Implementation-focused workflows
- Resource-optimized workflows
- Step dependencies and execution

```python
# Example: Creating and executing a workflow
workflow_id = await planning_workflow.create_research_driven_workflow(
    name="Feature Research",
    description="Research for new feature",
    initial_goal=goal_definition
)

result = await planning_workflow.execute_workflow(workflow_id)
```

### Planning Metrics

Collects and analyzes metrics for planning activities:
- Performance metrics
- Quality metrics
- Efficiency metrics
- Resource usage metrics

```python
# Example: Recording and analyzing metrics
timing_id = metrics_collector.start_timing("goal_planning")
# ... perform operation ...
metrics_collector.end_timing(timing_id, category="performance")

summary = metrics_collector.get_metric_summary(
    name="goal_planning_time",
    category="performance"
)
```

### Planning Visualization

Generates visualizations for plans and workflows:
- Goal decomposition trees
- Workflow diagrams
- Metrics charts
- Resource allocation visualizations

```python
# Example: Generating visualizations
visualization = visualizer.generate_goal_tree(decomposed_goal)
vis_id = visualizer.save_visualization(visualization, name="Goal Tree")
```

## Integration with Self-Aware System

The Planning Engine is integrated with the Self-Aware System through:
1. **Initialization**: The Planning Engine is initialized during Self-Aware System startup
2. **Knowledge Integration**: The Planning Engine uses the Knowledge Integration System for context
3. **Task Execution**: Planning workflows coordinate with the Task Execution System
4. **Resource Management**: Resource allocation integrates with system resource monitoring

```python
# Example: Initializing Planning Engine in Self-Aware System
await self.initialize_planning_engine()

# Example: Creating a plan from the Self-Aware System
plan = await self.create_goal_plan(
    name="New Feature",
    description="Develop a new feature",
    goal_requirements=requirements,
    goal_type=GoalType.DEVELOPMENT
)
```

## Workflows

The Planning Engine supports several standard workflows:

### Research-Driven Workflow

1. **Goal Decomposition**: Break down the initial goal
2. **Research Planning**: Identify knowledge gaps and create research plans
3. **Research Analysis**: Analyze research results
4. **Goal Refinement**: Refine goals based on research findings
5. **Implementation Planning**: Create implementation plans
6. **Resource Allocation**: Allocate resources for implementation
7. **Plan Integration**: Integrate all components into a coherent plan

### Implementation-Focused Workflow

1. **Goal Decomposition**: Break down the implementation goal
2. **Solution Design**: Design the implementation solution
3. **Implementation Planning**: Create detailed implementation plans
4. **Resource Allocation**: Allocate resources for implementation
5. **Implementation Integration**: Integrate implementation components

### Resource-Optimized Workflow

1. **Goal Decomposition**: Break down the goal with resource constraints
2. **Resource Analysis**: Analyze available resources
3. **Implementation Planning**: Create resource-aware implementation plans
4. **Resource Allocation**: Optimize resource allocation
5. **Plan Optimization**: Optimize plans based on resource constraints

## Best Practices

1. **Component Independence**: Each planning component should function independently
2. **Cross-Component Integration**: Use the Planning Engine for cross-component workflows
3. **Metrics Collection**: Always collect metrics for planning activities
4. **Visualization**: Use visualizations to understand complex plans
5. **Version Control**: Maintain version history for important plans
6. **Configuration Management**: Use configuration profiles for different planning scenarios
7. **Resource Awareness**: Always consider resource constraints in planning
8. **Knowledge Integration**: Leverage the Knowledge Integration System for context

## Extension Points

The Planning Engine can be extended through:
1. **Custom Workflows**: Creating specialized workflow templates
2. **New Planning Components**: Adding new specialized planners
3. **Custom Metrics**: Defining domain-specific metrics
4. **Custom Visualizations**: Creating specialized visualizations
5. **Integration Hooks**: Adding hooks for external systems

## API Reference

For detailed API reference, see the following documentation:
- [PlanningEngine API](../api/planning_engine.md)
- [PlanningWorkflow API](../api/planning_workflow.md)
- [PlanningMetrics API](../api/planning_metrics.md)
- [PlanningVisualization API](../api/planning_visualization.md)
```

### 10. Create API Documentation

**File to create**: `docs/api/planning_engine.md`

```markdown
# Planning Engine API

This document provides the API reference for the Planning Engine.

## PlanningEngine

The central orchestrator that integrates all planning components.

### Methods

#### `__init__`

```python
def __init__(
    self,
    goal_decomposition_engine: Optional[GoalDecompositionEngine] = None,
    research_planner: Optional[ResearchPlanner] = None,
    implementation_planner: Optional[ImplementationPlanner] = None,
    solution_design_system: Optional[SolutionDesignSystem] = None,
    resource_allocation_manager: Optional[ResourceAllocationManager] = None,
    knowledge_system: Optional[KnowledgeIntegrationSystem] = None,
    storage_path: Optional[str] = None
) -> None
```

Initialize the Planning Engine.

**Parameters:**
- `goal_decomposition_engine`: Goal Decomposition Engine instance
- `research_planner`: Research Planner instance
- `implementation_planner`: Implementation Planner instance
- `solution_design_system`: Solution Design System instance
- `resource_allocation_manager`: Resource Allocation Manager instance
- `knowledge_system`: Knowledge Integration System instance
- `storage_path`: Path to store planning data

#### `create_complete_plan`

```python
async def create_complete_plan(
    self,
    name: str,
    description: str,
    goal_requirements: Dict[str, Any],
    goal_type: GoalType,
    include_research: bool = True,
    include_implementation: bool = True,
    include_resource_allocation: bool = True,
    context: Optional[Dict[str, Any]] = None
) -> IntegratedPlan
```

Create a complete plan integrating all planning components.

**Parameters:**
- `name`: Name of the plan
- `description`: Description of the plan
- `goal_requirements`: Requirements for the goal
- `goal_type`: Type of goal
- `include_research`: Whether to include research planning
- `include_implementation`: Whether to include implementation planning
- `include_resource_allocation`: Whether to include resource allocation
- `context`: Additional context information

**Returns:**
- `IntegratedPlan`: The created integrated plan

#### `create_research_plan_for_goal`

```python
async def create_research_plan_for_goal(
    self,
    goal_id: str,
    context: Optional[Dict[str, Any]] = None
) -> str
```

Create a research plan for a specific goal.

**Parameters:**
- `goal_id`: ID of the decomposed goal
- `context`: Additional context information

**Returns:**
- `str`: ID of the created research plan

#### `create_implementation_plan_for_goal`

```python
async def create_implementation_plan_for_goal(
    self,
    goal_id: str,
    research_plan_ids: Optional[List[str]] = None,
    context: Optional[Dict[str, Any]] = None
) -> str
```

Create an implementation plan for a specific goal.

**Parameters:**
- `goal_id`: ID of the decomposed goal
- `research_plan_ids`: IDs of research plans to incorporate
- `context`: Additional context information

**Returns:**
- `str`: ID of the created implementation plan

#### `create_resource_allocation_for_plan`

```python
async def create_resource_allocation_for_plan(
    self,
    implementation_plan_id: str,
    context: Optional[Dict[str, Any]] = None
) -> str
```

Create a resource allocation plan for an implementation plan.

**Parameters:**
- `implementation_plan_id`: ID of the implementation plan
- `context`: Additional context information

**Returns:**
- `str`: ID of the created resource allocation plan

#### `get_integrated_plan`

```python
async def get_integrated_plan(
    self,
    plan_id: str
) -> Optional[IntegratedPlan]
```

Get an integrated plan by ID.

**Parameters:**
- `plan_id`: ID of the integrated plan

**Returns:**
- `Optional[IntegratedPlan]`: The integrated plan, or None if not found

#### `get_plan_version_history`

```python
async def get_plan_version_history(
    self,
    plan_id: str
) -> List[Dict[str, Any]]
```

Get the version history for a plan.

**Parameters:**
- `plan_id`: ID of the integrated plan

**Returns:**
- `List[Dict[str, Any]]`: List of version history entries

#### `create_plan_version`

```python
async def create_plan_version(
    self,
    plan_id: str,
    version_name: str,
    description: str
) -> str
```

Create a new version of a plan.

**Parameters:**
- `plan_id`: ID of the integrated plan
- `version_name`: Name of the version
- `description`: Description of the version

**Returns:**
- `str`: ID of the created version

#### `get_configuration`

```python
def get_configuration(self) -> Dict[str, Any]
```

Get the current configuration of the Planning Engine.

**Returns:**
- `Dict[str, Any]`: Current configuration

#### `update_configuration`

```python
async def update_configuration(
    self,
    config: Dict[str, Any]
) -> None
```

Update the configuration of the Planning Engine.

**Parameters:**
- `config`: New configuration values

## PlanningEngineFactory

Factory for creating Planning Engine instances.

### Methods

#### `create_planning_engine`

```python
@staticmethod
async def create_planning_engine(
    knowledge_system: Optional[KnowledgeIntegrationSystem] = None,
    storage_path: Optional[str] = None,
    config: Optional[Dict[str, Any]] = None
) -> PlanningEngine
```

Create a Planning Engine instance.

**Parameters:**
- `knowledge_system`: Knowledge Integration System instance
- `storage_path`: Path to store planning data
- `config`: Configuration for the Planning Engine

**Returns:**
- `PlanningEngine`: The created Planning Engine instance

## IntegratedPlan

Represents an integrated plan that combines multiple planning components.

### Properties

- `id`: ID of the integrated plan
- `name`: Name of the plan
- `description`: Description of the plan
- `plan_type`: Type of plan
- `goal_decomposition_id`: ID of the goal decomposition
- `research_plan_ids`: IDs of research plans
- `implementation_plan_id`: ID of the implementation plan
- `resource_allocation_id`: ID of the resource allocation plan
- `metrics`: Metrics for the plan
- `created_at`: Creation timestamp
- `updated_at`: Last update timestamp
```

## Completion Summary

This completes the detailed implementation instructions for Work Unit 2.5: Planning Engine Integration. The implementation covers:

1. Core Planning Engine classes with component integration
2. Planning workflow management for orchestrating planning processes 
3. Metrics collection and visualization support
4. Integration with the Self-Aware System
5. Comprehensive testing infrastructure
6. Detailed documentation

The Planning Engine serves as the orchestration layer that brings together all planning components (Goal Decomposition, Research Planner, Implementation Planner, and Resource Allocation Manager) into a cohesive system. It provides integrated planning workflows, cross-component orchestration, metrics collection, visualization capabilities, and proper versioning.

The implementation follows best practices for:
- Component independence with integrated workflows
- Version control and configuration management
- Metrics collection and visualization
- Resource awareness and optimization
- Knowledge integration for context-aware planning

The testing ensures all components work together correctly, and the documentation provides comprehensive guidance for using and extending the Planning Engine.
    
