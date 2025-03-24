
# Implementation Guide for Phase 3 Work Units 3.1 and 3.2

## Work Unit 3.1: Task Selector

### Overview
The Task Selector is responsible for dynamically selecting and prioritizing tasks from the execution queue based on context, dependencies, and available resources. It must interface with the Planning Engine and coordinate with the Context Manager to ensure optimal task execution.

### Core Components

#### 1. TaskSelector Class

```python
from typing import List, Dict, Optional, Set, Tuple
from enum import Enum
from dataclasses import dataclass
import uuid
from datetime import datetime

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

@dataclass
class TaskDependency:
    task_id: str
    type: str  # "hard" or "soft"
    condition: str  # Optional condition expression

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
    metadata: Dict[str, any]

class TaskSelector:
    def __init__(self, context_manager, resource_manager):
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
        
        return task.id
    
    def update_task_status(self, task_id: str, status: TaskStatus) -> None:
        """Update the status of a task and propagate changes to dependent tasks."""
        if task_id not in self.tasks:
            raise ValueError(f"Task with ID {task_id} not found")
        
        old_status = self.tasks[task_id].status
        self.tasks[task_id].status = status
        self.tasks[task_id].updated_at = datetime.now()
        
        # If task was completed, check if any dependent tasks can be unblocked
        if status == TaskStatus.COMPLETED and old_status != TaskStatus.COMPLETED:
            self._update_dependent_tasks(task_id)
    
    def _update_dependent_tasks(self, completed_task_id: str) -> None:
        """Update tasks that depend on the completed task."""
        if completed_task_id not in self.dependency_graph:
            return
        
        for dependent_id in self.dependency_graph[completed_task_id]:
            dependent_task = self.tasks[dependent_id]
            if dependent_task.status == TaskStatus.BLOCKED:
                # Check if all dependencies are now satisfied
                all_deps_satisfied = True
                for dep in dependent_task.dependencies:
                    if dep.task_id in self.tasks:
                        if self.tasks[dep.task_id].status != TaskStatus.COMPLETED:
                            all_deps_satisfied = False
                            break
                    else:
                        all_deps_satisfied = False
                        break
                
                if all_deps_satisfied:
                    dependent_task.status = TaskStatus.READY
                    dependent_task.updated_at = datetime.now()
    
    def select_next_task(self, available_resources: Dict[str, float] = None) -> Optional[Task]:
        """Select the next task to execute based on the current selection strategy."""
        ready_tasks = [task for task in self.tasks.values() if task.status == TaskStatus.READY]
        if not ready_tasks:
            return None
        
        # Apply current selection strategy
        return self.selection_strategies[self.current_strategy](ready_tasks, available_resources)
    
    def set_selection_strategy(self, strategy_name: str) -> None:
        """Set the task selection strategy."""
        if strategy_name not in self.selection_strategies:
            raise ValueError(f"Unknown selection strategy: {strategy_name}")
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
        
        current_context = self.context_manager.get_current_context()
        
        # Calculate context match score for each task
        context_scores = {}
        for task in tasks:
            context_scores[task.id] = self._calculate_context_match(task, current_context)
        
        # Return task with highest context match score, weighted by priority
        return max(tasks, key=lambda t: context_scores[t.id] * t.priority.value)
    
    def _calculate_context_match(self, task: Task, current_context: Dict[str, any]) -> float:
        """Calculate how well a task matches the current execution context."""
        if not task.context_requirements or not current_context:
            return 0
        
        # Count how many context requirements are already satisfied
        matches = 0
        for req in task.context_requirements:
            if req in current_context:
                matches += 1
        
        return matches / len(task.context_requirements) if task.context_requirements else 0
    
    def get_task_by_id(self, task_id: str) -> Optional[Task]:
        """Get a task by its ID."""
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
```

#### 2. Priority Algorithm Implementation

```python
class PriorityCalculator:
    """Calculates dynamic task priorities based on multiple factors."""
    
    def __init__(self, base_weights=None):
        self.weights = base_weights or {
            "base_priority": 1.0,
            "urgency": 0.8,
            "dependency_impact": 0.7,
            "resource_availability": 0.6,
            "context_relevance": 0.5
        }
    
    def calculate_effective_priority(self, task: Task, context_manager, resource_manager) -> float:
        """Calculate effective priority based on multiple factors."""
        factors = {
            "base_priority": self._normalize_base_priority(task.priority),
            "urgency": self._calculate_urgency(task),
            "dependency_impact": self._calculate_dependency_impact(task, context_manager.task_selector),
            "resource_availability": self._calculate_resource_availability(task, resource_manager),
            "context_relevance": self._calculate_context_relevance(task, context_manager)
        }
        
        # Calculate weighted sum
        effective_priority = 0
        for factor, value in factors.items():
            effective_priority += value * self.weights[factor]
        
        return effective_priority
    
    def _normalize_base_priority(self, priority: TaskPriority) -> float:
        """Normalize base priority to 0-1 range."""
        return priority.value / 100.0
    
    def _calculate_urgency(self, task: Task) -> float:
        """Calculate urgency factor based on creation time and deadlines."""
        # Implementation depends on how urgency is defined in your system
        # This is a simplified example
        if 'deadline' in task.metadata:
            deadline = task.metadata['deadline']
            now = datetime.now()
            time_left = (deadline - now).total_seconds()
            total_time = (deadline - task.created_at).total_seconds()
            
            if time_left <= 0:
                return 1.0  # Past deadline
            
            return 1.0 - (time_left / total_time)
        
        # No deadline specified
        return 0.5
    
    def _calculate_dependency_impact(self, task: Task, task_selector) -> float:
        """Calculate how many other tasks this task is blocking."""
        if task.id not in task_selector.dependency_graph:
            return 0.0
        
        dependent_count = len(task_selector.dependency_graph[task.id])
        # Normalize to 0-1 range (assuming max 10 dependents is 100%)
        return min(1.0, dependent_count / 10.0)
    
    def _calculate_resource_availability(self, task: Task, resource_manager) -> float:
        """Calculate how well resource availability matches task needs."""
        if not task.estimated_resources:
            return 1.0  # No resources needed
        
        available_resources = resource_manager.get_available_resources()
        
        # Calculate resource match ratio
        match_ratio = 0
        resource_count = 0
        
        for resource_type, amount_needed in task.estimated_resources.items():
            resource_count += 1
            if resource_type in available_resources:
                available = available_resources[resource_type]
                if available >= amount_needed:
                    match_ratio += 1.0
                else:
                    match_ratio += available / amount_needed
        
        return match_ratio / resource_count if resource_count > 0 else 1.0
    
    def _calculate_context_relevance(self, task: Task, context_manager) -> float:
        """Calculate how relevant the task is to current execution context."""
        current_context = context_manager.get_current_context()
        
        if not task.context_requirements or not current_context:
            return 0.5  # Neutral relevance
        
        # Count matches
        matches = 0
        for req in task.context_requirements:
            if req in current_context:
                matches += 1
        
        return matches / len(task.context_requirements)
    
    def adjust_weights(self, new_weights: Dict[str, float]) -> None:
        """Adjust the weights used for priority calculation."""
        for factor, weight in new_weights.items():
            if factor in self.weights:
                self.weights[factor] = weight
```

#### 3. Dependency Resolution Implementation

```python
class DependencyResolver:
    """Resolves task dependencies and manages the dependency graph."""
    
    def __init__(self, task_selector):
        self.task_selector = task_selector
    
    def analyze_dependency_graph(self) -> Dict[str, any]:
        """Analyze the dependency graph and provide metrics."""
        if not self.task_selector.dependency_graph:
            return {"empty": True}
        
        # Calculate metrics
        metrics = {
            "total_tasks": len(self.task_selector.tasks),
            "independent_tasks": self._count_independent_tasks(),
            "terminal_tasks": self._count_terminal_tasks(),
            "max_chain_length": self._find_max_chain_length(),
            "critical_path": self._find_critical_path(),
            "bottleneck_tasks": self._find_bottleneck_tasks(),
            "circular_dependencies": self._detect_circular_dependencies()
        }
        
        return metrics
    
    def _count_independent_tasks(self) -> int:
        """Count tasks with no dependencies."""
        count = 0
        for task in self.task_selector.tasks.values():
            if not task.dependencies:
                count += 1
        return count
    
    def _count_terminal_tasks(self) -> int:
        """Count tasks that no other task depends on."""
        terminal_tasks = set()
        for task_id in self.task_selector.tasks:
            if task_id not in self.task_selector.dependency_graph or not self.task_selector.dependency_graph[task_id]:
                terminal_tasks.add(task_id)
        return len(terminal_tasks)
    
    def _find_max_chain_length(self) -> int:
        """Find the length of the longest dependency chain."""
        max_length = 0
        for task_id in self.task_selector.tasks:
            length = self._calculate_max_chain_from(task_id, set())
            max_length = max(max_length, length)
        return max_length
    
    def _calculate_max_chain_from(self, task_id: str, visited: Set[str]) -> int:
        """Calculate the maximum chain length starting from a task."""
        if task_id in visited:  # Prevent infinite recursion with circular dependencies
            return 0
        
        visited.add(task_id)
        
        if task_id not in self.task_selector.reverse_dependency_graph or not self.task_selector.reverse_dependency_graph[task_id]:
            return 1
        
        max_length = 0
        for dep_id in self.task_selector.reverse_dependency_graph[task_id]:
            length = 1 + self._calculate_max_chain_from(dep_id, visited.copy())
            max_length = max(max_length, length)
        
        return max_length
    
    def _find_critical_path(self) -> List[str]:
        """Find the critical path in the dependency graph."""
        # This is a simplified implementation; a real one would use more sophisticated algorithms
        paths = []
        start_tasks = [task_id for task_id, task in self.task_selector.tasks.items() if not task.dependencies]
        
        for start_id in start_tasks:
            self._find_paths_from(start_id, [], paths, set())
        
        if not paths:
            return []
        
        # Find the longest path
        critical_path = max(paths, key=len)
        return critical_path
    
    def _find_paths_from(self, task_id: str, current_path: List[str], all_paths: List[List[str]], visited: Set[str]) -> None:
        """Find all paths from a starting task."""
        if task_id in visited:  # Prevent infinite recursion
            return
        
        visited.add(task_id)
        current_path.append(task_id)
        
        if task_id not in self.task_selector.dependency_graph or not self.task_selector.dependency_graph[task_id]:
            # This is a terminal task
            all_paths.append(current_path.copy())
        else:
            for dependent_id in self.task_selector.dependency_graph[task_id]:
                self._find_paths_from(dependent_id, current_path.copy(), all_paths, visited.copy())
    
    def _find_bottleneck_tasks(self) -> List[str]:
        """Find tasks that many other tasks depend on."""
        bottlenecks = []
        threshold = max(3, len(self.task_selector.tasks) // 5)  # Adjust threshold based on total tasks
        
        for task_id, dependents in self.task_selector.dependency_graph.items():
            if len(dependents) >= threshold:
                bottlenecks.append(task_id)
        
        return bottlenecks
    
    def _detect_circular_dependencies(self) -> List[List[str]]:
        """Detect circular dependencies in the graph."""
        circular_deps = []
        
        for task_id in self.task_selector.tasks:
            path = []
            visited = set()
            self._find_circular_deps_from(task_id, path, visited, circular_deps)
        
        return circular_deps
    
    def _find_circular_deps_from(self, task_id: str, path: List[str], visited: Set[str], circular_deps: List[List[str]]) -> None:
        """Find circular dependencies starting from a task."""
        if task_id in path:
            # Found a cycle
            start_index = path.index(task_id)
            cycle = path[start_index:] + [task_id]
            if cycle not in circular_deps:
                circular_deps.append(cycle)
            return
        
        if task_id in visited:
            return
        
        visited.add(task_id)
        path.append(task_id)
        
        if task_id in self.task_selector.dependency_graph:
            for dependent_id in self.task_selector.dependency_graph[task_id]:
                self._find_circular_deps_from(dependent_id, path.copy(), visited, circular_deps)
    
    def resolve_dependencies(self, task_id: str) -> bool:
        """Attempt to resolve dependencies for a task."""
        if task_id not in self.task_selector.tasks:
            return False
        
        task = self.task_selector.tasks[task_id]
        
        # Check if all dependencies are satisfied
        all_satisfied = True
        for dep in task.dependencies:
            if dep.task_id in self.task_selector.tasks:
                dep_task = self.task_selector.tasks[dep.task_id]
                if dep_task.status != TaskStatus.COMPLETED:
                    all_satisfied = False
                    break
            else:
                all_satisfied = False
                break
        
        if all_satisfied and task.status == TaskStatus.BLOCKED:
            task.status = TaskStatus.READY
            task.updated_at = datetime.now()
            return True
        
        return all_satisfied
```

## Work Unit 3.2: Context Manager

### Overview
The Context Manager is responsible for managing execution context across tasks, ensuring relevant information is propagated, validated, and optimized for efficient task execution.

### Core Components

#### 1. ContextManager Class

```python
from typing import Dict, List, Set, Any, Optional
import json
import hashlib
from datetime import datetime

class ContextType(Enum):
    GLOBAL = "global"
    SESSION = "session"
    TASK = "task"
    TEMPORARY = "temporary"

@dataclass
class ContextEntry:
    key: str
    value: Any
    type: ContextType
    created_at: datetime
    updated_at: datetime
    expires_at: Optional[datetime] = None
    metadata: Dict[str, Any] = None
    
    def is_expired(self) -> bool:
        """Check if the context entry is expired."""
        if self.expires_at is None:
            return False
        return datetime.now() > self.expires_at

class ContextManager:
    def __init__(self, task_selector=None):
        self.contexts = {
            ContextType.GLOBAL: {},  # Persistent across all sessions
            ContextType.SESSION: {},  # Persistent for current session
            ContextType.TASK: {},  # Current task context
            ContextType.TEMPORARY: {}  # Short-lived context
        }
        self.context_history = []  # History of context changes
        self.validation_rules = {}  # Key -> validation function
        self.propagation_rules = {}  # Source key -> list of target keys
        self.optimization_enabled = True
        self.task_selector = task_selector
        
    def set_context(self, key: str, value: Any, context_type: ContextType = ContextType.TASK, 
                   expires_at: datetime = None, metadata: Dict[str, Any] = None) -> None:
        """Set a context value."""
        now = datetime.now()
        
        # Validate the context value if rules exist
        if key in self.validation_rules:
            if not self.validation_rules[key](value):
                raise ValueError(f"Invalid value for context key: {key}")
        
        # Create or update context entry
        if key in self.contexts[context_type]:
            entry = self.contexts[context_type][key]
            old_value = entry.value
            entry.value = value
            entry.updated_at = now
            entry.expires_at = expires_at
            if metadata:
                entry.metadata = {**(entry.metadata or {}), **metadata}
        else:
            entry = ContextEntry(
                key=key,
                value=value,
                type=context_type,
                created_at=now,
                updated_at=now,
                expires_at=expires_at,
                metadata=metadata
            )
            self.contexts[context_type][key] = entry
        
        # Record history
        self.context_history.append({
            "key": key,
            "old_value": old_value if key in self.contexts[context_type] else None,
            "new_value": value,
            "type": context_type.value,
            "timestamp": now.isoformat()
        })
        
        # Apply propagation rules
        if key in self.propagation_rules:
            for target_key, transform_func in self.propagation_rules[key]:
                transformed_value = transform_func(value)
                target_type = ContextType.TASK  # Default to task context for propagated values
                self.set_context(target_key, transformed_value, target_type)
    
    def get_context(self, key: str, default: Any = None) -> Any:
        """Get a context value, checking all context types in order of specificity."""
        # Order of precedence: Task, Session, Global, Temporary
        for context_type in [ContextType.TASK, ContextType.SESSION, ContextType.GLOBAL, ContextType.TEMPORARY]:
            if key in self.contexts[context_type]:
                entry = self.contexts[context_type][key]
                if not entry.is_expired():
                    return entry.value
        
        return default
    
    def get_typed_context(self, key: str, context_type: ContextType, default: Any = None) -> Any:
        """Get a context value from a specific context type."""
        if key in self.contexts[context_type]:
            entry = self.contexts[context_type][key]
            if not entry.is_expired():
                return entry.value
        
        return default
    
    def delete_context(self, key: str, context_type: Optional[ContextType] = None) -> bool:
        """Delete a context entry."""
        if context_type is not None:
            if key in self.contexts[context_type]:
                del self.contexts[context_type][key]
                return True
            return False
        
        # Delete from all context types if type not specified
        deleted = False
        for context_type in self.contexts:
            if key in self.contexts[context_type]:
                del self.contexts[context_type][key]
                deleted = True
        
        return deleted
    
    def clear_context(self, context_type: ContextType) -> None:
        """Clear all entries for a specific context type."""
        self.contexts[context_type] = {}
    
    def get_current_context(self) -> Dict[str, Any]:
        """Get all current context values across all types."""
        result = {}
        
        # Start with global context
        for key, entry in self.contexts[ContextType.GLOBAL].items():
            if not entry.is_expired():
                result[key] = entry.value
        
        # Override with session context
        for key, entry in self.contexts[ContextType.SESSION].items():
            if not entry.is_expired():
                result[key] = entry.value
        
        # Override with task context
        for key, entry in self.contexts[ContextType.TASK].items():
            if not entry.is_expired():
                result[key] = entry.value
        
        # Add temporary context
        for key, entry in self.contexts[ContextType.TEMPORARY].items():
            if not entry.is_expired():
                result[key] = entry.value
        
        return result
    
    def add_validation_rule(self, key: str, validation_func) -> None:
        """Add a validation rule for a context key."""
        self.validation_rules[key] = validation_func
    
    def add_propagation_rule(self, source_key: str, target_key: str, transform_func=None) -> None:
        """Add a propagation rule to automatically update related context values."""
        if transform_func is None:
            transform_func = lambda x: x  # Identity function by default
        
        if source_key not in self.propagation_rules:
            self.propagation_rules[source_key] = []
        
        self.propagation_rules[source_key].append((target_key, transform_func))
    
    def optimize_context(self) -> None:
        """Optimize the context by removing expired entries and consolidating frequently used values."""
        if not self.optimization_enabled:
            return
        
        # Remove expired entries
        for context_type in self.contexts:
            expired_keys = []
            for key, entry in self.contexts[context_type].items():
                if entry.is_expired():
                    expired_keys.append(key)
            
            for key in expired_keys:
                del self.contexts[context_type][key]
        
        # Compact history
        if len(self.context_history) > 1000:  # Arbitrary threshold
            self.context_history = self.context_history[-500:]  # Keep only recent history
    
    def prepare_task_context(self, task_id: str) -> Dict[str, Any]:
        """Prepare context for a specific task."""
        if not self.task_selector or task_id not in self.task_selector.tasks:
            return {}
        
        task = self.task_selector.tasks[task_id]
        
        # Get the current context
        current_context = self.get_current_context()
        
        # Filter context based on task requirements
        task_context = {}
        if task.context_requirements:
            for req in task.context_requirements:
                if req in current_context:
                    task_context[req] = current_context[req]
        
        return task_context
    
    def propagate_context_from_task(self, task_id: str, task_output: Dict[str, Any]) -> None:
        """Propagate context from task output to the context store."""
        if not task_output:
            return
        
        # Update task context with task output
        for key, value in task_output.items():
            self.set_context(key, value, ContextType.TASK)
    
    def serialize_context(self, include_types: List[ContextType] = None) -> str:
        """Serialize the context to a JSON string."""
        if include_types is None:
            include_types = [ContextType.GLOBAL, ContextType.SESSION, ContextType.TASK]
        
        serializable = {}
        for context_type in include_types:
            type_dict = {}
            for key, entry in self.contexts[context_type].items():
                if not entry.is_expired():
                    type_dict[key] = {
                        "value": entry.value,
                        "created_at": entry.created_at.isoformat(),
                        "updated_at": entry.updated_at.isoformat(),
                        "expires_at": entry.expires_at.isoformat() if entry.expires_at else None,
                        "metadata": entry.metadata
                    }
            serializable[context_type.value] = type_dict
        
        return json.dumps(serializable)
    
    def deserialize_context(self, serialized: str) -> None:
        """Deserialize context from a JSON string."""
        data = json.loads(serialized)
        
        for type_str, entries in data.items():
            context_type = ContextType(type_str)
            for key, entry_data in entries.items():
                expires_at = None
                if entry_data["expires_at"]:
                    expires_at = datetime.fromisoformat(entry_data["expires_at"])
                
                entry = ContextEntry(
                    key=key,
                    value=entry_data["value"],
                    type=context_type,
                    created_at=datetime.fromisoformat(entry_data["created_at"]),
                    updated_at=datetime.fromisoformat(entry_data["updated_at"]),
                    expires_at=expires_at,
                    metadata=entry_data["metadata"]
                )
                
                self.contexts[context_type][key] = entry
    
    def get_context_hash(self) -> str:
        """Get a hash of the current context state."""
        context_str = self.serialize_context()
        return hashlib.sha256(context_str.encode()).hexdigest()
    
    def get_context_diff(self, other_context_manager) -> Dict[str, Any]:
        """Get the difference between this context and another context manager."""
        diff = {
            "added": {},
            "modified": {},
            "removed": {}
        }
        
        current = self.get_current_context()
        other = other_context_manager.get_current_context()
        
        # Find added and modified
        for key, value in current.items():
            if key not in other:
                diff["added"][key] = value
            elif value != other[key]:
                diff["modified"][key] = {
                    "old": other[key],
                    "new": value
                }
        
        # Find removed
        for key in other:
            if key not in current:
                diff["removed"][key] = other[key]
        
        return diff
```

#### 2. Context Propagation Implementation

```python
class ContextPropagator:
    """Manages context propagation across tasks."""
    
    def __init__(self, context_manager):
        self.context_manager = context_manager
        self.propagation_rules = {}  # source_pattern -> (target_pattern, transform_func)
    
    def add_rule(self, source_pattern: str, target_pattern: str, transform_func=None):
        """Add a pattern-based propagation rule."""
        if transform_func is None:
            transform_func = lambda x: x  # Identity function
        
        self.propagation_rules[source_pattern] = (target_pattern, transform_func)
    
    def propagate_from_task_output(self, task_id: str, output: Dict[str, Any]) -> None:
        """Propagate context from task output using defined rules."""
        if not output:
            return
        
        for source_key, value in output.items():
            # Check for direct key matches
            for source_pattern, (target_pattern, transform_func) in self.propagation_rules.items():
                if self._match_pattern(source_key, source_pattern):
                    target_key = self._apply_pattern(source_key, source_pattern, target_pattern)
                    transformed_value = transform_func(value)
                    self.context_manager.set_context(target_key, transformed_value, ContextType.TASK)
    
    def _match_pattern(self, key: str, pattern: str) -> bool:
        """Check if a key matches a pattern."""
        if pattern.endswith('*'):
            return key.startswith(pattern[:-1])
        return key == pattern
    
    def _apply_pattern(self, source_key: str, source_pattern: str, target_pattern: str) -> str:
        """Apply a pattern transformation to generate a target key."""
        if source_pattern.endswith('*') and target_pattern.endswith('*'):
            # Extract the wildcard part
            wildcard_part = source_key[len(source_pattern)-1:]
            return target_pattern[:-1] + wildcard_part
        return target_pattern
    
    def prepare_context_for_task(self, task_id: str) -> Dict[str, Any]:
        """Prepare the context for a task based on its requirements."""
        if not self.context_manager.task_selector or task_id not in self.context_manager.task_selector.tasks:
            return {}
        
        task = self.context_manager.task_selector.tasks[task_id]
        if not task.context_requirements:
            return {}
        
        current_context = self.context_manager.get_current_context()
        task_context = {}
        
        for req in task.context_requirements:
            # Handle direct key matches
            if req in current_context:
                task_context[req] = current_context[req]
                continue
            
            # Handle pattern matches
            for key, value in current_context.items():
                for source_pattern, (target_pattern, _) in self.propagation_rules.items():
                    if self._match_pattern(key, source_pattern):
                        target_key = self._apply_pattern(key, source_pattern, target_pattern)
                        if target_key == req:
                            transformed_value = self.propagation_rules[source_pattern][1](current_context[key])
                            task_context[req] = transformed_value
                            break
            
        return task_context
    
    def validate_context_for_task(self, task_id: str) -> (bool, List[str]):
        """Validate that all required context for a task is available."""
        if not self.context_manager.task_selector or task_id not in self.context_manager.task_selector.tasks:
            return False, ["Task not found"]
        
        task = self.context_manager.task_selector.tasks[task_id]
        if not task.context_requirements:
            return True, []  # No requirements means validation passes
        
        current_context = self.context_manager.get_current_context()
        missing_requirements = []
        
        for req in task.context_requirements:
            if req not in current_context:
                # Check if any propagation rule could satisfy this
                satisfied_by_rule = False
                for key in current_context:
                    for source_pattern, (target_pattern, _) in self.propagation_rules.items():
                        if self._match_pattern(key, source_pattern):
                            target_key = self._apply_pattern(key, source_pattern, target_pattern)
                            if target_key == req:
                                satisfied_by_rule = True
                                break
                    if satisfied_by_rule:
                        break
                
                if not satisfied_by_rule:
                    missing_requirements.append(req)
        
        return len(missing_requirements) == 0, missing_requirements
```

#### 3. Context Validation Implementation

```python
class ContextValidator:
    """Validates context values against defined rules."""
    
    def __init__(self, context_manager):
        self.context_manager = context_manager
        self.type_validators = {
            "string": lambda v: isinstance(v, str),
            "number": lambda v: isinstance(v, (int, float)),
            "boolean": lambda v: isinstance(v, bool),
            "array": lambda v: isinstance(v, list),
            "object": lambda v: isinstance(v, dict),
            "null": lambda v: v is None
        }
        self.schema_validators = {}  # key -> schema
    
    def add_type_validator(self, key: str, expected_type: str) -> None:
        """Add a simple type validator for a context key."""
        if expected_type not in self.type_validators:
            raise ValueError(f"Unknown type validator: {expected_type}")
        
        self.context_manager.add_validation_rule(key, self.type_validators[expected_type])
    
    def add_schema_validator(self, key: str, schema: Dict[str, Any]) -> None:
        """Add a JSON schema validator for an object context value."""
        self.schema_validators[key] = schema
        
        def validate_schema(value):
            if not isinstance(value, dict):
                return False
            
            # Basic schema validation (could use jsonschema in production)
            for field, field_schema in schema.get("properties", {}).items():
                if field_schema.get("required", False) and field not in value:
                    return False
                
                if field in value:
                    field_type = field_schema.get("type")
                    if field_type and not self.type_validators.get(field_type, lambda v: True)(value[field]):
                        return False
            
            return True
        
        self.context_manager.add_validation_rule(key, validate_schema)
    
    def add_range_validator(self, key: str, min_value=None, max_value=None) -> None:
        """Add a range validator for numeric context values."""
        def validate_range(value):
            if not isinstance(value, (int, float)):
                return False
            
            if min_value is not None and value < min_value:
                return False
            
            if max_value is not None and value > max_value:
                return False
            
            return True
        
        self.context_manager.add_validation_rule(key, validate_range)
    
    def add_regex_validator(self, key: str, pattern: str) -> None:
        """Add a regex validator for string context values."""
        import re
        regex = re.compile(pattern)
        
        def validate_regex(value):
            if not isinstance(value, str):
                return False
            return bool(regex.match(value))
        
        self.context_manager.add_validation_rule(key, validate_regex)
    
    def add_enum_validator(self, key: str, allowed_values: List[Any]) -> None:
        """Add an enum validator that restricts values to a set of options."""
        def validate_enum(value):
            return value in allowed_values
        
        self.context_manager.add_validation_rule(key, validate_enum)
    
    def add_custom_validator(self, key: str, validator_func) -> None:
        """Add a custom validator function for a context key."""
        self.context_manager.add_validation_rule(key, validator_func)
    
    def validate_context(self) -> (bool, Dict[str, List[str]]):
        """Validate the entire current context against all rules."""
        current_context = self.context_manager.get_current_context()
        validation_errors = {}
        
        for key, value in current_context.items():
            if key in self.context_manager.validation_rules:
                validator = self.context_manager.validation_rules[key]
                if not validator(value):
                    validation_errors[key] = ["Failed validation check"]
            
            # Check schema validators
            if key in self.schema_validators and isinstance(value, dict):
                schema = self.schema_validators[key]
                errors = self._validate_against_schema(value, schema)
                if errors:
                    validation_errors[key] = errors
        
        return len(validation_errors) == 0, validation_errors
    
    def _validate_against_schema(self, value: Dict[str, Any], schema: Dict[str, Any]) -> List[str]:
        """Validate a value against a JSON schema."""
        errors = []
        
        # Check required fields
        for field, field_schema in schema.get("properties", {}).items():
            if field_schema.get("required", False) and field not in value:
                errors.append(f"Missing required field: {field}")
        
        # Check field types
        for field, field_value in value.items():
            if field in schema.get("properties", {}):
                field_schema = schema["properties"][field]
                field_type = field_schema.get("type")
                
                if field_type and not self.type_validators.get(field_type, lambda v: True)(field_value):
                    errors.append(f"Field {field} has wrong type, expected {field_type}")
                
                # Validate nested objects
                if field_type == "object" and "properties" in field_schema and isinstance(field_value, dict):
                    nested_errors = self._validate_against_schema(field_value, field_schema)
                    for error in nested_errors:
                        errors.append(f"{field}.{error}")
        
        return errors
```

#### 4. Context Optimization Implementation

```python
class ContextOptimizer:
    """Optimizes context storage and management for efficient execution."""
    
    def __init__(self, context_manager):
        self.context_manager = context_manager
        self.usage_stats = {}  # key -> {access_count, last_access}
        self.dependency_graph = {}  # key -> [dependent_keys]
        self.optimization_thresholds = {
            "cleanup_threshold": 0.7,  # Percentage of unused context to trigger cleanup
            "access_threshold": 5,  # Minimum accesses to keep during optimization
            "time_threshold": 3600  # Time in seconds since last access to consider stale
        }
    
    def track_context_access(self, key: str) -> None:
        """Track access to context keys for optimization."""
        now = datetime.now()
        
        if key not in self.usage_stats:
            self.usage_stats[key] = {"access_count": 0, "last_access": now}
        
        self.usage_stats[key]["access_count"] += 1
        self.usage_stats[key]["last_access"] = now
    
    def track_context_dependency(self, dependent_key: str, dependency_key: str) -> None:
        """Track dependencies between context keys."""
        if dependency_key not in self.dependency_graph:
            self.dependency_graph[dependency_key] = []
        
        if dependent_key not in self.dependency_graph[dependency_key]:
            self.dependency_graph[dependency_key].append(dependent_key)
    
    def optimize(self) -> int:
        """Optimize the context by removing stale or unused entries."""
        if not self.context_manager.optimization_enabled:
            return 0
        
        removed_count = 0
        now = datetime.now()
        
        # Update the tracked keys from current context
        current_context = self.context_manager.get_current_context()
        for key in current_context:
            if key not in self.usage_stats:
                self.usage_stats[key] = {"access_count": 0, "last_access": now}
        
        # Find candidates for removal
        candidates = []
        for key, stats in self.usage_stats.items():
            # Skip keys not in context (already removed)
            if key not in current_context:
                continue
                
            # Skip keys with dependencies
            if key in self.dependency_graph and self.dependency_graph[key]:
                continue
                
            # Calculate staleness score (higher means more stale)
            time_since_access = (now - stats["last_access"]).total_seconds()
            staleness = time_since_access / self.optimization_thresholds["time_threshold"]
            
            # Calculate usage score (higher means less used)
            usage = 1.0 - min(1.0, stats["access_count"] / self.optimization_thresholds["access_threshold"])
            
            # Combine scores
            score = (staleness + usage) / 2.0
            
            if score > self.optimization_thresholds["cleanup_threshold"]:
                candidates.append((key, score))
        
        # Sort candidates by score (highest first)
        candidates.sort(key=lambda x: x[1], reverse=True)
        
        # Remove high-scoring candidates
        for key, _ in candidates:
            # Check which context type this key belongs to
            for context_type in [ContextType.TEMPORARY, ContextType.TASK]:
                if key in self.context_manager.contexts[context_type]:
                    self.context_manager.delete_context(key, context_type)
                    removed_count += 1
                    break
        
        # Also clean up expired entries
        for context_type in self.context_manager.contexts:
            expired_keys = []
            for key, entry in self.context_manager.contexts[context_type].items():
                if entry.is_expired():
                    expired_keys.append(key)
            
            for key in expired_keys:
                self.context_manager.delete_context(key, context_type)
                removed_count += 1
        
        # Clean up usage stats for keys that no longer exist
        keys_to_remove = []
        for key in self.usage_stats:
            exists = False
            for context_type in self.context_manager.contexts:
                if key in self.context_manager.contexts[context_type]:
                    exists = True
                    break
            
            if not exists:
                keys_to_remove.append(key)
        
        for key in keys_to_remove:
            del self.usage_stats[key]
        
        return removed_count
    
    def set_optimization_thresholds(self, thresholds: Dict[str, float]) -> None:
        """Update optimization thresholds."""
        for key, value in thresholds.items():
            if key in self.optimization_thresholds:
                self.optimization_thresholds[key] = value
    
    def analyze_context_usage(self) -> Dict[str, Any]:
        """Analyze context usage patterns."""
        analysis = {
            "total_keys": len(self.usage_stats),
            "avg_access_count": 0,
            "most_accessed": [],
            "least_accessed": [],
            "stalest": []
        }
        
        if not self.usage_stats:
            return analysis
        
        # Calculate average access count
        total_accesses = sum(stats["access_count"] for stats in self.usage_stats.values())
        analysis["avg_access_count"] = total_accesses / len(self.usage_stats)
        
        # Sort by access count
        by_access = sorted(self.usage_stats.items(), key=lambda x: x[1]["access_count"], reverse=True)
        
        # Most accessed keys
        analysis["most_accessed"] = [
            {"key": key, "count": stats["access_count"]} 
            for key, stats in by_access[:5]
        ]
        
        # Least accessed keys
        analysis["least_accessed"] = [
            {"key": key, "count": stats["access_count"]} 
            for key, stats in by_access[-5:]
        ]
        
        # Stalest keys
        now = datetime.now()
        by_staleness = sorted(
            self.usage_stats.items(),
            key=lambda x: (now - x[1]["last_access"]).total_seconds(),
            reverse=True
        )
        
        analysis["stalest"] = [
            {
                "key": key, 
                "seconds_since_access": (now - stats["last_access"]).total_seconds()
            } 
            for key, stats in by_staleness[:5]
        ]
        
        return analysis
```

## Integration with Execution Engine

To connect the Task Selector and Context Manager with the rest of the Execution Engine, we'll implement a simple integration layer:

```python
class ExecutionEngine:
    """Coordinates the execution of tasks, managing context and resources."""
    
    def __init__(self, resource_manager=None):
        # Initialize components
        self.context_manager = ContextManager()
        self.task_selector = TaskSelector(self.context_manager, resource_manager)
        
        # Update context_manager with task_selector reference
        self.context_manager.task_selector = self.task_selector
        
        # Create supporting components
        self.context_validator = ContextValidator(self.context_manager)
        self.context_optimizer = ContextOptimizer(self.context_manager)
        self.context_propagator = ContextPropagator(self.context_manager)
        self.dependency_resolver = DependencyResolver(self.task_selector)
        self.priority_calculator = PriorityCalculator()
        
        # Execution state
        self.current_task_id = None
        self.execution_history = []
    
    def register_task(self, task: Task) -> str:
        """Register a task for execution."""
        return self.task_selector.register_task(task)
    
    def select_next_task(self, available_resources=None) -> Optional[Task]:
        """Select the next task to execute."""
        return self.task_selector.select_next_task(available_resources)
    
    def execute_task(self, task_id: str) -> Dict[str, Any]:
        """Execute a task and handle its context."""
        task = self.task_selector.get_task_by_id(task_id)
        if not task:
            raise ValueError(f"Task with ID {task_id} not found")
        
        if task.status != TaskStatus.READY:
            raise ValueError(f"Task {task_id} is not ready for execution, current status: {task.status.value}")
        
        # Prepare context for task
        task_context = self.context_propagator.prepare_context_for_task(task_id)
        
        # Update task status
        self.task_selector.update_task_status(task_id, TaskStatus.IN_PROGRESS)
        self.current_task_id = task_id
        
        start_time = datetime.now()
        
        # This would be replaced with actual task execution logic
        # For now, we'll simulate task execution
        task_output = self._simulate_task_execution(task, task_context)
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        # Record execution in history
        self.execution_history.append({
            "task_id": task_id,
            "task_name": task.name,
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "duration": duration,
            "status": "success" if task_output else "failure",
            "context_before": task_context,
            "context_after": task_output
        })
        
        # Propagate task output to context
        if task_output:
            self.context_propagator.propagate_from_task_output(task_id, task_output)
            self.task_selector.update_task_status(task_id, TaskStatus.COMPLETED)
        else:
            self.task_selector.update_task_status(task_id, TaskStatus.FAILED)
        
        self.current_task_id = None
        
        # Optimize context after task execution
        self.context_optimizer.optimize()
        
        return task_output
    
    def _simulate_task_execution(self, task: Task, context: Dict[str, Any]) -> Dict[str, Any]:
        """Simulate task execution for demonstration purposes."""
        # In a real implementation, this would execute the actual task
        # For now, we'll return a simulated output
        return {
            f"result_{task.id}": f"Executed task {task.name}",
            "timestamp": datetime.now().isoformat(),
            "status": "complete"
        }
    
    def execute_next_task(self, available_resources=None) -> Optional[Dict[str, Any]]:
        """Select and execute the next task."""
        next_task = self.select_next_task(available_resources)
        if not next_task:
            return None
        
        return self.execute_task(next_task.id)
    
    def get_execution_state(self) -> Dict[str, Any]:
        """Get the current execution state."""
        return {
            "task_counts": {
                "total": len(self.task_selector.tasks),
                "pending": len(self.task_selector.get_tasks_by_status(TaskStatus.PENDING)),
                "ready": len(self.task_selector.get_tasks_by_status(TaskStatus.READY)),
                "in_progress": len(self.task_selector.get_tasks_by_status(TaskStatus.IN_PROGRESS)),
                "completed": len(self.task_selector.get_tasks_by_status(TaskStatus.COMPLETED)),
                "failed": len(self.task_selector.get_tasks_by_status(TaskStatus.FAILED)),
                "blocked": len(self.task_selector.get_tasks_by_status(TaskStatus.BLOCKED))
            },
            "current_task": self.current_task_id,
            "context_stats": {
                "global_keys": len(self.context_manager.contexts[ContextType.GLOBAL]),
                "session_keys": len(self.context_manager.contexts[ContextType.SESSION]),
                "task_keys": len(self.context_manager.contexts[ContextType.TASK]),
                "temporary_keys": len(self.context_manager.contexts[ContextType.TEMPORARY])
            },
            "dependency_analysis": self.dependency_resolver.analyze_dependency_graph()
        }
```

## Example Usage

Here's an example of how to use the Task Selector and Context Manager together:

```python
# Create the execution engine
execution_engine = ExecutionEngine()

# Set up some context validation rules
execution_engine.context_validator.add_type_validator("project_name", "string")
execution_engine.context_validator.add_range_validator("priority_factor", 1, 10)

# Set up context propagation rules
execution_engine.context_propagator.add_rule("input_data", "processed_data", 
                                           lambda x: {"processed": True, "original": x})

# Create some tasks
task1 = Task(
    id=str(uuid.uuid4()),
    name="Initialize Project",
    description="Set up project structure and configuration",
    priority=TaskPriority.HIGH,
    status=TaskStatus.PENDING,
    dependencies=[],
    estimated_duration=15.0,
    estimated_resources={"cpu": 1.0, "memory": 512},
    context_requirements=[],
    created_at=datetime.now(),
    updated_at=datetime.now(),
    tags=["setup", "initialization"],
    metadata={}
)

task2 = Task(
    id=str(uuid.uuid4()),
    name="Process Data",
    description="Process input data from initialization",
    priority=TaskPriority.MEDIUM,
    status=TaskStatus.PENDING,
    dependencies=[TaskDependency(task1.id, "hard", "")],
    estimated_duration=30.0,
    estimated_resources={"cpu": 2.0, "memory": 1024},
    context_requirements=["input_data"],
    created_at=datetime.now(),
    updated_at=datetime.now(),
    tags=["processing", "data"],
    metadata={}
)

# Register tasks
execution_engine.register_task(task1)
execution_engine.register_task(task2)

# Set initial context
execution_engine.context_manager.set_context("project_name", "Self-Aware System", ContextType.GLOBAL)
execution_engine.context_manager.set_context("priority_factor", 5, ContextType.SESSION)

# Execute tasks
result1 = execution_engine.execute_task(task1.id)
print(f"Task 1 executed with result: {result1}")

# Set context from task1 result
execution_engine.context_manager.set_context("input_data", {"samples": 1000, "source": "database"}, ContextType.TASK)

# Execute next task
result2 = execution_engine.execute_task(task2.id)
print(f"Task 2 executed with result: {result2}")

# Get execution state
state = execution_engine.get_execution_state()
print(f"Execution state: {state}")
```

## Connection to Other System Components

The Task Selector and Context Manager components integrate with other parts of the self-aware system:

1. **Connection to Planning Engine**: The Task Selector receives tasks from the Planning Engine, which has decomposed high-level goals into executable tasks with dependencies. It maintains the execution graph created by the planning process.

2. **Connection to Parallel Execution Controller**: Once tasks are selected, they are passed to the Parallel Execution Controller, which manages concurrent execution based on resource availability and dependencies.

3. **Connection to Execution Tracker**: The Task Selector updates task statuses, which are tracked by the Execution Tracker for monitoring and reporting purposes.

4. **Connection to Resource Allocation Manager**: The Task Selector works with the Resource Allocation Manager to determine which tasks can be executed based on available resources.

5. **Connection to Cognitive Loop Orchestrator**: The Context Manager maintains context that is used by the Cognitive Loop Orchestrator to guide the overall system behavior and adapt to changing conditions.

By implementing these components, we create a robust foundation for the Execution Engine, enabling dynamic task selection, context propagation, and efficient execution based on dependencies and available resources.
