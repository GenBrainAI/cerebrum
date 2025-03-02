from typing import Dict, List, Optional, Any, Set, Tuple
import asyncio
import logging
import uuid
import time
from datetime import datetime

logger = logging.getLogger(__name__)

class Task:
    """Represents a task that can be executed in parallel."""
    
    def __init__(self, 
                 task_id: str, 
                 coroutine: Any, 
                 resource_requirements: Optional[Dict[str, float]] = None,
                 dependencies: Optional[List[str]] = None):
        """
        Initialize a task with its execution coroutine and resource requirements.
        
        Args:
            task_id: Unique identifier for the task
            coroutine: The coroutine to execute
            resource_requirements: Dictionary of resource requirements (e.g., {"cpu": 0.5, "memory": 256})
            dependencies: List of task IDs that must complete before this task can start
        """
        self.task_id = task_id
        self.coroutine = coroutine
        self.resource_requirements = resource_requirements or {}
        self.dependencies = dependencies or []
        self.status = "pending"
        self.result = None
        self.error = None
        self.start_time = None
        self.end_time = None
        self.resource_usage = {}
    
    def __str__(self):
        return f"Task({self.task_id}, status={self.status})"


class ParallelExecutionController:
    """Manages parallel execution of tasks with resource-aware scheduling."""
    
    def __init__(self, max_concurrent_tasks: int = 5, resource_limits: Optional[Dict[str, float]] = None):
        """
        Initialize the controller with resource limits.
        
        Args:
            max_concurrent_tasks: Maximum number of tasks to run concurrently
            resource_limits: Dictionary of resource limits (e.g., {"cpu": 4.0, "memory": 8192})
        """
        self.max_concurrent_tasks = max_concurrent_tasks
        self.resource_limits = resource_limits or {}
        self.tasks: Dict[str, Task] = {}
        self.running_tasks: Set[str] = set()
        self.completed_tasks: Set[str] = set()
        self.failed_tasks: Set[str] = set()
        self.current_resource_usage: Dict[str, float] = {k: 0.0 for k in self.resource_limits.keys()}
        self.task_queue: asyncio.Queue = asyncio.Queue()
        self.task_results: Dict[str, Any] = {}
        self.task_events: Dict[str, asyncio.Event] = {}
        self.cancellation_requests: Set[str] = set()
        self._scheduler_running = False
        self._scheduler_task = None
    
    async def execute_tasks(self, tasks: List[Task], strategy: str = "resource_aware") -> Dict[str, Any]:
        """
        Execute multiple tasks in parallel using the specified strategy.
        
        Args:
            tasks: List of Task objects to execute
            strategy: Execution strategy ("resource_aware", "priority_based", "fifo")
            
        Returns:
            Dictionary mapping task IDs to their results
        """
        # Register all tasks
        for task in tasks:
            await self.add_task_object(task)
        
        # Start the scheduler if not already running
        await self._ensure_scheduler_running()
        
        # Wait for all tasks to complete
        pending_tasks = set(task.task_id for task in tasks)
        while pending_tasks:
            # Create a list of events to wait for
            events = [self.task_events[task_id] for task_id in pending_tasks 
                     if task_id in self.task_events]
            
            if not events:
                # No events to wait for, all tasks might be completed already
                break
                
            # Wait for any task to complete
            done, _ = await asyncio.wait(
                [event.wait() for event in events],
                return_when=asyncio.FIRST_COMPLETED
            )
            
            # Update the set of pending tasks
            completed = set()
            for task_id in pending_tasks:
                if (task_id in self.completed_tasks or 
                    task_id in self.failed_tasks):
                    completed.add(task_id)
            
            pending_tasks -= completed
        
        # Collect and return results
        results = {}
        for task in tasks:
            task_id = task.task_id
            if task_id in self.completed_tasks:
                results[task_id] = {
                    "status": "completed",
                    "result": self.task_results.get(task_id),
                    "start_time": self.tasks[task_id].start_time,
                    "end_time": self.tasks[task_id].end_time,
                    "execution_time": (self.tasks[task_id].end_time - self.tasks[task_id].start_time).total_seconds() 
                    if self.tasks[task_id].end_time and self.tasks[task_id].start_time else None,
                    "resource_usage": self.tasks[task_id].resource_usage
                }
            elif task_id in self.failed_tasks:
                results[task_id] = {
                    "status": "failed",
                    "error": str(self.tasks[task_id].error),
                    "start_time": self.tasks[task_id].start_time,
                    "end_time": self.tasks[task_id].end_time,
                    "execution_time": (self.tasks[task_id].end_time - self.tasks[task_id].start_time).total_seconds() 
                    if self.tasks[task_id].end_time and self.tasks[task_id].start_time else None,
                    "resource_usage": self.tasks[task_id].resource_usage
                }
            else:
                results[task_id] = {
                    "status": self.tasks[task_id].status,
                    "start_time": self.tasks[task_id].start_time
                }
        
        return results
    
    async def add_task(self, coroutine: Any, 
                      resource_requirements: Optional[Dict[str, float]] = None,
                      dependencies: List[str] = None) -> str:
        """
        Add a task to the execution queue with optional dependencies.
        
        Args:
            coroutine: The coroutine to execute
            resource_requirements: Dictionary of resource requirements
            dependencies: List of task IDs that must complete before this task can start
            
        Returns:
            Task ID
        """
        task_id = str(uuid.uuid4())
        task = Task(
            task_id=task_id,
            coroutine=coroutine,
            resource_requirements=resource_requirements,
            dependencies=dependencies
        )
        
        await self.add_task_object(task)
        return task_id
    
    async def add_task_object(self, task: Task) -> str:
        """
        Add a Task object to the execution queue.
        
        Args:
            task: The Task object to add
            
        Returns:
            Task ID
        """
        self.tasks[task.task_id] = task
        self.task_events[task.task_id] = asyncio.Event()
        
        # Add to queue if no dependencies or all dependencies are completed
        if not task.dependencies or all(dep_id in self.completed_tasks for dep_id in task.dependencies):
            await self.task_queue.put(task.task_id)
        
        # Start the scheduler if not already running
        await self._ensure_scheduler_running()
        
        return task.task_id
    
    async def cancel_task(self, task_id: str) -> bool:
        """
        Cancel a running or pending task.
        
        Args:
            task_id: ID of the task to cancel
            
        Returns:
            True if the task was found and cancellation was requested, False otherwise
        """
        if task_id not in self.tasks:
            return False
        
        if task_id in self.running_tasks:
            # Mark for cancellation
            self.cancellation_requests.add(task_id)
            return True
        elif self.tasks[task_id].status == "pending":
            # Remove from queue (this is a bit tricky with asyncio.Queue)
            # For now, we'll mark it as cancelled and skip it in the scheduler
            self.tasks[task_id].status = "cancelled"
            self.task_events[task_id].set()
            return True
        
        return False
    
    async def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """
        Get the current status of a task.
        
        Args:
            task_id: ID of the task
            
        Returns:
            Dictionary with task status information
        """
        if task_id not in self.tasks:
            return {"status": "not_found"}
        
        task = self.tasks[task_id]
        status_info = {
            "status": task.status,
            "start_time": task.start_time,
            "end_time": task.end_time,
            "dependencies": task.dependencies,
            "resource_requirements": task.resource_requirements,
            "resource_usage": task.resource_usage
        }
        
        if task_id in self.completed_tasks:
            status_info["result"] = self.task_results.get(task_id)
        elif task_id in self.failed_tasks:
            status_info["error"] = str(task.error)
        
        return status_info
    
    async def wait_for_task(self, task_id: str, timeout: Optional[float] = None) -> Dict[str, Any]:
        """
        Wait for a task to complete and return its result.
        
        Args:
            task_id: ID of the task to wait for
            timeout: Maximum time to wait in seconds, or None to wait indefinitely
            
        Returns:
            Dictionary with task result information
        """
        if task_id not in self.tasks:
            return {"status": "not_found"}
        
        if task_id not in self.task_events:
            self.task_events[task_id] = asyncio.Event()
        
        if task_id in self.completed_tasks or task_id in self.failed_tasks:
            # Task already completed or failed
            self.task_events[task_id].set()
        
        try:
            # Wait for the task to complete
            await asyncio.wait_for(self.task_events[task_id].wait(), timeout)
            
            # Return the result
            return await self.get_task_status(task_id)
        except asyncio.TimeoutError:
            return {
                "status": "timeout",
                "task_status": self.tasks[task_id].status
            }
    
    async def _ensure_scheduler_running(self):
        """Ensure the task scheduler is running."""
        if not self._scheduler_running:
            self._scheduler_running = True
            self._scheduler_task = asyncio.create_task(self._task_scheduler())
    
    async def _task_scheduler(self):
        """Task scheduler coroutine that manages execution of tasks."""
        try:
            while True:
                # Check if we can start more tasks
                while (len(self.running_tasks) < self.max_concurrent_tasks and 
                       not self.task_queue.empty()):
                    # Get the next task ID from the queue
                    task_id = await self.task_queue.get()
                    
                    # Skip if task was cancelled
                    if self.tasks[task_id].status == "cancelled":
                        self.task_queue.task_done()
                        continue
                    
                    # Check if all dependencies are satisfied
                    dependencies_satisfied = all(
                        dep_id in self.completed_tasks 
                        for dep_id in self.tasks[task_id].dependencies
                    )
                    
                    if not dependencies_satisfied:
                        # Put back in the queue for later
                        await self.task_queue.put(task_id)
                        self.task_queue.task_done()
                        # Avoid spinning too fast on dependency checks
                        await asyncio.sleep(0.1)
                        continue
                    
                    # Check if we have enough resources
                    resource_requirements = self.tasks[task_id].resource_requirements
                    can_allocate = True
                    
                    for resource, amount in resource_requirements.items():
                        if resource in self.resource_limits:
                            if self.current_resource_usage.get(resource, 0) + amount > self.resource_limits[resource]:
                                can_allocate = False
                                break
                    
                    if not can_allocate:
                        # Put back in the queue for later
                        await self.task_queue.put(task_id)
                        self.task_queue.task_done()
                        # Avoid spinning too fast on resource checks
                        await asyncio.sleep(0.1)
                        continue
                    
                    # Allocate resources and start the task
                    for resource, amount in resource_requirements.items():
                        self.current_resource_usage[resource] = self.current_resource_usage.get(resource, 0) + amount
                    
                    # Start the task
                    self.running_tasks.add(task_id)
                    self.tasks[task_id].status = "running"
                    self.tasks[task_id].start_time = datetime.now()
                    
                    # Create and start the task execution
                    asyncio.create_task(self._execute_task(task_id))
                    
                    self.task_queue.task_done()
                
                # Wait a bit before checking again
                await asyncio.sleep(0.1)
        except asyncio.CancelledError:
            logger.info("Task scheduler cancelled")
            self._scheduler_running = False
        except Exception as e:
            logger.exception(f"Error in task scheduler: {e}")
            self._scheduler_running = False
    
    async def _execute_task(self, task_id: str):
        """Execute a single task and update its status."""
        task = self.tasks[task_id]
        
        try:
            # Check for cancellation
            if task_id in self.cancellation_requests:
                self.cancellation_requests.remove(task_id)
                task.status = "cancelled"
                task.end_time = datetime.now()
                self.running_tasks.remove(task_id)
                
                # Release resources
                for resource, amount in task.resource_requirements.items():
                    self.current_resource_usage[resource] = max(
                        0, self.current_resource_usage.get(resource, 0) - amount
                    )
                
                # Signal completion
                self.task_events[task_id].set()
                return
            
            # Execute the task
            start_time = time.time()
            result = await task.coroutine
            end_time = time.time()
            
            # Record resource usage (this is a simple estimate)
            task.resource_usage = {
                "execution_time": end_time - start_time,
                **task.resource_requirements
            }
            
            # Update task status
            task.status = "completed"
            task.result = result
            task.end_time = datetime.now()
            self.completed_tasks.add(task_id)
            self.running_tasks.remove(task_id)
            self.task_results[task_id] = result
            
            # Release resources
            for resource, amount in task.resource_requirements.items():
                self.current_resource_usage[resource] = max(
                    0, self.current_resource_usage.get(resource, 0) - amount
                )
            
            # Check if this completion unblocks any dependent tasks
            for dependent_task_id, dependent_task in self.tasks.items():
                if (task_id in dependent_task.dependencies and 
                    dependent_task.status == "pending" and
                    all(dep_id in self.completed_tasks for dep_id in dependent_task.dependencies)):
                    # All dependencies satisfied, add to queue
                    await self.task_queue.put(dependent_task_id)
            
        except Exception as e:
            # Handle task failure
            logger.exception(f"Task {task_id} failed: {e}")
            task.status = "failed"
            task.error = e
            task.end_time = datetime.now()
            self.failed_tasks.add(task_id)
            self.running_tasks.remove(task_id)
            
            # Release resources
            for resource, amount in task.resource_requirements.items():
                self.current_resource_usage[resource] = max(
                    0, self.current_resource_usage.get(resource, 0) - amount
                )
        
        # Signal that the task has completed (successfully or with failure)
        self.task_events[task_id].set()
    
    async def shutdown(self):
        """Shutdown the controller and cancel all running tasks."""
        if self._scheduler_task:
            self._scheduler_task.cancel()
            try:
                await self._scheduler_task
            except asyncio.CancelledError:
                pass
        
        # Cancel all running tasks
        for task_id in list(self.running_tasks):
            await self.cancel_task(task_id)
        
        self._scheduler_running = False 