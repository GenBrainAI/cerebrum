"""
Implementation Planner for the Self-Aware Cerebrum.

This module provides capabilities for planning software implementation,
including task breakdown, effort estimation, and implementation sequencing.
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
import heapq

from src.server.planning.solution_design import SolutionDesign, ComponentSpec, SolutionDesignSystem
from src.server.planning.goal_decomposition import ResourceEstimate

logger = logging.getLogger(__name__)

class TaskType(Enum):
    """Types of implementation tasks."""
    SETUP = auto()
    CORE_IMPLEMENTATION = auto()
    INTERFACE_IMPLEMENTATION = auto()
    TESTING = auto()
    DOCUMENTATION = auto()
    INTEGRATION = auto()
    REFACTORING = auto()

@dataclass
class ImplementationTask:
    """A specific implementation task."""
    id: str
    title: str
    description: str
    task_type: TaskType
    component_id: str
    estimated_hours: float
    estimated_complexity: int  # 1-10 scale
    dependencies: List[str] = field(default_factory=list)
    priority: int = 5  # 1-10 scale
    status: str = "pending"
    acceptance_criteria: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "task_type": self.task_type.name,
            "component_id": self.component_id,
            "estimated_hours": self.estimated_hours,
            "estimated_complexity": self.estimated_complexity,
            "dependencies": self.dependencies,
            "priority": self.priority,
            "status": self.status,
            "acceptance_criteria": self.acceptance_criteria,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ImplementationTask':
        """Create task from dictionary."""
        return cls(
            id=data["id"],
            title=data["title"],
            description=data["description"],
            task_type=TaskType[data["task_type"]],
            component_id=data["component_id"],
            estimated_hours=data["estimated_hours"],
            estimated_complexity=data["estimated_complexity"],
            dependencies=data.get("dependencies", []),
            priority=data.get("priority", 5),
            status=data.get("status", "pending"),
            acceptance_criteria=data.get("acceptance_criteria", []),
            metadata=data.get("metadata", {})
        )
    
@dataclass
class ImplementationPlan:
    """Complete plan for implementing a solution."""
    id: str
    name: str
    description: str
    solution_design_id: str
    tasks: Dict[str, ImplementationTask]
    critical_path: List[str]
    execution_sequence: List[str]
    total_estimated_hours: float
    creation_time: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "solution_design_id": self.solution_design_id,
            "tasks": {k: v.to_dict() for k, v in self.tasks.items()},
            "critical_path": list(self.critical_path) if self.critical_path else [],
            "execution_sequence": list(self.execution_sequence) if self.execution_sequence else [],
            "total_estimated_hours": self.total_estimated_hours,
            "creation_time": self.creation_time,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ImplementationPlan':
        """Create plan from dictionary."""
        tasks = {
            k: ImplementationTask.from_dict(v) for k, v in data["tasks"].items()
        }
        
        return cls(
            id=data["id"],
            name=data["name"],
            description=data["description"],
            solution_design_id=data["solution_design_id"],
            tasks=tasks,
            critical_path=data["critical_path"],
            execution_sequence=data["execution_sequence"],
            total_estimated_hours=data["total_estimated_hours"],
            creation_time=data["creation_time"],
            metadata=data.get("metadata", {})
        )

class ImplementationPlanner:
    """Plans software implementation based on solution designs."""
    
    def __init__(
        self, 
        solution_design_system: Optional[SolutionDesignSystem] = None,
        storage_path: Optional[str] = None
    ):
        """
        Initialize the Implementation Planner.
        
        Args:
            solution_design_system: Solution Design System for retrieving designs
            storage_path: Path to store implementation plans
        """
        self.solution_design_system = solution_design_system
        self.storage_path = storage_path or os.path.join(os.path.expanduser("~"), ".cerebrum", "implementation_plans")
        os.makedirs(self.storage_path, exist_ok=True)
        self.plans: Dict[str, ImplementationPlan] = {}
        self._load_existing_plans()
    
    async def create_implementation_plan(
        self,
        name: str,
        description: str,
        solution_design_id: str,
        context: Optional[Dict[str, Any]] = None
    ) -> ImplementationPlan:
        """
        Create an implementation plan based on a solution design.
        
        Args:
            name: Name of the implementation plan
            description: Description of the plan
            solution_design_id: ID of the solution design to implement
            context: Additional context information
            
        Returns:
            A complete implementation plan
        """
        # Get the solution design
        if not self.solution_design_system:
            raise ValueError("Solution Design System is required to create an implementation plan")
        
        solution_design = await self.solution_design_system.get_solution_design(solution_design_id)
        if not solution_design:
            raise ValueError(f"Solution design not found: {solution_design_id}")
        
        # Break down components into tasks
        tasks = await self.breakdown_components_to_tasks(solution_design, context)
        
        # Estimate task effort
        effort_estimates = await self.estimate_task_effort(tasks, context)
        for task_id, hours in effort_estimates.items():
            if task_id in tasks:
                tasks[task_id].estimated_hours = hours
        
        # Calculate total estimated hours
        total_hours = sum(task.estimated_hours for task in tasks.values())
        
        # Determine critical path
        critical_path = await self.determine_critical_path(tasks)
        
        # Generate execution sequence
        execution_sequence = await self.generate_execution_sequence(tasks, critical_path, context=context)
        
        # Create plan
        plan_id = str(uuid.uuid4())
        creation_time = datetime.now().isoformat()
        
        implementation_plan = ImplementationPlan(
            id=plan_id,
            name=name,
            description=description,
            solution_design_id=solution_design_id,
            tasks=tasks,
            critical_path=critical_path,
            execution_sequence=execution_sequence,
            total_estimated_hours=total_hours,
            creation_time=creation_time,
            metadata={
                "context": context or {}
            }
        )
        
        # Save plan
        self.plans[plan_id] = implementation_plan
        self._save_plan(implementation_plan)
        
        return implementation_plan
    
    async def breakdown_components_to_tasks(
        self,
        solution_design: SolutionDesign,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, ImplementationTask]:
        """
        Break down components into implementation tasks.
        
        Returns:
            Dictionary of implementation tasks
        """
        tasks: Dict[str, ImplementationTask] = {}
        component_tasks: Dict[str, List[str]] = {}
        
        # First, create setup tasks
        setup_tasks = await self._create_setup_tasks(solution_design)
        for task_id, task in setup_tasks.items():
            tasks[task_id] = task
        
        # For each component, create implementation tasks
        for component_id, component in solution_design.components.items():
            component_tasks[component_id] = []
            
            # Create core implementation task
            core_task_id = str(uuid.uuid4())
            core_task = ImplementationTask(
                id=core_task_id,
                title=f"Implement {component.name} Core",
                description=f"Implement core functionality for {component.name}",
                task_type=TaskType.CORE_IMPLEMENTATION,
                component_id=component_id,
                estimated_hours=0.0,  # To be estimated later
                estimated_complexity=component.estimated_complexity,
                dependencies=setup_tasks.keys(),  # Depends on setup tasks
                priority=8,  # High priority for core tasks
                status="pending",
                acceptance_criteria=[
                    f"All core functionality for {component.name} is implemented",
                    "Unit tests pass",
                    "Code follows project standards"
                ],
                metadata=dict()
            )
            tasks[core_task_id] = core_task
            component_tasks[component_id].append(core_task_id)
            
            # Create interface implementation tasks for each interface
            for interface_info in component.interfaces:
                interface_task_id = str(uuid.uuid4())
                interface_task = ImplementationTask(
                    id=interface_task_id,
                    title=f"Implement {component.name} Interface",
                    description=f"Implement the interface for {component.name}",
                    task_type=TaskType.INTERFACE_IMPLEMENTATION,
                    component_id=component_id,
                    estimated_hours=0.0,  # To be estimated later
                    estimated_complexity=max(3, component.estimated_complexity - 2),
                    dependencies=[core_task_id],  # Depends on core implementation
                    priority=7,
                    status="pending",
                    acceptance_criteria=[
                        f"Interface for {component.name} is implemented",
                        "Interface tests pass",
                        "Documentation is complete"
                    ],
                    metadata=dict()
                )
                tasks[interface_task_id] = interface_task
                component_tasks[component_id].append(interface_task_id)
            
            # Create testing task
            testing_task_id = str(uuid.uuid4())
            testing_task = ImplementationTask(
                id=testing_task_id,
                title=f"Test {component.name}",
                description=f"Create and run tests for {component.name}",
                task_type=TaskType.TESTING,
                component_id=component_id,
                estimated_hours=0.0,  # To be estimated later
                estimated_complexity=component.estimated_complexity,
                dependencies=component_tasks[component_id],  # Depends on all component tasks
                priority=6,
                status="pending",
                acceptance_criteria=[
                    f"Unit tests for {component.name} are implemented",
                    "Integration tests are implemented",
                    "Test coverage meets project standards"
                ],
                metadata=dict()
            )
            tasks[testing_task_id] = testing_task
            component_tasks[component_id].append(testing_task_id)
            
            # Create documentation task
            doc_task_id = str(uuid.uuid4())
            doc_task = ImplementationTask(
                id=doc_task_id,
                title=f"Document {component.name}",
                description=f"Create documentation for {component.name}",
                task_type=TaskType.DOCUMENTATION,
                component_id=component_id,
                estimated_hours=0.0,  # To be estimated later
                estimated_complexity=max(2, component.estimated_complexity - 3),
                dependencies=[core_task_id],  # Depends on core implementation
                priority=5,
                status="pending",
                acceptance_criteria=[
                    f"API documentation for {component.name} is complete",
                    "Usage examples are provided",
                    "Documentation follows project standards"
                ],
                metadata=dict()
            )
            tasks[doc_task_id] = doc_task
            component_tasks[component_id].append(doc_task_id)
        
        # Create integration tasks
        integration_tasks = await self._create_integration_tasks(solution_design, component_tasks)
        for task_id, task in integration_tasks.items():
            tasks[task_id] = task
        
        return tasks
    
    async def _create_setup_tasks(self, solution_design: SolutionDesign) -> Dict[str, ImplementationTask]:
        """Create setup tasks for the implementation."""
        setup_tasks: Dict[str, ImplementationTask] = {}
        
        # Project structure setup
        struct_task_id = str(uuid.uuid4())
        setup_tasks[struct_task_id] = ImplementationTask(
            id=struct_task_id,
            title="Setup Project Structure",
            description="Create initial project structure and configuration files",
            task_type=TaskType.SETUP,
            component_id="",  # No specific component
            estimated_hours=4.0,
            estimated_complexity=3,
            dependencies=[],
            priority=10,  # Highest priority
            status="pending",
            acceptance_criteria=[
                "Project directory structure is created",
                "Configuration files are in place",
                "Build system is configured"
            ],
            metadata=dict()
        )
        
        # Dependencies setup
        deps_task_id = str(uuid.uuid4())
        setup_tasks[deps_task_id] = ImplementationTask(
            id=deps_task_id,
            title="Setup Dependencies",
            description="Configure project dependencies and external libraries",
            task_type=TaskType.SETUP,
            component_id="",  # No specific component
            estimated_hours=3.0,
            estimated_complexity=3,
            dependencies=[struct_task_id],
            priority=9,
            status="pending",
            acceptance_criteria=[
                "All dependencies are specified in configuration files",
                "Dependency resolution works",
                "External libraries are properly configured"
            ],
            metadata=dict()
        )
        
        # CI/CD setup
        ci_task_id = str(uuid.uuid4())
        setup_tasks[ci_task_id] = ImplementationTask(
            id=ci_task_id,
            title="Setup CI/CD",
            description="Configure continuous integration and deployment",
            task_type=TaskType.SETUP,
            component_id="",  # No specific component
            estimated_hours=4.0,
            estimated_complexity=4,
            dependencies=[struct_task_id],
            priority=8,
            status="pending",
            acceptance_criteria=[
                "CI/CD pipeline is configured",
                "Automated tests run in CI",
                "Deployment process is defined"
            ],
            metadata=dict()
        )
        
        return setup_tasks
    
    async def _create_integration_tasks(
        self, 
        solution_design: SolutionDesign,
        component_tasks: Dict[str, List[str]]
    ) -> Dict[str, ImplementationTask]:
        """Create integration tasks between components."""
        integration_tasks: Dict[str, ImplementationTask] = {}
        
        # Get all component implementation task IDs
        all_component_implementation_tasks = []
        for tasks in component_tasks.values():
            all_component_implementation_tasks.extend(tasks)
        
        # Create main integration task
        integration_task_id = str(uuid.uuid4())
        integration_tasks[integration_task_id] = ImplementationTask(
            id=integration_task_id,
            title="Integrate Components",
            description="Integrate all components into a cohesive system",
            task_type=TaskType.INTEGRATION,
            component_id="",  # No specific component
            estimated_hours=0.0,  # To be estimated later
            estimated_complexity=7,
            dependencies=all_component_implementation_tasks,
            priority=7,
            status="pending",
            acceptance_criteria=[
                "All components are properly integrated",
                "System functions as a whole",
                "Integration tests pass"
            ],
            metadata=dict()
        )
        
        # Create system testing task
        system_test_task_id = str(uuid.uuid4())
        integration_tasks[system_test_task_id] = ImplementationTask(
            id=system_test_task_id,
            title="System Testing",
            description="Perform system-level testing",
            task_type=TaskType.TESTING,
            component_id="",  # No specific component
            estimated_hours=0.0,  # To be estimated later
            estimated_complexity=6,
            dependencies=[integration_task_id],
            priority=6,
            status="pending",
            acceptance_criteria=[
                "System tests are implemented",
                "System tests pass",
                "Edge cases are covered"
            ],
            metadata=dict()
        )
        
        # Create deployment task
        deployment_task_id = str(uuid.uuid4())
        integration_tasks[deployment_task_id] = ImplementationTask(
            id=deployment_task_id,
            title="Deployment Preparation",
            description="Prepare for system deployment",
            task_type=TaskType.INTEGRATION,
            component_id="",  # No specific component
            estimated_hours=0.0,  # To be estimated later
            estimated_complexity=5,
            dependencies=[system_test_task_id],
            priority=5,
            status="pending",
            acceptance_criteria=[
                "Deployment process is documented",
                "Deployment artifacts are created",
                "Deployment verification plan is in place"
            ],
            metadata=dict()
        )
        
        return integration_tasks
    
    async def estimate_task_effort(
        self,
        tasks: Dict[str, ImplementationTask],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, float]:
        """
        Estimate effort for implementation tasks.
        
        Returns:
            Dictionary mapping task IDs to estimated hours
        """
        effort_estimates: Dict[str, float] = {}
        
        # Base effort multipliers by task type
        type_multipliers = {
            TaskType.SETUP: 1.0,
            TaskType.CORE_IMPLEMENTATION: 3.0,
            TaskType.INTERFACE_IMPLEMENTATION: 1.5,
            TaskType.TESTING: 2.0,
            TaskType.DOCUMENTATION: 1.0,
            TaskType.INTEGRATION: 2.5,
            TaskType.REFACTORING: 2.0
        }
        
        # Complexity multipliers
        complexity_multipliers = {
            1: 0.5,
            2: 0.7,
            3: 0.9,
            4: 1.0,
            5: 1.2,
            6: 1.5,
            7: 1.8,
            8: 2.2,
            9: 2.7,
            10: 3.5
        }
        
        # Calculate estimates based on task type and complexity
        for task_id, task in tasks.items():
            # Base estimate by task type
            base_hours = type_multipliers.get(task.task_type, 1.0) * 4.0  # 4 hours is the baseline
            
            # Apply complexity multiplier
            complexity_factor = complexity_multipliers.get(task.estimated_complexity, 1.0)
            
            # Calculate final estimate
            estimated_hours = base_hours * complexity_factor
            
            # Round to nearest half-hour
            estimated_hours = round(estimated_hours * 2) / 2
            
            # Store estimate
            effort_estimates[task_id] = estimated_hours
        
        return effort_estimates
    
    async def determine_critical_path(
        self,
        tasks: Dict[str, ImplementationTask]
    ) -> List[str]:
        """
        Determine the critical path of tasks.
        
        Returns:
            List of task IDs in the critical path
        """
        # Build directed graph
        graph: Dict[str, List[Tuple[str, float]]] = {}
        for task_id, task in tasks.items():
            if task_id not in graph:
                graph[task_id] = []
            
            # Add edges from this task to its dependents
            for dependent_id, dependent in tasks.items():
                if task_id in dependent.dependencies:
                    graph[task_id].append((dependent_id, dependent.estimated_hours))
        
        # Find nodes with no dependencies (start nodes)
        start_nodes = []
        for task_id, task in tasks.items():
            if not task.dependencies:
                start_nodes.append(task_id)
        
        if not start_nodes:
            logger.warning("No start tasks found, using first task as start")
            start_nodes = [next(iter(tasks.keys()))]
        
        # Find nodes with no dependents (end nodes)
        end_nodes = []
        has_dependents = set()
        for edges in graph.values():
            for dependent_id, _ in edges:
                has_dependents.add(dependent_id)
        
        for task_id in tasks:
            if task_id not in has_dependents:
                end_nodes.append(task_id)
        
        if not end_nodes:
            logger.warning("No end tasks found, using last task as end")
            end_nodes = [next(reversed(tasks.keys()))]
        
        # Find longest path from each start node to each end node
        critical_path = []
        max_length = 0.0
        
        for start in start_nodes:
            for end in end_nodes:
                path, length = self._find_longest_path(graph, start, end, tasks)
                if length > max_length:
                    max_length = length
                    critical_path = path
        
        return critical_path
    
    def _find_longest_path(
        self, 
        graph: Dict[str, List[Tuple[str, float]]],
        start: str,
        end: str,
        tasks: Dict[str, ImplementationTask]
    ) -> Tuple[List[str], float]:
        """Find longest path from start to end using dynamic programming."""
        # Initialize distance and predecessor arrays
        distance: Dict[str, float] = {node: float('-inf') for node in graph}
        predecessor: Dict[str, Optional[str]] = {node: None for node in graph}
        
        # Set start node distance to its own duration
        distance[start] = tasks[start].estimated_hours
        
        # Topologically sort nodes
        sorted_nodes = self._topological_sort(graph, list(tasks.keys()))
        
        # Compute longest paths
        for node in sorted_nodes:
            if node in graph:
                for neighbor, weight in graph[node]:
                    if distance[node] + weight > distance[neighbor]:
                        distance[neighbor] = distance[node] + weight
                        predecessor[neighbor] = node
        
        # Reconstruct path
        path = []
        current = end
        while current is not None:
            path.append(current)
            current = predecessor[current]
        
        path.reverse()
        
        # If start is not in path, path doesn't exist
        if start not in path:
            return [], 0.0
        
        return path, distance[end]
    
    def _topological_sort(
        self, 
        graph: Dict[str, List[Tuple[str, float]]],
        nodes: List[str]
    ) -> List[str]:
        """Perform topological sort on the graph."""
        # Build indegree map
        indegree: Dict[str, int] = {node: 0 for node in nodes}
        for node in graph:
            for neighbor, _ in graph[node]:
                indegree[neighbor] = indegree.get(neighbor, 0) + 1
        
        # Start with nodes that have no incoming edges
        queue = [node for node in nodes if indegree[node] == 0]
        sorted_nodes = []
        
        while queue:
            node = queue.pop(0)
            sorted_nodes.append(node)
            
            if node in graph:
                for neighbor, _ in graph[node]:
                    indegree[neighbor] -= 1
                    if indegree[neighbor] == 0:
                        queue.append(neighbor)
        
        # If not all nodes are sorted, there's a cycle
        if len(sorted_nodes) != len(nodes):
            logger.warning("Cycle detected in task dependencies, sorting may be incorrect")
        
        return sorted_nodes
    
    async def generate_execution_sequence(
        self,
        tasks: Dict[str, ImplementationTask],
        critical_path: List[str],
        max_parallel_tasks: int = 3,
        context: Optional[Dict[str, Any]] = None
    ) -> List[str]:
        """
        Generate an optimal execution sequence for tasks.
        
        Returns:
            List of task IDs in execution order
        """
        # Critical path tasks should be prioritized
        critical_path_set = set(critical_path)
        
        # Create priority queue based on earliest start time and priority
        task_queue = []
        visited = set()
        ready_tasks = []
        
        # Find tasks with no dependencies
        for task_id, task in tasks.items():
            if not task.dependencies:
                # Priority factors: critical path (high), priority (high), complexity (low)
                priority_factor = (
                    10 if task_id in critical_path_set else 0,
                    task.priority,
                    -task.estimated_complexity
                )
                heapq.heappush(task_queue, (-priority_factor[0], -priority_factor[1], priority_factor[2], task_id))
        
        execution_sequence = []
        in_progress = set()
        time = 0.0
        
        while task_queue or in_progress:
            # Complete tasks that are done at this time
            new_in_progress = set()
            completed_tasks = []
            
            for task_id in in_progress:
                task = tasks[task_id]
                if time >= task.estimated_hours:
                    completed_tasks.append(task_id)
                    execution_sequence.append(task_id)
                    visited.add(task_id)
                else:
                    new_in_progress.add(task_id)
            
            in_progress = new_in_progress
            
            # Add newly available tasks to the queue
            for completed_task_id in completed_tasks:
                for task_id, task in tasks.items():
                    if task_id not in visited and task_id not in in_progress:
                        if all(dep in visited for dep in task.dependencies):
                            # Priority factors: critical path (high), priority (high), complexity (low)
                            priority_factor = (
                                10 if task_id in critical_path_set else 0,
                                task.priority,
                                -task.estimated_complexity
                            )
                            heapq.heappush(task_queue, (-priority_factor[0], -priority_factor[1], priority_factor[2], task_id))
            
            # Start new tasks if we have capacity
            while len(in_progress) < max_parallel_tasks and task_queue:
                _, _, _, task_id = heapq.heappop(task_queue)
                # Check if all dependencies are met
                task = tasks[task_id]
                if all(dep in visited for dep in task.dependencies):
                    in_progress.add(task_id)
                else:
                    # Put it back in the queue for later
                    priority_factor = (
                        10 if task_id in critical_path_set else 0,
                        task.priority,
                        -task.estimated_complexity
                    )
                    heapq.heappush(task_queue, (-priority_factor[0], -priority_factor[1], priority_factor[2], task_id))
            
            # Advance time to the next event
            if in_progress:
                # Find the task that will complete next
                next_completion = min(time + tasks[task_id].estimated_hours for task_id in in_progress)
                time = next_completion
            elif task_queue:
                # If no tasks in progress but tasks in queue, dependencies are not met
                # This is a safety check to prevent infinite loops
                logger.warning("Task dependencies cannot be satisfied, breaking execution sequence generation")
                break
        
        return execution_sequence
    
    async def get_implementation_plan(self, plan_id: str) -> Optional[ImplementationPlan]:
        """Get an implementation plan by ID."""
        return self.plans.get(plan_id)
    
    async def get_all_implementation_plans(self) -> Dict[str, ImplementationPlan]:
        """Get all implementation plans."""
        return self.plans
    
    async def delete_implementation_plan(self, plan_id: str) -> bool:
        """Delete an implementation plan."""
        if plan_id in self.plans:
            del self.plans[plan_id]
            
            # Delete the file
            plan_path = os.path.join(self.storage_path, f"{plan_id}.json")
            if os.path.exists(plan_path):
                os.remove(plan_path)
            
            return True
        
        return False
    
    def _load_existing_plans(self) -> None:
        """Load existing plans from storage."""
        if not os.path.exists(self.storage_path):
            return
        
        for filename in os.listdir(self.storage_path):
            if filename.endswith('.json'):
                file_path = os.path.join(self.storage_path, filename)
                try:
                    with open(file_path, 'r') as f:
                        plan_data = json.load(f)
                        plan = ImplementationPlan.from_dict(plan_data)
                        self.plans[plan.id] = plan
                        logger.info(f"Loaded implementation plan: {plan.name} ({plan.id})")
                except Exception as e:
                    logger.error(f"Error loading implementation plan {filename}: {e}")
    
    def _save_plan(self, plan: ImplementationPlan) -> None:
        """Save an implementation plan to storage."""
        plan_path = os.path.join(self.storage_path, f"{plan.id}.json")
        try:
            with open(plan_path, 'w') as f:
                json.dump(plan.to_dict(), f, indent=2)
            logger.info(f"Saved implementation plan: {plan.name} ({plan.id})")
        except Exception as e:
            logger.error(f"Error saving implementation plan {plan.id}: {e}") 