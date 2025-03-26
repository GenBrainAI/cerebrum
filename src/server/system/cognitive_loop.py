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
    
    async def initialize(self):
        """Initialize the Cognitive Loop Orchestrator."""
        # This method is called by the SelfAwareSystem during initialization
        # Currently, all initialization is done in __init__, so this is just a placeholder
        # for future async initialization tasks
        logger.info("Cognitive Loop Orchestrator initialized")
        return True
    
    async def register_worker(self, worker_type: WorkerType, worker: WorkerInterface) -> None:
        """Register a worker for a specific worker type.
        
        Args:
            worker_type: Type of worker to register
            worker: Worker instance to register
        """
        if worker_type not in self.workers:
            self.workers[worker_type] = []
        
        self.workers[worker_type].append(worker)
        logger.info(f"Registered worker for {worker_type.value}")
    
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
    
    async def create_task(self, title: str, description: str, phase: CognitivePhase, 
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
    
    async def get_task(self, task_id: str) -> Optional[CognitiveTask]:
        """Get a task by ID"""
        return self.tasks.get(task_id)
    
    async def update_task(self, task_id: str, **kwargs) -> bool:
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
    
    async def update_task_status(self, task_id: str, status: TaskStatus) -> bool:
        """Update a task's status"""
        if task_id not in self.tasks:
            return False
        
        task = self.tasks[task_id]
        task.update_status(status)
        self._save_data()
        return True
    
    async def set_task_result(self, task_id: str, result: Any) -> bool:
        """Set a task's result"""
        if task_id not in self.tasks:
            return False
        
        task = self.tasks[task_id]
        task.result = result
        task.update_status(TaskStatus.COMPLETED)
        self._save_data()
        return True
    
    async def set_task_error(self, task_id: str, error: str) -> bool:
        """Set a task's error"""
        if task_id not in self.tasks:
            return False
        
        task = self.tasks[task_id]
        task.error = error
        task.update_status(TaskStatus.FAILED)
        self._save_data()
        return True
    
    async def get_tasks_by_phase(self, phase: CognitivePhase, status: Optional[TaskStatus] = None) -> List[CognitiveTask]:
        """Get all tasks in a specific phase"""
        tasks = [task for task in self.tasks.values() if task.phase == phase]
        if status:
            tasks = [task for task in tasks if task.status == status]
        return tasks
    
    async def get_tasks_by_worker(self, worker_type: WorkerType, status: Optional[TaskStatus] = None) -> List[CognitiveTask]:
        """Get all tasks assigned to a specific worker type"""
        tasks = [task for task in self.tasks.values() if task.worker_type == worker_type]
        if status:
            tasks = [task for task in tasks if task.status == status]
        return tasks
    
    async def get_subtasks(self, task_id: str) -> List[CognitiveTask]:
        """Get all subtasks of a task"""
        if task_id not in self.tasks:
            return []
        return [self.tasks[subtask_id] for subtask_id in self.tasks[task_id].subtasks if subtask_id in self.tasks]
    
    async def set_current_phase(self, phase: CognitivePhase) -> None:
        """Set the current cognitive phase"""
        self.current_phase = phase
        self._save_data()
    
    async def get_current_phase(self) -> CognitivePhase:
        """Get the current cognitive phase"""
        return self.current_phase
    
    async def update_development_context(self, key: str, value: Any) -> None:
        """Update a value in the development context"""
        self.development_context[key] = value
        self._save_data()
    
    async def get_development_context(self, key: Optional[str] = None) -> Any:
        """Get a value from the development context"""
        if key is None:
            return self.development_context
        return self.development_context.get(key)
    
    async def _handle_understand_phase(self) -> bool:
        """Handle the understand phase of the cognitive loop"""
        # Get all pending understand tasks
        tasks = await self.get_tasks_by_phase(CognitivePhase.UNDERSTAND, TaskStatus.PENDING)
        
        # Sort by priority
        tasks.sort(key=lambda t: t.priority.value, reverse=True)
        
        # Process tasks with appropriate workers
        for task in tasks:
            if task.worker_type:
                # Task has a specific worker type
                workers = self.workers.get(task.worker_type, [])
                for worker in workers:
                    if await worker.can_handle(task):
                        await self.update_task_status(task.id, TaskStatus.IN_PROGRESS)
                        
                        try:
                            updated_task = await worker.process_task(task)
                            self.tasks[task.id] = updated_task
                            self._save_data()
                        except Exception as e:
                            logger.error(f"Error processing task {task.id}: {e}")
                            await self.set_task_error(task.id, str(e))
                        
                        break
            else:
                # Task doesn't have a specific worker type, try all workers
                for worker_type, workers in self.workers.items():
                    for worker in workers:
                        if await worker.can_handle(task):
                            await self.update_task_status(task.id, TaskStatus.IN_PROGRESS)
                            await self.update_task(task.id, worker_type=worker_type)
                            
                            try:
                                updated_task = await worker.process_task(task)
                                self.tasks[task.id] = updated_task
                                self._save_data()
                            except Exception as e:
                                logger.error(f"Error processing task {task.id}: {e}")
                                await self.set_task_error(task.id, str(e))
                            
                            break
                    else:
                        continue
                    break
        
        # Check if all understand tasks are completed
        pending_tasks = await self.get_tasks_by_phase(CognitivePhase.UNDERSTAND, TaskStatus.PENDING)
        in_progress_tasks = await self.get_tasks_by_phase(CognitivePhase.UNDERSTAND, TaskStatus.IN_PROGRESS)
        
        if not pending_tasks and not in_progress_tasks:
            # All understand tasks are completed, move to plan phase
            await self.set_current_phase(CognitivePhase.PLAN)
            return True
        
        return False
    
    async def _handle_plan_phase(self) -> bool:
        """Handle the plan phase of the cognitive loop"""
        # Get all pending plan tasks
        tasks = await self.get_tasks_by_phase(CognitivePhase.PLAN, TaskStatus.PENDING)
        
        # Sort by priority
        tasks.sort(key=lambda t: t.priority.value, reverse=True)
        
        # Process tasks with appropriate workers
        for task in tasks:
            if task.worker_type:
                # Task has a specific worker type
                workers = self.workers.get(task.worker_type, [])
                for worker in workers:
                    if await worker.can_handle(task):
                        await self.update_task_status(task.id, TaskStatus.IN_PROGRESS)
                        
                        try:
                            updated_task = await worker.process_task(task)
                            self.tasks[task.id] = updated_task
                            self._save_data()
                        except Exception as e:
                            logger.error(f"Error processing task {task.id}: {e}")
                            await self.set_task_error(task.id, str(e))
                        
                        break
            else:
                # Task doesn't have a specific worker type, try all workers
                for worker_type, workers in self.workers.items():
                    for worker in workers:
                        if await worker.can_handle(task):
                            await self.update_task_status(task.id, TaskStatus.IN_PROGRESS)
                            await self.update_task(task.id, worker_type=worker_type)
                            
                            try:
                                updated_task = await worker.process_task(task)
                                self.tasks[task.id] = updated_task
                                self._save_data()
                            except Exception as e:
                                logger.error(f"Error processing task {task.id}: {e}")
                                await self.set_task_error(task.id, str(e))
                            
                            break
                    else:
                        continue
                    break
        
        # Check if all plan tasks are completed
        pending_tasks = await self.get_tasks_by_phase(CognitivePhase.PLAN, TaskStatus.PENDING)
        in_progress_tasks = await self.get_tasks_by_phase(CognitivePhase.PLAN, TaskStatus.IN_PROGRESS)
        
        if not pending_tasks and not in_progress_tasks:
            # All plan tasks are completed, move to execute phase
            await self.set_current_phase(CognitivePhase.EXECUTE)
            return True
        
        return False
    
    async def _handle_execute_phase(self) -> bool:
        """Handle the execute phase of the cognitive loop"""
        # Get all pending execute tasks
        tasks = await self.get_tasks_by_phase(CognitivePhase.EXECUTE, TaskStatus.PENDING)
        
        # Sort by priority
        tasks.sort(key=lambda t: t.priority.value, reverse=True)
        
        # Process tasks with appropriate workers
        for task in tasks:
            if task.worker_type:
                # Task has a specific worker type
                workers = self.workers.get(task.worker_type, [])
                for worker in workers:
                    if await worker.can_handle(task):
                        await self.update_task_status(task.id, TaskStatus.IN_PROGRESS)
                        
                        try:
                            updated_task = await worker.process_task(task)
                            self.tasks[task.id] = updated_task
                            self._save_data()
                        except Exception as e:
                            logger.error(f"Error processing task {task.id}: {e}")
                            await self.set_task_error(task.id, str(e))
                        
                        break
            else:
                # Task doesn't have a specific worker type, try all workers
                for worker_type, workers in self.workers.items():
                    for worker in workers:
                        if await worker.can_handle(task):
                            await self.update_task_status(task.id, TaskStatus.IN_PROGRESS)
                            await self.update_task(task.id, worker_type=worker_type)
                            
                            try:
                                updated_task = await worker.process_task(task)
                                self.tasks[task.id] = updated_task
                                self._save_data()
                            except Exception as e:
                                logger.error(f"Error processing task {task.id}: {e}")
                                await self.set_task_error(task.id, str(e))
                            
                            break
                    else:
                        continue
                    break
        
        # Check if all execute tasks are completed
        pending_tasks = await self.get_tasks_by_phase(CognitivePhase.EXECUTE, TaskStatus.PENDING)
        in_progress_tasks = await self.get_tasks_by_phase(CognitivePhase.EXECUTE, TaskStatus.IN_PROGRESS)
        
        if not pending_tasks and not in_progress_tasks:
            # All execute tasks are completed, move to reflect phase
            await self.set_current_phase(CognitivePhase.REFLECT)
            return True
        
        return False
    
    async def _handle_reflect_phase(self) -> bool:
        """Handle the reflect phase of the cognitive loop"""
        # Get all pending reflect tasks
        tasks = await self.get_tasks_by_phase(CognitivePhase.REFLECT, TaskStatus.PENDING)
        
        # Sort by priority
        tasks.sort(key=lambda t: t.priority.value, reverse=True)
        
        # Process tasks with appropriate workers
        for task in tasks:
            if task.worker_type:
                # Task has a specific worker type
                workers = self.workers.get(task.worker_type, [])
                for worker in workers:
                    if await worker.can_handle(task):
                        await self.update_task_status(task.id, TaskStatus.IN_PROGRESS)
                        
                        try:
                            updated_task = await worker.process_task(task)
                            self.tasks[task.id] = updated_task
                            self._save_data()
                        except Exception as e:
                            logger.error(f"Error processing task {task.id}: {e}")
                            await self.set_task_error(task.id, str(e))
                        
                        break
            else:
                # Task doesn't have a specific worker type, try all workers
                for worker_type, workers in self.workers.items():
                    for worker in workers:
                        if await worker.can_handle(task):
                            await self.update_task_status(task.id, TaskStatus.IN_PROGRESS)
                            await self.update_task(task.id, worker_type=worker_type)
                            
                            try:
                                updated_task = await worker.process_task(task)
                                self.tasks[task.id] = updated_task
                                self._save_data()
                            except Exception as e:
                                logger.error(f"Error processing task {task.id}: {e}")
                                await self.set_task_error(task.id, str(e))
                            
                            break
                    else:
                        continue
                    break
        
        # Check if all reflect tasks are completed
        pending_tasks = await self.get_tasks_by_phase(CognitivePhase.REFLECT, TaskStatus.PENDING)
        in_progress_tasks = await self.get_tasks_by_phase(CognitivePhase.REFLECT, TaskStatus.IN_PROGRESS)
        
        if not pending_tasks and not in_progress_tasks:
            # All reflect tasks are completed, move back to understand phase for the next cycle
            await self.set_current_phase(CognitivePhase.UNDERSTAND)
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
        await self.set_current_phase(CognitivePhase.UNDERSTAND)
        
        # Process each phase until completion
        max_iterations = 100  # Prevent infinite loops
        iteration_count = 0
        
        while iteration_count < max_iterations:
            iteration_count += 1
            phase_completed = await self.process_current_phase()
            
            current_phase = await self.get_current_phase()
            if phase_completed and current_phase == CognitivePhase.UNDERSTAND:
                # We've completed a full cycle
                break
        
        if iteration_count >= max_iterations:
            logger.warning(f"Cognitive cycle reached maximum iterations ({max_iterations}). Possible infinite loop detected.")
    
    async def run_continuous(self, interval_seconds: float = 1.0) -> None:
        """Run the cognitive loop continuously"""
        while True:
            await self.process_current_phase()
            await asyncio.sleep(interval_seconds)

    async def get_tasks(self) -> Dict[str, CognitiveTask]:
        """Get all tasks in the system"""
        return self.tasks

class RequirementsWorker(WorkerInterface):
    """Worker for requirements analysis tasks"""
    
    def __init__(self, knowledge_system=None, parameter_manager=None):
        """Initialize the RequirementsWorker.
        
        Args:
            knowledge_system: Knowledge Integration System for context
            parameter_manager: AI Parameter Manager for optimal parameters
        """
        self.knowledge_system = knowledge_system
        self.parameter_manager = parameter_manager
    
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
    
    def __init__(self, knowledge_system=None, parameter_manager=None, goal_decomposition_engine=None):
        """Initialize the PlanningWorker.
        
        Args:
            knowledge_system: Knowledge Integration System for context
            parameter_manager: AI Parameter Manager for optimal parameters
            goal_decomposition_engine: Goal Decomposition Engine for breaking down goals
        """
        self.knowledge_system = knowledge_system
        self.parameter_manager = parameter_manager
        self.goal_decomposition_engine = goal_decomposition_engine
    
    async def process_task(self, task: CognitiveTask) -> CognitiveTask:
        """Process a planning task"""
        try:
            # Extract goal information from task
            goal_info = {
                "name": task.title,
                "description": task.description,
                "type": task.context.get("goal_type", "GENERAL"),
                "metadata": {
                    "task_id": task.id,
                    "priority": str(task.priority.name).lower(),
                    "created_at": task.created_at.isoformat()
                }
            }
            
            # Extract decomposition strategy from context or use default
            strategy_str = task.context.get("decomposition_strategy", "TOP_DOWN")
            
            # Convert string to DecompositionStrategy enum
            try:
                from src.server.planning.goal_decomposition import DecompositionStrategy
                strategy = DecompositionStrategy.from_str(strategy_str)
            except (ValueError, ImportError) as e:
                logger.warning(f"Error converting strategy string: {e}, using TOP_DOWN")
                from src.server.planning.goal_decomposition import DecompositionStrategy
                strategy = DecompositionStrategy.TOP_DOWN
            
            # Use Goal Decomposition Engine if available
            if self.goal_decomposition_engine:
                # Decompose the goal
                decomposed_goal = await self.goal_decomposition_engine.decompose_goal(
                    goal=goal_info,
                    strategy=strategy,
                    context=task.context
                )
                
                # Prioritize subgoals
                prioritized_subgoals = await self.goal_decomposition_engine.prioritize_subgoals(decomposed_goal.id)
                
                # Estimate resources
                resource_estimate = await self.goal_decomposition_engine.estimate_resources(decomposed_goal.id)
                
                # Update task with result
                task.result = {
                    "plan_created": True,
                    "decomposed_goal_id": decomposed_goal.id,
                    "goal_name": decomposed_goal.name,
                    "subgoal_count": len(decomposed_goal.subgoals),
                    "prioritized_subgoals": prioritized_subgoals,
                    "resource_estimate": {
                        "time_hours": resource_estimate.time_hours,
                        "complexity": resource_estimate.complexity,
                        "knowledge_requirements": resource_estimate.knowledge_requirements,
                        "dependencies": resource_estimate.dependencies,
                        "risk_level": resource_estimate.risk_level
                    },
                    "critical_path": decomposed_goal.get_critical_path()
                }
            else:
                # Fallback to simple planning if Goal Decomposition Engine is not available
                task.result = {
                    "plan_created": True,
                    "steps": ["Step 1", "Step 2", "Step 3"],
                    "note": "Using fallback planning as Goal Decomposition Engine is not available"
                }
            
            task.update_status(TaskStatus.COMPLETED)
            
        except Exception as e:
            task.error = f"Error in planning task: {str(e)}"
            task.update_status(TaskStatus.FAILED)
        
        return task
    
    async def can_handle(self, task: CognitiveTask) -> bool:
        """Check if this worker can handle the given task"""
        return task.worker_type == WorkerType.PLANNING or (
            task.phase == CognitivePhase.PLAN and
            ("plan" in task.title.lower() or "plan" in task.description.lower())
        )

class ImplementationWorker(WorkerInterface):
    """Worker for implementation tasks"""
    
    def __init__(self, knowledge_system=None, parameter_manager=None, code_generator=None, safety_validator=None):
        """Initialize the ImplementationWorker.
        
        Args:
            knowledge_system: Knowledge Integration System for context
            parameter_manager: AI Parameter Manager for optimal parameters
            code_generator: Code Generator for generating code
            safety_validator: Safety Validator for validating code
        """
        self.knowledge_system = knowledge_system
        self.parameter_manager = parameter_manager
        self.code_generator = code_generator
        self.safety_validator = safety_validator
    
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
    
    def __init__(self, knowledge_system=None, parameter_manager=None, test_runner=None):
        """Initialize the EvaluationWorker.
        
        Args:
            knowledge_system: Knowledge Integration System for context
            parameter_manager: AI Parameter Manager for optimal parameters
            test_runner: Test Runner for running tests
        """
        self.knowledge_system = knowledge_system
        self.parameter_manager = parameter_manager
        self.test_runner = test_runner
    
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