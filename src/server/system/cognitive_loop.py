from typing import Dict, List, Optional, Any, Union, Callable, Tuple
from enum import Enum
from datetime import datetime
import uuid
import json
import os
import logging
import asyncio
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

class CognitivePhase(str, Enum):
    """Phases of the development cognitive loop"""
    UNDERSTAND = "understand"
    PLAN = "plan"
    EXECUTE = "execute"
    REFLECT = "reflect"

class WorkerType(str, Enum):
    """Types of specialized workers in the development cognitive loop"""
    REQUIREMENTS = "requirements"
    PLANNING = "planning"
    IMPLEMENTATION = "implementation"
    EVALUATION = "evaluation"

class TaskStatus(str, Enum):
    """Status of a cognitive loop task"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class TaskPriority(int, Enum):
    """Priority levels for cognitive loop tasks"""
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4

class CognitiveTask(BaseModel):
    """Task within the development cognitive loop"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str
    description: str
    phase: CognitivePhase
    worker_type: Optional[WorkerType] = None
    status: TaskStatus = TaskStatus.PENDING
    priority: TaskPriority = TaskPriority.MEDIUM
    parent_id: Optional[str] = None
    subtasks: List[str] = []
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    assigned_to: Optional[str] = None
    context: Dict[str, Any] = {}
    result: Optional[Any] = None
    error: Optional[str] = None
    
    def update_status(self, status: TaskStatus) -> None:
        """Update the task status with appropriate timestamps"""
        self.status = status
        self.updated_at = datetime.now()
        
        if status == TaskStatus.IN_PROGRESS and not self.started_at:
            self.started_at = datetime.now()
        elif status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]:
            self.completed_at = datetime.now()

class WorkerInterface:
    """Interface for specialized workers in the development cognitive loop"""
    
    async def process_task(self, task: CognitiveTask) -> CognitiveTask:
        """Process a cognitive task and return the updated task"""
        raise NotImplementedError("Worker must implement process_task method")
    
    async def can_handle(self, task: CognitiveTask) -> bool:
        """Check if this worker can handle the given task"""
        raise NotImplementedError("Worker must implement can_handle method")

class CognitiveLoopOrchestrator:
    """Orchestrates the development cognitive loop process"""
    
    def __init__(self, storage_path: Optional[str] = None):
        self.storage_path = storage_path or os.path.join(os.path.expanduser("~"), ".cerebrum", "cognitive_loop")
        os.makedirs(self.storage_path, exist_ok=True)
        
        self.tasks: Dict[str, CognitiveTask] = {}
        self.workers: Dict[WorkerType, List[WorkerInterface]] = {
            WorkerType.REQUIREMENTS: [],
            WorkerType.PLANNING: [],
            WorkerType.IMPLEMENTATION: [],
            WorkerType.EVALUATION: []
        }
        
        self.current_phase: CognitivePhase = CognitivePhase.UNDERSTAND
        self.phase_handlers: Dict[CognitivePhase, Callable] = {
            CognitivePhase.UNDERSTAND: self._handle_understand_phase,
            CognitivePhase.PLAN: self._handle_plan_phase,
            CognitivePhase.EXECUTE: self._handle_execute_phase,
            CognitivePhase.REFLECT: self._handle_reflect_phase
        }
        
        self.development_context: Dict[str, Any] = {}
        
        self._load_data()
    
    def _load_data(self) -> None:
        """Load saved cognitive loop data"""
        tasks_path = os.path.join(self.storage_path, "tasks.json")
        context_path = os.path.join(self.storage_path, "context.json")
        state_path = os.path.join(self.storage_path, "state.json")
        
        # Load tasks
        if os.path.exists(tasks_path):
            try:
                with open(tasks_path, 'r') as f:
                    data = json.load(f)
                    for task_data in data:
                        # Convert string dates to datetime objects
                        for date_field in ['created_at', 'updated_at', 'started_at', 'completed_at']:
                            if date_field in task_data and isinstance(task_data[date_field], str):
                                task_data[date_field] = datetime.fromisoformat(task_data[date_field])
                        task = CognitiveTask(**task_data)
                        self.tasks[task.id] = task
            except Exception as e:
                logger.error(f"Error loading cognitive loop tasks: {e}")
        
        # Load development context
        if os.path.exists(context_path):
            try:
                with open(context_path, 'r') as f:
                    self.development_context = json.load(f)
            except Exception as e:
                logger.error(f"Error loading development context: {e}")
        
        # Load orchestrator state
        if os.path.exists(state_path):
            try:
                with open(state_path, 'r') as f:
                    state = json.load(f)
                    if 'current_phase' in state:
                        self.current_phase = CognitivePhase(state['current_phase'])
            except Exception as e:
                logger.error(f"Error loading orchestrator state: {e}")
    
    def _save_data(self) -> None:
        """Save cognitive loop data"""
        tasks_path = os.path.join(self.storage_path, "tasks.json")
        context_path = os.path.join(self.storage_path, "context.json")
        state_path = os.path.join(self.storage_path, "state.json")
        
        # Save tasks
        with open(tasks_path, 'w') as f:
            data = []
            for task in self.tasks.values():
                task_dict = task.model_dump()
                # Convert datetime objects to ISO format strings
                for date_field in ['created_at', 'updated_at', 'started_at', 'completed_at']:
                    if date_field in task_dict and task_dict[date_field] is not None:
                        if isinstance(task_dict[date_field], datetime):
                            task_dict[date_field] = task_dict[date_field].isoformat()
                data.append(task_dict)
            json.dump(data, f, indent=2)
        
        # Save development context
        with open(context_path, 'w') as f:
            json.dump(self.development_context, f, indent=2)
        
        # Save orchestrator state
        with open(state_path, 'w') as f:
            state = {
                'current_phase': self.current_phase
            }
            json.dump(state, f, indent=2)
    
    def register_worker(self, worker_type: WorkerType, worker: WorkerInterface) -> None:
        """Register a worker for a specific type"""
        self.workers[worker_type].append(worker)
    
    def create_task(self, title: str, description: str, phase: CognitivePhase, 
                   worker_type: Optional[WorkerType] = None, priority: TaskPriority = TaskPriority.MEDIUM,
                   parent_id: Optional[str] = None, context: Optional[Dict[str, Any]] = None) -> str:
        """Create a new cognitive task and return its ID"""
        task = CognitiveTask(
            title=title,
            description=description,
            phase=phase,
            worker_type=worker_type,
            priority=priority,
            parent_id=parent_id,
            context=context or {}
        )
        
        self.tasks[task.id] = task
        
        # Add as subtask to parent if specified
        if parent_id and parent_id in self.tasks:
            parent = self.tasks[parent_id]
            parent.subtasks.append(task.id)
        
        self._save_data()
        return task.id
    
    def get_task(self, task_id: str) -> Optional[CognitiveTask]:
        """Get a task by ID"""
        return self.tasks.get(task_id)
    
    def update_task(self, task_id: str, **kwargs) -> bool:
        """Update a task with new values"""
        if task_id not in self.tasks:
            return False
        
        task = self.tasks[task_id]
        
        for key, value in kwargs.items():
            if hasattr(task, key):
                setattr(task, key, value)
        
        task.updated_at = datetime.now()
        self._save_data()
        return True
    
    def update_task_status(self, task_id: str, status: TaskStatus) -> bool:
        """Update a task's status"""
        if task_id not in self.tasks:
            return False
        
        task = self.tasks[task_id]
        task.update_status(status)
        self._save_data()
        return True
    
    def set_task_result(self, task_id: str, result: Any) -> bool:
        """Set a task's result"""
        if task_id not in self.tasks:
            return False
        
        task = self.tasks[task_id]
        task.result = result
        task.update_status(TaskStatus.COMPLETED)
        self._save_data()
        return True
    
    def set_task_error(self, task_id: str, error: str) -> bool:
        """Set a task's error"""
        if task_id not in self.tasks:
            return False
        
        task = self.tasks[task_id]
        task.error = error
        task.update_status(TaskStatus.FAILED)
        self._save_data()
        return True
    
    def get_tasks_by_phase(self, phase: CognitivePhase, status: Optional[TaskStatus] = None) -> List[CognitiveTask]:
        """Get tasks for a specific phase, optionally filtered by status"""
        tasks = [task for task in self.tasks.values() if task.phase == phase]
        
        if status is not None:
            tasks = [task for task in tasks if task.status == status]
        
        return tasks
    
    def get_tasks_by_worker(self, worker_type: WorkerType, status: Optional[TaskStatus] = None) -> List[CognitiveTask]:
        """Get tasks for a specific worker type, optionally filtered by status"""
        tasks = [task for task in self.tasks.values() if task.worker_type == worker_type]
        
        if status is not None:
            tasks = [task for task in tasks if task.status == status]
        
        return tasks
    
    def get_subtasks(self, task_id: str) -> List[CognitiveTask]:
        """Get all subtasks for a task"""
        if task_id not in self.tasks:
            return []
        
        task = self.tasks[task_id]
        return [self.tasks[subtask_id] for subtask_id in task.subtasks if subtask_id in self.tasks]
    
    def set_current_phase(self, phase: CognitivePhase) -> None:
        """Set the current phase of the cognitive loop"""
        self.current_phase = phase
        self._save_data()
    
    def get_current_phase(self) -> CognitivePhase:
        """Get the current phase of the cognitive loop"""
        return self.current_phase
    
    def update_development_context(self, key: str, value: Any) -> None:
        """Update a value in the development context"""
        self.development_context[key] = value
        self._save_data()
    
    def get_development_context(self, key: Optional[str] = None) -> Any:
        """Get a value from the development context, or the entire context if no key is specified"""
        if key is None:
            return self.development_context
        return self.development_context.get(key)
    
    async def _handle_understand_phase(self) -> bool:
        """Handle the understand phase of the cognitive loop"""
        # Get all pending understand tasks
        tasks = self.get_tasks_by_phase(CognitivePhase.UNDERSTAND, TaskStatus.PENDING)
        
        # Sort by priority
        tasks.sort(key=lambda t: t.priority.value, reverse=True)
        
        # Process tasks with appropriate workers
        for task in tasks:
            if task.worker_type:
                # Task has a specific worker type
                workers = self.workers.get(task.worker_type, [])
                for worker in workers:
                    if await worker.can_handle(task):
                        task.update_status(TaskStatus.IN_PROGRESS)
                        self._save_data()
                        
                        try:
                            updated_task = await worker.process_task(task)
                            self.tasks[task.id] = updated_task
                            self._save_data()
                        except Exception as e:
                            logger.error(f"Error processing task {task.id}: {e}")
                            self.set_task_error(task.id, str(e))
                        
                        break
            else:
                # Task doesn't have a specific worker type, try all workers
                for worker_type, workers in self.workers.items():
                    for worker in workers:
                        if await worker.can_handle(task):
                            task.update_status(TaskStatus.IN_PROGRESS)
                            task.worker_type = worker_type
                            self._save_data()
                            
                            try:
                                updated_task = await worker.process_task(task)
                                self.tasks[task.id] = updated_task
                                self._save_data()
                            except Exception as e:
                                logger.error(f"Error processing task {task.id}: {e}")
                                self.set_task_error(task.id, str(e))
                            
                            break
                    else:
                        continue
                    break
        
        # Check if all understand tasks are completed
        pending_tasks = self.get_tasks_by_phase(CognitivePhase.UNDERSTAND, TaskStatus.PENDING)
        in_progress_tasks = self.get_tasks_by_phase(CognitivePhase.UNDERSTAND, TaskStatus.IN_PROGRESS)
        
        if not pending_tasks and not in_progress_tasks:
            # All understand tasks are completed, move to plan phase
            self.set_current_phase(CognitivePhase.PLAN)
            return True
        
        return False
    
    async def _handle_plan_phase(self) -> bool:
        """Handle the plan phase of the cognitive loop"""
        # Get all pending plan tasks
        tasks = self.get_tasks_by_phase(CognitivePhase.PLAN, TaskStatus.PENDING)
        
        # Sort by priority
        tasks.sort(key=lambda t: t.priority.value, reverse=True)
        
        # Process tasks with appropriate workers
        for task in tasks:
            if task.worker_type:
                # Task has a specific worker type
                workers = self.workers.get(task.worker_type, [])
                for worker in workers:
                    if await worker.can_handle(task):
                        task.update_status(TaskStatus.IN_PROGRESS)
                        self._save_data()
                        
                        try:
                            updated_task = await worker.process_task(task)
                            self.tasks[task.id] = updated_task
                            self._save_data()
                        except Exception as e:
                            logger.error(f"Error processing task {task.id}: {e}")
                            self.set_task_error(task.id, str(e))
                        
                        break
            else:
                # Task doesn't have a specific worker type, try all workers
                for worker_type, workers in self.workers.items():
                    for worker in workers:
                        if await worker.can_handle(task):
                            task.update_status(TaskStatus.IN_PROGRESS)
                            task.worker_type = worker_type
                            self._save_data()
                            
                            try:
                                updated_task = await worker.process_task(task)
                                self.tasks[task.id] = updated_task
                                self._save_data()
                            except Exception as e:
                                logger.error(f"Error processing task {task.id}: {e}")
                                self.set_task_error(task.id, str(e))
                            
                            break
                    else:
                        continue
                    break
        
        # Check if all plan tasks are completed
        pending_tasks = self.get_tasks_by_phase(CognitivePhase.PLAN, TaskStatus.PENDING)
        in_progress_tasks = self.get_tasks_by_phase(CognitivePhase.PLAN, TaskStatus.IN_PROGRESS)
        
        if not pending_tasks and not in_progress_tasks:
            # All plan tasks are completed, move to execute phase
            self.set_current_phase(CognitivePhase.EXECUTE)
            return True
        
        return False
    
    async def _handle_execute_phase(self) -> bool:
        """Handle the execute phase of the cognitive loop"""
        # Get all pending execute tasks
        tasks = self.get_tasks_by_phase(CognitivePhase.EXECUTE, TaskStatus.PENDING)
        
        # Sort by priority
        tasks.sort(key=lambda t: t.priority.value, reverse=True)
        
        # Process tasks with appropriate workers
        for task in tasks:
            if task.worker_type:
                # Task has a specific worker type
                workers = self.workers.get(task.worker_type, [])
                for worker in workers:
                    if await worker.can_handle(task):
                        task.update_status(TaskStatus.IN_PROGRESS)
                        self._save_data()
                        
                        try:
                            updated_task = await worker.process_task(task)
                            self.tasks[task.id] = updated_task
                            self._save_data()
                        except Exception as e:
                            logger.error(f"Error processing task {task.id}: {e}")
                            self.set_task_error(task.id, str(e))
                        
                        break
            else:
                # Task doesn't have a specific worker type, try all workers
                for worker_type, workers in self.workers.items():
                    for worker in workers:
                        if await worker.can_handle(task):
                            task.update_status(TaskStatus.IN_PROGRESS)
                            task.worker_type = worker_type
                            self._save_data()
                            
                            try:
                                updated_task = await worker.process_task(task)
                                self.tasks[task.id] = updated_task
                                self._save_data()
                            except Exception as e:
                                logger.error(f"Error processing task {task.id}: {e}")
                                self.set_task_error(task.id, str(e))
                            
                            break
                    else:
                        continue
                    break
        
        # Check if all execute tasks are completed
        pending_tasks = self.get_tasks_by_phase(CognitivePhase.EXECUTE, TaskStatus.PENDING)
        in_progress_tasks = self.get_tasks_by_phase(CognitivePhase.EXECUTE, TaskStatus.IN_PROGRESS)
        
        if not pending_tasks and not in_progress_tasks:
            # All execute tasks are completed, move to reflect phase
            self.set_current_phase(CognitivePhase.REFLECT)
            return True
        
        return False
    
    async def _handle_reflect_phase(self) -> bool:
        """Handle the reflect phase of the cognitive loop"""
        # Get all pending reflect tasks
        tasks = self.get_tasks_by_phase(CognitivePhase.REFLECT, TaskStatus.PENDING)
        
        # Sort by priority
        tasks.sort(key=lambda t: t.priority.value, reverse=True)
        
        # Process tasks with appropriate workers
        for task in tasks:
            if task.worker_type:
                # Task has a specific worker type
                workers = self.workers.get(task.worker_type, [])
                for worker in workers:
                    if await worker.can_handle(task):
                        task.update_status(TaskStatus.IN_PROGRESS)
                        self._save_data()
                        
                        try:
                            updated_task = await worker.process_task(task)
                            self.tasks[task.id] = updated_task
                            self._save_data()
                        except Exception as e:
                            logger.error(f"Error processing task {task.id}: {e}")
                            self.set_task_error(task.id, str(e))
                        
                        break
            else:
                # Task doesn't have a specific worker type, try all workers
                for worker_type, workers in self.workers.items():
                    for worker in workers:
                        if await worker.can_handle(task):
                            task.update_status(TaskStatus.IN_PROGRESS)
                            task.worker_type = worker_type
                            self._save_data()
                            
                            try:
                                updated_task = await worker.process_task(task)
                                self.tasks[task.id] = updated_task
                                self._save_data()
                            except Exception as e:
                                logger.error(f"Error processing task {task.id}: {e}")
                                self.set_task_error(task.id, str(e))
                            
                            break
                    else:
                        continue
                    break
        
        # Check if all reflect tasks are completed
        pending_tasks = self.get_tasks_by_phase(CognitivePhase.REFLECT, TaskStatus.PENDING)
        in_progress_tasks = self.get_tasks_by_phase(CognitivePhase.REFLECT, TaskStatus.IN_PROGRESS)
        
        if not pending_tasks and not in_progress_tasks:
            # All reflect tasks are completed, move back to understand phase for the next cycle
            self.set_current_phase(CognitivePhase.UNDERSTAND)
            return True
        
        return False
    
    async def process_current_phase(self) -> bool:
        """Process the current phase of the cognitive loop"""
        handler = self.phase_handlers.get(self.current_phase)
        if handler:
            return await handler()
        return False
    
    async def run_cognitive_cycle(self) -> None:
        """Run a complete cognitive cycle"""
        # Start with understand phase
        self.set_current_phase(CognitivePhase.UNDERSTAND)
        
        # Process each phase until completion
        while True:
            phase_completed = await self.process_current_phase()
            
            if phase_completed and self.current_phase == CognitivePhase.UNDERSTAND:
                # We've completed a full cycle
                break
    
    async def run_continuous(self, interval_seconds: float = 1.0) -> None:
        """Run the cognitive loop continuously"""
        while True:
            await self.process_current_phase()
            await asyncio.sleep(interval_seconds)

class RequirementsWorker(WorkerInterface):
    """Worker for requirements analysis tasks"""
    
    async def process_task(self, task: CognitiveTask) -> CognitiveTask:
        """Process a requirements analysis task"""
        # Implementation would depend on specific requirements analysis logic
        # This is a placeholder for the actual implementation
        
        # Update task with result
        task.result = {
            "requirements_analyzed": True,
            "requirements": ["Requirement 1", "Requirement 2", "Requirement 3"]
        }
        task.update_status(TaskStatus.COMPLETED)
        
        return task
    
    async def can_handle(self, task: CognitiveTask) -> bool:
        """Check if this worker can handle the given task"""
        return task.worker_type == WorkerType.REQUIREMENTS or (
            task.phase == CognitivePhase.UNDERSTAND and
            "requirements" in task.title.lower() or "requirements" in task.description.lower()
        )

class PlanningWorker(WorkerInterface):
    """Worker for planning tasks"""
    
    async def process_task(self, task: CognitiveTask) -> CognitiveTask:
        """Process a planning task"""
        # Implementation would depend on specific planning logic
        # This is a placeholder for the actual implementation
        
        # Update task with result
        task.result = {
            "plan_created": True,
            "steps": ["Step 1", "Step 2", "Step 3"]
        }
        task.update_status(TaskStatus.COMPLETED)
        
        return task
    
    async def can_handle(self, task: CognitiveTask) -> bool:
        """Check if this worker can handle the given task"""
        return task.worker_type == WorkerType.PLANNING or (
            task.phase == CognitivePhase.PLAN and
            "plan" in task.title.lower() or "plan" in task.description.lower()
        )

class ImplementationWorker(WorkerInterface):
    """Worker for implementation tasks"""
    
    async def process_task(self, task: CognitiveTask) -> CognitiveTask:
        """Process an implementation task"""
        # Implementation would depend on specific implementation logic
        # This is a placeholder for the actual implementation
        
        # Update task with result
        task.result = {
            "implementation_completed": True,
            "files_modified": ["file1.py", "file2.py"]
        }
        task.update_status(TaskStatus.COMPLETED)
        
        return task
    
    async def can_handle(self, task: CognitiveTask) -> bool:
        """Check if this worker can handle the given task"""
        return task.worker_type == WorkerType.IMPLEMENTATION or (
            task.phase == CognitivePhase.EXECUTE and
            "implement" in task.title.lower() or "implement" in task.description.lower()
        )

class EvaluationWorker(WorkerInterface):
    """Worker for evaluation tasks"""
    
    async def process_task(self, task: CognitiveTask) -> CognitiveTask:
        """Process an evaluation task"""
        # Implementation would depend on specific evaluation logic
        # This is a placeholder for the actual implementation
        
        # Update task with result
        task.result = {
            "evaluation_completed": True,
            "success": True,
            "metrics": {
                "accuracy": 0.95,
                "performance": 0.87
            }
        }
        task.update_status(TaskStatus.COMPLETED)
        
        return task
    
    async def can_handle(self, task: CognitiveTask) -> bool:
        """Check if this worker can handle the given task"""
        return task.worker_type == WorkerType.EVALUATION or (
            task.phase == CognitivePhase.REFLECT and
            "evaluate" in task.title.lower() or "evaluate" in task.description.lower()
        ) 