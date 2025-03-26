from typing import List, Dict, Optional, Set, Tuple, Any
from enum import Enum
from dataclasses import dataclass
import uuid
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class TaskStatus(Enum):
    PENDING = "pending"
    READY = "ready"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"

class TaskPriority(Enum):
    CRITICAL = 100
    HIGH = 75
    MEDIUM = 50
    LOW = 25
    BACKGROUND = 10

class DependencyType(Enum):
    REQUIRED = "hard"
    OPTIONAL = "soft"

@dataclass
class TaskDependency:
    task_id: str
    type: DependencyType = DependencyType.REQUIRED
    condition: str = ""  # Optional condition expression

@dataclass
class Task:
    id: str
    name: str
    description: str
    priority: TaskPriority
    status: TaskStatus
    dependencies: List[TaskDependency]
    estimated_duration: float  # in minutes
    estimated_resources: Dict[str, float]  # resource_type -> amount
    context_requirements: List[str]
    created_at: datetime
    updated_at: datetime
    tags: List[str]
    metadata: Dict[str, Any]

class TaskSelector:
    """
    Responsible for selecting and prioritizing tasks based on context,
    dependencies, and available resources.
    """
    
    def __init__(self, context_manager=None, resource_manager=None):
        self.tasks = {}  # id -> Task
        self.dependency_graph = {}  # id -> Set[dependent_task_ids]
        self.reverse_dependency_graph = {}  # id -> Set[dependency_task_ids]
        self.context_manager = context_manager
        self.resource_manager = resource_manager
        self.selection_strategies = {
            "priority_first": self._select_by_priority,
            "shortest_first": self._select_by_duration,
            "resource_optimal": self._select_by_resource_optimization,
            "dependency_chain": self._select_by_dependency_chain,
            "context_efficiency": self._select_by_context_efficiency
        }
        self.current_strategy = "priority_first"
    
    def register_task(self, task: Task) -> str:
        """Register a new task in the system."""
        logger.info(f"Registering task: {task.id} - {task.name}")
        self.tasks[task.id] = task
        self.dependency_graph[task.id] = set()
        self.reverse_dependency_graph[task.id] = {dep.task_id for dep in task.dependencies}
        
        # Update dependency graph
        for dep in task.dependencies:
            if dep.task_id in self.dependency_graph:
                self.dependency_graph[dep.task_id].add(task.id)
            else:
                self.dependency_graph[dep.task_id] = {task.id}
        
        # Check if task is ready or blocked
        if not task.dependencies:
            task.status = TaskStatus.READY
            logger.debug(f"Task {task.id} is ready for execution (no dependencies)")
        else:
            blocked = False
            for dep in task.dependencies:
                if dep.task_id in self.tasks:
                    if self.tasks[dep.task_id].status != TaskStatus.COMPLETED:
                        blocked = True
                        break
                else:
                    blocked = True
                    break
            task.status = TaskStatus.BLOCKED if blocked else TaskStatus.READY
            logger.debug(f"Task {task.id} is {'blocked' if blocked else 'ready for execution'}")
        
        return task.id
    
    def update_task_status(self, task_id: str, status: TaskStatus) -> None:
        """Update the status of a task and propagate changes to dependent tasks."""
        if task_id not in self.tasks:
            raise ValueError(f"Task with ID {task_id} not found")
        
        old_status = self.tasks[task_id].status
        self.tasks[task_id].status = status
        self.tasks[task_id].updated_at = datetime.now()
        
        logger.info(f"Updated task {task_id} status: {old_status.value} -> {status.value}")
        
        # If task was completed, check if any dependent tasks can be unblocked
        if status == TaskStatus.COMPLETED and old_status != TaskStatus.COMPLETED:
            self.update_dependent_tasks(task_id)
    
    def update_dependent_tasks(self, task_id: str) -> None:
        """Update the status of tasks that depend on the completed task."""
        completed_task = self.get_task_by_id(task_id)
        if not completed_task or completed_task.status != TaskStatus.COMPLETED:
            return

        # Find all tasks that depend on the completed task
        for task in self.tasks.values():
            if any(dep.task_id == task_id for dep in task.dependencies):
                # Check if all dependencies are completed
                all_deps_completed = all(
                    self.get_task_by_id(dep.task_id).status == TaskStatus.COMPLETED
                    for dep in task.dependencies
                )
                if all_deps_completed and task.status == TaskStatus.BLOCKED:
                    task.status = TaskStatus.READY
                    self.update_task_status(task.id, TaskStatus.READY)
    
    def select_next_task(self, available_resources: Dict[str, float] = None) -> Optional[Task]:
        """Select the next task to execute based on the current selection strategy."""
        ready_tasks = [task for task in self.tasks.values() if task.status == TaskStatus.READY]
        if not ready_tasks:
            logger.info("No ready tasks available for selection")
            return None
        
        # Apply current selection strategy
        selected_task = self.selection_strategies[self.current_strategy](ready_tasks, available_resources)
        if selected_task:
            logger.info(f"Selected task {selected_task.id} using strategy '{self.current_strategy}'")
        return selected_task
    
    def set_selection_strategy(self, strategy_name: str) -> None:
        """Set the task selection strategy."""
        if strategy_name not in self.selection_strategies:
            raise ValueError(f"Unknown selection strategy: {strategy_name}")
        logger.info(f"Setting task selection strategy to: {strategy_name}")
        self.current_strategy = strategy_name
    
    def _select_by_priority(self, tasks: List[Task], available_resources: Dict[str, float] = None) -> Optional[Task]:
        """Select task with highest priority."""
        if not tasks:
            return None
        return max(tasks, key=lambda t: t.priority.value)
    
    def _select_by_duration(self, tasks: List[Task], available_resources: Dict[str, float] = None) -> Optional[Task]:
        """Select task with shortest estimated duration."""
        if not tasks:
            return None
        return min(tasks, key=lambda t: t.estimated_duration)
    
    def _select_by_resource_optimization(self, tasks: List[Task], available_resources: Dict[str, float]) -> Optional[Task]:
        """Select task that makes optimal use of available resources."""
        if not tasks or not available_resources:
            return self._select_by_priority(tasks)
        
        # Find tasks that can be executed with available resources
        executable_tasks = []
        for task in tasks:
            can_execute = True
            for resource_type, amount in task.estimated_resources.items():
                if resource_type in available_resources:
                    if available_resources[resource_type] < amount:
                        can_execute = False
                        break
                else:
                    can_execute = False
                    break
            
            if can_execute:
                executable_tasks.append(task)
        
        if not executable_tasks:
            logger.debug("No tasks can be executed with available resources")
            return None
        
        # Select task with highest resource utilization efficiency
        return max(executable_tasks, key=lambda t: self._calculate_resource_efficiency(t, available_resources))
    
    def _calculate_resource_efficiency(self, task: Task, available_resources: Dict[str, float]) -> float:
        """Calculate resource utilization efficiency for a task."""
        total_efficiency = 0
        for resource_type, amount in task.estimated_resources.items():
            if resource_type in available_resources and available_resources[resource_type] > 0:
                efficiency = amount / available_resources[resource_type]
                total_efficiency += efficiency
        
        return total_efficiency * task.priority.value
    
    def _select_by_dependency_chain(self, tasks: List[Task], available_resources: Dict[str, float] = None) -> Optional[Task]:
        """Select task that unblocks the longest dependency chain."""
        if not tasks:
            return None
        
        # Calculate the depth of dependency chains for each task
        chain_depths = {}
        for task in tasks:
            chain_depths[task.id] = self._calculate_dependency_chain_depth(task.id)
        
        return max(tasks, key=lambda t: chain_depths[t.id])
    
    def _calculate_dependency_chain_depth(self, task_id: str) -> int:
        """Calculate the depth of the dependency chain starting from a task."""
        if task_id not in self.dependency_graph or not self.dependency_graph[task_id]:
            return 0
        
        max_depth = 0
        for dependent_id in self.dependency_graph[task_id]:
            depth = 1 + self._calculate_dependency_chain_depth(dependent_id)
            max_depth = max(max_depth, depth)
        
        return max_depth
    
    def _select_by_context_efficiency(self, tasks: List[Task], available_resources: Dict[str, float] = None) -> Optional[Task]:
        """Select task that maximizes context reuse efficiency."""
        if not tasks:
            return None
        
        if not self.context_manager:
            logger.warning("Context manager not available for context efficiency selection")
            return self._select_by_priority(tasks)
        
        current_context = self.context_manager.get_current_context()
        
        # Calculate context match score for each task
        context_scores = {}
        for task in tasks:
            context_scores[task.id] = self._calculate_context_match(task, current_context)
        
        # Return task with highest context match score, weighted by priority
        return max(tasks, key=lambda t: context_scores[t.id] * t.priority.value)
    
    def _calculate_context_match(self, task: Task, current_context: Dict[str, Any]) -> float:
        """Calculate how well a task matches the current execution context."""
        if not task.context_requirements or not current_context:
            return 0
        
        # Count how many context requirements are already satisfied
        matches = 0
        for req in task.context_requirements:
            if req in current_context:
                matches += 1
        
        return matches / len(task.context_requirements) if task.context_requirements else 0
    
    def get_task(self, task_id: str) -> Task:
        """
        Retrieve a task by its ID.
        
        Args:
            task_id: The ID of the task to retrieve
            
        Returns:
            The task object
            
        Raises:
            ValueError: If the task with the given ID is not found
        """
        if task_id not in self.tasks:
            raise ValueError(f"Task with ID {task_id} not found")
        return self.tasks[task_id]
    
    def get_task_by_id(self, task_id: str) -> Optional[Task]:
        """Get a task by its ID or None if not found."""
        return self.tasks.get(task_id)
    
    def get_tasks_by_status(self, status: TaskStatus) -> List[Task]:
        """Get all tasks with a specific status."""
        return [task for task in self.tasks.values() if task.status == status]
    
    def get_blocked_task_reasons(self, task_id: str) -> List[str]:
        """Get the reasons why a task is blocked."""
        if task_id not in self.tasks:
            raise ValueError(f"Task with ID {task_id} not found")
        
        task = self.tasks[task_id]
        if task.status != TaskStatus.BLOCKED:
            return []
        
        reasons = []
        for dep in task.dependencies:
            if dep.task_id in self.tasks:
                if self.tasks[dep.task_id].status != TaskStatus.COMPLETED:
                    reasons.append(f"Dependency '{self.tasks[dep.task_id].name}' is not completed")
            else:
                reasons.append(f"Dependency with ID {dep.task_id} not found")
        
        return reasons 