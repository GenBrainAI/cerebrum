"""
Planning Integration for the Self-Aware Cerebrum.

This module integrates the various planning components including:
- Solution Design System
- Implementation Planner
- Resource Allocation Manager
- Planning Visualizations
"""

from typing import Dict, List, Optional, Any, Tuple, Set
import logging
import asyncio
import json
import os
import uuid
from datetime import datetime, timedelta

from src.server.planning.solution_design import SolutionDesignSystem, SolutionDesign, ComponentSpec, InterfaceSpec, ArchitecturePattern
from src.server.planning.implementation_planner import ImplementationPlanner, ImplementationPlan, ImplementationTask, TaskType
from src.server.planning.resource_allocation import ResourceAllocationManager, ResourcePool, AllocationPlan, ResourceType, AllocationStrategy
from src.server.planning.implementation_visualization import ImplementationVisualization
from src.server.planning.resource_visualization import ResourceVisualization
from src.server.observability.resource_monitor import ResourceMonitor

logger = logging.getLogger(__name__)

class PlanningOrchestrator:
    """
    Orchestrates the planning subsystems for solution design, implementation planning,
    and resource allocation.
    """
    
    def __init__(
        self, 
        storage_path: Optional[str] = None,
        resource_monitor: Optional[ResourceMonitor] = None
    ):
        """
        Initialize the Planning Orchestrator.
        
        Args:
            storage_path: Base path for storing planning artifacts
            resource_monitor: Resource monitor for tracking usage
        """
        self.storage_path = storage_path or os.path.join(os.path.expanduser("~"), ".cerebrum", "planning")
        os.makedirs(self.storage_path, exist_ok=True)
        
        # Initialize subsystems
        self.solution_design_system = SolutionDesignSystem(
            storage_path=os.path.join(self.storage_path, "solution_designs")
        )
        
        self.implementation_planner = ImplementationPlanner(
            solution_design_system=self.solution_design_system,
            storage_path=os.path.join(self.storage_path, "implementation_plans")
        )
        
        self.resource_allocation_manager = ResourceAllocationManager(
            resource_monitor=resource_monitor,
            storage_path=os.path.join(self.storage_path, "resource_allocations")
        )
        
        self.implementation_visualization = ImplementationVisualization(
            storage_path=os.path.join(self.storage_path, "visualizations", "implementation")
        )
        
        self.resource_visualization = ResourceVisualization(
            storage_path=os.path.join(self.storage_path, "visualizations", "resources")
        )
        
        # Planning contexts track the relationships between artifacts
        self.planning_contexts: Dict[str, Dict[str, Any]] = {}
        self._load_planning_contexts()
    
    async def create_planning_context(
        self, 
        name: str, 
        description: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Create a new planning context to group related artifacts.
        
        Args:
            name: Name of the planning context
            description: Description of the context
            metadata: Additional metadata for the context
            
        Returns:
            ID of the created planning context
        """
        context_id = str(uuid.uuid4())
        creation_time = datetime.now().isoformat()
        
        context = {
            "id": context_id,
            "name": name,
            "description": description,
            "creation_time": creation_time,
            "artifacts": {
                "solution_designs": [],
                "implementation_plans": [],
                "resource_pools": [],
                "allocation_plans": []
            },
            "metadata": metadata or {}
        }
        
        self.planning_contexts[context_id] = context
        self._save_planning_context(context_id)
        
        return context_id
    
    async def design_solution(
        self,
        context_id: str,
        name: str,
        description: str,
        requirements: List[str],
        constraints: Optional[List[str]] = None
    ) -> SolutionDesign:
        """
        Design a solution within a planning context.
        
        Args:
            context_id: ID of the planning context
            name: Name of the solution design
            description: Description of the design
            requirements: List of requirements
            constraints: List of constraints
            
        Returns:
            Created solution design
        """
        if context_id not in self.planning_contexts:
            raise ValueError(f"Planning context not found: {context_id}")
        
        # Create the solution design
        solution_design = await self.solution_design_system.create_solution_design(
            name=name,
            description=description,
            requirements=requirements,
            constraints=constraints or []
        )
        
        # Add to planning context
        self.planning_contexts[context_id]["artifacts"]["solution_designs"].append(solution_design.id)
        self._save_planning_context(context_id)
        
        return solution_design
    
    async def generate_implementation_plan(
        self,
        context_id: str,
        solution_design_id: str,
        name: str,
        description: str,
        start_date: str = None
    ) -> ImplementationPlan:
        """
        Generate an implementation plan for a solution design.
        
        Args:
            context_id: ID of the planning context
            solution_design_id: ID of the solution design
            name: Name of the implementation plan
            description: Description of the plan
            start_date: Optional start date (ISO format)
            
        Returns:
            Created implementation plan
        """
        if context_id not in self.planning_contexts:
            raise ValueError(f"Planning context not found: {context_id}")
        
        # Check if solution design is in this context
        context = self.planning_contexts[context_id]
        if solution_design_id not in context["artifacts"]["solution_designs"]:
            raise ValueError(f"Solution design {solution_design_id} not found in context {context_id}")
        
        # Get the solution design
        solution_design = await self.solution_design_system.get_solution_design(solution_design_id)
        if not solution_design:
            raise ValueError(f"Solution design not found: {solution_design_id}")
        
        # Create the implementation plan
        implementation_plan = await self.implementation_planner.create_implementation_plan(
            solution_design=solution_design,
            name=name,
            description=description
        )
        
        # Add to planning context
        context["artifacts"]["implementation_plans"].append(implementation_plan.id)
        self._save_planning_context(context_id)
        
        # Generate visualization
        if start_date:
            await self.implementation_visualization.generate_gantt_chart(
                plan=implementation_plan,
                start_date=start_date
            )
        
        await self.implementation_visualization.generate_dependency_graph(
            plan=implementation_plan
        )
        
        return implementation_plan
    
    async def create_resource_pool(
        self,
        context_id: str,
        name: str,
        description: str,
        resources: Dict[str, float],
        cost_per_unit: Optional[Dict[str, float]] = None
    ) -> ResourcePool:
        """
        Create a resource pool within a planning context.
        
        Args:
            context_id: ID of the planning context
            name: Name of the resource pool
            description: Description of the pool
            resources: Dictionary mapping resource types to amounts
            cost_per_unit: Dictionary mapping resource types to costs
            
        Returns:
            Created resource pool
        """
        if context_id not in self.planning_contexts:
            raise ValueError(f"Planning context not found: {context_id}")
        
        # Convert string resource types to enum
        enum_resources = {}
        for resource_type, amount in resources.items():
            try:
                enum_resources[ResourceType[resource_type.upper()]] = amount
            except KeyError:
                logger.warning(f"Invalid resource type: {resource_type}")
        
        # Convert cost per unit if provided
        enum_costs = None
        if cost_per_unit:
            enum_costs = {}
            for resource_type, cost in cost_per_unit.items():
                try:
                    enum_costs[ResourceType[resource_type.upper()]] = cost
                except KeyError:
                    logger.warning(f"Invalid resource type: {resource_type}")
        
        # Create the resource pool
        resource_pool = await self.resource_allocation_manager.create_resource_pool(
            name=name,
            description=description,
            resources=enum_resources,
            cost_per_unit=enum_costs
        )
        
        # Add to planning context
        self.planning_contexts[context_id]["artifacts"]["resource_pools"].append(resource_pool.id)
        self._save_planning_context(context_id)
        
        return resource_pool
    
    async def create_resource_allocation_plan(
        self,
        context_id: str,
        name: str,
        description: str,
        pool_id: str,
        implementation_plan_id: str,
        strategy: str = "PRIORITY_BASED"
    ) -> AllocationPlan:
        """
        Create a resource allocation plan for an implementation plan.
        
        Args:
            context_id: ID of the planning context
            name: Name of the allocation plan
            description: Description of the plan
            pool_id: ID of the resource pool
            implementation_plan_id: ID of the implementation plan
            strategy: Allocation strategy
            
        Returns:
            Created allocation plan
        """
        if context_id not in self.planning_contexts:
            raise ValueError(f"Planning context not found: {context_id}")
        
        # Check if resources and implementation plan are in this context
        context = self.planning_contexts[context_id]
        if pool_id not in context["artifacts"]["resource_pools"]:
            raise ValueError(f"Resource pool {pool_id} not found in context {context_id}")
        
        if implementation_plan_id not in context["artifacts"]["implementation_plans"]:
            raise ValueError(f"Implementation plan {implementation_plan_id} not found in context {context_id}")
        
        # Get the implementation plan
        implementation_plan = await self.implementation_planner.get_implementation_plan(implementation_plan_id)
        if not implementation_plan:
            raise ValueError(f"Implementation plan not found: {implementation_plan_id}")
        
        # Convert tasks to resource requirements
        task_requirements = {}
        task_priorities = {}
        
        for task_id, task in implementation_plan.tasks.items():
            # Map task complexity to resource requirements
            resource_requirements = {}
            
            # CPU requirements based on complexity
            if task.estimated_complexity <= 3:
                resource_requirements[ResourceType.CPU] = 1.0
            elif task.estimated_complexity <= 6:
                resource_requirements[ResourceType.CPU] = 2.0
            else:
                resource_requirements[ResourceType.CPU] = 3.0
            
            # Memory requirements based on complexity
            if task.estimated_complexity <= 3:
                resource_requirements[ResourceType.MEMORY] = 512.0
            elif task.estimated_complexity <= 6:
                resource_requirements[ResourceType.MEMORY] = 1024.0
            else:
                resource_requirements[ResourceType.MEMORY] = 2048.0
            
            # Time requirements based on estimated hours
            resource_requirements[ResourceType.TIME] = float(task.estimated_hours)
            
            # Add to task requirements
            task_requirements[task_id] = resource_requirements
            
            # Set priority based on task priority (1-10)
            task_priorities[task_id] = task.priority
        
        # Convert strategy string to enum
        try:
            strategy_enum = AllocationStrategy[strategy]
        except KeyError:
            logger.warning(f"Invalid allocation strategy: {strategy}, using PRIORITY_BASED")
            strategy_enum = AllocationStrategy.PRIORITY_BASED
        
        # Create the allocation plan
        allocation_plan = await self.resource_allocation_manager.create_allocation_plan(
            name=name,
            description=description,
            pool_id=pool_id,
            task_requirements=task_requirements,
            task_priorities=task_priorities,
            strategy=strategy_enum,
            context={"implementation_plan_id": implementation_plan_id}
        )
        
        # Add to planning context
        context["artifacts"]["allocation_plans"].append(allocation_plan.id)
        self._save_planning_context(context_id)
        
        # Generate cost visualization
        pool = await self.resource_allocation_manager.get_resource_pool(pool_id)
        if pool:
            await self.resource_visualization.generate_cost_chart(
                plan=allocation_plan,
                pool=pool
            )
        
        return allocation_plan
    
    async def optimize_resource_allocation(
        self,
        context_id: str,
        plan_id: str,
        optimization_goal: str = "cost"
    ) -> AllocationPlan:
        """
        Optimize a resource allocation plan.
        
        Args:
            context_id: ID of the planning context
            plan_id: ID of the allocation plan
            optimization_goal: Goal of the optimization (cost, performance, balance)
            
        Returns:
            Optimized allocation plan
        """
        if context_id not in self.planning_contexts:
            raise ValueError(f"Planning context not found: {context_id}")
        
        # Check if allocation plan is in this context
        context = self.planning_contexts[context_id]
        if plan_id not in context["artifacts"]["allocation_plans"]:
            raise ValueError(f"Allocation plan {plan_id} not found in context {context_id}")
        
        # Optimize the plan
        optimized_plan = await self.resource_allocation_manager.optimize_allocation_plan(
            plan_id=plan_id,
            optimization_goal=optimization_goal
        )
        
        # Generate cost visualization for the optimized plan
        pool = await self.resource_allocation_manager.get_resource_pool(optimized_plan.pool_id)
        if pool:
            await self.resource_visualization.generate_cost_chart(
                plan=optimized_plan,
                pool=pool
            )
        
        return optimized_plan
    
    async def compare_allocation_strategies(
        self,
        context_id: str,
        implementation_plan_id: str,
        pool_id: str
    ) -> str:
        """
        Compare different allocation strategies for an implementation plan.
        
        Args:
            context_id: ID of the planning context
            implementation_plan_id: ID of the implementation plan
            pool_id: ID of the resource pool
            
        Returns:
            ID of the comparison visualization
        """
        if context_id not in self.planning_contexts:
            raise ValueError(f"Planning context not found: {context_id}")
        
        # Check if resources and implementation plan are in this context
        context = self.planning_contexts[context_id]
        if pool_id not in context["artifacts"]["resource_pools"]:
            raise ValueError(f"Resource pool {pool_id} not found in context {context_id}")
        
        if implementation_plan_id not in context["artifacts"]["implementation_plans"]:
            raise ValueError(f"Implementation plan {implementation_plan_id} not found in context {context_id}")
        
        # Get the implementation plan
        implementation_plan = await self.implementation_planner.get_implementation_plan(implementation_plan_id)
        if not implementation_plan:
            raise ValueError(f"Implementation plan not found: {implementation_plan_id}")
        
        # Create a temporary plan for each strategy
        plans = []
        
        for strategy in AllocationStrategy:
            name = f"Comparison - {strategy.name}"
            description = f"Strategy comparison plan using {strategy.name}"
            
            # Create a temporary plan using this strategy
            temp_plan = await self.create_resource_allocation_plan(
                context_id=context_id,
                name=name,
                description=description,
                pool_id=pool_id,
                implementation_plan_id=implementation_plan_id,
                strategy=strategy.name
            )
            
            plans.append(temp_plan)
        
        # Generate comparison visualization
        comparison_chart = await self.resource_visualization.generate_comparison_chart(plans)
        
        # Add the comparison to context metadata
        comparison_id = str(uuid.uuid4())
        
        if "comparisons" not in context["metadata"]:
            context["metadata"]["comparisons"] = {}
        
        context["metadata"]["comparisons"][comparison_id] = {
            "type": "allocation_strategy",
            "implementation_plan_id": implementation_plan_id,
            "pool_id": pool_id,
            "plans": [plan.id for plan in plans],
            "timestamp": datetime.now().isoformat()
        }
        
        self._save_planning_context(context_id)
        
        return comparison_id
    
    async def generate_implementation_visualization(
        self,
        context_id: str,
        implementation_plan_id: str,
        start_date: Optional[str] = None
    ) -> Tuple[str, str]:
        """
        Generate visualizations for an implementation plan.
        
        Args:
            context_id: ID of the planning context
            implementation_plan_id: ID of the implementation plan
            start_date: Optional start date (ISO format)
            
        Returns:
            Tuple of (gantt_chart_id, dependency_graph_id)
        """
        if context_id not in self.planning_contexts:
            raise ValueError(f"Planning context not found: {context_id}")
        
        # Check if implementation plan is in this context
        context = self.planning_contexts[context_id]
        if implementation_plan_id not in context["artifacts"]["implementation_plans"]:
            raise ValueError(f"Implementation plan {implementation_plan_id} not found in context {context_id}")
        
        # Get the implementation plan
        implementation_plan = await self.implementation_planner.get_implementation_plan(implementation_plan_id)
        if not implementation_plan:
            raise ValueError(f"Implementation plan not found: {implementation_plan_id}")
        
        # Generate visualizations
        gantt_chart = await self.implementation_visualization.generate_gantt_chart(
            plan=implementation_plan,
            start_date=start_date or datetime.now().isoformat()
        )
        
        dependency_graph = await self.implementation_visualization.generate_dependency_graph(
            plan=implementation_plan
        )
        
        return gantt_chart.id, dependency_graph.id
    
    async def generate_resource_utilization_chart(
        self,
        context_id: str,
        pool_id: str
    ) -> str:
        """
        Generate a resource utilization chart for a pool.
        
        Args:
            context_id: ID of the planning context
            pool_id: ID of the resource pool
            
        Returns:
            ID of the utilization chart
        """
        if context_id not in self.planning_contexts:
            raise ValueError(f"Planning context not found: {context_id}")
        
        # Check if resource pool is in this context
        context = self.planning_contexts[context_id]
        if pool_id not in context["artifacts"]["resource_pools"]:
            raise ValueError(f"Resource pool {pool_id} not found in context {context_id}")
        
        # Get the resource pool
        pool = await self.resource_allocation_manager.get_resource_pool(pool_id)
        if not pool:
            raise ValueError(f"Resource pool not found: {pool_id}")
        
        # Calculate utilization
        utilization = await self.resource_allocation_manager.calculate_resource_utilization(pool_id)
        
        # Generate visualization
        chart = await self.resource_visualization.generate_utilization_chart(
            pool=pool,
            utilization=utilization
        )
        
        return pool_id  # Chart ID is the same as the pool ID
    
    async def get_planning_context(self, context_id: str) -> Optional[Dict[str, Any]]:
        """Get a planning context by ID."""
        return self.planning_contexts.get(context_id)
    
    async def get_all_planning_contexts(self) -> Dict[str, Dict[str, Any]]:
        """Get all planning contexts."""
        return self.planning_contexts
    
    def _save_planning_context(self, context_id: str) -> None:
        """Save a planning context to storage."""
        context_path = os.path.join(self.storage_path, "contexts")
        os.makedirs(context_path, exist_ok=True)
        
        file_path = os.path.join(context_path, f"{context_id}.json")
        try:
            with open(file_path, 'w') as f:
                json.dump(self.planning_contexts[context_id], f, indent=2)
        except Exception as e:
            logger.error(f"Error saving planning context {context_id}: {e}")
    
    def _load_planning_contexts(self) -> None:
        """Load planning contexts from storage."""
        context_path = os.path.join(self.storage_path, "contexts")
        os.makedirs(context_path, exist_ok=True)
        
        for filename in os.listdir(context_path):
            if filename.endswith('.json'):
                file_path = os.path.join(context_path, filename)
                try:
                    with open(file_path, 'r') as f:
                        context = json.load(f)
                        self.planning_contexts[context["id"]] = context
                except Exception as e:
                    logger.error(f"Error loading planning context {filename}: {e}")
    
    async def delete_planning_context(self, context_id: str) -> bool:
        """Delete a planning context and all its artifacts."""
        if context_id not in self.planning_contexts:
            return False
        
        # Get the context
        context = self.planning_contexts[context_id]
        
        # Delete all artifacts
        try:
            # Delete solution designs
            for design_id in context["artifacts"]["solution_designs"]:
                await self.solution_design_system.delete_solution_design(design_id)
            
            # Delete implementation plans
            for plan_id in context["artifacts"]["implementation_plans"]:
                await self.implementation_planner.delete_implementation_plan(plan_id)
            
            # Delete allocation plans
            for plan_id in context["artifacts"]["allocation_plans"]:
                await self.resource_allocation_manager.delete_allocation_plan(plan_id)
            
            # Delete resource pools
            for pool_id in context["artifacts"]["resource_pools"]:
                await self.resource_allocation_manager.delete_resource_pool(pool_id)
            
            # Delete context from memory
            del self.planning_contexts[context_id]
            
            # Delete context file
            context_path = os.path.join(self.storage_path, "contexts", f"{context_id}.json")
            if os.path.exists(context_path):
                os.remove(context_path)
            
            return True
        except Exception as e:
            logger.error(f"Error deleting planning context {context_id}: {e}")
            return False 