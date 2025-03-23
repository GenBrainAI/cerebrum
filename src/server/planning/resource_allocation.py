"""
Resource Allocation Manager for the Self-Aware Cerebrum.

This module provides capabilities for modeling, allocating,
and optimizing resource usage during planning and execution.
"""

from typing import Dict, List, Optional, Any, Tuple, Set
import logging
import asyncio
import json
import os
import uuid
from datetime import datetime, timedelta
from enum import Enum, auto
from dataclasses import dataclass, field

from src.server.observability.resource_monitor import ResourceMonitor

logger = logging.getLogger(__name__)

class ResourceType(Enum):
    """Types of resources that can be allocated."""
    CPU = auto()
    MEMORY = auto()
    STORAGE = auto()
    NETWORK = auto()
    API_CALLS = auto()
    GPU = auto()
    TOKENS = auto()
    TIME = auto()
    CONCURRENCY = auto()

class AllocationStrategy(Enum):
    """Strategies for allocating resources."""
    GREEDY = auto()          # Allocate as much as possible to high-priority tasks
    FAIR_SHARE = auto()      # Distribute evenly across all tasks
    PRIORITY_BASED = auto()  # Allocate based on task priorities
    ADAPTIVE = auto()        # Adapt allocations based on task performance
    COST_OPTIMIZED = auto()  # Optimize for lowest cost

@dataclass
class ResourcePool:
    """A pool of available resources."""
    id: str
    name: str
    description: str
    resources: Dict[ResourceType, float]
    cost_per_unit: Dict[ResourceType, float]
    creation_time: str
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "resources": {k.name: v for k, v in self.resources.items()},
            "cost_per_unit": {k.name: v for k, v in self.cost_per_unit.items()},
            "creation_time": self.creation_time
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ResourcePool':
        """Create resource pool from dictionary."""
        resources = {ResourceType[k]: v for k, v in data["resources"].items()}
        cost_per_unit = {ResourceType[k]: v for k, v in data["cost_per_unit"].items()}
        
        return cls(
            id=data["id"],
            name=data["name"],
            description=data["description"],
            resources=resources,
            cost_per_unit=cost_per_unit,
            creation_time=data["creation_time"]
        )
    
    def available(self, resource_type: ResourceType) -> float:
        """Get available amount of a resource."""
        return self.resources.get(resource_type, 0.0)
    
    def cost(self, resource_type: ResourceType, amount: float) -> float:
        """Calculate cost for a resource amount."""
        cost_per_unit = self.cost_per_unit.get(resource_type, 0.0)
        return amount * cost_per_unit
    
    def total_cost(self) -> float:
        """Calculate total cost of all resources."""
        total = 0.0
        for resource_type, amount in self.resources.items():
            total += self.cost(resource_type, amount)
        return total

@dataclass
class ResourceAllocation:
    """An allocation of resources to a specific task or plan."""
    id: str
    task_id: str
    pool_id: str
    resources: Dict[ResourceType, float]
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    status: str = "pending"  # pending, active, completed, failed
    actual_usage: Optional[Dict[ResourceType, float]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "id": self.id,
            "task_id": self.task_id,
            "pool_id": self.pool_id,
            "resources": {k.name: v for k, v in self.resources.items()},
            "start_time": self.start_time,
            "end_time": self.end_time,
            "status": self.status,
            "actual_usage": {k.name: v for k, v in self.actual_usage.items()} if self.actual_usage else None
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ResourceAllocation':
        """Create resource allocation from dictionary."""
        resources = {ResourceType[k]: v for k, v in data["resources"].items()}
        actual_usage = {ResourceType[k]: v for k, v in data["actual_usage"].items()} if data.get("actual_usage") else None
        
        return cls(
            id=data["id"],
            task_id=data["task_id"],
            pool_id=data["pool_id"],
            resources=resources,
            start_time=data.get("start_time"),
            end_time=data.get("end_time"),
            status=data.get("status", "pending"),
            actual_usage=actual_usage
        )
    
    def total_allocated(self) -> Dict[ResourceType, float]:
        """Get total allocated resources."""
        return self.resources
    
    def is_active(self) -> bool:
        """Check if allocation is active."""
        return self.status == "active"
    
    def is_completed(self) -> bool:
        """Check if allocation is completed."""
        return self.status == "completed"

@dataclass
class AllocationPlan:
    """A complete plan for allocating resources across tasks."""
    id: str
    name: str
    description: str
    pool_id: str
    allocations: Dict[str, ResourceAllocation]
    strategy: AllocationStrategy
    total_cost: float
    creation_time: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def efficiency_score(self) -> float:
        """Calculate the efficiency score of this allocation plan."""
        # If no allocations, return a default score
        if not self.allocations:
            return 0.5
        
        # Calculate based on how well resources are distributed
        # This is a simplified calculation
        total_allocations = len(self.allocations)
        if total_allocations == 0:
            return 0.5
            
        # A more complex implementation would consider resource utilization,
        # task priorities, deadlines, etc.
        return min(1.0, 0.6 + (0.4 * (total_allocations / 10)))
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "pool_id": self.pool_id,
            "allocations": {k: v.to_dict() for k, v in self.allocations.items()},
            "strategy": self.strategy.name,
            "total_cost": self.total_cost,
            "creation_time": self.creation_time,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AllocationPlan':
        """Create allocation plan from dictionary."""
        allocations = {
            k: ResourceAllocation.from_dict(v) for k, v in data["allocations"].items()
        }
        
        return cls(
            id=data["id"],
            name=data["name"],
            description=data["description"],
            pool_id=data["pool_id"],
            allocations=allocations,
            strategy=AllocationStrategy[data["strategy"]],
            total_cost=data["total_cost"],
            creation_time=data["creation_time"],
            metadata=data.get("metadata", {})
        )

class ResourceAllocationManager:
    """Manages resource allocation for planning and execution."""
    
    def __init__(
        self, 
        resource_monitor: Optional[ResourceMonitor] = None,
        storage_path: Optional[str] = None
    ):
        """
        Initialize the Resource Allocation Manager.
        
        Args:
            resource_monitor: Resource Monitor for tracking actual usage
            storage_path: Path to store allocation plans
        """
        self.resource_monitor = resource_monitor
        self.storage_path = storage_path or os.path.join(os.path.expanduser("~"), ".cerebrum", "resource_allocations")
        os.makedirs(self.storage_path, exist_ok=True)
        
        # Create subdirectories
        self.pools_path = os.path.join(self.storage_path, "pools")
        self.plans_path = os.path.join(self.storage_path, "plans")
        self.allocations_path = os.path.join(self.storage_path, "allocations")
        
        os.makedirs(self.pools_path, exist_ok=True)
        os.makedirs(self.plans_path, exist_ok=True)
        os.makedirs(self.allocations_path, exist_ok=True)
        
        self.resource_pools: Dict[str, ResourcePool] = {}
        self.allocation_plans: Dict[str, AllocationPlan] = {}
        self.active_allocations: Dict[str, ResourceAllocation] = {}
        
        # Load existing data
        self._load_resource_pools()
        self._load_allocation_plans()
        self._load_active_allocations()
    
    async def create_resource_pool(
        self,
        name: str,
        description: str,
        resources: Dict[ResourceType, float],
        cost_per_unit: Optional[Dict[ResourceType, float]] = None
    ) -> ResourcePool:
        """
        Create a new resource pool.
        
        Args:
            name: Name of the resource pool
            description: Description of the pool
            resources: Dictionary mapping resource types to available amounts
            cost_per_unit: Dictionary mapping resource types to cost per unit
            
        Returns:
            A new resource pool
        """
        # Generate ID
        pool_id = str(uuid.uuid4())
        creation_time = datetime.now().isoformat()
        
        # Set default costs if not provided
        if cost_per_unit is None:
            cost_per_unit = {}
            for resource_type in resources:
                # Default cost values
                if resource_type == ResourceType.CPU:
                    cost_per_unit[resource_type] = 0.1
                elif resource_type == ResourceType.MEMORY:
                    cost_per_unit[resource_type] = 0.01
                elif resource_type == ResourceType.STORAGE:
                    cost_per_unit[resource_type] = 0.001
                elif resource_type == ResourceType.API_CALLS:
                    cost_per_unit[resource_type] = 0.0001
                elif resource_type == ResourceType.TOKENS:
                    cost_per_unit[resource_type] = 0.00002
                elif resource_type == ResourceType.GPU:
                    cost_per_unit[resource_type] = 1.0
                else:
                    cost_per_unit[resource_type] = 0.1
        
        # Create pool
        pool = ResourcePool(
            id=pool_id,
            name=name,
            description=description,
            resources=resources,
            cost_per_unit=cost_per_unit,
            creation_time=creation_time
        )
        
        # Save pool
        self.resource_pools[pool_id] = pool
        self._save_resource_pool(pool)
        
        return pool
    
    async def create_allocation_plan(
        self,
        name: str,
        description: str,
        pool_id: str,
        task_requirements: Dict[str, Dict[ResourceType, float]],
        task_priorities: Dict[str, int],
        strategy: AllocationStrategy = AllocationStrategy.PRIORITY_BASED,
        context: Optional[Dict[str, Any]] = None
    ) -> AllocationPlan:
        """
        Create an allocation plan for a set of tasks.
        
        Args:
            name: Name of the allocation plan
            description: Description of the plan
            pool_id: ID of the resource pool to allocate from
            task_requirements: Dictionary mapping task IDs to their resource requirements
            task_priorities: Dictionary mapping task IDs to their priorities (1-10)
            strategy: Allocation strategy to use
            context: Additional context information
            
        Returns:
            A complete allocation plan
        """
        # Check if pool exists
        if pool_id not in self.resource_pools:
            raise ValueError(f"Resource pool not found: {pool_id}")
        
        pool = self.resource_pools[pool_id]
        
        # Generate ID
        plan_id = str(uuid.uuid4())
        creation_time = datetime.now().isoformat()
        
        # Create allocations based on strategy
        allocations, total_cost = await self._create_allocations_by_strategy(
            strategy,
            pool,
            task_requirements,
            task_priorities
        )
        
        # Create allocation plan
        plan = AllocationPlan(
            id=plan_id,
            name=name,
            description=description,
            pool_id=pool_id,
            allocations=allocations,
            strategy=strategy,
            total_cost=total_cost,
            creation_time=creation_time,
            metadata={
                "context": context or {}
            }
        )
        
        # Save plan
        self.allocation_plans[plan_id] = plan
        self._save_allocation_plan(plan)
        
        return plan
    
    async def _create_allocations_by_strategy(
        self,
        strategy: AllocationStrategy,
        pool: ResourcePool,
        task_requirements: Dict[str, Dict[ResourceType, float]],
        task_priorities: Dict[str, int]
    ) -> Tuple[Dict[str, ResourceAllocation], float]:
        """Create allocations based on strategy."""
        allocations: Dict[str, ResourceAllocation] = {}
        total_cost = 0.0
        
        if strategy == AllocationStrategy.GREEDY:
            # Allocate as much as possible to high-priority tasks
            
            # Sort tasks by priority (descending)
            sorted_tasks = sorted(
                task_requirements.items(),
                key=lambda x: task_priorities.get(x[0], 0),
                reverse=True
            )
            
            # Keep track of remaining resources
            remaining_resources = dict(pool.resources)
            
            # Allocate to each task in order
            for task_id, requirements in sorted_tasks:
                allocation_id = str(uuid.uuid4())
                allocated_resources: Dict[ResourceType, float] = {}
                
                for resource_type, amount in requirements.items():
                    # Allocate as much as possible
                    available = remaining_resources.get(resource_type, 0.0)
                    allocated = min(amount, available)
                    
                    if allocated > 0:
                        allocated_resources[resource_type] = allocated
                        remaining_resources[resource_type] = available - allocated
                        total_cost += pool.cost(resource_type, allocated)
                
                # Create allocation
                allocation = ResourceAllocation(
                    id=allocation_id,
                    task_id=task_id,
                    pool_id=pool.id,
                    resources=allocated_resources,
                    status="pending"
                )
                
                allocations[allocation_id] = allocation
            
        elif strategy == AllocationStrategy.FAIR_SHARE:
            # Distribute evenly across all tasks
            
            # Count number of tasks requiring each resource
            resource_task_counts: Dict[ResourceType, int] = {}
            for requirements in task_requirements.values():
                for resource_type in requirements:
                    resource_task_counts[resource_type] = resource_task_counts.get(resource_type, 0) + 1
            
            # Calculate fair share for each resource
            fair_shares: Dict[ResourceType, float] = {}
            for resource_type, count in resource_task_counts.items():
                available = pool.resources.get(resource_type, 0.0)
                fair_shares[resource_type] = available / count if count > 0 else 0
            
            # Allocate fair share to each task
            for task_id, requirements in task_requirements.items():
                allocation_id = str(uuid.uuid4())
                allocated_resources: Dict[ResourceType, float] = {}
                
                for resource_type, amount in requirements.items():
                    fair_share = fair_shares.get(resource_type, 0.0)
                    allocated = min(amount, fair_share)
                    
                    if allocated > 0:
                        allocated_resources[resource_type] = allocated
                        total_cost += pool.cost(resource_type, allocated)
                
                # Create allocation
                allocation = ResourceAllocation(
                    id=allocation_id,
                    task_id=task_id,
                    pool_id=pool.id,
                    resources=allocated_resources,
                    status="pending"
                )
                
                allocations[allocation_id] = allocation
            
        elif strategy == AllocationStrategy.PRIORITY_BASED:
            # Allocate based on task priorities
            
            # Calculate total priority points
            total_priority = sum(task_priorities.values())
            
            # Calculate priority-weighted shares
            priority_shares: Dict[str, Dict[ResourceType, float]] = {}
            for task_id, requirements in task_requirements.items():
                priority = task_priorities.get(task_id, 1)
                priority_ratio = priority / total_priority if total_priority > 0 else 0
                
                shares = {}
                for resource_type, amount in requirements.items():
                    available = pool.resources.get(resource_type, 0.0)
                    shares[resource_type] = available * priority_ratio
                
                priority_shares[task_id] = shares
            
            # Allocate resources based on priority shares
            for task_id, requirements in task_requirements.items():
                allocation_id = str(uuid.uuid4())
                allocated_resources: Dict[ResourceType, float] = {}
                
                for resource_type, amount in requirements.items():
                    share = priority_shares[task_id].get(resource_type, 0.0)
                    allocated = min(amount, share)
                    
                    if allocated > 0:
                        allocated_resources[resource_type] = allocated
                        total_cost += pool.cost(resource_type, allocated)
                
                # Create allocation
                allocation = ResourceAllocation(
                    id=allocation_id,
                    task_id=task_id,
                    pool_id=pool.id,
                    resources=allocated_resources,
                    status="pending"
                )
                
                allocations[allocation_id] = allocation
            
        elif strategy == AllocationStrategy.COST_OPTIMIZED:
            # Optimize for lowest cost
            
            # Calculate cost per unit for each task and resource
            task_costs: Dict[str, Dict[ResourceType, float]] = {}
            for task_id, requirements in task_requirements.items():
                costs = {}
                for resource_type, amount in requirements.items():
                    costs[resource_type] = pool.cost(resource_type, amount)
                task_costs[task_id] = costs
            
            # Sort tasks by cost (ascending) for each resource
            resource_task_costs: Dict[ResourceType, List[Tuple[str, float]]] = {}
            for resource_type in pool.resources:
                costs = []
                for task_id, costs_dict in task_costs.items():
                    if resource_type in costs_dict:
                        costs.append((task_id, costs_dict[resource_type]))
                resource_task_costs[resource_type] = sorted(costs, key=lambda x: x[1])
            
            # Allocate resources starting with lowest cost tasks
            remaining_resources = dict(pool.resources)
            task_allocations: Dict[str, Dict[ResourceType, float]] = {
                task_id: {} for task_id in task_requirements
            }
            
            for resource_type, task_costs in resource_task_costs.items():
                available = remaining_resources.get(resource_type, 0.0)
                
                for task_id, cost in task_costs:
                    # Allocate only what's needed
                    needed = task_requirements[task_id].get(resource_type, 0.0)
                    allocated = min(needed, available)
                    
                    if allocated > 0:
                        task_allocations[task_id][resource_type] = allocated
                        available -= allocated
                        total_cost += pool.cost(resource_type, allocated)
                
                remaining_resources[resource_type] = available
            
            # Create allocation objects
            for task_id, allocated_resources in task_allocations.items():
                if allocated_resources:
                    allocation_id = str(uuid.uuid4())
                    allocation = ResourceAllocation(
                        id=allocation_id,
                        task_id=task_id,
                        pool_id=pool.id,
                        resources=allocated_resources,
                        status="pending"
                    )
                    
                    allocations[allocation_id] = allocation
        
        else:  # AllocationStrategy.ADAPTIVE falls back to PRIORITY_BASED for now
            # For adaptive, we'd need historical performance data
            # Fallback to priority-based for now
            return await self._create_allocations_by_strategy(
                AllocationStrategy.PRIORITY_BASED,
                pool,
                task_requirements,
                task_priorities
            )
        
        return allocations, total_cost
    
    async def allocate_resources(
        self,
        allocation_id: str
    ) -> bool:
        """
        Activate a specific resource allocation.
        
        Args:
            allocation_id: ID of the allocation to activate
            
        Returns:
            True if allocation was successful, False otherwise
        """
        # Find the allocation
        allocation = None
        for plan in self.allocation_plans.values():
            if allocation_id in plan.allocations:
                allocation = plan.allocations[allocation_id]
                break
        
        if not allocation:
            logger.error(f"Allocation not found: {allocation_id}")
            return False
        
        # Check if already active
        if allocation.status == "active":
            logger.warning(f"Allocation already active: {allocation_id}")
            return True
        
        # Get the resource pool
        if allocation.pool_id not in self.resource_pools:
            logger.error(f"Resource pool not found: {allocation.pool_id}")
            return False
        
        pool = self.resource_pools[allocation.pool_id]
        
        # Check if resources are available
        for resource_type, amount in allocation.resources.items():
            available = pool.available(resource_type)
            
            # Account for active allocations
            for active_allocation in self.active_allocations.values():
                if active_allocation.pool_id == pool.id:
                    active_amount = active_allocation.resources.get(resource_type, 0.0)
                    available -= active_amount
            
            if amount > available:
                logger.error(f"Insufficient {resource_type.name} resources: needed {amount}, available {available}")
                return False
        
        # Activate allocation
        allocation.status = "active"
        allocation.start_time = datetime.now().isoformat()
        self.active_allocations[allocation_id] = allocation
        
        # Record resource usage if resource monitor is available
        if self.resource_monitor:
            for resource_type, amount in allocation.resources.items():
                await self.resource_monitor.record_usage(
                    resource_type.name.lower(),
                    amount,
                    operation_id=allocation_id
                )
        
        # Save the updated allocation
        self._save_active_allocation(allocation)
        
        logger.info(f"Allocation {allocation_id} activated")
        return True
    
    async def release_resources(
        self,
        allocation_id: str,
        usage_data: Optional[Dict[ResourceType, float]] = None
    ) -> bool:
        """
        Release resources from an active allocation.
        
        Args:
            allocation_id: ID of the allocation to release
            usage_data: Actual resource usage data
            
        Returns:
            True if release was successful, False otherwise
        """
        # Check if allocation is active
        if allocation_id not in self.active_allocations:
            logger.error(f"Allocation not active: {allocation_id}")
            return False
        
        allocation = self.active_allocations[allocation_id]
        
        # Complete the allocation
        allocation.status = "completed"
        allocation.end_time = datetime.now().isoformat()
        allocation.actual_usage = usage_data
        
        # Remove from active allocations
        del self.active_allocations[allocation_id]
        
        # Update the allocation in the plan
        for plan in self.allocation_plans.values():
            if allocation_id in plan.allocations:
                plan.allocations[allocation_id] = allocation
                self._save_allocation_plan(plan)
                break
        
        # Save the completed allocation
        self._save_completed_allocation(allocation)
        
        logger.info(f"Allocation {allocation_id} released")
        return True
    
    async def optimize_allocation_plan(
        self,
        plan_id: str,
        optimization_goal: str = "cost",  # cost, performance, or balance
        context: Optional[Dict[str, Any]] = None
    ) -> AllocationPlan:
        """
        Optimize an existing allocation plan.
        
        Args:
            plan_id: ID of the plan to optimize
            optimization_goal: Goal of the optimization
            context: Additional context information
            
        Returns:
            An optimized allocation plan
        """
        # Check if plan exists
        if plan_id not in self.allocation_plans:
            raise ValueError(f"Allocation plan not found: {plan_id}")
        
        original_plan = self.allocation_plans[plan_id]
        
        # Get the resource pool
        if original_plan.pool_id not in self.resource_pools:
            raise ValueError(f"Resource pool not found: {original_plan.pool_id}")
        
        pool = self.resource_pools[original_plan.pool_id]
        
        # Extract task requirements and priorities
        task_requirements: Dict[str, Dict[ResourceType, float]] = {}
        task_priorities: Dict[str, int] = {}
        
        for allocation_id, allocation in original_plan.allocations.items():
            if allocation.task_id not in task_requirements:
                task_requirements[allocation.task_id] = {}
                
            for resource_type, amount in allocation.resources.items():
                task_requirements[allocation.task_id][resource_type] = amount
            
            # Extract priority from metadata if available
            priority = 5  # Default priority
            if "priority" in original_plan.metadata.get("context", {}):
                priorities = original_plan.metadata["context"]["priority"]
                if allocation.task_id in priorities:
                    priority = priorities[allocation.task_id]
            
            task_priorities[allocation.task_id] = priority
        
        # Choose new strategy based on optimization goal
        new_strategy = original_plan.strategy
        
        if optimization_goal == "cost":
            new_strategy = AllocationStrategy.COST_OPTIMIZED
        elif optimization_goal == "performance":
            new_strategy = AllocationStrategy.GREEDY
        elif optimization_goal == "balance":
            new_strategy = AllocationStrategy.PRIORITY_BASED
        
        # Create new allocations
        new_allocations, total_cost = await self._create_allocations_by_strategy(
            new_strategy,
            pool,
            task_requirements,
            task_priorities
        )
        
        # Create new plan with the same ID
        optimized_plan = AllocationPlan(
            id=original_plan.id,
            name=f"{original_plan.name} (Optimized)",
            description=f"{original_plan.description} - Optimized for {optimization_goal}",
            pool_id=original_plan.pool_id,
            allocations=new_allocations,
            strategy=new_strategy,
            total_cost=total_cost,
            creation_time=datetime.now().isoformat(),
            metadata={
                "original_plan_id": original_plan.id,
                "optimization_goal": optimization_goal,
                "context": context or original_plan.metadata.get("context", {})
            }
        )
        
        # Save the plan (replacing the original)
        self.allocation_plans[plan_id] = optimized_plan
        self._save_allocation_plan(optimized_plan)
        
        return optimized_plan
    
    async def get_resource_pool(self, pool_id: str) -> Optional[ResourcePool]:
        """Get a resource pool by ID."""
        return self.resource_pools.get(pool_id)
    
    async def get_all_resource_pools(self) -> Dict[str, ResourcePool]:
        """Get all resource pools."""
        return self.resource_pools
    
    async def get_allocation_plan(self, plan_id: str) -> Optional[AllocationPlan]:
        """Get an allocation plan by ID."""
        return self.allocation_plans.get(plan_id)
    
    async def get_all_allocation_plans(self) -> Dict[str, AllocationPlan]:
        """Get all allocation plans."""
        return self.allocation_plans
    
    async def get_allocation(self, allocation_id: str) -> Optional[ResourceAllocation]:
        """Get a resource allocation by ID."""
        if allocation_id in self.active_allocations:
            return self.active_allocations[allocation_id]
        
        # Check in plans
        for plan in self.allocation_plans.values():
            if allocation_id in plan.allocations:
                return plan.allocations[allocation_id]
        
        return None
    
    async def get_active_allocations(self) -> Dict[str, ResourceAllocation]:
        """Get all active allocations."""
        return self.active_allocations
    
    async def calculate_resource_utilization(self, pool_id: str) -> Dict[ResourceType, float]:
        """
        Calculate current resource utilization for a pool.
        
        Args:
            pool_id: ID of the resource pool
            
        Returns:
            Dictionary mapping resource types to utilization percentages
        """
        if pool_id not in self.resource_pools:
            raise ValueError(f"Resource pool not found: {pool_id}")
        
        pool = self.resource_pools[pool_id]
        utilization: Dict[ResourceType, float] = {}
        
        # Calculate total allocated resources
        allocated: Dict[ResourceType, float] = {}
        for allocation in self.active_allocations.values():
            if allocation.pool_id == pool_id:
                for resource_type, amount in allocation.resources.items():
                    allocated[resource_type] = allocated.get(resource_type, 0.0) + amount
        
        # Calculate utilization percentages
        for resource_type, total in pool.resources.items():
            if total > 0:
                used = allocated.get(resource_type, 0.0)
                utilization[resource_type] = (used / total) * 100.0
            else:
                utilization[resource_type] = 0.0
        
        return utilization
    
    def _load_resource_pools(self) -> None:
        """Load existing resource pools from storage."""
        for filename in os.listdir(self.pools_path):
            if filename.endswith('.json'):
                file_path = os.path.join(self.pools_path, filename)
                try:
                    with open(file_path, 'r') as f:
                        data = json.load(f)
                        pool = ResourcePool.from_dict(data)
                        self.resource_pools[pool.id] = pool
                except Exception as e:
                    logger.error(f"Error loading resource pool {filename}: {e}")
    
    def _load_allocation_plans(self) -> None:
        """Load existing allocation plans from storage."""
        for filename in os.listdir(self.plans_path):
            if filename.endswith('.json'):
                file_path = os.path.join(self.plans_path, filename)
                try:
                    with open(file_path, 'r') as f:
                        data = json.load(f)
                        plan = AllocationPlan.from_dict(data)
                        self.allocation_plans[plan.id] = plan
                except Exception as e:
                    logger.error(f"Error loading allocation plan {filename}: {e}")
    
    def _load_active_allocations(self) -> None:
        """Load active allocations from storage."""
        active_dir = os.path.join(self.allocations_path, "active")
        if os.path.exists(active_dir):
            for filename in os.listdir(active_dir):
                if filename.endswith('.json'):
                    file_path = os.path.join(active_dir, filename)
                    try:
                        with open(file_path, 'r') as f:
                            data = json.load(f)
                            allocation = ResourceAllocation.from_dict(data)
                            self.active_allocations[allocation.id] = allocation
                    except Exception as e:
                        logger.error(f"Error loading active allocation {filename}: {e}")
    
    def _save_resource_pool(self, pool: ResourcePool) -> None:
        """Save a resource pool to storage."""
        file_path = os.path.join(self.pools_path, f"{pool.id}.json")
        try:
            with open(file_path, 'w') as f:
                json.dump(pool.to_dict(), f, indent=2)
        except Exception as e:
            logger.error(f"Error saving resource pool {pool.id}: {e}")
    
    def _save_allocation_plan(self, plan: AllocationPlan) -> None:
        """Save an allocation plan to storage."""
        file_path = os.path.join(self.plans_path, f"{plan.id}.json")
        try:
            with open(file_path, 'w') as f:
                json.dump(plan.to_dict(), f, indent=2)
        except Exception as e:
            logger.error(f"Error saving allocation plan {plan.id}: {e}")
    
    def _save_active_allocation(self, allocation: ResourceAllocation) -> None:
        """Save an active allocation to storage."""
        active_dir = os.path.join(self.allocations_path, "active")
        os.makedirs(active_dir, exist_ok=True)
        file_path = os.path.join(active_dir, f"{allocation.id}.json")
        try:
            with open(file_path, 'w') as f:
                json.dump(allocation.to_dict(), f, indent=2)
        except Exception as e:
            logger.error(f"Error saving active allocation {allocation.id}: {e}")
    
    def _save_completed_allocation(self, allocation: ResourceAllocation) -> None:
        """Save a completed allocation to storage."""
        # Remove from active directory
        active_file = os.path.join(self.allocations_path, "active", f"{allocation.id}.json")
        if os.path.exists(active_file):
            os.remove(active_file)
        
        # Save to completed directory
        completed_dir = os.path.join(self.allocations_path, "completed")
        os.makedirs(completed_dir, exist_ok=True)
        file_path = os.path.join(completed_dir, f"{allocation.id}.json")
        try:
            with open(file_path, 'w') as f:
                json.dump(allocation.to_dict(), f, indent=2)
        except Exception as e:
            logger.error(f"Error saving completed allocation {allocation.id}: {e}")
    
    async def delete_resource_pool(self, pool_id: str) -> bool:
        """Delete a resource pool."""
        if pool_id not in self.resource_pools:
            return False
        
        # Check if pool is in use by any plan
        for plan in self.allocation_plans.values():
            if plan.pool_id == pool_id:
                logger.error(f"Cannot delete pool {pool_id}, it is in use by plan {plan.id}")
                return False
        
        # Delete pool
        del self.resource_pools[pool_id]
        
        # Delete file
        file_path = os.path.join(self.pools_path, f"{pool_id}.json")
        if os.path.exists(file_path):
            os.remove(file_path)
        
        return True
    
    async def delete_allocation_plan(self, plan_id: str) -> bool:
        """Delete an allocation plan."""
        if plan_id not in self.allocation_plans:
            return False
        
        plan = self.allocation_plans[plan_id]
        
        # Check if any allocations are active
        for allocation_id in plan.allocations:
            if allocation_id in self.active_allocations:
                logger.error(f"Cannot delete plan {plan_id}, allocation {allocation_id} is active")
                return False
        
        # Delete plan
        del self.allocation_plans[plan_id]
        
        # Delete file
        file_path = os.path.join(self.plans_path, f"{plan_id}.json")
        if os.path.exists(file_path):
            os.remove(file_path)
        
        return True 