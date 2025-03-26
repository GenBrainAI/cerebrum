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

# Import dependencies from other modules
from server.execution_engine.task_selector import TaskSelector, Task, TaskStatus, TaskPriority, TaskDependency
from server.execution_engine.context_manager import ContextManager, ContextType

logger = logging.getLogger(__name__)

class ExecutionMode(Enum):
    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"
    PARALLEL_WITH_LIMIT = "parallel_with_limit"

@dataclass
class ExecutionResult:
    task_id: str
    success: bool
    output: Dict[str, Any] = field(default_factory=dict)
    start_time: datetime = field(default_factory=datetime.now)
    end_time: datetime = field(default_factory=datetime.now)
    error: Optional[str] = None
    duration: float = 0
    resource_usage: Dict[str, float] = field(default_factory=dict)

    def __post_init__(self):
        # Ensure output is a dictionary
        if self.output is None:
            self.output = {}
        elif not isinstance(self.output, dict):
            self.output = {"result": self.output}
        
        # Validate dictionary keys to ensure they are hashable
        for key in list(self.output.keys()):
            if not isinstance(key, str):
                # Convert unhashable keys to strings
                str_key = str(key)
                self.output[str_key] = self.output.pop(key)
        
        # Calculate duration if not provided
        if not self.duration and self.start_time and self.end_time:
            self.duration = (self.end_time - self.start_time).total_seconds()
        
        # Initialize resource usage if None
        if self.resource_usage is None:
            self.resource_usage = {}

class ResourceCoordinator:
    """
    Manages resource allocation and release for parallel task execution.
    Ensures that tasks don't exceed available system resources.
    """
    
    def __init__(self, available_resources: Dict[str, float]):
        self.available_resources = available_resources.copy()
        self.allocated_resources = {}  # task_id -> Dict[resource_type, amount]
        self.lock = threading.RLock()  # Use RLock to allow reentrant locking
        self._shutdown = False
        logger.info(f"Resource coordinator initialized with resources: {available_resources}")
    
    def can_allocate(self, task_id: str, required_resources: Dict[str, float]) -> bool:
        """Check if the required resources can be allocated."""
        if self._shutdown:
            return False
            
        # No lock needed here as this is called within allocate_resources
        for resource_type, amount in required_resources.items():
            if resource_type not in self.available_resources:
                logger.warning(f"Resource type {resource_type} not available")
                return False
            if self.available_resources[resource_type] < amount:
                logger.debug(f"Insufficient {resource_type} resources: " 
                            f"required {amount}, available {self.available_resources[resource_type]}")
                return False
        return True
    
    def allocate_resources(self, task_id: str, required_resources: Dict[str, float]) -> bool:
        """Allocate resources for a task."""
        if self._shutdown:
            return False
            
        with self.lock:
            # Check availability and allocate in one atomic operation
            if not self.can_allocate(task_id, required_resources):
                return False
            
            self.allocated_resources[task_id] = {}
            for resource_type, amount in required_resources.items():
                self.available_resources[resource_type] -= amount
                self.allocated_resources[task_id][resource_type] = amount
            
            logger.info(f"Allocated resources for task {task_id}: {required_resources}")
            return True
    
    def release_resources(self, task_id: str) -> Dict[str, float]:
        """Release resources allocated to a task."""
        released = {}
        with self.lock:
            if task_id not in self.allocated_resources:
                logger.warning(f"No resources allocated for task {task_id}")
                return {}
            
            released = self.allocated_resources[task_id].copy()  # Make a copy before modifying
            for resource_type, amount in released.items():
                self.available_resources[resource_type] += amount
            
            del self.allocated_resources[task_id]
            logger.info(f"Released resources for task {task_id}: {released}")
        
        return released
    
    def release_all_resources(self) -> None:
        """Release all allocated resources."""
        with self.lock:
            task_ids = list(self.allocated_resources.keys())
            for task_id in task_ids:
                self.release_resources(task_id)
            logger.info("Released all allocated resources")
    
    def shutdown(self) -> None:
        """Shutdown the resource coordinator and release all resources."""
        self._shutdown = True
        self.release_all_resources()
        logger.info("Resource coordinator shut down")
    
    def get_available_resources(self) -> Dict[str, float]:
        """Get currently available resources."""
        with self.lock:
            return self.available_resources.copy()
    
    def get_allocated_resources(self) -> Dict[str, Dict[str, float]]:
        """Get all allocated resources."""
        with self.lock:
            return self.allocated_resources.copy()

class ResultAggregator:
    """
    Manages the aggregation of results from multiple tasks.
    Supports different aggregation methods for combining results.
    """
    
    def __init__(self, execution_controller):
        self.execution_controller = execution_controller
        self.aggregation_methods = {
            "sum": self._aggregate_sum,
            "average": self._aggregate_average,
            "min": self._aggregate_min,
            "max": self._aggregate_max,
            "concat": self._aggregate_concat,
            "merge": self._aggregate_merge,
            "first": self._aggregate_first,
            "last": self._aggregate_last,
            "count": self._aggregate_count,
        }
    
    def aggregate_results(self, task_ids: List[str], result_key: str, method: str) -> Any:
        """Aggregate results from multiple tasks using the specified method."""
        if method not in self.aggregation_methods:
            raise ValueError(f"Unknown aggregation method: {method}")
        
        task_results = []
        for task_id in task_ids:
            result = self.execution_controller.get_execution_result(task_id)
            if result and result.success and result_key in result.output:
                task_results.append(result.output[result_key])
        
        if not task_results:
            logger.warning(f"No results to aggregate for key {result_key}")
            return None
        
        logger.debug(f"Aggregating {len(task_results)} results using method {method}")
        return self.aggregation_methods[method](task_results)
    
    def create_aggregated_result(self, task_ids: List[str], aggregations: Dict[str, Tuple[str, str]]) -> Dict[str, Any]:
        """Create a result with multiple aggregations."""
        result = {}
        for output_key, (input_key, method) in aggregations.items():
            result[output_key] = self.aggregate_results(task_ids, input_key, method)
        return result
    
    def _aggregate_sum(self, values: List[Any]) -> Any:
        """Sum values."""
        try:
            return sum(values)
        except TypeError:
            logger.error("Cannot sum non-numeric values")
            return None
    
    def _aggregate_average(self, values: List[Any]) -> Any:
        """Calculate average of values."""
        try:
            return sum(values) / len(values) if values else None
        except TypeError:
            logger.error("Cannot average non-numeric values")
            return None
    
    def _aggregate_min(self, values: List[Any]) -> Any:
        """Get minimum value."""
        try:
            return min(values)
        except (TypeError, ValueError):
            logger.error("Cannot find minimum in incomparable values")
            return None
    
    def _aggregate_max(self, values: List[Any]) -> Any:
        """Get maximum value."""
        try:
            return max(values)
        except (TypeError, ValueError):
            logger.error("Cannot find maximum in incomparable values")
            return None
    
    def _aggregate_concat(self, values: List[Any]) -> Any:
        """Concatenate values."""
        try:
            if all(isinstance(v, list) for v in values):
                result = []
                for v in values:
                    result.extend(v)
                return result
            elif all(isinstance(v, str) for v in values):
                return "".join(values)
            else:
                return values
        except Exception as e:
            logger.error(f"Error concatenating values: {str(e)}")
            return values
    
    def _aggregate_merge(self, values: List[Any]) -> Any:
        """Merge dictionaries."""
        try:
            if all(isinstance(v, dict) for v in values):
                result = {}
                for v in values:
                    result.update(v)
                return result
            else:
                return values
        except Exception as e:
            logger.error(f"Error merging dictionaries: {str(e)}")
            return values
    
    def _aggregate_first(self, values: List[Any]) -> Any:
        """Get first value."""
        return values[0] if values else None
    
    def _aggregate_last(self, values: List[Any]) -> Any:
        """Get last value."""
        return values[-1] if values else None
    
    def _aggregate_count(self, values: List[Any]) -> Any:
        """Count values."""
        return len(values)

class ParallelExecutionController:
    """
    Manages the parallel execution of tasks, handling resource allocation,
    dependency resolution, and execution coordination.
    """
    
    def __init__(self, task_selector: TaskSelector, context_manager: ContextManager, 
                resource_manager, max_workers: int = 4):
        self.task_selector = task_selector
        self.context_manager = context_manager
        self.resource_manager = resource_manager
        self.max_workers = max_workers
        self.execution_results = {}  # task_id -> ExecutionResult
        self.task_executors = {}  # task_id -> executor function
        self.running_tasks = set()  # Set of running task_ids
        self.results_lock = threading.RLock()  # Use RLock to allow reentrant locking
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=max_workers)
        self.result_aggregator = ResultAggregator(self)
        logger.info(f"Parallel execution controller initialized with {max_workers} workers")
    
    def register_task_executor(self, task_id: str, executor_func: Callable[[Dict[str, Any]], Dict[str, Any]]) -> None:
        """Register an executor function for a task."""
        self.task_executors[task_id] = executor_func
        logger.debug(f"Registered executor for task {task_id}")
    
    def get_execution_result(self, task_id: str) -> Optional[ExecutionResult]:
        """Get the execution result for a task."""
        with self.results_lock:
            return self.execution_results.get(task_id)
    
    def execute_task(
        self,
        task_id: str,
        execution_mode: ExecutionMode = ExecutionMode.SEQUENTIAL,
        context_override: Dict[str, Any] = None,
        context: Dict[str, Any] = None
    ) -> Optional[ExecutionResult]:
        """
        Execute a single task.
        
        Args:
            task_id: The ID of the task to execute.
            execution_mode: The execution mode to use.
            context_override: Optional context data to override task context.
            context: Optional context data for the task.
            
        Returns:
            Optional[ExecutionResult]: The result of the task execution, or None if execution fails.
        """
        task = self.task_selector.get_task_by_id(task_id)
        if not task:
            logger.error(f"Task {task_id} not found")
            return None
        
        if task_id not in self.task_executors:
            logger.error(f"No executor registered for task {task_id}")
            return None
        
        # Check if task is already running
        with self.results_lock:
            if task_id in self.running_tasks:
                logger.warning(f"Task {task_id} is already running")
                return None
            self.running_tasks.add(task_id)
        
        logger.info(f"Executing task {task_id} in {execution_mode.value} mode")
        
        try:
            # Prepare context
            task_context = context if context is not None else context_override if context_override is not None else self.context_manager.prepare_task_context(task_id)
            
            # Try to allocate resources if task has estimated resources
            if task.estimated_resources:
                try:
                    if not self.resource_manager.allocate_resources(task_id, task.estimated_resources):
                        logger.warning(f"Could not allocate resources for task {task_id}")
                        # Create a failure result
                        result = ExecutionResult(
                            task_id=task_id,
                            success=False,
                            output={"error": "Failed to allocate resources"},
                            start_time=datetime.now(),
                            end_time=datetime.now(),
                            error="Resource allocation failed",
                            duration=0,
                            resource_usage={}
                        )
                        with self.results_lock:
                            self.execution_results[task_id] = result
                            self.running_tasks.remove(task_id)
                        return result
                except Exception as e:
                    logger.error(f"Error allocating resources for task {task_id}: {str(e)}")
                    # Continue execution with no resources if allocation fails
            
            # Mark task as in progress
            self.task_selector.update_task_status(task_id, TaskStatus.IN_PROGRESS)
            
            # Execute based on mode
            if execution_mode == ExecutionMode.SEQUENTIAL:
                result = self._execute_sequential(task_id, task_context)
            else:
                result = self._execute_parallel(task_id, task_context)
            
            return result
        except Exception as e:
            logger.error(f"Error in execute_task for {task_id}: {str(e)}")
            # Create a failure result
            result = ExecutionResult(
                task_id=task_id,
                success=False,
                output={"error": str(e)},
                start_time=datetime.now(),
                end_time=datetime.now(),
                error=str(e),
                duration=0,
                resource_usage={}
            )
            with self.results_lock:
                self.execution_results[task_id] = result
                self.running_tasks.remove(task_id)
            return result
    
    def _execute_sequential(
        self, task_id: str, context: Dict[str, Any] = None
    ) -> ExecutionResult:
        """
        Execute a task sequentially.
        
        Args:
            task_id: The ID of the task to execute.
            context: Optional context data for the task.
            
        Returns:
            ExecutionResult: The result of the task execution.
        """
        if task_id not in self.task_executors:
            raise ValueError(f"No executor registered for task {task_id}")
        
        executor = self.task_executors[task_id]
        resources_allocated = {}
        
        try:
            start_time = datetime.now()
            
            # Allocate resources if needed
            if hasattr(executor, "resource_requirements") and self.resource_manager:
                requirements = executor.resource_requirements()
                if requirements:
                    resources_allocated = self.resource_manager.allocate_resources(task_id, requirements)
            
            # Execute the task
            try:
                raw_output = executor(task_id, context)
                success = True
                error = None
                
                # Standardize output format
                if isinstance(raw_output, dict) and "result" in raw_output:
                    output = raw_output
                else:
                    output = {"result": raw_output}
                
            except Exception as e:
                logger.error(f"Error executing task {task_id}: {str(e)}")
                success = False
                output = {}
                error = str(e)
            
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            # Free allocated resources
            if resources_allocated and self.resource_manager:
                self.resource_manager.free_resources(task_id, resources_allocated)
            
            # Create and return execution result
            result = ExecutionResult(
                task_id=task_id,
                success=success,
                output=output,
                error=error,
                start_time=start_time,
                end_time=end_time,
                duration=duration,
                resource_usage=resources_allocated
            )
            
            # Update task status in task_selector if available
            if hasattr(self, 'task_selector') and self.task_selector:
                new_status = TaskStatus.COMPLETED if success else TaskStatus.FAILED
                self.task_selector.update_task_status(task_id, new_status)
                if success:
                    self.task_selector.update_dependent_tasks(task_id)
            
            return result
            
        except Exception as e:
            # Free allocated resources in case of error
            if resources_allocated and self.resource_manager:
                self.resource_manager.free_resources(task_id, resources_allocated)
            
            logger.error(f"Failed to execute task {task_id}: {str(e)}")
            
            result = ExecutionResult(
                task_id=task_id,
                success=False,
                output={},
                error=f"Error executing task: {str(e)}",
                start_time=datetime.now(),
                end_time=datetime.now(),
                resource_usage={}
            )
            
            # Update task status to FAILED
            if hasattr(self, 'task_selector') and self.task_selector:
                self.task_selector.update_task_status(task_id, TaskStatus.FAILED)
            
            return result
    
    def _execute_parallel(self, task_id: str, task_context: Dict[str, Any]) -> None:
        """Submit a task for parallel execution."""
        future = self.executor.submit(self._execute_task_wrapper, task_id, task_context)
        future.add_done_callback(self._task_completion_callback)
        return None
    
    def _execute_task_wrapper(self, task_id: str, task_context: Dict[str, Any]) -> ExecutionResult:
        """Wrapper function for task execution in parallel mode."""
        return self._execute_sequential(task_id, task_context)
    
    def _task_completion_callback(self, future):
        """Callback for task completion in parallel mode."""
        try:
            future.result()
        except Exception as e:
            logger.error(f"Error in task execution: {str(e)}")
    
    def execute_tasks(self, task_ids: List[str], 
                     execution_mode: ExecutionMode = ExecutionMode.PARALLEL,
                     max_concurrent: int = None) -> Dict[str, ExecutionResult]:
        """Execute multiple tasks with the specified execution mode."""
        if not task_ids:
            logger.warning("No tasks to execute")
            return {}
        
        logger.info(f"Executing {len(task_ids)} tasks in {execution_mode.value} mode")
        
        # Use Sequential mode for single task
        if len(task_ids) == 1 and execution_mode != ExecutionMode.SEQUENTIAL:
            result = self.execute_task(task_ids[0], ExecutionMode.SEQUENTIAL)
            return {task_ids[0]: result} if result else {}
        
        # Use parallel mode with limit if specified
        if execution_mode == ExecutionMode.PARALLEL_WITH_LIMIT and max_concurrent:
            worker_limit = min(max_concurrent, self.max_workers)
        else:
            worker_limit = self.max_workers
        
        # Sequential execution
        if execution_mode == ExecutionMode.SEQUENTIAL:
            results = {}
            for task_id in task_ids:
                result = self.execute_task(task_id, ExecutionMode.SEQUENTIAL)
                if result:
                    results[task_id] = result
            return results
        
        # Parallel execution (with or without limit)
        futures = {}
        semaphore = threading.Semaphore(worker_limit)
        
        for task_id in task_ids:
            task = self.task_selector.get_task_by_id(task_id)
            if not task:
                logger.warning(f"Task {task_id} not found")
                continue
            
            if task_id not in self.task_executors:
                logger.warning(f"No executor registered for task {task_id}")
                continue
            
            # Acquire semaphore before submitting task
            semaphore.acquire()
            
            # Submit task
            future = self.executor.submit(self._execute_with_semaphore_release, 
                                         task_id, ExecutionMode.SEQUENTIAL, semaphore)
            futures[future] = task_id
        
        # Wait for all tasks to complete
        concurrent.futures.wait(futures.keys())
        
        # Collect results
        results = {}
        with self.results_lock:
            for task_id in task_ids:
                if task_id in self.execution_results:
                    results[task_id] = self.execution_results[task_id]
        
        return results
    
    def _execute_with_semaphore_release(self, task_id: str, mode: ExecutionMode, semaphore: threading.Semaphore) -> ExecutionResult:
        """Execute a task and release the semaphore when done."""
        try:
            # Prepare context
            task_context = self.context_manager.prepare_task_context(task_id)
            return self._execute_sequential(task_id, task_context)
        finally:
            semaphore.release()
    
    def wait_for_completion(self, task_ids: List[str], timeout: float = None) -> bool:
        """Wait for the completion of specified tasks."""
        start_time = time.time()
        while True:
            with self.results_lock:
                if all(task_id in self.execution_results and task_id not in self.running_tasks for task_id in task_ids):
                    return True
            
            if timeout is not None and time.time() - start_time > timeout:
                logger.warning(f"Timeout waiting for tasks to complete")
                return False
            
            time.sleep(0.1)
    
    def stop_task(self, task_id: str) -> bool:
        """Stop a running task (best effort)."""
        with self.results_lock:
            if task_id not in self.running_tasks:
                logger.warning(f"Task {task_id} is not running")
                return False
        
        # We cannot forcibly stop a thread, so just release resources and mark as failed
        logger.info(f"Stopping task {task_id}")
        self.resource_manager.release_resources(task_id)
        self.task_selector.update_task_status(task_id, TaskStatus.FAILED)
        
        with self.results_lock:
            if task_id in self.running_tasks:
                self.running_tasks.remove(task_id)
            
            # Create a failed result if not already present
            if task_id not in self.execution_results:
                self.execution_results[task_id] = ExecutionResult(
                    task_id=task_id,
                    success=False,
                    output={"error": "Task execution stopped"},
                    start_time=datetime.now(),
                    end_time=datetime.now(),
                    error="Task execution stopped"
                )
        
        return True
    
    def stop_all_tasks(self) -> List[str]:
        """Stop all running tasks (best effort)."""
        with self.results_lock:
            running = list(self.running_tasks)
        
        stopped = []
        for task_id in running:
            if self.stop_task(task_id):
                stopped.append(task_id)
        
        logger.info(f"Stopped {len(stopped)} tasks")
        return stopped
    
    def get_running_tasks(self) -> List[str]:
        """Get IDs of currently running tasks."""
        with self.results_lock:
            return list(self.running_tasks)
    
    def clear_results(self, task_ids: List[str] = None) -> None:
        """Clear execution results for specified tasks or all tasks."""
        with self.results_lock:
            if task_ids is None:
                self.execution_results = {}
                logger.info("Cleared all execution results")
            else:
                for task_id in task_ids:
                    if task_id in self.execution_results:
                        del self.execution_results[task_id]
                logger.info(f"Cleared execution results for {len(task_ids)} tasks")

class AsyncParallelExecutionController:
    """
    Asynchronous version of the ParallelExecutionController, using asyncio.
    Provides the same functionality but with async/await support.
    """
    
    def __init__(self, task_selector: TaskSelector, context_manager: ContextManager, 
                resource_manager, max_workers: int = 4):
        self.task_selector = task_selector
        self.context_manager = context_manager
        self.resource_manager = resource_manager
        self.max_workers = max_workers
        self.execution_results = {}  # task_id -> ExecutionResult
        self.task_executors = {}  # task_id -> executor function (async or sync)
        self.running_tasks = set()  # Set of running task_ids
        self.results_lock = asyncio.Lock()
        self.semaphore = asyncio.Semaphore(max_workers)
        self.result_aggregator = ResultAggregator(self)
        self.loop = asyncio.get_event_loop()
        logger.info(f"Async parallel execution controller initialized with {max_workers} workers")
    
    def register_task_executor(self, task_id: str, executor_func) -> None:
        """Register an executor function for a task (can be async or sync)."""
        self.task_executors[task_id] = executor_func
        logger.debug(f"Registered executor for task {task_id}")
    
    def get_execution_result(self, task_id: str) -> Optional[ExecutionResult]:
        """Get the execution result for a task."""
        return self.execution_results.get(task_id)
    
    async def execute_task(self, task_id: str, execution_mode: ExecutionMode = ExecutionMode.SEQUENTIAL,
                         context_override: Dict[str, Any] = None) -> Optional[ExecutionResult]:
        """Execute a task with the specified execution mode."""
        task = self.task_selector.get_task_by_id(task_id)
        if not task:
            logger.error(f"Task {task_id} not found")
            return None
        
        if task_id not in self.task_executors:
            logger.error(f"No executor registered for task {task_id}")
            return None
        
        # Check if task is already running
        async with self.results_lock:
            if task_id in self.running_tasks:
                logger.warning(f"Task {task_id} is already running")
                return None
            self.running_tasks.add(task_id)
        
        logger.info(f"Executing task {task_id} in {execution_mode.value} mode")
        
        try:
            # Prepare context
            task_context = context_override if context_override is not None else self.context_manager.prepare_task_context(task_id)
            
            # Try to allocate resources if task has estimated resources
            if task.estimated_resources:
                try:
                    if not self.resource_manager.allocate_resources(task_id, task.estimated_resources):
                        logger.warning(f"Could not allocate resources for task {task_id}")
                        # Create a failure result
                        result = ExecutionResult(
                            task_id=task_id,
                            success=False,
                            output={"error": "Failed to allocate resources"},
                            start_time=datetime.now(),
                            end_time=datetime.now(),
                            error="Resource allocation failed",
                            duration=0,
                            resource_usage={}
                        )
                        async with self.results_lock:
                            self.execution_results[task_id] = result
                            self.running_tasks.remove(task_id)
                        return result
                except Exception as e:
                    logger.error(f"Error allocating resources for task {task_id}: {str(e)}")
                    # Continue execution with no resources if allocation fails
            
            # Mark task as in progress
            self.task_selector.update_task_status(task_id, TaskStatus.IN_PROGRESS)
            
            # Execute based on mode
            if execution_mode == ExecutionMode.SEQUENTIAL:
                result = await self._execute_sequential(task_id, task_context)
            else:
                # For parallel mode, we still execute sequentially but don't wait for result
                if execution_mode == ExecutionMode.PARALLEL:
                    asyncio.create_task(self._execute_sequential(task_id, task_context))
                    result = None
                else:
                    async with self.semaphore:
                        result = await self._execute_sequential(task_id, task_context)
            
            return result
        except Exception as e:
            logger.error(f"Error in execute_task for {task_id}: {str(e)}")
            # Create a failure result
            result = ExecutionResult(
                task_id=task_id,
                success=False,
                output={"error": str(e)},
                start_time=datetime.now(),
                end_time=datetime.now(),
                error=str(e),
                duration=0,
                resource_usage={}
            )
            async with self.results_lock:
                self.execution_results[task_id] = result
                self.running_tasks.remove(task_id)
            return result
    
    async def _execute_sequential(self, task_id: str, task_context: Dict[str, Any]) -> ExecutionResult:
        """Execute a task sequentially."""
        start_time = datetime.now()
        try:
            executor = self.task_executors[task_id]
            if asyncio.iscoroutinefunction(executor):
                output = await executor(task_id, task_context)
            else:
                # Run sync function in executor to avoid blocking the event loop
                output = await self.loop.run_in_executor(None, executor, task_id, task_context)
            success = True
            error = None
        except Exception as e:
            logger.error(f"Error executing task {task_id}: {str(e)}")
            output = {"error": str(e)}
            success = False
            error = str(e)
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        # Release resources
        resource_usage = self.resource_manager.free_resources(task_id)
        
        # Create result
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
        
        # Update task status
        new_status = TaskStatus.COMPLETED if success else TaskStatus.FAILED
        self.task_selector.update_task_status(task_id, new_status)
        
        # Update context if successful
        if success:
            self.context_manager.propagate_context_from_task(task_id, output)
        
        # Store result
        async with self.results_lock:
            self.execution_results[task_id] = result
            self.running_tasks.remove(task_id)
        
        logger.info(f"Task {task_id} completed with status: {new_status.value}, duration: {duration:.2f}s")
        return result
    
    async def execute_tasks(self, task_ids: List[str], 
                          execution_mode: ExecutionMode = ExecutionMode.PARALLEL,
                          max_concurrent: int = None) -> Dict[str, ExecutionResult]:
        """Execute multiple tasks with the specified execution mode."""
        if not task_ids:
            logger.warning("No tasks to execute")
            return {}
        
        logger.info(f"Executing {len(task_ids)} tasks in {execution_mode.value} mode")
        
        # Use Sequential mode for single task
        if len(task_ids) == 1:
            result = await self.execute_task(task_ids[0], ExecutionMode.SEQUENTIAL)
            return {task_ids[0]: result} if result else {}
        
        # Sequential execution
        if execution_mode == ExecutionMode.SEQUENTIAL:
            results = {}
            for task_id in task_ids:
                result = await self.execute_task(task_id, ExecutionMode.SEQUENTIAL)
                if result:
                    results[task_id] = result
            return results
        
        # Parallel execution
        if execution_mode == ExecutionMode.PARALLEL_WITH_LIMIT and max_concurrent:
            # Use custom semaphore for limited concurrency
            sem = asyncio.Semaphore(min(max_concurrent, self.max_workers))
            
            async def limited_execute(tid):
                async with sem:
                    return await self.execute_task(tid, ExecutionMode.SEQUENTIAL)
            
            tasks = [limited_execute(task_id) for task_id in task_ids]
        else:
            # Full parallel execution
            tasks = [self.execute_task(task_id, ExecutionMode.SEQUENTIAL) for task_id in task_ids]
        
        # Wait for all tasks to complete
        results_list = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        results = {}
        for i, result in enumerate(results_list):
            if isinstance(result, Exception):
                logger.error(f"Error executing task {task_ids[i]}: {str(result)}")
            elif result:
                results[task_ids[i]] = result
        
        return results
    
    async def wait_for_completion(self, task_ids: List[str], timeout: float = None) -> bool:
        """Wait for the completion of specified tasks."""
        start_time = time.time()
        while True:
            async with self.results_lock:
                if all(task_id in self.execution_results and task_id not in self.running_tasks for task_id in task_ids):
                    return True
            
            if timeout is not None and time.time() - start_time > timeout:
                logger.warning(f"Timeout waiting for tasks to complete")
                return False
            
            await asyncio.sleep(0.1)
    
    async def stop_task(self, task_id: str) -> bool:
        """Stop a running task (best effort)."""
        async with self.results_lock:
            if task_id not in self.running_tasks:
                logger.warning(f"Task {task_id} is not running")
                return False
        
        # Release resources and mark as failed
        logger.info(f"Stopping task {task_id}")
        self.resource_manager.release_resources(task_id)
        self.task_selector.update_task_status(task_id, TaskStatus.FAILED)
        
        async with self.results_lock:
            if task_id in self.running_tasks:
                self.running_tasks.remove(task_id)
            
            # Create a failed result if not already present
            if task_id not in self.execution_results:
                self.execution_results[task_id] = ExecutionResult(
                    task_id=task_id,
                    success=False,
                    output={"error": "Task execution stopped"},
                    start_time=datetime.now(),
                    end_time=datetime.now(),
                    error="Task execution stopped"
                )
        
        return True
    
    async def stop_all_tasks(self) -> List[str]:
        """Stop all running tasks (best effort)."""
        async with self.results_lock:
            running = list(self.running_tasks)
        
        stopped = []
        for task_id in running:
            if await self.stop_task(task_id):
                stopped.append(task_id)
        
        logger.info(f"Stopped {len(stopped)} tasks")
        return stopped
    
    async def get_running_tasks(self) -> List[str]:
        """Get IDs of currently running tasks."""
        async with self.results_lock:
            return list(self.running_tasks)
    
    async def clear_results(self, task_ids: List[str] = None) -> None:
        """Clear execution results for specified tasks or all tasks."""
        async with self.results_lock:
            if task_ids is None:
                self.execution_results = {}
                logger.info("Cleared all execution results")
            else:
                for task_id in task_ids:
                    if task_id in self.execution_results:
                        del self.execution_results[task_id]
                logger.info(f"Cleared execution results for {len(task_ids)} tasks") 