
# Implementation Guide for Phase 3 Work Units 3.3 and 3.4

## Work Unit 3.3: Parallel Execution Controller

### Overview
The Parallel Execution Controller manages concurrent task execution, coordinating resource allocation, synchronization, and result aggregation. It builds on the Task Selector (3.1) and Context Manager (3.2) to enable efficient parallel processing of tasks while respecting dependencies and resource constraints.

### Core Components

#### 1. ParallelExecutionController Class

```python
from typing import List, Dict, Set, Optional, Any, Callable, Tuple
from enum import Enum
from dataclasses import dataclass, field
import uuid
from datetime import datetime
import threading
import asyncio
import concurrent.futures
import time
import logging
from queue import Queue, PriorityQueue

# Use the Task, TaskStatus, TaskPriority classes from Task Selector (3.1)

class ExecutionMode(Enum):
    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"
    PARALLEL_WITH_LIMIT = "parallel_with_limit"

@dataclass
class ExecutionResult:
    task_id: str
    success: bool
    output: Dict[str, Any]
    start_time: datetime
    end_time: datetime
    error: Optional[str] = None
    duration: float = 0
    resource_usage: Dict[str, float] = field(default_factory=dict)

class ParallelExecutionController:
    def __init__(self, task_selector, context_manager, resource_manager=None, max_workers=4):
        self.task_selector = task_selector
        self.context_manager = context_manager
        self.resource_manager = resource_manager
        self.max_workers = max_workers
        self.execution_mode = ExecutionMode.PARALLEL_WITH_LIMIT
        
        # Execution state
        self.running_tasks = {}  # task_id -> future/thread
        self.pending_tasks = Queue()  # Task IDs waiting to be executed
        self.completed_tasks = {}  # task_id -> ExecutionResult
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=max_workers)
        
        # Synchronization primitives
        self.lock = threading.Lock()
        self.task_events = {}  # task_id -> Event
        
        # Execution hooks
        self.pre_execution_hooks = []
        self.post_execution_hooks = []
        
        # Resource tracking
        self.resource_locks = {}  # resource_type -> lock
        self.resource_usage = {}  # resource_type -> current usage
        
        # Configuration
        self.timeout = 3600  # Default timeout in seconds (1 hour)
        self.retry_count = 3  # Default retry count
        self.retry_delay = 5  # Default retry delay in seconds
        
        # Logging
        self.logger = logging.getLogger("ParallelExecutionController")
        
    def set_execution_mode(self, mode: ExecutionMode) -> None:
        """Set the execution mode."""
        self.execution_mode = mode
        
    def set_max_workers(self, max_workers: int) -> None:
        """Set the maximum number of parallel workers."""
        if max_workers <= 0:
            raise ValueError("max_workers must be greater than 0")
        
        self.max_workers = max_workers
        # Recreate the executor with new worker count
        self.executor.shutdown(wait=True)
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=max_workers)
    
    def add_pre_execution_hook(self, hook: Callable[[str, Dict[str, Any]], None]) -> None:
        """Add a hook to be called before task execution."""
        self.pre_execution_hooks.append(hook)
    
    def add_post_execution_hook(self, hook: Callable[[str, ExecutionResult], None]) -> None:
        """Add a hook to be called after task execution."""
        self.post_execution_hooks.append(hook)
    
    def execute_task(self, task_id: str) -> ExecutionResult:
        """Execute a single task synchronously."""
        task = self.task_selector.get_task_by_id(task_id)
        if not task:
            raise ValueError(f"Task with ID {task_id} not found")
        
        if task.status != TaskStatus.READY:
            raise ValueError(f"Task {task_id} is not ready for execution, current status: {task.status.value}")
        
        # Prepare context for task
        task_context = self._prepare_task_context(task_id)
        
        # Acquire resources
        if self.resource_manager and task.estimated_resources:
            success = self._acquire_resources(task.estimated_resources)
            if not success:
                raise RuntimeError(f"Failed to acquire resources for task {task_id}")
        
        # Update task status
        self.task_selector.update_task_status(task_id, TaskStatus.IN_PROGRESS)
        
        # Execute pre-execution hooks
        for hook in self.pre_execution_hooks:
            try:
                hook(task_id, task_context)
            except Exception as e:
                self.logger.error(f"Error in pre-execution hook for task {task_id}: {str(e)}")
        
        start_time = datetime.now()
        output = {}
        error = None
        success = False
        resource_usage = {}
        
        try:
            # Execute the task with retry logic
            for attempt in range(self.retry_count):
                try:
                    output = self._execute_task_logic(task, task_context)
                    success = True
                    break
                except Exception as e:
                    if attempt < self.retry_count - 1:
                        self.logger.warning(f"Task {task_id} failed, retrying ({attempt+1}/{self.retry_count}): {str(e)}")
                        time.sleep(self.retry_delay)
                    else:
                        error = str(e)
                        self.logger.error(f"Task {task_id} failed after {self.retry_count} attempts: {str(e)}")
        finally:
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            # Release resources
            if self.resource_manager and task.estimated_resources:
                self._release_resources(task.estimated_resources)
                
                # Record resource usage
                if self.resource_manager.supports_usage_tracking:
                    resource_usage = self.resource_manager.get_task_resource_usage(task_id)
        
        # Update task status
        if success:
            self.task_selector.update_task_status(task_id, TaskStatus.COMPLETED)
            # Propagate context from task output
            if output:
                self._propagate_task_output(task_id, output)
        else:
            self.task_selector.update_task_status(task_id, TaskStatus.FAILED)
        
        # Create execution result
        result = ExecutionResult(
            task_id=task_id,
            success=success,
            output=output,
            start_time=start_time,
            end_time=end_time,
            error=error,
            duration=duration,
            resource_usage=resource_usage
        )
        
        # Store completed task result
        self.completed_tasks[task_id] = result
        
        # Execute post-execution hooks
        for hook in self.post_execution_hooks:
            try:
                hook(task_id, result)
            except Exception as e:
                self.logger.error(f"Error in post-execution hook for task {task_id}: {str(e)}")
        
        return result
    
    def _execute_task_logic(self, task, context) -> Dict[str, Any]:
        """Execute the task logic. Override this in subclasses for actual implementation."""
        # This is a placeholder for actual task execution
        # In a real implementation, this would invoke the task's code
        return {
            f"result_{task.id}": f"Executed task {task.name}",
            "timestamp": datetime.now().isoformat(),
            "status": "complete"
        }
    
    def _prepare_task_context(self, task_id: str) -> Dict[str, Any]:
        """Prepare the context for a task execution."""
        task = self.task_selector.get_task_by_id(task_id)
        if not task:
            return {}
        
        # Get the current context
        current_context = self.context_manager.get_current_context()
        
        # Filter context based on task requirements
        task_context = {}
        if task.context_requirements:
            for req in task.context_requirements:
                if req in current_context:
                    task_context[req] = current_context[req]
        
        return task_context
    
    def _propagate_task_output(self, task_id: str, output: Dict[str, Any]) -> None:
        """Propagate task output to the context."""
        if not output:
            return
        
        for key, value in output.items():
            self.context_manager.set_context(key, value, ContextType.TASK)
    
    def _acquire_resources(self, resources: Dict[str, float]) -> bool:
        """Acquire resources for a task."""
        if not self.resource_manager:
            return True
        
        # Create locks for resources if they don't exist
        for resource_type in resources:
            if resource_type not in self.resource_locks:
                self.resource_locks[resource_type] = threading.Lock()
                self.resource_usage[resource_type] = 0.0
        
        # Try to acquire all resources
        acquired_resources = []
        success = True
        
        try:
            for resource_type, amount in resources.items():
                with self.resource_locks[resource_type]:
                    available = self.resource_manager.get_available_resource(resource_type)
                    if available >= amount:
                        self.resource_manager.allocate_resource(resource_type, amount)
                        self.resource_usage[resource_type] += amount
                        acquired_resources.append((resource_type, amount))
                    else:
                        success = False
                        break
            
            if not success:
                # Release any acquired resources
                for resource_type, amount in acquired_resources:
                    with self.resource_locks[resource_type]:
                        self.resource_manager.release_resource(resource_type, amount)
                        self.resource_usage[resource_type] -= amount
        
        except Exception as e:
            self.logger.error(f"Error acquiring resources: {str(e)}")
            # Release any acquired resources
            for resource_type, amount in acquired_resources:
                try:
                    with self.resource_locks[resource_type]:
                        self.resource_manager.release_resource(resource_type, amount)
                        self.resource_usage[resource_type] -= amount
                except Exception as inner_e:
                    self.logger.error(f"Error releasing resource {resource_type}: {str(inner_e)}")
            success = False
        
        return success
    
    def _release_resources(self, resources: Dict[str, float]) -> None:
        """Release resources after task execution."""
        if not self.resource_manager:
            return
        
        for resource_type, amount in resources.items():
            if resource_type in self.resource_locks:
                try:
                    with self.resource_locks[resource_type]:
                        self.resource_manager.release_resource(resource_type, amount)
                        self.resource_usage[resource_type] -= amount
                except Exception as e:
                    self.logger.error(f"Error releasing resource {resource_type}: {str(e)}")
    
    def execute_tasks_parallel(self, task_ids: List[str]) -> Dict[str, ExecutionResult]:
        """Execute multiple tasks in parallel."""
        if not task_ids:
            return {}
        
        # Check execution mode
        if self.execution_mode == ExecutionMode.SEQUENTIAL:
            return self.execute_tasks_sequential(task_ids)
        
        results = {}
        futures = {}
        
        # Determine how many tasks to execute in parallel
        max_concurrent = len(task_ids) if self.execution_mode == ExecutionMode.PARALLEL else self.max_workers
        
        # Submit tasks to the executor
        for task_id in task_ids[:max_concurrent]:
            futures[self.executor.submit(self.execute_task, task_id)] = task_id
        
        # Process remaining tasks as others complete
        remaining_task_index = max_concurrent
        
        # Wait for all futures to complete
        for future in concurrent.futures.as_completed(futures):
            task_id = futures[future]
            try:
                result = future.result()
                results[task_id] = result
                
                # Submit next task if there are more
                if remaining_task_index < len(task_ids):
                    next_task_id = task_ids[remaining_task_index]
                    futures[self.executor.submit(self.execute_task, next_task_id)] = next_task_id
                    remaining_task_index += 1
                    
            except Exception as e:
                self.logger.error(f"Error executing task {task_id}: {str(e)}")
                # Create failure result
                results[task_id] = ExecutionResult(
                    task_id=task_id,
                    success=False,
                    output={},
                    start_time=datetime.now(),
                    end_time=datetime.now(),
                    error=str(e),
                    duration=0
                )
        
        return results
    
    def execute_tasks_sequential(self, task_ids: List[str]) -> Dict[str, ExecutionResult]:
        """Execute multiple tasks sequentially."""
        results = {}
        for task_id in task_ids:
            try:
                result = self.execute_task(task_id)
                results[task_id] = result
            except Exception as e:
                self.logger.error(f"Error executing task {task_id}: {str(e)}")
                # Create failure result
                results[task_id] = ExecutionResult(
                    task_id=task_id,
                    success=False,
                    output={},
                    start_time=datetime.now(),
                    end_time=datetime.now(),
                    error=str(e),
                    duration=0
                )
                # Stop execution if a task fails
                break
        
        return results
    
    async def execute_tasks_async(self, task_ids: List[str]) -> Dict[str, ExecutionResult]:
        """Execute tasks asynchronously (requires asyncio event loop)."""
        if not task_ids:
            return {}
        
        results = {}
        loop = asyncio.get_event_loop()
        
        # Determine how many tasks to execute in parallel
        max_concurrent = len(task_ids) if self.execution_mode == ExecutionMode.PARALLEL else self.max_workers
        
        # Create a semaphore to limit concurrency
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def execute_with_semaphore(task_id):
            async with semaphore:
                return await loop.run_in_executor(None, self.execute_task, task_id)
        
        # Create tasks for all task IDs
        tasks = [execute_with_semaphore(task_id) for task_id in task_ids]
        
        # Wait for all tasks to complete
        completed_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        for i, result in enumerate(completed_results):
            task_id = task_ids[i]
            if isinstance(result, Exception):
                self.logger.error(f"Error executing task {task_id}: {str(result)}")
                # Create failure result
                results[task_id] = ExecutionResult(
                    task_id=task_id,
                    success=False,
                    output={},
                    start_time=datetime.now(),
                    end_time=datetime.now(),
                    error=str(result),
                    duration=0
                )
            else:
                results[task_id] = result
        
        return results
    
    def execute_task_tree(self, root_task_id: str) -> Dict[str, ExecutionResult]:
        """Execute a tree of tasks starting from a root task."""
        # Get the tree of tasks
        task_tree = self._build_task_tree(root_task_id)
        if not task_tree:
            return {}
        
        # Execute the tree level by level
        results = {}
        for level in task_tree:
            level_results = self.execute_tasks_parallel(level)
            results.update(level_results)
            
            # Check if any critical tasks failed
            failed_critical = False
            for task_id in level:
                task = self.task_selector.get_task_by_id(task_id)
                if task and task.priority == TaskPriority.CRITICAL and not results.get(task_id, {}).get("success", False):
                    failed_critical = True
                    break
            
            if failed_critical:
                self.logger.warning(f"Critical task failed, stopping execution of task tree from root {root_task_id}")
                break
        
        return results
    
    def _build_task_tree(self, root_task_id: str) -> List[List[str]]:
        """Build a tree of tasks from a root task, organized by levels."""
        if not self.task_selector.dependency_graph:
            return [[root_task_id]] if root_task_id in self.task_selector.tasks else []
        
        # Initialize the tree with the root task
        tree = [[root_task_id]]
        visited = {root_task_id}
        
        # Build the tree level by level
        current_level = [root_task_id]
        while current_level:
            next_level = []
            for task_id in current_level:
                if task_id in self.task_selector.dependency_graph:
                    for dependent_id in self.task_selector.dependency_graph[task_id]:
                        if dependent_id not in visited:
                            next_level.append(dependent_id)
                            visited.add(dependent_id)
            
            if next_level:
                tree.append(next_level)
            current_level = next_level
        
        return tree
    
    def get_resource_usage(self) -> Dict[str, float]:
        """Get the current resource usage."""
        return self.resource_usage.copy()
    
    def get_running_tasks(self) -> List[str]:
        """Get the list of currently running task IDs."""
        return list(self.running_tasks.keys())
    
    def get_task_result(self, task_id: str) -> Optional[ExecutionResult]:
        """Get the execution result for a completed task."""
        return self.completed_tasks.get(task_id)
    
    def get_execution_stats(self) -> Dict[str, Any]:
        """Get execution statistics."""
        completed_count = len(self.completed_tasks)
        if completed_count == 0:
            return {
                "completed_tasks": 0,
                "success_rate": 0,
                "avg_duration": 0,
                "running_tasks": len(self.running_tasks)
            }
        
        success_count = sum(1 for result in self.completed_tasks.values() if result.success)
        total_duration = sum(result.duration for result in self.completed_tasks.values())
        
        return {
            "completed_tasks": completed_count,
            "success_rate": success_count / completed_count,
            "avg_duration": total_duration / completed_count,
            "running_tasks": len(self.running_tasks)
        }
    
    def shutdown(self, wait=True) -> None:
        """Shutdown the executor and cleanup resources."""
        self.executor.shutdown(wait=wait)
```

#### 2. AsyncParallelExecutionController Extension

```python
class AsyncParallelExecutionController:
    """Asynchronous extension of the ParallelExecutionController."""
    
    def __init__(self, parallel_controller):
        self.controller = parallel_controller
        self.event_loop = None
    
    async def initialize(self):
        """Initialize the async controller."""
        self.event_loop = asyncio.get_event_loop()
    
    async def execute_task(self, task_id: str) -> ExecutionResult:
        """Execute a task asynchronously."""
        return await self.event_loop.run_in_executor(None, self.controller.execute_task, task_id)
    
    async def execute_tasks(self, task_ids: List[str]) -> Dict[str, ExecutionResult]:
        """Execute multiple tasks asynchronously."""
        return await self.controller.execute_tasks_async(task_ids)
    
    async def execute_task_tree(self, root_task_id: str) -> Dict[str, ExecutionResult]:
        """Execute a task tree asynchronously."""
        # Implement this using the async execute_tasks method level by level
        task_tree = await self.event_loop.run_in_executor(
            None, self.controller._build_task_tree, root_task_id
        )
        
        if not task_tree:
            return {}
        
        results = {}
        for level in task_tree:
            level_results = await self.execute_tasks(level)
            results.update(level_results)
            
            # Check if any critical tasks failed
            failed_critical = False
            for task_id in level:
                task = self.controller.task_selector.get_task_by_id(task_id)
                if task and task.priority == TaskPriority.CRITICAL and not results.get(task_id).success:
                    failed_critical = True
                    break
            
            if failed_critical:
                break
        
        return results
    
    async def get_execution_stats(self) -> Dict[str, Any]:
        """Get execution statistics asynchronously."""
        return await self.event_loop.run_in_executor(None, self.controller.get_execution_stats)
```

#### 3. ResourceCoordinator Implementation

```python
class ResourceCoordinator:
    """Coordinates resource allocation for parallel task execution."""
    
    def __init__(self, resource_manager, parallel_controller):
        self.resource_manager = resource_manager
        self.parallel_controller = parallel_controller
        self.resource_requests = PriorityQueue()  # (priority, task_id, resources)
        self.resource_locks = {}  # resource_type -> lock
        self.allocation_map = {}  # task_id -> {resource_type: amount}
        self.allocation_status = {}  # task_id -> status ("pending", "allocated", "denied")
        
        # Start the allocation thread
        self.running = True
        self.allocation_thread = threading.Thread(target=self._allocation_worker)
        self.allocation_thread.daemon = True
        self.allocation_thread.start()
    
    def request_resources(self, task_id: str, resources: Dict[str, float], priority: int = 0) -> bool:
        """Request resources for a task."""
        self.resource_requests.put((priority, task_id, resources))
        self.allocation_status[task_id] = "pending"
        return True
    
    def _allocation_worker(self):
        """Worker thread that processes resource allocation requests."""
        while self.running:
            try:
                # Get the next resource request
                if self.resource_requests.empty():
                    time.sleep(0.1)
                    continue
                
                priority, task_id, resources = self.resource_requests.get()
                
                # Check if resources are available
                can_allocate = True
                for resource_type, amount in resources.items():
                    if self.resource_manager.get_available_resource(resource_type) < amount:
                        can_allocate = False
                        break
                
                if can_allocate:
                    # Allocate resources
                    allocated_resources = {}
                    for resource_type, amount in resources.items():
                        if resource_type not in self.resource_locks:
                            self.resource_locks[resource_type] = threading.Lock()
                        
                        with self.resource_locks[resource_type]:
                            self.resource_manager.allocate_resource(resource_type, amount)
                            allocated_resources[resource_type] = amount
                    
                    self.allocation_map[task_id] = allocated_resources
                    self.allocation_status[task_id] = "allocated"
                else:
                    # Put the request back in the queue with a small delay
                    self.allocation_status[task_id] = "denied"
                    time.sleep(0.5)
                    self.resource_requests.put((priority, task_id, resources))
            
            except Exception as e:
                logging.error(f"Error in resource allocation worker: {str(e)}")
                time.sleep(1)  # Avoid tight loop in case of errors
    
    def release_resources(self, task_id: str) -> bool:
        """Release resources allocated to a task."""
        if task_id not in self.allocation_map:
            return False
        
        resources = self.allocation_map[task_id]
        for resource_type, amount in resources.items():
            if resource_type in self.resource_locks:
                with self.resource_locks[resource_type]:
                    self.resource_manager.release_resource(resource_type, amount)
        
        del self.allocation_map[task_id]
        del self.allocation_status[task_id]
        return True
    
    def get_allocation_status(self, task_id: str) -> str:
        """Get the allocation status for a task."""
        return self.allocation_status.get(task_id, "unknown")
    
    def shutdown(self):
        """Shutdown the resource coordinator."""
        self.running = False
        if self.allocation_thread.is_alive():
            self.allocation_thread.join(timeout=5)
        
        # Release all allocated resources
        for task_id in list(self.allocation_map.keys()):
            self.release_resources(task_id)
```

#### 4. ResultAggregator Implementation

```python
class ResultAggregator:
    """Aggregates results from parallel task execution."""
    
    def __init__(self, parallel_controller):
        self.parallel_controller = parallel_controller
        self.aggregation_functions = {
            "sum": self._aggregate_sum,
            "average": self._aggregate_average,
            "min": self._aggregate_min,
            "max": self._aggregate_max,
            "concat": self._aggregate_concat,
            "merge": self._aggregate_merge,
            "count": self._aggregate_count
        }
    
    def aggregate_results(self, task_ids: List[str], key: str, method: str = "merge") -> Any:
        """Aggregate results from multiple tasks using a specified method."""
        if method not in self.aggregation_functions:
            raise ValueError(f"Unknown aggregation method: {method}")
        
        values = []
        for task_id in task_ids:
            result = self.parallel_controller.get_task_result(task_id)
            if result and result.success and key in result.output:
                values.append(result.output[key])
        
        if not values:
            return None
        
        return self.aggregation_functions[method](values)
    
    def _aggregate_sum(self, values: List[Any]) -> Any:
        """Sum numeric values."""
        if all(isinstance(v, (int, float)) for v in values):
            return sum(values)
        return None
    
    def _aggregate_average(self, values: List[Any]) -> Any:
        """Average numeric values."""
        if all(isinstance(v, (int, float)) for v in values):
            return sum(values) / len(values)
        return None
    
    def _aggregate_min(self, values: List[Any]) -> Any:
        """Find minimum value."""
        if all(isinstance(v, (int, float)) for v in values):
            return min(values)
        return min(values, key=str)
    
    def _aggregate_max(self, values: List[Any]) -> Any:
        """Find maximum value."""
        if all(isinstance(v, (int, float)) for v in values):
            return max(values)
        return max(values, key=str)
    
    def _aggregate_concat(self, values: List[Any]) -> Any:
        """Concatenate values."""
        if all(isinstance(v, str) for v in values):
            return ''.join(values)
        elif all(isinstance(v, list) for v in values):
            result = []
            for value in values:
                result.extend(value)
            return result
        return str(values)
    
    def _aggregate_merge(self, values: List[Any]) -> Any:
        """Merge dictionaries or lists."""
        if all(isinstance(v, dict) for v in values):
            result = {}
            for value in values:
                result.update(value)
            return result
        elif all(isinstance(v, list) for v in values):
            result = []
            for value in values:
                result.extend(value)
            return result
        return values
    
    def _aggregate_count(self, values: List[Any]) -> int:
        """Count values."""
        return len(values)
    
    def aggregate_task_tree(self, root_task_id: str, key: str, method: str = "merge") -> Any:
        """Aggregate results from a task tree."""
        task_tree = self.parallel_controller._build_task_tree(root_task_id)
        if not task_tree:
            return None
        
        # Flatten the tree
        all_task_ids = [task_id for level in task_tree for task_id in level]
        return self.aggregate_results(all_task_ids, key, method)
    
    def create_aggregated_result(self, task_ids: List[str], aggregations: Dict[str, Tuple[str, str]]) -> Dict[str, Any]:
        """Create a result with multiple aggregations."""
        result = {}
        for output_key, (input_key, method) in aggregations.items():
            result[output_key] = self.aggregate_results(task_ids, input_key, method)
        return result
```

## Work Unit 3.4: Execution Tracker

### Overview
The Execution Tracker monitors task execution progress, detects failures, and generates reports and visualizations. It works closely with the Task Selector (3.1), Context Manager (3.2), and Parallel Execution Controller (3.3) to provide a comprehensive view of execution status.

### Core Components

#### 1. ExecutionTracker Class

```python
from typing import List, Dict, Set, Optional, Any, Tuple, Callable
from enum import Enum
from dataclasses import dataclass, field
import uuid
from datetime import datetime, timedelta
import json
import logging
import threading
import time
import os
import csv
from collections import defaultdict

class TrackingLevel(Enum):
    MINIMAL = "minimal"  # Basic task status only
    STANDARD = "standard"  # Task status, timing, and basic metrics
    DETAILED = "detailed"  # Full execution details including context and resources
    DEBUG = "debug"  # All possible information for debugging

class ExecutionTracker:
    def __init__(self, task_selector, context_manager, parallel_controller=None):
        self.task_selector = task_selector
        self.context_manager = context_manager
        self.parallel_controller = parallel_controller
        
        # Tracking configuration
        self.tracking_level = TrackingLevel.STANDARD
        self.update_interval = 1.0  # seconds
        self.persistence_enabled = True
        self.persistence_path = "execution_tracking"
        
        # Tracking state
        self.tracking_start_time = None
        self.tracking_end_time = None
        self.task_tracking = {}  # task_id -> tracking info
        self.execution_timeline = []  # List of events
        self.failure_records = []  # List of failure records
        self.performance_metrics = defaultdict(list)  # metric_name -> [values]
        
        # Live tracking
        self.tracking_thread = None
        self.tracking_active = False
        
        # Notifications
        self.notification_handlers = []  # Functions to call for notifications
        self.notification_thresholds = {
            "success_rate": 0.8,  # Notify if success rate falls below this
            "duration_factor": 2.0,  # Notify if task takes this times longer than estimated
            "resource_usage_factor": 1.5  # Notify if resource usage exceeds estimate by this factor
        }
        
        # Logging
        self.logger = logging.getLogger("ExecutionTracker")
        self.log_handler = None
        
        # Initialize persistence directory
        if self.persistence_enabled:
            os.makedirs(self.persistence_path, exist_ok=True)
    
    def start_tracking(self) -> None:
        """Start execution tracking."""
        if self.tracking_active:
            return
        
        self.tracking_start_time = datetime.now()
        self.tracking_active = True
        
        # Initialize log handler if needed
        if self.persistence_enabled and not self.log_handler:
            log_file = os.path.join(self.persistence_path, f"execution_{self.tracking_start_time.strftime('%Y%m%d_%H%M%S')}.log")
            self.log_handler = logging.FileHandler(log_file)
            self.log_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
            self.logger.addHandler(self.log_handler)
        
        # Record start event
        self._record_event("tracking_started", {"time": self.tracking_start_time.isoformat()})
        
        # Start tracking thread for live updates
        self.tracking_thread = threading.Thread(target=self._tracking_worker)
        self.tracking_thread.daemon = True
        self.tracking_thread.start()
        
        self.logger.info("Execution tracking started")
    
    def stop_tracking(self) -> None:
        """Stop execution tracking."""
        if not self.tracking_active:
            return
        
        self.tracking_active = False
        self.tracking_end_time = datetime.now()
        
        # Wait for tracking thread to stop
        if self.tracking_thread and self.tracking_thread.is_alive():
            self.tracking_thread.join(timeout=5)
        
        # Record stop event
        self._record_event("tracking_stopped", {
            "time": self.tracking_end_time.isoformat(),
            "duration": (self.tracking_end_time - self.tracking_start_time).total_seconds()
        })
        
        # Save final tracking data
        if self.persistence_enabled:
            self.save_tracking_data()
        
        # Remove log handler
        if self.log_handler:
            self.logger.removeHandler(self.log_handler)
            self.log_handler.close()
            self.log_handler = None
        
        self.logger.info("Execution tracking stopped")
    
    def _tracking_worker(self) -> None:
        """Worker thread for continuous tracking updates."""
        while self.tracking_active:
            try:
                # Update tracking data for all tasks
                self._update_task_tracking()
                
                # Update performance metrics
                self._update_performance_metrics()
                
                # Check for notifications
                self._check_notification_thresholds()
                
                # Save tracking data periodically if enabled
                if self.persistence_enabled and datetime.now().second % 30 == 0:  # Every 30 seconds
                    self.save_tracking_data()
                
                # Sleep for update interval
                time.sleep(self.update_interval)
            
            except Exception as e:
                self.logger.error(f"Error in tracking worker: {str(e)}")
                time.sleep(self.update_interval * 2)  # Longer sleep on error
    
    def _update_task_tracking(self) -> None:
        """Update tracking information for all tasks."""
        # Get all tasks
        tasks = {task_id: task for task_id, task in self.task_selector.tasks.items()}
        
        # Update tracking for each task
        for task_id, task in tasks.items():
            if task_id not in self.task_tracking:
                # Initialize tracking for new task
                self.task_tracking[task_id] = {
                    "task_id": task_id,
                    "name": task.name,
                    "status": task.status.value,
                    "priority": task.priority.value,
                    "created_at": task.created_at.isoformat(),
                    "updated_at": task.updated_at.isoformat(),
                    "start_time": None,
                    "end_time": None,
                    "duration": None,
                    "estimated_duration": task.estimated_duration,
                    "estimated_resources": task.estimated_resources,
                    "actual_resources": {},
                    "success": None,
                    "error": None,
                    "output_keys": [],
                    "dependencies": [dep.task_id for dep in task.dependencies],
                    "status_history": [(datetime.now().isoformat(), task.status.value)]
                }
                
                # Record task registered event
                self._record_event("task_registered", {
                    "task_id": task_id,
                    "name": task.name,
                    "priority": task.priority.value,
                    "time": datetime.now().isoformat()
                })
            else:
                # Update existing tracking
                tracking = self.task_tracking[task_id]
                
                # Check if status changed
                if tracking["status"] != task.status.value:
                    old_status = tracking["status"]
                    tracking["status"] = task.status.value
                    tracking["status_history"].append((datetime.now().isoformat(), task.status.value))
                    
                    # Record status change event
                    self._record_event("task_status_changed", {
                        "task_id": task_id,
                        "name": task.name,
                        "old_status": old_status,
                        "new_status": task.status.value,
                        "time": datetime.now().isoformat()
                    })
                    
                    # Update start/end times based on status
                    if task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED] and tracking["end_time"] is None:
                        tracking["end_time"] = datetime.now().isoformat()
                        
                        # Calculate duration if we have both start and end times
                        if tracking["start_time"]:
                            start = datetime.fromisoformat(tracking["start_time"])
                            end = datetime.fromisoformat(tracking["end_time"])
                            tracking["duration"] = (end - start).total_seconds()
                
                # Update updated_at
                tracking["updated_at"] = task.updated_at.isoformat()
                
                # Add result information if available from parallel controller
                if self.parallel_controller and task_id in self.parallel_controller.completed_tasks:
                    result = self.parallel_controller.completed_tasks[task_id]
                    tracking["success"] = result.success
                    tracking["error"] = result.error
                    tracking["output_keys"] = list(result.output.keys())
                    tracking["actual_resources"] = result.resource_usage
                    
                    # If this is a newly completed task, record the completion event
                    if task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED] and tracking["end_time"] == datetime.now().isoformat():
                        event_type = "task_completed" if result.success else "task_failed"
                        self._record_event(event_type, {
                            "task_id": task_id,
                            "name": task.name,
                            "duration": tracking["duration"],
                            "time": tracking["end_time"],
                            "error": result.error
                        })
                        
                        # Record failure details if failed
                        if not result.success:
                            self._record_failure(task_id, task.name, result.error)
    
    def _update_performance_metrics(self) -> None:
        """Update performance metrics based on current execution state."""
        # Calculate success rate
        completed_tasks = [t for t in self.task_tracking.values() 
                          if t["status"] in [TaskStatus.COMPLETED.value, TaskStatus.FAILED.value]]
        if completed_tasks:
            success_count = sum(1 for t in completed_tasks if t["success"] is True)
            self.performance_metrics["success_rate"].append((
                datetime.now().isoformat(),
                success_count / len(completed_tasks)
            ))
        
        # Calculate average duration ratio (actual/estimated)
        tasks_with_duration = [t for t in completed_tasks 
                              if t["duration"] is not None and t["estimated_duration"] is not None]
        if tasks_with_duration:
            avg_duration_ratio = sum(t["duration"] / t["estimated_duration"] for t in tasks_with_duration) / len(tasks_with_duration)
            self.performance_metrics["duration_ratio"].append((
                datetime.now().isoformat(),
                avg_duration_ratio
            ))
        
        # Calculate resource utilization
        if self.parallel_controller:
            resource_usage = self.parallel_controller.get_resource_usage()
            for resource_type, usage in resource_usage.items():
                self.performance_metrics[f"resource_{resource_type}"].append((
                    datetime.now().isoformat(),
                    usage
                ))
    
    def _check_notification_thresholds(self) -> None:
        """Check if any notification thresholds have been crossed."""
        # Check success rate
        if "success_rate" in self.performance_metrics and self.performance_metrics["success_rate"]:
            current_rate = self.performance_metrics["success_rate"][-1][1]
            if current_rate < self.notification_thresholds["success_rate"]:
                self._send_notification("success_rate_low", {
                    "current_rate": current_rate,
                    "threshold": self.notification_thresholds["success_rate"]
                })
        
        # Check for tasks that exceed duration estimates
        for task_id, tracking in self.task_tracking.items():
            if tracking["status"] == TaskStatus.IN_PROGRESS.value and tracking["start_time"]:
                start_time = datetime.fromisoformat(tracking["start_time"])
                current_duration = (datetime.now() - start_time).total_seconds()
                
                if tracking["estimated_duration"] and current_duration > tracking["estimated_duration"] * self.notification_thresholds["duration_factor"]:
                    self._send_notification("task_duration_exceeded", {
                        "task_id": task_id,
                        "task_name": tracking["name"],
                        "estimated_duration": tracking["estimated_duration"],
                        "current_duration": current_duration,
                        "factor": current_duration / tracking["estimated_duration"]
                    })
    
    def _record_event(self, event_type: str, event_data: Dict[str, Any]) -> None:
        """Record an execution event in the timeline."""
        event = {
            "event_type": event_type,
            "timestamp": datetime.now().isoformat(),
            "data": event_data
        }
        self.execution_timeline.append(event)
        
        # Log the event
        self.logger.info(f"Event: {event_type} - {json.dumps(event_data)}")
    
    def _record_failure(self, task_id: str, task_name: str, error: str) -> None:
        """Record a task failure for analysis."""
        failure = {
            "task_id": task_id,
            "task_name": task_name,
            "timestamp": datetime.now().isoformat(),
            "error": error,
            "context": {}
        }
        
        # Add context information if available and tracking level permits
        if self.tracking_level in [TrackingLevel.DETAILED, TrackingLevel.DEBUG]:
            task_context = self.context_manager._prepare_task_context(task_id)
            failure["context"] = task_context
        
        self.failure_records.append(failure)
        
        # Log the failure
        self.logger.error(f"Task failure: {task_name} ({task_id}) - {error}")
    
    def _send_notification(self, notification_type: str, notification_data: Dict[str, Any]) -> None:
        """Send a notification to registered handlers."""
        notification = {
            "type": notification_type,
            "timestamp": datetime.now().isoformat(),
            "data": notification_data
        }
        
        # Call registered notification handlers
        for handler in self.notification_handlers:
            try:
                handler(notification)
            except Exception as e:
                self.logger.error(f"Error in notification handler: {str(e)}")
        
        # Log the notification
        self.logger.warning(f"Notification: {notification_type} - {json.dumps(notification_data)}")
    
    def add_notification_handler(self, handler: Callable[[Dict[str, Any]], None]) -> None:
        """Add a notification handler function."""
        if handler not in self.notification_handlers:
            self.notification_handlers.append(handler)
    
    def set_notification_thresholds(self, thresholds: Dict[str, float]) -> None:
        """Update notification thresholds."""
        for key, value in thresholds.items():
            if key in self.notification_thresholds:
                self.notification_thresholds[key] = value
    
    def set_tracking_level(self, level: TrackingLevel) -> None:
        """Set the tracking detail level."""
        self.tracking_level = level
    
    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get the current tracking status for a task."""
        return self.task_tracking.get(task_id)
    
    def get_execution_summary(self) -> Dict[str, Any]:
        """Get a summary of the execution status."""
        # Count tasks by status
        status_counts = defaultdict(int)
        for tracking in self.task_tracking.values():
            status_counts[tracking["status"]] += 1
        
        # Calculate timing statistics
        completed_tasks = [t for t in self.task_tracking.values() 
                          if t["status"] in [TaskStatus.COMPLETED.value, TaskStatus.FAILED.value]
                          and t["duration"] is not None]
        
        timing_stats = {
            "avg_duration": 0,
            "min_duration": 0,
            "max_duration": 0
        }
        
        if completed_tasks:
            durations = [t["duration"] for t in completed_tasks]
            timing_stats["avg_duration"] = sum(durations) / len(durations)
            timing_stats["min_duration"] = min(durations)
            timing_stats["max_duration"] = max(durations)
        
        # Calculate success rate
        success_rate = 0
        if completed_tasks:
            success_count = sum(1 for t in completed_tasks if t["success"] is True)
            success_rate = success_count / len(completed_tasks)
        
        # Get execution duration
        execution_duration = 0
        if self.tracking_start_time:
            end_time = self.tracking_end_time or datetime.now()
            execution_duration = (end_time - self.tracking_start_time).total_seconds()
        
        return {
            "start_time": self.tracking_start_time.isoformat() if self.tracking_start_time else None,
            "end_time": self.tracking_end_time.isoformat() if self.tracking_end_time else None,
            "execution_duration": execution_duration,
            "total_tasks": len(self.task_tracking),
            "status_counts": status_counts,
            "success_rate": success_rate,
            "timing_stats": timing_stats,
            "failure_count": len(self.failure_records)
        }
    
    def get_task_dependencies_status(self, task_id: str) -> Dict[str, Any]:
        """Get the status of dependencies for a task."""
        if task_id not in self.task_tracking:
            return {}
        
        tracking = self.task_tracking[task_id]
        dependency_status = {}
        
        for dep_id in tracking["dependencies"]:
            if dep_id in self.task_tracking:
                dep_tracking = self.task_tracking[dep_id]
                dependency_status[dep_id] = {
                    "name": dep_tracking["name"],
                    "status": dep_tracking["status"],
                    "success": dep_tracking["success"]
                }
            else:
                dependency_status[dep_id] = {
                    "name": "Unknown",
                    "status": "unknown",
                    "success": None
                }
        
        return dependency_status
    
    def get_execution_timeline(self, start_time: datetime = None, end_time: datetime = None) -> List[Dict[str, Any]]:
        """Get the execution timeline, optionally filtered by time range."""
        if not start_time and not end_time:
            return self.execution_timeline
        
        filtered_timeline = []
        for event in self.execution_timeline:
            event_time = datetime.fromisoformat(event["timestamp"])
            
            if start_time and event_time < start_time:
                continue
            
            if end_time and event_time > end_time:
                continue
            
            filtered_timeline.append(event)
        
        return filtered_timeline
    
    def get_performance_metrics(self, metric_name: str = None) -> Dict[str, List[Tuple[str, float]]]:
        """Get performance metrics, optionally filtered by metric name."""
        if metric_name:
            return {metric_name: self.performance_metrics.get(metric_name, [])}
        
        return dict(self.performance_metrics)
    
    def get_failure_analysis(self) -> Dict[str, Any]:
        """Get analysis of task failures."""
        if not self.failure_records:
            return {"count": 0, "common_errors": [], "failure_rate": 0}
        
        # Count errors by type
        error_counts = defaultdict(int)
        for failure in self.failure_records:
            error_type = failure["error"].split(':')[0] if failure["error"] else "Unknown"
            error_counts[error_type] += 1
        
        # Sort by frequency
        common_errors = sorted(
            [{"type": error_type, "count": count} for error_type, count in error_counts.items()],
            key=lambda x: x["count"],
            reverse=True
        )
        
        # Calculate failure rate
        total_completed = sum(1 for t in self.task_tracking.values() 
                             if t["status"] in [TaskStatus.COMPLETED.value, TaskStatus.FAILED.value])
        failure_rate = len(self.failure_records) / total_completed if total_completed > 0 else 0
        
        return {
            "count": len(self.failure_records),
            "common_errors": common_errors,
            "failure_rate": failure_rate
        }
    
    def save_tracking_data(self) -> str:
        """Save tracking data to disk."""
        if not self.persistence_enabled:
            return ""
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        base_path = os.path.join(self.persistence_path, f"tracking_{timestamp}")
        
        # Save task tracking data
        tasks_file = f"{base_path}_tasks.json"
        with open(tasks_file, 'w') as f:
            json.dump(self.task_tracking, f, indent=2)
        
        # Save timeline data
        timeline_file = f"{base_path}_timeline.json"
        with open(timeline_file, 'w') as f:
            json.dump(self.execution_timeline, f, indent=2)
        
        # Save performance metrics as CSV
        for metric_name, values in self.performance_metrics.items():
            metric_file = f"{base_path}_{metric_name}.csv"
            with open(metric_file, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(["timestamp", "value"])
                for timestamp, value in values:
                    writer.writerow([timestamp, value])
        
        # Save execution summary
        summary_file = f"{base_path}_summary.json"
        with open(summary_file, 'w') as f:
            json.dump(self.get_execution_summary(), f, indent=2)
        
        self.logger.info(f"Tracking data saved to {base_path}*")
        return base_path
    
    def load_tracking_data(self, base_path: str) -> bool:
        """Load tracking data from disk."""
        try:
            # Load task tracking data
            tasks_file = f"{base_path}_tasks.json"
            if os.path.exists(tasks_file):
                with open(tasks_file, 'r') as f:
                    self.task_tracking = json.load(f)
            
            # Load timeline data
            timeline_file = f"{base_path}_timeline.json"
            if os.path.exists(timeline_file):
                with open(timeline_file, 'r') as f:
                    self.execution_timeline = json.load(f)
            
            # Load performance metrics
            self.performance_metrics = defaultdict(list)
            for file in os.listdir(os.path.dirname(base_path)):
                if file.startswith(os.path.basename(base_path)) and file.endswith(".csv"):
                    metric_name = file.replace(f"{os.path.basename(base_path)}_", "").replace(".csv", "")
                    metric_file = os.path.join(os.path.dirname(base_path), file)
                    
                    with open(metric_file, 'r', newline='') as f:
                        reader = csv.reader(f)
                        next(reader)  # Skip header
                        for row in reader:
                            if len(row) >= 2:
                                self.performance_metrics[metric_name].append((row[0], float(row[1])))
            
            self.logger.info(f"Tracking data loaded from {base_path}*")
            return True
        
        except Exception as e:
            self.logger.error(f"Error loading tracking data: {str(e)}")
            return False
```

#### 2. ProgressVisualizer Implementation

```python
class ProgressVisualizer:
    """Creates visualizations of execution progress."""
    
    def __init__(self, execution_tracker):
        self.tracker = execution_tracker
        self.visualization_handlers = {}
        
        # Register default visualization handlers
        self._register_default_handlers()
    
    def _register_default_handlers(self) -> None:
        """Register default visualization handlers."""
        self.visualization_handlers["task_status_counts"] = self._visualize_task_status_counts
        self.visualization_handlers["task_timeline"] = self._visualize_task_timeline
        self.visualization_handlers["task_dependencies"] = self._visualize_task_dependencies
        self.visualization_handlers["performance_metrics"] = self._visualize_performance_metrics
        self.visualization_handlers["success_failure_ratio"] = self._visualize_success_failure_ratio
    
    def register_visualization_handler(self, name: str, handler_func: Callable) -> None:
        """Register a custom visualization handler."""
        self.visualization_handlers[name] = handler_func
    
    def create_visualization(self, visualization_type: str, **kwargs) -> Dict[str, Any]:
        """Create a visualization using the specified handler."""
        if visualization_type not in self.visualization_handlers:
            raise ValueError(f"Unknown visualization type: {visualization_type}")
        
        return self.visualization_handlers[visualization_type](**kwargs)
    
    def _visualize_task_status_counts(self, **kwargs) -> Dict[str, Any]:
        """Create a visualization of task status counts."""
        summary = self.tracker.get_execution_summary()
        status_counts = summary.get("status_counts", {})
        
        # Convert to format suitable for visualization (e.g., pie chart)
        data = [
            {"status": status, "count": count} 
            for status, count in status_counts.items()
        ]
        
        return {
            "type": "pie_chart",
            "title": "Task Status Distribution",
            "data": data,
            "total": summary.get("total_tasks", 0)
        }
    
    def _visualize_task_timeline(self, **kwargs) -> Dict[str, Any]:
        """Create a visualization of task execution timeline."""
        task_ids = kwargs.get("task_ids", list(self.tracker.task_tracking.keys()))
        
        timeline_data = []
        for task_id in task_ids:
            if task_id in self.tracker.task_tracking:
                tracking = self.tracker.task_tracking[task_id]
                
                if tracking["start_time"] and tracking["end_time"]:
                    timeline_data.append({
                        "task_id": task_id,
                        "name": tracking["name"],
                        "start": tracking["start_time"],
                        "end": tracking["end_time"],
                        "status": tracking["status"],
                        "success": tracking["success"]
                    })
        
        return {
            "type": "gantt_chart",
            "title": "Task Execution Timeline",
            "data": timeline_data
        }
    
    def _visualize_task_dependencies(self, **kwargs) -> Dict[str, Any]:
        """Create a visualization of task dependencies."""
        task_id = kwargs.get("task_id")
        if not task_id or task_id not in self.tracker.task_tracking:
            # Build full dependency graph
            nodes = []
            edges = []
            
            for task_id, tracking in self.tracker.task_tracking.items():
                nodes.append({
                    "id": task_id,
                    "name": tracking["name"],
                    "status": tracking["status"],
                    "success": tracking["success"]
                })
                
                for dep_id in tracking["dependencies"]:
                    edges.append({
                        "source": dep_id,
                        "target": task_id
                    })
        else:
            # Build dependency graph for specific task
            nodes = []
            edges = []
            visited = set()
            
            def add_dependencies(task_id, visited):
                if task_id in visited:
                    return
                
                visited.add(task_id)
                
                if task_id in self.tracker.task_tracking:
                    tracking = self.tracker.task_tracking[task_id]
                    nodes.append({
                        "id": task_id,
                        "name": tracking["name"],
                        "status": tracking["status"],
                        "success": tracking["success"]
                    })
                    
                    for dep_id in tracking["dependencies"]:
                        edges.append({
                            "source": dep_id,
                            "target": task_id
                        })
                        add_dependencies(dep_id, visited)
            
            add_dependencies(task_id, visited)
        
        return {
            "type": "dependency_graph",
            "title": "Task Dependencies",
            "nodes": nodes,
            "edges": edges
        }
    
    def _visualize_performance_metrics(self, **kwargs) -> Dict[str, Any]:
        """Create a visualization of performance metrics over time."""
        metric_name = kwargs.get("metric_name")
        metrics = self.tracker.get_performance_metrics(metric_name)
        
        series_data = []
        for name, values in metrics.items():
            data_points = [
                {"timestamp": timestamp, "value": value} 
                for timestamp, value in values
            ]
            series_data.append({
                "name": name,
                "data": data_points
            })
        
        return {
            "type": "time_series",
            "title": f"Performance Metrics{f': {metric_name}' if metric_name else ''}",
            "series": series_data
        }
    
    def _visualize_success_failure_ratio(self, **kwargs) -> Dict[str, Any]:
        """Create a visualization of success vs failure ratio."""
        summary = self.tracker.get_execution_summary()
        status_counts = summary.get("status_counts", {})
        
        completed = status_counts.get(TaskStatus.COMPLETED.value, 0)
        failed = status_counts.get(TaskStatus.FAILED.value, 0)
        
        data = [
            {"status": "Completed", "count": completed},
            {"status": "Failed", "count": failed}
        ]
        
        return {
            "type": "bar_chart",
            "title": "Task Success vs Failure",
            "data": data,
            "success_rate": summary.get("success_rate", 0)
        }
    
    def create_progress_report(self) -> Dict[str, Any]:
        """Create a comprehensive progress report with multiple visualizations."""
        summary = self.tracker.get_execution_summary()
        
        report = {
            "summary": summary,
            "visualizations": {
                "status_distribution": self._visualize_task_status_counts(),
                "success_failure": self._visualize_success_failure_ratio(),
                "timeline": self._visualize_task_timeline(),
                "dependencies": self._visualize_task_dependencies(),
                "performance": self._visualize_performance_metrics()
            },
            "failure_analysis": self.tracker.get_failure_analysis(),
            "generated_at": datetime.now().isoformat()
        }
        
        return report
    
    def save_progress_report(self, output_path: str) -> str:
        """Generate and save a progress report to disk."""
        report = self.create_progress_report()
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # Save report as JSON
        with open(output_path, 'w') as f:
            json.dump(report, f, indent=2)
        
        return output_path
```

#### 3. FailureAnalyzer Implementation

```python
class FailureAnalyzer:
    """Analyzes task failures to identify patterns and common causes."""
    
    def __init__(self, execution_tracker):
        self.tracker = execution_tracker
        self.failure_patterns = {}  # pattern_name -> pattern_matcher_function
        self.failure_categories = {}  # category_name -> category_detector_function
        
        # Register common failure patterns
        self._register_default_patterns()
    
    def _register_default_patterns(self) -> None:
        """Register default failure patterns."""
        # Resource-related failures
        self.failure_patterns["resource_exhaustion"] = lambda error: any(
            term in error.lower() for term in ["memory", "out of memory", "resource", "capacity"]
        )
        
        # Timeout failures
        self.failure_patterns["timeout"] = lambda error: any(
            term in error.lower() for term in ["timeout", "timed out", "deadline exceeded"]
        )
        
        # Dependency failures
        self.failure_patterns["dependency_failure"] = lambda error: any(
            term in error.lower() for term in ["dependency", "dependent", "required"]
        )
        
        # Configuration errors
        self.failure_patterns["configuration"] = lambda error: any(
            term in error.lower() for term in ["config", "configuration", "setting", "parameter"]
        )
        
        # Register categories
        self.failure_categories["resource"] = lambda failure: (
            self.failure_patterns["resource_exhaustion"](failure["error"])
        )
        
        self.failure_categories["timing"] = lambda failure: (
            self.failure_patterns["timeout"](failure["error"])
        )
        
        self.failure_categories["dependency"] = lambda failure: (
            self.failure_patterns["dependency_failure"](failure["error"])
        )
        
        self.failure_categories["configuration"] = lambda failure: (
            self.failure_patterns["configuration"](failure["error"])
        )
    
    def register_failure_pattern(self, pattern_name: str, pattern_matcher: Callable[[str], bool]) -> None:
        """Register a new failure pattern detector."""
        self.failure_patterns[pattern_name] = pattern_matcher
    
    def register_failure_category(self, category_name: str, category_detector: Callable[[Dict[str, Any]], bool]) -> None:
        """Register a new failure category detector."""
        self.failure_categories[category_name] = category_detector
    
    def analyze_failures(self) -> Dict[str, Any]:
        """Analyze all recorded failures and generate a report."""
        failures = self.tracker.failure_records
        
        if not failures:
            return {
                "count": 0,
                "patterns": {},
                "categories": {},
                "tasks": {},
                "timeline": []
            }
        
        # Analyze patterns
        pattern_counts = defaultdict(int)
        for failure in failures:
            for pattern_name, pattern_matcher in self.failure_patterns.items():
                if pattern_matcher(failure["error"]):
                    pattern_counts[pattern_name] += 1
        
        # Analyze categories
        category_counts = defaultdict(int)
        failure_categories = {}
        for failure in failures:
            failure_categories[failure["task_id"]] = []
            for category_name, category_detector in self.failure_categories.items():
                if category_detector(failure):
                    category_counts[category_name] += 1
                    failure_categories[failure["task_id"]].append(category_name)
        
        # Analyze by task
        task_failure_counts = defaultdict(int)
        for failure in failures:
            task_failure_counts[failure["task_name"]] += 1
        
        # Create timeline of failures
        failure_timeline = []
        for failure in failures:
            failure_timeline.append({
                "timestamp": failure["timestamp"],
                "task_id": failure["task_id"],
                "task_name": failure["task_name"],
                "error": failure["error"],
                "categories": failure_categories.get(failure["task_id"], [])
            })
        
        # Sort timeline by timestamp
        failure_timeline.sort(key=lambda x: x["timestamp"])
        
        return {
            "count": len(failures),
            "patterns": dict(pattern_counts),
            "categories": dict(category_counts),
            "tasks": dict(task_failure_counts),
            "timeline": failure_timeline
        }
    
    def get_recurring_failures(self) -> List[Dict[str, Any]]:
        """Identify recurring failures across multiple tasks."""
        failures = self.tracker.failure_records
        if not failures:
            return []
        
        # Group failures by error message similarity
        error_groups = defaultdict(list)
        for failure in failures:
            # Create a simplified error key by taking first sentence or up to 50 chars
            error_key = failure["error"].split('.')[0][:50].strip().lower()
            error_groups[error_key].append(failure)
        
        # Find recurring failures (appearing in multiple tasks)
        recurring = []
        for error_key, group in error_groups.items():
            task_ids = set(f["task_id"] for f in group)
            if len(group) > 1 and len(task_ids) > 1:
                recurring.append({
                    "error_key": error_key,
                    "count": len(group),
                    "task_count": len(task_ids),
                    "first_occurrence": min(f["timestamp"] for f in group),
                    "last_occurrence": max(f["timestamp"] for f in group),
                    "examples": [f["task_name"] for f in group[:3]]
                })
        
        return sorted(recurring, key=lambda x: x["count"], reverse=True)
    
    def suggest_failure_mitigations(self) -> Dict[str, List[str]]:
        """Suggest mitigations for common failure categories."""
        analysis = self.analyze_failures()
        
        mitigations = {}
        
        if "resource" in analysis["categories"] and analysis["categories"]["resource"] > 0:
            mitigations["resource"] = [
                "Increase resource allocation for affected tasks",
                "Optimize resource usage in task implementation",
                "Split large tasks into smaller ones",
                "Implement more efficient algorithms or data structures",
                "Add resource monitoring and dynamic scaling"
            ]
        
        if "timing" in analysis["categories"] and analysis["categories"]["timing"] > 0:
            mitigations["timing"] = [
                "Increase timeout thresholds for affected tasks",
                "Optimize task performance to reduce execution time",
                "Implement progress reporting to avoid false timeouts",
                "Use checkpointing for long-running tasks",
                "Split time-consuming tasks into smaller steps"
            ]
        
        if "dependency" in analysis["categories"] and analysis["categories"]["dependency"] > 0:
            mitigations["dependency"] = [
                "Validate dependency availability before task execution",
                "Implement more robust dependency checking",
                "Add retry logic for transient dependency issues",
                "Improve error handling for missing dependencies",
                "Add fallback options for critical dependencies"
            ]
        
        if "configuration" in analysis["categories"] and analysis["categories"]["configuration"] > 0:
            mitigations["configuration"] = [
                "Validate configuration before task execution",
                "Implement configuration schema validation",
                "Add defaults for missing configuration values",
                "Improve error messages for configuration issues",
                "Create configuration presets for common scenarios"
            ]
        
        return mitigations
```

#### 4. AlertManager Implementation

```python
class AlertManager:
    """Manages alerts and notifications for execution tracking."""
    
    def __init__(self, execution_tracker):
        self.tracker = execution_tracker
        self.alert_handlers = {}  # alert_type -> handler_function
        self.alert_history = []
        self.alert_rules = {}  # rule_name -> (condition_func, alert_type, alert_data_func)
        self.alert_counters = defaultdict(int)  # rule_name -> count
        self.suppression_intervals = {}  # rule_name -> seconds_to_suppress
        self.last_alert_times = {}  # rule_name -> last_alert_timestamp
        
        # Register with tracker's notification system
        self.tracker.add_notification_handler(self._handle_notification)
        
        # Register default alert rules
        self._register_default_rules()
    
    def _register_default_rules(self) -> None:
        """Register default alert rules."""
        # Low success rate alert
        self.alert_rules["low_success_rate"] = (
            lambda summary: summary.get("success_rate", 1.0) < 0.7,  # Condition
            "critical",  # Alert type
            lambda summary: {  # Alert data function
                "message": f"Low success rate: {summary.get('success_rate', 0)*100:.1f}%",
                "success_rate": summary.get("success_rate", 0),
                "failure_count": len(self.tracker.failure_records)
            }
        )
        
        # High failure count alert
        self.alert_rules["high_failure_count"] = (
            lambda summary: len(self.tracker.failure_records) > 5,  # Condition
            "warning",  # Alert type
            lambda summary: {  # Alert data function
                "message": f"High failure count: {len(self.tracker.failure_records)} tasks failed",
                "failure_count": len(self.tracker.failure_records)
            }
        )
        
        # Execution duration alert
        self.alert_rules["long_execution_duration"] = (
            lambda summary: summary.get("execution_duration", 0) > 3600,  # Condition (1 hour)
            "info",  # Alert type
            lambda summary: {  # Alert data function
                "message": f"Long execution duration: {summary.get('execution_duration', 0)/60:.1f} minutes",
                "duration": summary.get("execution_duration", 0)
            }
        )
        
        # Set suppression intervals (in seconds)
        self.suppression_intervals["low_success_rate"] = 300  # 5 minutes
        self.suppression_intervals["high_failure_count"] = 180  # 3 minutes
        self.suppression_intervals["long_execution_duration"] = 600  # 10 minutes
    
    def register_alert_handler(self, alert_type: str, handler_func: Callable[[Dict[str, Any]], None]) -> None:
        """Register a handler for a specific alert type."""
        self.alert_handlers[alert_type] = handler_func
    
    def register_alert_rule(self, rule_name: str, condition_func: Callable,
                           alert_type: str, alert_data_func: Callable,
                           suppression_interval: int = 300) -> None:
        """Register a new alert rule."""
        self.alert_rules[rule_name] = (condition_func, alert_type, alert_data_func)
        self.suppression_intervals[rule_name] = suppression_interval
    
    def _handle_notification(self, notification: Dict[str, Any]) -> None:
        """Handle notifications from the execution tracker."""
        # Convert notifications to alerts if needed
        alert_type = None
        alert_data = None
        
        if notification["type"] == "success_rate_low":
            alert_type = "critical"
            alert_data = {
                "message": f"Success rate fell below threshold: {notification['data']['current_rate']*100:.1f}%",
                "success_rate": notification["data"]["current_rate"],
                "threshold": notification["data"]["threshold"]
            }
        
        elif notification["type"] == "task_duration_exceeded":
            alert_type = "warning"
            alert_data = {
                "message": f"Task duration exceeded estimate: {notification['data']['task_name']}",
                "task_id": notification["data"]["task_id"],
                "task_name": notification["data"]["task_name"],
                "estimated_duration": notification["data"]["estimated_duration"],
                "current_duration": notification["data"]["current_duration"],
                "factor": notification["data"]["factor"]
            }
        
        if alert_type and alert_data:
            self._trigger_alert(alert_type, alert_data)
    
    def _trigger_alert(self, alert_type: str, alert_data: Dict[str, Any]) -> None:
        """Trigger an alert of the specified type."""
        alert = {
            "type": alert_type,
            "timestamp": datetime.now().isoformat(),
            "data": alert_data
        }
        
        # Add to alert history
        self.alert_history.append(alert)
        
        # Call alert handler if registered
        if alert_type in self.alert_handlers:
            try:
                self.alert_handlers[alert_type](alert)
            except Exception as e:
                logging.error(f"Error in alert handler for {alert_type}: {str(e)}")
    
    def check_alert_conditions(self) -> None:
        """Check all alert conditions and trigger alerts if needed."""
        summary = self.tracker.get_execution_summary()
        now = datetime.now()
        
        for rule_name, (condition_func, alert_type, alert_data_func) in self.alert_rules.items():
            # Check if alert is suppressed
            if rule_name in self.last_alert_times:
                last_time = datetime.fromisoformat(self.last_alert_times[rule_name])
                seconds_since_last = (now - last_time).total_seconds()
                if seconds_since_last < self.suppression_intervals.get(rule_name, 300):
                    continue
            
            # Check condition
            try:
                if condition_func(summary):
                    # Generate alert data
                    alert_data = alert_data_func(summary)
                    
                    # Trigger alert
                    self._trigger_alert(alert_type, alert_data)
                    
                    # Update counters and timestamps
                    self.alert_counters[rule_name] += 1
                    self.last_alert_times[rule_name] = now.isoformat()
            except Exception as e:
                logging.error(f"Error checking alert condition for {rule_name}: {str(e)}")
    
    def get_recent_alerts(self, limit: int = 10, alert_type: str = None) -> List[Dict[str, Any]]:
        """Get recent alerts, optionally filtered by type."""
        filtered_alerts = self.alert_history
        if alert_type:
            filtered_alerts = [a for a in filtered_alerts if a["type"] == alert_type]
        
        # Return most recent alerts first
        return sorted(filtered_alerts, key=lambda x: x["timestamp"], reverse=True)[:limit]
    
    def get_alert_summary(self) -> Dict[str, Any]:
        """Get a summary of triggered alerts."""
        type_counts = defaultdict(int)
        for alert in self.alert_history:
            type_counts[alert["type"]] += 1
        # Calculate time periods
        alert_periods = {}
        if self.alert_history:
            first_alert = datetime.fromisoformat(min(a["timestamp"] for a in self.alert_history))
            last_alert = datetime.fromisoformat(max(a["timestamp"] for a in self.alert_history))
            total_seconds = (last_alert - first_alert).total_seconds()
            
            if total_seconds > 0:
                for alert_type, count in type_counts.items():
                    alert_periods[alert_type] = total_seconds / count  # Average seconds between alerts
        
        return {
            "total_alerts": len(self.alert_history),
            "type_counts": dict(type_counts),
            "alert_periods": alert_periods,
            "rule_counters": dict(self.alert_counters)
        }
    
    def clear_alerts(self, older_than: datetime = None) -> int:
        """Clear alerts, optionally only those older than a specified time."""
        if older_than is None:
            count = len(self.alert_history)
            self.alert_history = []
            return count
        
        original_count = len(self.alert_history)
        self.alert_history = [
            alert for alert in self.alert_history
            if datetime.fromisoformat(alert["timestamp"]) >= older_than
        ]
        return original_count - len(self.alert_history)
```

## Unit Tests

Here are comprehensive unit tests for the components of Work Units 3.3 and 3.4:

### Unit Tests for Parallel Execution Controller (Work Unit 3.3)

```python
import unittest
from unittest.mock import Mock, patch, MagicMock
import threading
import time
import asyncio
from datetime import datetime, timedelta

# Import the components to test
from parallel_execution_controller import (
    ParallelExecutionController, ExecutionMode, ExecutionResult,
    ResourceCoordinator, ResultAggregator, AsyncParallelExecutionController
)

# Import types from previous units
from task_selector import TaskSelector, Task, TaskStatus, TaskPriority, TaskDependency
from context_manager import ContextManager, ContextType

class TestParallelExecutionController(unittest.TestCase):
    def setUp(self):
        """Set up test fixtures."""
        self.task_selector = Mock(spec=TaskSelector)
        self.context_manager = Mock(spec=ContextManager)
        self.resource_manager = Mock()
        
        # Configure mocks
        self.task_selector.get_task_by_id.side_effect = self._mock_get_task
        self.context_manager.get_current_context.return_value = {"test_key": "test_value"}
        
        # Create controller
        self.controller = ParallelExecutionController(
            self.task_selector, 
            self.context_manager,
            self.resource_manager,
            max_workers=2
        )
    
    def _mock_get_task(self, task_id):
        """Mock implementation for get_task_by_id."""
        if task_id == "task1":
            return Task(
                id="task1",
                name="Test Task 1",
                description="Test description",
                priority=TaskPriority.MEDIUM,
                status=TaskStatus.READY,
                dependencies=[],
                estimated_duration=10.0,
                estimated_resources={"cpu": 1.0, "memory": 512},
                context_requirements=["test_key"],
                created_at=datetime.now(),
                updated_at=datetime.now(),
                tags=["test"],
                metadata={}
            )
        elif task_id == "task2":
            return Task(
                id="task2",
                name="Test Task 2",
                description="Test description",
                priority=TaskPriority.HIGH,
                status=TaskStatus.READY,
                dependencies=[TaskDependency("task1", "hard", "")],
                estimated_duration=20.0,
                estimated_resources={"cpu": 2.0, "memory": 1024},
                context_requirements=["test_key"],
                created_at=datetime.now(),
                updated_at=datetime.now(),
                tags=["test"],
                metadata={}
            )
        elif task_id == "failed_task":
            return Task(
                id="failed_task",
                name="Failed Task",
                description="Task that fails",
                priority=TaskPriority.MEDIUM,
                status=TaskStatus.READY,
                dependencies=[],
                estimated_duration=5.0,
                estimated_resources={"cpu": 1.0},
                context_requirements=[],
                created_at=datetime.now(),
                updated_at=datetime.now(),
                tags=["test"],
                metadata={}
            )
        return None

    def test_execute_task_success(self):
        """Test successful task execution."""
        # Patch the _execute_task_logic method to return a known result
        with patch.object(self.controller, '_execute_task_logic', return_value={"result": "success"}):
            result = self.controller.execute_task("task1")
            
            # Verify task selector was called correctly
            self.task_selector.get_task_by_id.assert_called_with("task1")
            self.task_selector.update_task_status.assert_any_call("task1", TaskStatus.IN_PROGRESS)
            self.task_selector.update_task_status.assert_any_call("task1", TaskStatus.COMPLETED)
            
            # Verify result
            self.assertTrue(result.success)
            self.assertEqual(result.task_id, "task1")
            self.assertEqual(result.output, {"result": "success"})
            self.assertIsNone(result.error)
            
            # Verify task completed
            self.assertIn("task1", self.controller.completed_tasks)
    
    def test_execute_task_failure(self):
        """Test task execution failure."""
        # Patch the _execute_task_logic method to raise an exception
        with patch.object(self.controller, '_execute_task_logic', side_effect=Exception("Test error")):
            result = self.controller.execute_task("task1")
            
            # Verify task selector was called correctly
            self.task_selector.update_task_status.assert_any_call("task1", TaskStatus.IN_PROGRESS)
            self.task_selector.update_task_status.assert_any_call("task1", TaskStatus.FAILED)
            
            # Verify result
            self.assertFalse(result.success)
            self.assertEqual(result.task_id, "task1")
            self.assertEqual(result.error, "Test error")
            
            # Verify task completed with failure
            self.assertIn("task1", self.controller.completed_tasks)
    
    def test_execute_tasks_parallel(self):
        """Test parallel execution of multiple tasks."""
        # Patch the execute_task method to return success for task1 and failure for failed_task
        def mock_execute_task(task_id):
            if task_id == "task1":
                return ExecutionResult(
                    task_id="task1",
                    success=True,
                    output={"result": "success"},
                    start_time=datetime.now(),
                    end_time=datetime.now() + timedelta(seconds=1),
                    duration=1.0
                )
            else:
                return ExecutionResult(
                    task_id="failed_task",
                    success=False,
                    output={},
                    start_time=datetime.now(),
                    end_time=datetime.now() + timedelta(seconds=1),
                    error="Test error",
                    duration=1.0
                )
        
        with patch.object(self.controller, 'execute_task', side_effect=mock_execute_task):
            results = self.controller.execute_tasks_parallel(["task1", "failed_task"])
            
            # Verify results
            self.assertEqual(len(results), 2)
            self.assertTrue(results["task1"].success)
            self.assertFalse(results["failed_task"].success)
    
    def test_execute_tasks_sequential(self):
        """Test sequential execution of multiple tasks."""
        # Patch the execute_task method to return success for task1 and raise for task2
        def mock_execute_task(task_id):
            if task_id == "task1":
                return ExecutionResult(
                    task_id="task1",
                    success=True,
                    output={"result": "success"},
                    start_time=datetime.now(),
                    end_time=datetime.now() + timedelta(seconds=1),
                    duration=1.0
                )
            else:
                raise Exception("Test error")
        
        with patch.object(self.controller, 'execute_task', side_effect=mock_execute_task):
            # Set sequential execution mode
            self.controller.set_execution_mode(ExecutionMode.SEQUENTIAL)
            
            results = self.controller.execute_tasks_sequential(["task1", "task2"])
            
            # Verify results
            self.assertEqual(len(results), 2)
            self.assertTrue(results["task1"].success)
            self.assertFalse(results["task2"].success)
            self.assertEqual(results["task2"].error, "Test error")
    
    def test_execute_task_tree(self):
        """Test execution of a task tree."""
        # Configure mock for _build_task_tree
        self.controller._build_task_tree = MagicMock(return_value=[["task1"], ["task2"]])
        
        # Patch execute_tasks_parallel to return success for both tasks
        mock_results = {
            "task1": ExecutionResult(
                task_id="task1",
                success=True,
                output={"result": "success"},
                start_time=datetime.now(),
                end_time=datetime.now() + timedelta(seconds=1),
                duration=1.0
            ),
            "task2": ExecutionResult(
                task_id="task2",
                success=True,
                output={"result": "success"},
                start_time=datetime.now(),
                end_time=datetime.now() + timedelta(seconds=1),
                duration=1.0
            )
        }
        
        self.controller.execute_tasks_parallel = MagicMock(side_effect=[
            {"task1": mock_results["task1"]},
            {"task2": mock_results["task2"]}
        ])
        
        results = self.controller.execute_task_tree("task1")
        
        # Verify results
        self.assertEqual(len(results), 2)
        self.assertTrue(results["task1"].success)
        self.assertTrue(results["task2"].success)
        
        # Verify _build_task_tree was called
        self.controller._build_task_tree.assert_called_once_with("task1")
        
        # Verify execute_tasks_parallel was called twice (once per level)
        self.assertEqual(self.controller.execute_tasks_parallel.call_count, 2)
    
    def test_resource_acquisition(self):
        """Test resource acquisition during task execution."""
        # Configure resource manager mock
        self.resource_manager.get_available_resource.return_value = 2.0
        
        # Patch the _execute_task_logic method to return a known result
        with patch.object(self.controller, '_execute_task_logic', return_value={"result": "success"}):
            result = self.controller.execute_task("task1")
            
            # Verify resource manager was called correctly
            self.resource_manager.allocate_resource.assert_any_call("cpu", 1.0)
            self.resource_manager.allocate_resource.assert_any_call("memory", 512)
            self.resource_manager.release_resource.assert_any_call("cpu", 1.0)
            self.resource_manager.release_resource.assert_any_call("memory", 512)
            
            # Verify result
            self.assertTrue(result.success)


class TestResourceCoordinator(unittest.TestCase):
    def setUp(self):
        """Set up test fixtures."""
        self.resource_manager = Mock()
        self.parallel_controller = Mock()
        self.coordinator = ResourceCoordinator(self.resource_manager, self.parallel_controller)
        
        # Configure resource manager
        self.resource_manager.get_available_resource.return_value = 2.0
    
    def tearDown(self):
        """Clean up after tests."""
        self.coordinator.shutdown()
    
    def test_request_resources(self):
        """Test requesting resources."""
        result = self.coordinator.request_resources("task1", {"cpu": 1.0, "memory": 512}, priority=1)
        
        # Should return True to indicate request was accepted
        self.assertTrue(result)
        
        # Status should be set to pending
        self.assertEqual(self.coordinator.allocation_status.get("task1"), "pending")
        
        # Wait for allocation to complete
        max_wait = 2  # seconds
        start = time.time()
        while self.coordinator.allocation_status.get("task1") == "pending":
            time.sleep(0.1)
            if time.time() - start > max_wait:
                break
        
        # Status should be updated to allocated
        self.assertEqual(self.coordinator.allocation_status.get("task1"), "allocated")
        
        # Resource manager should be called
        self.resource_manager.allocate_resource.assert_any_call("cpu", 1.0)
        self.resource_manager.allocate_resource.assert_any_call("memory", 512)
    
    def test_release_resources(self):
        """Test releasing resources."""
        # First allocate resources
        self.coordinator.allocation_map["task1"] = {"cpu": 1.0, "memory": 512}
        self.coordinator.allocation_status["task1"] = "allocated"
        
        # Now release them
        result = self.coordinator.release_resources("task1")
        
        # Should return True to indicate success
        self.assertTrue(result)
        
        # Resource manager should be called
        self.resource_manager.release_resource.assert_any_call("cpu", 1.0)
        self.resource_manager.release_resource.assert_any_call("memory", 512)
        
        # Task should be removed from maps
        self.assertNotIn("task1", self.coordinator.allocation_map)
        self.assertNotIn("task1", self.coordinator.allocation_status)


class TestResultAggregator(unittest.TestCase):
    def setUp(self):
        """Set up test fixtures."""
        self.parallel_controller = Mock()
        self.aggregator = ResultAggregator(self.parallel_controller)
        
        # Configure parallel controller to return test results
        self.parallel_controller.get_task_result.side_effect = self._mock_get_task_result
    
    def _mock_get_task_result(self, task_id):
        """Mock implementation for get_task_result."""
        if task_id == "task1":
            return ExecutionResult(
                task_id="task1",
                success=True,
                output={"count": 5, "value": 10, "data": [1, 2], "metadata": {"name": "test1"}},
                start_time=datetime.now(),
                end_time=datetime.now() + timedelta(seconds=1),
                duration=1.0
            )
        elif task_id == "task2":
            return ExecutionResult(
                task_id="task2",
                success=True,
                output={"count": 3, "value": 20, "data": [3, 4], "metadata": {"name": "test2"}},
                start_time=datetime.now(),
                end_time=datetime.now() + timedelta(seconds=2),
                duration=2.0
            )
        elif task_id == "failed_task":
            return ExecutionResult(
                task_id="failed_task",
                success=False,
                output={},
                start_time=datetime.now(),
                end_time=datetime.now() + timedelta(seconds=1),
                error="Test error",
                duration=1.0
            )
        return None
    
    def test_aggregate_sum(self):
        """Test sum aggregation."""
        result = self.aggregator.aggregate_results(["task1", "task2"], "count", "sum")
        self.assertEqual(result, 8)  # 5 + 3
    
    def test_aggregate_average(self):
        """Test average aggregation."""
        result = self.aggregator.aggregate_results(["task1", "task2"], "value", "average")
        self.assertEqual(result, 15)  # (10 + 20) / 2
    
    def test_aggregate_concat(self):
        """Test concatenation aggregation."""
        result = self.aggregator.aggregate_results(["task1", "task2"], "data", "concat")
        self.assertEqual(result, [1, 2, 3, 4])
    
    def test_aggregate_merge(self):
        """Test merge aggregation."""
        result = self.aggregator.aggregate_results(["task1", "task2"], "metadata", "merge")
        self.assertEqual(result, {"name": "test2"})  # test2 overwrites test1
    
    def test_aggregate_with_failures(self):
        """Test aggregation with failed tasks."""
        result = self.aggregator.aggregate_results(["task1", "failed_task"], "count", "sum")
        self.assertEqual(result, 5)  # Only task1 contributes
    
    def test_create_aggregated_result(self):
        """Test creating multiple aggregations."""
        aggregations = {
            "total_count": ("count", "sum"),
            "avg_value": ("value", "average"),
            "all_data": ("data", "concat")
        }
        
        result = self.aggregator.create_aggregated_result(["task1", "task2"], aggregations)
        
        self.assertEqual(result["total_count"], 8)
        self.assertEqual(result["avg_value"], 15)
        self.assertEqual(result["all_data"], [1, 2, 3, 4])


class TestAsyncParallelExecutionController(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        """Set up test fixtures."""
        self.parallel_controller = Mock()
        self.async_controller = AsyncParallelExecutionController(self.parallel_controller)
        await self.async_controller.initialize()
        
        # Configure mocks
        self.parallel_controller.execute_task.return_value = ExecutionResult(
            task_id="task1",
            success=True,
            output={"result": "success"},
            start_time=datetime.now(),
            end_time=datetime.now() + timedelta(seconds=1),
            duration=1.0
        )
        
        self.parallel_controller.execute_tasks_async.return_value = {
            "task1": ExecutionResult(
                task_id="task1",
                success=True,
                output={"result": "success"},
                start_time=datetime.now(),
                end_time=datetime.now() + timedelta(seconds=1),
                duration=1.0
            ),
            "task2": ExecutionResult(
                task_id="task2",
                success=True,
                output={"result": "success2"},
                start_time=datetime.now(),
                end_time=datetime.now() + timedelta(seconds=2),
                duration=2.0
            )
        }
    
    async def test_execute_task(self):
        """Test asynchronous execution of a single task."""
        result = await self.async_controller.execute_task("task1")
        
        # Verify parallel controller was called
        self.parallel_controller.execute_task.assert_called_once_with("task1")
        
        # Verify result
        self.assertTrue(result.success)
        self.assertEqual(result.task_id, "task1")
        self.assertEqual(result.output, {"result": "success"})
    
    async def test_execute_tasks(self):
        """Test asynchronous execution of multiple tasks."""
        results = await self.async_controller.execute_tasks(["task1", "task2"])
        
        # Verify parallel controller was called
        self.parallel_controller.execute_tasks_async.assert_called_once_with(["task1", "task2"])
        
        # Verify results
        self.assertEqual(len(results), 2)
        self.assertTrue(results["task1"].success)
        self.assertTrue(results["task2"].success)
        self.assertEqual(results["task1"].output, {"result": "success"})
        self.assertEqual(results["task2"].output, {"result": "success2"})
```

### Unit Tests for Execution Tracker (Work Unit 3.4)

```python
import unittest
from unittest.mock import Mock, patch, MagicMock
import os
import tempfile
import shutil
from datetime import datetime, timedelta
import json

# Import the components to test
from execution_tracker import (
    ExecutionTracker, TrackingLevel, ProgressVisualizer,
    FailureAnalyzer, AlertManager
)

# Import types from previous units
from task_selector import TaskSelector, Task, TaskStatus, TaskPriority, TaskDependency
from context_manager import ContextManager, ContextType
from parallel_execution_controller import ParallelExecutionController, ExecutionResult

class TestExecutionTracker(unittest.TestCase):
    def setUp(self):
        """Set up test fixtures."""
        self.task_selector = Mock(spec=TaskSelector)
        self.context_manager = Mock(spec=ContextManager)
        self.parallel_controller = Mock(spec=ParallelExecutionController)
        
        # Configure mocks
        self.task_selector.tasks = {
            "task1": Mock(
                id="task1",
                name="Test Task 1",
                status=TaskStatus.IN_PROGRESS,
                priority=TaskPriority.MEDIUM,
                dependencies=[],
                estimated_duration=10.0,
                estimated_resources={"cpu": 1.0},
                created_at=datetime.now(),
                updated_at=datetime.now()
            ),
            "task2": Mock(
                id="task2",
                name="Test Task 2",
                status=TaskStatus.READY,
                priority=TaskPriority.HIGH,
                dependencies=[TaskDependency("task1", "hard", "")],
                estimated_duration=20.0,
                estimated_resources={"cpu": 2.0},
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
        }
        
        self.parallel_controller.completed_tasks = {
            "completed_task": ExecutionResult(
                task_id="completed_task",
                success=True,
                output={"result": "success"},
                start_time=datetime.now() - timedelta(minutes=5),
                end_time=datetime.now() - timedelta(minutes=4),
                duration=60.0
            ),
            "failed_task": ExecutionResult(
                task_id="failed_task",
                success=False,
                output={},
                start_time=datetime.now() - timedelta(minutes=3),
                end_time=datetime.now() - timedelta(minutes=2),
                error="Test error",
                duration=60.0
            )
        }
        
        # Create temp directory for persistence
        self.temp_dir = tempfile.mkdtemp()
        
        # Create tracker
        self.tracker = ExecutionTracker(
            self.task_selector,
            self.context_manager,
            self.parallel_controller
        )
        self.tracker.persistence_path = self.temp_dir
    
    def tearDown(self):
        """Clean up after tests."""
        if self.tracker.tracking_active:
            self.tracker.stop_tracking()
        
        # Remove temp directory
        shutil.rmtree(self.temp_dir)
    
    def test_start_stop_tracking(self):
        """Test starting and stopping tracking."""
        # Start tracking
        self.tracker.start_tracking()
        
        # Verify tracking is active
        self.assertTrue(self.tracker.tracking_active)
        self.assertIsNotNone(self.tracker.tracking_start_time)
        self.assertIsNotNone(self.tracker.tracking_thread)
        self.assertTrue(self.tracker.tracking_thread.is_alive())
        
        # Verify start event was recorded
        self.assertEqual(len(self.tracker.execution_timeline), 1)
        self.assertEqual(self.tracker.execution_timeline[0]["event_type"], "tracking_started")
        
        # Stop tracking
        self.tracker.stop_tracking()
        
        # Verify tracking is stopped
        self.assertFalse(self.tracker.tracking_active)
        self.assertFalse(self.tracker.tracking_thread.is_alive())
        self.assertIsNotNone(self.tracker.tracking_end_time)
        
        # Verify stop event was recorded
        self.assertEqual(len(self.tracker.execution_timeline), 2)
        self.assertEqual(self.tracker.execution_timeline[1]["event_type"], "tracking_stopped")
    
    def test_update_task_tracking(self):
        """Test updating task tracking information."""
        # Start tracking
        self.tracker.start_tracking()
        
        # Manually call _update_task_tracking
        self.tracker._update_task_tracking()
        
        # Verify tasks were tracked
        self.assertEqual(len(self.tracker.task_tracking), 2)
        self.assertIn("task1", self.tracker.task_tracking)
        self.assertIn("task2", self.tracker.task_tracking)
        
        # Verify task1 details
        task1_tracking = self.tracker.task_tracking["task1"]
        self.assertEqual(task1_tracking["task_id"], "task1")
        self.assertEqual(task1_tracking["name"], "Test Task 1")
        self.assertEqual(task1_tracking["status"], TaskStatus.IN_PROGRESS.value)
        self.assertEqual(task1_tracking["priority"], TaskPriority.MEDIUM.value)
        
        # Verify event was recorded
        self.assertEqual(len(self.tracker.execution_timeline), 3)  # start + 2 task registrations
        
        # Stop tracking
        self.tracker.stop_tracking()
    
    def test_record_failure(self):
        """Test recording a task failure."""
        self.tracker._record_failure("failed_task", "Failed Task", "Test error")
        
        # Verify failure was recorded
        self.assertEqual(len(self.tracker.failure_records), 1)
        failure = self.tracker.failure_records[0]
        self.assertEqual(failure["task_id"], "failed_task")
        self.assertEqual(failure["task_name"], "Failed Task")
        self.assertEqual(failure["error"], "Test error")
    
    def test_get_execution_summary(self):
        """Test getting execution summary."""
        # Start tracking
        self.tracker.start_tracking()
        
        # Update task tracking manually
        self.tracker._update_task_tracking()
        
        # Add some completed tasks to task_tracking
        self.tracker.task_tracking["completed_task"] = {
            "task_id": "completed_task",
            "name": "Completed Task",
            "status": TaskStatus.COMPLETED.value,
            "success": True,
            "duration": 60.0,
            "estimated_duration": 50.0
        }
        
        self.tracker.task_tracking["failed_task"] = {
            "task_id": "failed_task",
            "name": "Failed Task",
            "status": TaskStatus.FAILED.value,
            "success": False,
            "duration": 30.0,
            "estimated_duration": 40.0
        }
        
        # Get summary
        summary = self.tracker.get_execution_summary()
        
        # Verify summary
        self.assertEqual(summary["total_tasks"], 4)
        self.assertEqual(summary["status_counts"][TaskStatus.COMPLETED.value], 1)
        self.assertEqual(summary["status_counts"][TaskStatus.FAILED.value], 1)
        self.assertEqual(summary["status_counts"][TaskStatus.IN_PROGRESS.value], 1)
        self.assertEqual(summary["status_counts"][TaskStatus.READY.value], 1)
        self.assertEqual(summary["success_rate"], 0.5)  # 1 success out of 2 completed
        
        # Verify timing stats
        self.assertEqual(summary["timing_stats"]["avg_duration"], 45.0)  # (60 + 30) / 2
        self.assertEqual(summary["timing_stats"]["min_duration"], 30.0)
        self.assertEqual(summary["timing_stats"]["max_duration"], 60.0)
        
        # Stop tracking
        self.tracker.stop_tracking()
    
    def test_save_load_tracking_data(self):
        """Test saving and loading tracking data."""
        # Start tracking
        self.tracker.start_tracking()
        
        # Update task tracking manually
        self.tracker._update_task_tracking()
        
        # Add a performance metric
        self.tracker.performance_metrics["success_rate"].append((datetime.now().isoformat(), 0.8))
        
        # Save tracking data
        base_path = self.tracker.save_tracking_data()
        
        # Verify files were created
        self.assertTrue(os.path.exists(f"{base_path}_tasks.json"))
        self.assertTrue(os.path.exists(f"{base_path}_timeline.json"))
        self.assertTrue(os.path.exists(f"{base_path}_summary.json"))
        
        # Create a new tracker
        new_tracker = ExecutionTracker(self.task_selector, self.context_manager, self.parallel_controller)
        new_tracker.persistence_path = self.temp_dir
        
        # Load tracking data
        success = new_tracker.load_tracking_data(base_path)
        
        # Verify load was successful
        self.assertTrue(success)
        
        # Verify data was loaded
        self.assertEqual(len(new_tracker.task_tracking), 2)
        self.assertIn("task1", new_tracker.task_tracking)
        self.assertIn("task2", new_tracker.task_tracking)
        self.assertEqual(len(new_tracker.execution_timeline), 3)  # start + 2 task registrations
        
        # Stop tracking
        self.tracker.stop_tracking()


class TestProgressVisualizer(unittest.TestCase):
    def setUp(self):
        """Set up test fixtures."""
        self.tracker = Mock(spec=ExecutionTracker)
        self.visualizer = ProgressVisualizer(self.tracker)
        
        # Configure mocks
        self.tracker.get_execution_summary.return_value = {
            "total_tasks": 4,
            "status_counts": {
                TaskStatus.COMPLETED.value: 1,
                TaskStatus.FAILED.value: 1,
                TaskStatus.IN_PROGRESS.value: 1,
                TaskStatus.READY.value: 1
            },
            "success_rate": 0.5,
            "timing_stats": {
                "avg_duration": 45.0,
                "min_duration": 30.0,
                "max_duration": 60.0
            }
        }
        
        self.tracker.task_tracking = {
            "task1": {
                "task_id": "task1",
                "name": "Test Task 1",
                "status": TaskStatus.COMPLETED.value,
                "success": True,
                "start_time": (datetime.now() - timedelta(minutes=10)).isoformat(),
                "end_time": (datetime.now() - timedelta(minutes=9)).isoformat(),
                "dependencies": []
            },
            "task2": {
                "task_id": "task2",
                "name": "Test Task 2",
                "status": TaskStatus.IN_PROGRESS.value,
                "success": None,
                "start_time": (datetime.now() - timedelta(minutes=5)).isoformat(),
                "end_time": None,
                "dependencies": ["task1"]
            }
        }
        
        self.tracker.get_performance_metrics.return_value = {
            "success_rate": [
                (datetime.now().isoformat(), 0.8),
                (datetime.now().isoformat(), 0.7),
                (datetime.now().isoformat(), 0.6)
            ]
        }
        
        self.tracker.get_failure_analysis.return_value = {
            "count": 1,
            "common_errors": [{"type": "Test error", "count": 1}],
            "failure_rate": 0.25
        }
    
    def test_visualize_task_status_counts(self):
        """Test visualizing task status counts."""
        visualization = self.visualizer._visualize_task_status_counts()
        
        # Verify visualization structure
        self.assertEqual(visualization["type"], "pie_chart")
        self.assertEqual(visualization["title"], "Task Status Distribution")
        self.assertEqual(len(visualization["data"]), 4)
        self.assertEqual(visualization["total"], 4)
    
    def test_visualize_task_timeline(self):
        """Test visualizing task timeline."""
        visualization = self.visualizer._visualize_task_timeline()
        
        # Verify visualization structure
        self.assertEqual(visualization["type"], "gantt_chart")
        self.assertEqual(visualization["title"], "Task Execution Timeline")
        self.assertEqual(len(visualization["data"]), 1)  # Only task1 has both start and end times
        self.assertEqual(visualization["data"][0]["task_id"], "task1")
    
    def test_visualize_task_dependencies(self):
        """Test visualizing task dependencies."""
        visualization = self.visualizer._visualize_task_dependencies()
        
        # Verify visualization structure
        self.assertEqual(visualization["type"], "dependency_graph")
        self.assertEqual(visualization["title"], "Task Dependencies")
        self.assertEqual(len(visualization["nodes"]), 2)
        self.assertEqual(len(visualization["edges"]), 1)
        self.assertEqual(visualization["edges"][0]["source"], "task1")
        self.assertEqual(visualization["edges"][0]["target"], "task2")
    
    def test_visualize_performance_metrics(self):
        """Test visualizing performance metrics."""
        visualization = self.visualizer._visualize_performance_metrics(metric_name="success_rate")
        
        # Verify visualization structure
        self.assertEqual(visualization["type"], "time_series")
        self.assertEqual(visualization["title"], "Performance Metrics: success_rate")
        self.assertEqual(len(visualization["series"]), 1)
        self.assertEqual(visualization["series"][0]["name"], "success_rate")
        self.assertEqual(len(visualization["series"][0]["data"]), 3)
    
    def test_create_progress_report(self):
        """Test creating a comprehensive progress report."""
        report = self.visualizer.create_progress_report()
        
        # Verify report structure
        self.assertIn("summary", report)
        self.assertIn("visualizations", report)
        self.assertIn("failure_analysis", report)
        self.assertIn("generated_at", report)
        
        # Verify visualizations
        self.assertEqual(len(report["visualizations"]), 5)
        self.assertIn("status_distribution", report["visualizations"])
        self.assertIn("success_failure", report["visualizations"])
        self.assertIn("timeline", report["visualizations"])
        self.assertIn("dependencies", report["visualizations"])
        self.assertIn("performance", report["visualizations"])
    
    def test_save_progress_report(self):
        """Test saving a progress report."""
        # Create temp directory
        temp_dir = tempfile.mkdtemp()
        
        try:
            # Save report
            output_path = os.path.join(temp_dir, "report.json")
            saved_path = self.visualizer.save_progress_report(output_path)
            
            # Verify file was created
            self.assertTrue(os.path.exists(saved_path))
            
            # Verify file content
            with open(saved_path, 'r') as f:
                report = json.load(f)
                self.assertIn("summary", report)
                self.assertIn("visualizations", report)
        
        finally:
            # Clean up
            shutil.rmtree(temp_dir)


class TestFailureAnalyzer(unittest.TestCase):
    def setUp(self):
        """Set up test fixtures."""
        self.tracker = Mock(spec=ExecutionTracker)
        self.analyzer = FailureAnalyzer(self.tracker)
        
        # Configure mocks
        self.tracker.failure_records = [
            {
                "task_id": "task1",
                "task_name": "Memory Task",
                "timestamp": datetime.now().isoformat(),
                "error": "Out of memory error",
                "context": {}
            },
            {
                "task_id": "task2",
                "task_name": "Timeout Task",
                "timestamp": datetime.now().isoformat(),
                "error": "Task timed out after 60 seconds",
                "context": {}
            },
            {
                "task_id": "task3",
                "task_name": "Dependency Task",
                "timestamp": datetime.now().isoformat(),
                "error": "Required dependency not available",
                "context": {}
            },
            {
                "task_id": "task4",
                "task_name": "Memory Task 2",
                "timestamp": datetime.now().isoformat(),
                "error": "Out of memory error",
                "context": {}
            }
        ]
    
    def test_analyze_failures(self):
        """Test analyzing failures."""
        analysis = self.analyzer.analyze_failures()
        
        # Verify analysis structure
        self.assertEqual(analysis["count"], 4)
        self.assertIn("patterns", analysis)
        self.assertIn("categories", analysis)
        self.assertIn("tasks", analysis)
        self.assertIn("timeline", analysis)
        
        # Verify pattern detection
        self.assertEqual(analysis["patterns"]["resource_exhaustion"], 2)  # 2 memory errors
        self.assertEqual(analysis["patterns"]["timeout"], 1)  # 1 timeout error
        self.assertEqual(analysis["patterns"]["dependency_failure"], 1)  # 1 dependency error
        
        # Verify task counts
        self.assertEqual(analysis["tasks"]["Memory Task"], 1)
        self.assertEqual(analysis["tasks"]["Memory Task 2"], 1)
        self.assertEqual(analysis["tasks"]["Timeout Task"], 1)
        self.assertEqual(analysis["tasks"]["Dependency Task"], 1)
    
    def test_get_recurring_failures(self):
        """Test identifying recurring failures."""
        recurring = self.analyzer.get_recurring_failures()
        
        # Verify recurring failures
        self.assertEqual(len(recurring), 1)  # Only the memory error occurs in multiple tasks
        self.assertEqual(recurring[0]["count"], 2)
        self.assertEqual(recurring[0]["task_count"], 2)
        

class TestAlertManager(unittest.TestCase):
    def setUp(self):
        """Set up test fixtures."""
        self.tracker = Mock(spec=ExecutionTracker)
        self.alert_manager = AlertManager(self.tracker)
        
        # Configure mocks
        self.tracker.get_execution_summary.return_value = {
            "total_tasks": 10,
            "success_rate": 0.6,  # Below threshold of 0.7
            "execution_duration": 4000,  # Above threshold of 3600
            "status_counts": {
                TaskStatus.COMPLETED.value: 6,
                TaskStatus.FAILED.value: 4
            }
        }
        
        self.tracker.failure_records = [{"error": "test error"}] * 6  # Above threshold of 5
    
    def test_check_alert_conditions(self):
        """Test checking alert conditions."""
        # Create a mock alert handler
        alert_handler = Mock()
        self.alert_manager.register_alert_handler("critical", alert_handler)
        
        # Check alert conditions
        self.alert_manager.check_alert_conditions()
        
        # Verify alerts were triggered
        self.assertGreaterEqual(len(self.alert_manager.alert_history), 1)
        self.assertIn("low_success_rate", self.alert_manager.alert_counters)
        self.assertIn("high_failure_count", self.alert_manager.alert_counters)
        self.assertIn("long_execution_duration", self.alert_manager.alert_counters)
        
        # Verify alert handler was called
        self.assertTrue(alert_handler.called)
    
    def test_handle_notification(self):
        """Test handling notifications from tracker."""
        # Create a notification
        notification = {
            "type": "success_rate_low",
            "timestamp": datetime.now().isoformat(),
            "data": {
                "current_rate": 0.5,
                "threshold": 0.7
            }
        }
        
        # Create a mock alert handler
        alert_handler = Mock()
        self.alert_manager.register_alert_handler("critical", alert_handler)
        
        # Handle notification
        self.alert_manager._handle_notification(notification)
        
        # Verify alert was triggered
        self.assertEqual(len(self.alert_manager.alert_history), 1)
        self.assertEqual(self.alert_manager.alert_history[0]["type"], "critical")
        
        # Verify alert handler was called
        alert_handler.assert_called_once()
    
    def test_alert_suppression(self):
        """Test alert suppression to avoid alert floods."""
        # Set a short suppression interval for testing
        self.alert_manager.suppression_intervals["low_success_rate"] = 1  # 1 second
        
        # Check alert conditions to trigger initial alerts
        self.alert_manager.check_alert_conditions()
        initial_count = self.alert_manager.alert_counters["low_success_rate"]
        
        # Check again immediately - should be suppressed
        self.alert_manager.check_alert_conditions()
        suppressed_count = self.alert_manager.alert_counters["low_success_rate"]
        
        # Verify count didn't change due to suppression
        self.assertEqual(initial_count, suppressed_count)
        
        # Wait for suppression to expire
        time.sleep(1.5)
        
        # Check again - should trigger new alert
        self.alert_manager.check_alert_conditions()
        new_count = self.alert_manager.alert_counters["low_success_rate"]
        
        # Verify count increased
        self.assertGreater(new_count, suppressed_count)
    
    def test_get_alert_summary(self):
        """Test getting alert summary."""
        # Trigger some alerts
        self.alert_manager.check_alert_conditions()
        
        # Get summary
        summary = self.alert_manager.get_alert_summary()
        
        # Verify summary structure
        self.assertIn("total_alerts", summary)
        self.assertIn("type_counts", summary)
        self.assertIn("rule_counters", summary)
        
        # Verify counts
        self.assertGreater(summary["total_alerts"], 0)
        self.assertIn("critical", summary["type_counts"])
        self.assertIn("warning", summary["type_counts"])
        self.assertIn("info", summary["type_counts"])
        
        # Verify rule counters
        self.assertIn("low_success_rate", summary["rule_counters"])
        self.assertIn("high_failure_count", summary["rule_counters"])
        self.assertIn("long_execution_duration", summary["rule_counters"])
    
    def test_clear_alerts(self):
        """Test clearing alerts."""
        # Trigger some alerts
        self.alert_manager.check_alert_conditions()
        
        # Verify alerts exist
        self.assertGreater(len(self.alert_manager.alert_history), 0)
        
        # Clear alerts
        cleared_count = self.alert_manager.clear_alerts()
        
        # Verify alerts were cleared
        self.assertEqual(len(self.alert_manager.alert_history), 0)
        self.assertGreater(cleared_count, 0)
        
        # Trigger more alerts
        self.alert_manager.check_alert_conditions()
        
        # Clear alerts older than future time (should keep all)
        future_time = datetime.now() + timedelta(hours=1)
        cleared_count = self.alert_manager.clear_alerts(older_than=future_time)
        
        # Verify no alerts were cleared
        self.assertGreater(len(self.alert_manager.alert_history), 0)
        self.assertEqual(cleared_count, 0)
```

## Integration Example: Putting it All Together

Below is an example of how to integrate the Parallel Execution Controller (3.3) and Execution Tracker (3.4) with the Task Selector (3.1) and Context Manager (3.2) components:

```python
from datetime import datetime
import logging
import time
import threading
import uuid
import os

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("execution_engine")

# Create necessary components
context_manager = ContextManager()
resource_manager = ResourceManager()  # Assume this is implemented
task_selector = TaskSelector(context_manager, resource_manager)

# Connect components
parallel_controller = ParallelExecutionController(task_selector, context_manager, resource_manager)
execution_tracker = ExecutionTracker(task_selector, context_manager, parallel_controller)
progress_visualizer = ProgressVisualizer(execution_tracker)
failure_analyzer = FailureAnalyzer(execution_tracker)
alert_manager = AlertManager(execution_tracker)

# Register alert handler
def handle_critical_alert(alert):
    logger.critical(f"CRITICAL ALERT: {alert['data']['message']}")
    # Could send email, notification, etc.

alert_manager.register_alert_handler("critical", handle_critical_alert)

# Example tasks
def create_example_tasks():
    tasks = []
    
    # Root task
    root_task = Task(
        id="task_root",
        name="Initialize Execution",
        description="Set up initial state for execution",
        priority=TaskPriority.HIGH,
        status=TaskStatus.PENDING,
        dependencies=[],
        estimated_duration=10.0,
        estimated_resources={"cpu": 1.0, "memory": 512},
        context_requirements=[],
        created_at=datetime.now(),
        updated_at=datetime.now(),
        tags=["initialization"],
        metadata={}
    )
    tasks.append(root_task)
    
    # Level 1 tasks
    for i in range(3):
        task = Task(
            id=f"task_l1_{i}",
            name=f"Level 1 Task {i}",
            description=f"Task at level 1, position {i}",
            priority=TaskPriority.MEDIUM,
            status=TaskStatus.PENDING,
            dependencies=[TaskDependency("task_root", "hard", "")],
            estimated_duration=15.0,
            estimated_resources={"cpu": 1.0, "memory": 1024},
            context_requirements=["initialization_data"],
            created_at=datetime.now(),
            updated_at=datetime.now(),
            tags=["level_1"],
            metadata={}
        )
        tasks.append(task)
    
    # Level 2 tasks
    for i in range(5):
        parent_idx = i % 3
        task = Task(
            id=f"task_l2_{i}",
            name=f"Level 2 Task {i}",
            description=f"Task at level 2, position {i}",
            priority=TaskPriority.MEDIUM,
            status=TaskStatus.PENDING,
            dependencies=[TaskDependency(f"task_l1_{parent_idx}", "hard", "")],
            estimated_duration=20.0,
            estimated_resources={"cpu": 2.0, "memory": 1536},
            context_requirements=[f"l1_output_{parent_idx}"],
            created_at=datetime.now(),
            updated_at=datetime.now(),
            tags=["level_2"],
            metadata={}
        )
        tasks.append(task)
    
    return tasks

# Mock task execution function
def execute_task_logic(task, context):
    """Simulated task execution logic."""
    task_id = task.id
    logger.info(f"Executing task {task.name} ({task_id})")
    
    # Simulate work with sleep
    sleep_time = min(task.estimated_duration * 0.1, 2.0)  # Scale down for example
    time.sleep(sleep_time)
    
    # For example purposes, fail some tasks randomly
    import random
    if random.random() < 0.2 and "l2" in task_id:  # 20% chance for level 2 tasks
        raise Exception(f"Simulated failure in task {task_id}")
    
    # Generate output based on task level
    if task_id == "task_root":
        return {
            "initialization_data": {
                "timestamp": datetime.now().isoformat(),
                "config": {"max_workers": 3, "timeout": 30},
                "status": "initialized"
            }
        }
    elif task_id.startswith("task_l1_"):
        idx = int(task_id.split("_")[-1])
        return {
            f"l1_output_{idx}": {
                "processed_items": random.randint(100, 500),
                "success_rate": random.uniform(0.8, 1.0),
                "duration": sleep_time
            }
        }
    else:  # Level 2 task
        idx = int(task_id.split("_")[-1])
        return {
            f"l2_output_{idx}": {
                "result_count": random.randint(10, 50),
                "accuracy": random.uniform(0.7, 0.99),
                "duration": sleep_time
            }
        }

# Main execution function
def run_execution_example():
    # Start tracking
    execution_tracker.start_tracking()
    
    try:
        # Create and register tasks
        tasks = create_example_tasks()
        for task in tasks:
            task_selector.register_task(task)
        
        logger.info(f"Registered {len(tasks)} tasks")
        
        # Set execution mode
        parallel_controller.set_execution_mode(ExecutionMode.PARALLEL_WITH_LIMIT)
        parallel_controller.set_max_workers(3)
        
        # Inject our task execution logic
        parallel_controller._execute_task_logic = execute_task_logic
        
        # Execute the task tree
        logger.info("Starting task tree execution")
        results = parallel_controller.execute_task_tree("task_root")
        logger.info(f"Task tree execution completed with {len(results)} results")
        
        # Get execution summary
        summary = execution_tracker.get_execution_summary()
        logger.info(f"Execution summary: {summary}")
        
        # Analyze failures if any
        failure_analysis = failure_analyzer.analyze_failures()
        if failure_analysis["count"] > 0:
            logger.warning(f"Failures detected: {failure_analysis['count']}")
            mitigations = failure_analyzer.suggest_failure_mitigations()
            logger.info(f"Suggested mitigations: {mitigations}")
        
        # Generate report
        report_path = os.path.join("reports", f"execution_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
        os.makedirs(os.path.dirname(report_path), exist_ok=True)
        progress_visualizer.save_progress_report(report_path)
        logger.info(f"Execution report saved to {report_path}")
        
    except Exception as e:
        logger.error(f"Error during execution: {str(e)}")
        
    finally:
        # Stop tracking
        execution_tracker.stop_tracking()

if __name__ == "__main__":
    run_execution_example()
```

## System Integration and Connections

The Parallel Execution Controller (3.3) and Execution Tracker (3.4) components integrate with the Task Selector (3.1) and Context Manager (3.2) components to form a comprehensive Execution Engine. Here's how they all fit together:

1. **Task Selector (3.1)** - Manages tasks and their dependencies, prioritizing them for execution. It handles the dependency resolution and task state management.

2. **Context Manager (3.2)** - Manages execution context across tasks, ensuring relevant information is propagated and validated.

3. **Parallel Execution Controller (3.3)** - Orchestrates the actual execution of tasks, handling parallel processing, resource allocation, and result aggregation.

4. **Execution Tracker (3.4)** - Monitors task execution, collects metrics, detects failures, and generates reports and alerts.

### Flow of Execution

1. The Task Selector determines which tasks are ready for execution based on their dependencies.

2. The Parallel Execution Controller takes these tasks and executes them concurrently, respecting resource constraints.

3. During execution, the Context Manager ensures that each task has access to the context it needs and propagates results to subsequent tasks.

4. The Execution Tracker monitors the entire process, recording events, tracking progress, and detecting issues.

5. Visualizations and reports are generated by the Progress Visualizer to provide insights into the execution.

6. Failures are analyzed by the Failure Analyzer to identify patterns and suggest mitigations.

7. Critical issues trigger alerts via the Alert Manager, which can notify appropriate stakeholders.

### Connection to Other System Components

These Execution Engine components connect to the broader Self-Aware System as follows:

1. **Planning Engine Connection**: The Planning Engine (Phase 2) provides the task structure and dependencies that the Execution Engine processes. Work Unit 2.5 (Planning Engine Integration) feeds directly into the Task Selector (3.1).

2. **Cognitive Loop Connection**: The Execution Engine is part of the cognitive loop (Phase 6), which coordinates the planning, execution, and self-modification cycles. The Execution Tracker (3.4) provides critical feedback to guide future planning.

3. **Self-Modification Connection**: The Execution Engine's performance metrics and failure analyses inform the Self-Modification Engine (Phase 4), helping it generate improvements to the system.

4. **Observability Connection**: The Execution Tracker (3.4) provides data to the Observability Layer (Phase 5) for comprehensive system monitoring and intervention.

By implementing these components, we create a robust Execution Engine that can efficiently process complex task structures while adapting to changing conditions and learning from execution patterns. The engine provides both high performance through parallel execution and high reliability through comprehensive tracking and failure handling.
