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
    COMPLETE = auto()  # Includes all components

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
    plan_type: PlanType = PlanType.INTEGRATED

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
            metadata={"goal_type": goal_type.name},
            plan_type=PlanType.COMPLETE
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
        if plan_id not in self.integrated_plans:
            raise ValueError(f"Plan not found: {plan_id}")
            
        plan = self.integrated_plans[plan_id]
        
        # Apply updates
        for key, value in updates.items():
            if hasattr(plan, key):
                setattr(plan, key, value)
            elif key == "metadata":
                # Update metadata without overwriting existing keys
                for meta_key, meta_value in value.items():
                    plan.metadata[meta_key] = meta_value
        
        # Create new version
        version = PlanVersion(
            version_id=str(uuid.uuid4()),
            plan_id=plan_id,
            plan_type=plan.plan_type,
            timestamp=datetime.now().isoformat(),
            changes=[change_description]
        )
        plan.version_history.append(version)
        
        # Save the updated plan
        self._save_integrated_plan(plan_id)
        
        return plan
    
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
        if not self.resource_allocation_manager:
            logger.warning("No resource allocation manager available")
            raise ValueError("No resource allocation manager available")
        
        # Get the default resource pool
        # In a real implementation, you'd have logic to select the appropriate pool
        pools = await self.resource_allocation_manager.get_all_resource_pools()
        if not pools:
            raise ValueError("No resource pools available")
        
        pool = list(pools.values())[0]
        
        # Collect task requirements
        task_requirements = {}
        task_priorities = {}
        
        if implementation_plan_id and implementation_plan_id in self.implementation_planner.plans:
            # Use implementation tasks if available
            implementation_plan = self.implementation_planner.plans[implementation_plan_id]
            
            for task_id, task in implementation_plan.tasks.items():
                # Convert task resource needs to resource types
                resource_reqs = {
                    "compute": task.metadata.get("compute_requirements", 1),
                    "memory": task.metadata.get("memory_requirements", 1),
                    "storage": task.metadata.get("storage_requirements", 1),
                    "time": task.estimated_hours
                }
                task_requirements[task_id] = resource_reqs
                task_priorities[task_id] = task.priority
        else:
            # Fall back to using subgoals
            for subgoal_id, subgoal in decomposed_goal.subgoals.items():
                # Convert subgoal resource needs to resource types
                resource_reqs = {
                    "compute": 1,  # Default values
                    "memory": 1,
                    "storage": 1,
                    "time": subgoal.resources.time_hours
                }
                task_requirements[subgoal_id] = resource_reqs
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
        # Default metrics
        complexity_score = 5  # Mid-range default
        confidence_score = 0.7  # Reasonable default confidence
        resource_efficiency = 0.8  # Reasonable default efficiency
        adaptability_score = 0.6  # Moderate adaptability
        
        # Calculate complexity based on plan components
        component_count = 1  # Start with goal decomposition
        
        if integrated_plan.research_plan_ids:
            component_count += len(integrated_plan.research_plan_ids)
        
        if integrated_plan.implementation_plan_id:
            component_count += 1
            
        if integrated_plan.resource_allocation_id:
            component_count += 1
            
        # Scale complexity based on components (1-10 scale)
        complexity_score = min(10, max(1, component_count * 2))
        
        # Calculate confidence based on research plans (if available)
        if self.research_planner and integrated_plan.research_plan_ids:
            confidence_scores = []
            for plan_id in integrated_plan.research_plan_ids:
                plan = await self.research_planner.get_research_plan(plan_id)
                if plan:
                    # Calculate completeness of research
                    completed_items = sum(1 for item in plan.tasks.values() if item.status == "completed")
                    total_items = len(plan.tasks) or 1  # Avoid division by zero
                    confidence_scores.append(completed_items / total_items)
            
            if confidence_scores:
                confidence_score = sum(confidence_scores) / len(confidence_scores)
        
        # Calculate resource efficiency based on resource allocation (if available)
        if self.resource_allocation_manager and integrated_plan.resource_allocation_id:
            allocation_plan = await self.resource_allocation_manager.get_allocation_plan(
                integrated_plan.resource_allocation_id
            )
            if allocation_plan:
                resource_efficiency = allocation_plan.efficiency_score
        
        # Calculate adaptability score based on plan structure
        if integrated_plan.goal_decomposition_id and self.goal_decomposition_engine:
            decomposed_goal = await self.goal_decomposition_engine.get_decomposed_goal(
                integrated_plan.goal_decomposition_id
            )
            if decomposed_goal:
                # More subgoals usually means more granular and adaptable plan
                subgoal_count = len(decomposed_goal.subgoals)
                adaptability_score = min(1.0, max(0.2, 0.3 + (subgoal_count / 20)))
        
        # Create and return metrics
        return PlanningMetrics(
            planning_time=planning_time,
            complexity_score=complexity_score,
            confidence_score=confidence_score,
            resource_efficiency=resource_efficiency,
            adaptability_score=adaptability_score,
            metadata={
                "timestamp": datetime.now().isoformat(),
                "component_count": component_count
            }
        )
    
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
        if not os.path.exists(self.integrated_plans_path):
            return
            
        for filename in os.listdir(self.integrated_plans_path):
            if not filename.endswith('.json'):
                continue
                
            file_path = os.path.join(self.integrated_plans_path, filename)
            try:
                with open(file_path, 'r') as f:
                    plan_data = json.load(f)
                    
                # Convert version history
                version_history = []
                for version_data in plan_data.get("version_history", []):
                    version = PlanVersion(
                        version_id=version_data["version_id"],
                        plan_id=version_data["plan_id"],
                        plan_type=PlanType[version_data["plan_type"]],
                        timestamp=version_data["timestamp"],
                        changes=version_data["changes"],
                        metadata=version_data.get("metadata", {})
                    )
                    version_history.append(version)
                    
                # Convert metrics
                metrics = None
                if "metrics" in plan_data and plan_data["metrics"]:
                    metrics_data = plan_data["metrics"]
                    metrics = PlanningMetrics(
                        planning_time=metrics_data["planning_time"],
                        complexity_score=metrics_data["complexity_score"],
                        confidence_score=metrics_data["confidence_score"],
                        resource_efficiency=metrics_data["resource_efficiency"],
                        adaptability_score=metrics_data["adaptability_score"],
                        metadata=metrics_data.get("metadata", {})
                    )
                
                # Create plan
                plan = IntegratedPlan(
                    id=plan_data["id"],
                    name=plan_data["name"],
                    description=plan_data["description"],
                    goal_decomposition_id=plan_data.get("goal_decomposition_id"),
                    research_plan_ids=plan_data.get("research_plan_ids", []),
                    implementation_plan_id=plan_data.get("implementation_plan_id"),
                    resource_allocation_id=plan_data.get("resource_allocation_id"),
                    metrics=metrics,
                    version_history=version_history,
                    creation_time=plan_data.get("creation_time", datetime.now().isoformat()),
                    status=plan_data.get("status", "draft"),
                    metadata=plan_data.get("metadata", {}),
                    plan_type=PlanType[plan_data.get("plan_type", "INTEGRATED")]
                )
                
                self.integrated_plans[plan.id] = plan
                
            except Exception as e:
                logger.error(f"Error loading plan from {file_path}: {e}")
    
    def _load_plan_versions(self) -> None:
        """Load existing plan versions from storage."""
        if not os.path.exists(self.versions_path):
            return
            
        for filename in os.listdir(self.versions_path):
            if not filename.endswith('.json'):
                continue
                
            file_path = os.path.join(self.versions_path, filename)
            try:
                with open(file_path, 'r') as f:
                    version_data = json.load(f)
                    
                version = PlanVersion(
                    version_id=version_data["version_id"],
                    plan_id=version_data["plan_id"],
                    plan_type=PlanType[version_data["plan_type"]],
                    timestamp=version_data["timestamp"],
                    changes=version_data["changes"],
                    metadata=version_data.get("metadata", {})
                )
                
                self.plan_versions[version.version_id] = version
                
            except Exception as e:
                logger.error(f"Error loading version from {file_path}: {e}")
    
    def _save_integrated_plan(self, plan_id: str) -> None:
        """Save an integrated plan to storage."""
        if plan_id not in self.integrated_plans:
            return
            
        plan = self.integrated_plans[plan_id]
        file_path = os.path.join(self.integrated_plans_path, f"{plan_id}.json")
        
        try:
            # Convert plan to JSON-serializable format
            plan_dict = {
                "id": plan.id,
                "name": plan.name,
                "description": plan.description,
                "goal_decomposition_id": plan.goal_decomposition_id,
                "research_plan_ids": plan.research_plan_ids,
                "implementation_plan_id": plan.implementation_plan_id,
                "resource_allocation_id": plan.resource_allocation_id,
                "creation_time": plan.creation_time,
                "status": plan.status,
                "metadata": plan.metadata,
                "plan_type": plan.plan_type.name
            }
            
            # Convert metrics
            if plan.metrics:
                plan_dict["metrics"] = {
                    "planning_time": plan.metrics.planning_time,
                    "complexity_score": plan.metrics.complexity_score,
                    "confidence_score": plan.metrics.confidence_score,
                    "resource_efficiency": plan.metrics.resource_efficiency,
                    "adaptability_score": plan.metrics.adaptability_score,
                    "metadata": plan.metrics.metadata
                }
            
            # Convert version history
            plan_dict["version_history"] = []
            for version in plan.version_history:
                version_dict = {
                    "version_id": version.version_id,
                    "plan_id": version.plan_id,
                    "plan_type": version.plan_type.name,
                    "timestamp": version.timestamp,
                    "changes": version.changes,
                    "metadata": version.metadata
                }
                plan_dict["version_history"].append(version_dict)
                
                # Also save version separately
                self._save_plan_version(version)
            
            # Save plan
            with open(file_path, 'w') as f:
                json.dump(plan_dict, f, indent=2)
                
        except Exception as e:
            logger.error(f"Error saving plan {plan_id}: {e}")
    
    def _save_plan_version(self, version: PlanVersion) -> None:
        """Save a plan version to storage."""
        file_path = os.path.join(self.versions_path, f"{version.version_id}.json")
        
        try:
            # Convert version to JSON-serializable format
            version_dict = {
                "version_id": version.version_id,
                "plan_id": version.plan_id,
                "plan_type": version.plan_type.name,
                "timestamp": version.timestamp,
                "changes": version.changes,
                "metadata": version.metadata
            }
            
            # Save version
            with open(file_path, 'w') as f:
                json.dump(version_dict, f, indent=2)
                
        except Exception as e:
            logger.error(f"Error saving version {version.version_id}: {e}") 