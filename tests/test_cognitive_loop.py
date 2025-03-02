import pytest
import os
import shutil
import tempfile
import asyncio
from datetime import datetime

from src.server.system.cognitive_loop import (
    CognitiveLoopOrchestrator,
    CognitivePhase,
    WorkerType,
    TaskStatus,
    TaskPriority,
    CognitiveTask,
    WorkerInterface
)


class MockWorker(WorkerInterface):
    """Mock worker for testing"""
    
    def __init__(self, worker_type, can_handle_types=None):
        self.worker_type = worker_type
        self.can_handle_types = can_handle_types or [worker_type]
        self.processed_tasks = []
    
    async def process_task(self, task):
        """Process a task and return the updated task"""
        self.processed_tasks.append(task.id)
        task.update_status(TaskStatus.COMPLETED)
        task.result = {"processed_by": self.worker_type.value}
        return task
    
    async def can_handle(self, task):
        """Check if this worker can handle the given task"""
        if task.worker_type:
            return task.worker_type in self.can_handle_types
        return self.worker_type in self.can_handle_types


class TestCognitiveLoopOrchestrator:
    """Tests for the Cognitive Loop Orchestrator"""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for testing"""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)

    @pytest.fixture
    def orchestrator(self, temp_dir):
        """Create an orchestrator with a temporary storage path"""
        orchestrator = CognitiveLoopOrchestrator(storage_path=temp_dir)
        
        # Register mock workers
        orchestrator.register_worker(
            WorkerType.REQUIREMENTS,
            MockWorker(WorkerType.REQUIREMENTS)
        )
        
        orchestrator.register_worker(
            WorkerType.PLANNING,
            MockWorker(WorkerType.PLANNING)
        )
        
        orchestrator.register_worker(
            WorkerType.IMPLEMENTATION,
            MockWorker(WorkerType.IMPLEMENTATION)
        )
        
        orchestrator.register_worker(
            WorkerType.EVALUATION,
            MockWorker(WorkerType.EVALUATION)
        )
        
        return orchestrator

    def test_create_task(self, orchestrator):
        """Test creating a task"""
        task_id = orchestrator.create_task(
            title="Test Task",
            description="A test task",
            phase=CognitivePhase.UNDERSTAND,
            worker_type=WorkerType.REQUIREMENTS,
            priority=TaskPriority.HIGH
        )
        
        # Verify the task was created
        assert task_id in orchestrator.tasks
        task = orchestrator.tasks[task_id]
        assert task.title == "Test Task"
        assert task.description == "A test task"
        assert task.phase == CognitivePhase.UNDERSTAND
        assert task.worker_type == WorkerType.REQUIREMENTS
        assert task.priority == TaskPriority.HIGH
        assert task.status == TaskStatus.PENDING

    def test_get_task(self, orchestrator):
        """Test retrieving a task"""
        task_id = orchestrator.create_task(
            title="Test Task",
            description="A test task",
            phase=CognitivePhase.UNDERSTAND
        )
        
        # Retrieve the task
        task = orchestrator.get_task(task_id)
        assert task is not None
        assert task.title == "Test Task"
        assert task.description == "A test task"
        assert task.phase == CognitivePhase.UNDERSTAND

    def test_update_task(self, orchestrator):
        """Test updating a task"""
        task_id = orchestrator.create_task(
            title="Test Task",
            description="A test task",
            phase=CognitivePhase.UNDERSTAND
        )
        
        # Update the task
        result = orchestrator.update_task(
            task_id,
            title="Updated Task",
            description="An updated test task"
        )
        
        assert result is True
        task = orchestrator.get_task(task_id)
        assert task.title == "Updated Task"
        assert task.description == "An updated test task"
        assert task.phase == CognitivePhase.UNDERSTAND  # Unchanged

    def test_update_task_status(self, orchestrator):
        """Test updating a task's status"""
        task_id = orchestrator.create_task(
            title="Test Task",
            description="A test task",
            phase=CognitivePhase.UNDERSTAND
        )
        
        # Update the task status
        result = orchestrator.update_task_status(task_id, TaskStatus.IN_PROGRESS)
        assert result is True
        task = orchestrator.get_task(task_id)
        assert task.status == TaskStatus.IN_PROGRESS
        assert task.started_at is not None
        
        # Update to completed
        result = orchestrator.update_task_status(task_id, TaskStatus.COMPLETED)
        assert result is True
        task = orchestrator.get_task(task_id)
        assert task.status == TaskStatus.COMPLETED
        assert task.completed_at is not None

    def test_set_task_result(self, orchestrator):
        """Test setting a task's result"""
        task_id = orchestrator.create_task(
            title="Test Task",
            description="A test task",
            phase=CognitivePhase.UNDERSTAND
        )
        
        # Set the task result
        result = orchestrator.set_task_result(task_id, {"status": "success"})
        assert result is True
        task = orchestrator.get_task(task_id)
        assert task.result == {"status": "success"}
        assert task.status == TaskStatus.COMPLETED

    def test_set_task_error(self, orchestrator):
        """Test setting a task's error"""
        task_id = orchestrator.create_task(
            title="Test Task",
            description="A test task",
            phase=CognitivePhase.UNDERSTAND
        )
        
        # Set the task error
        result = orchestrator.set_task_error(task_id, "An error occurred")
        assert result is True
        task = orchestrator.get_task(task_id)
        assert task.error == "An error occurred"
        assert task.status == TaskStatus.FAILED

    def test_get_tasks_by_phase(self, orchestrator):
        """Test getting tasks by phase"""
        # Create tasks in different phases
        understand_id = orchestrator.create_task(
            title="Understand Task",
            description="An understand task",
            phase=CognitivePhase.UNDERSTAND
        )
        
        plan_id = orchestrator.create_task(
            title="Plan Task",
            description="A plan task",
            phase=CognitivePhase.PLAN
        )
        
        # Get tasks by phase
        understand_tasks = orchestrator.get_tasks_by_phase(CognitivePhase.UNDERSTAND)
        assert len(understand_tasks) == 1
        assert understand_tasks[0].id == understand_id
        
        plan_tasks = orchestrator.get_tasks_by_phase(CognitivePhase.PLAN)
        assert len(plan_tasks) == 1
        assert plan_tasks[0].id == plan_id
        
        # Get tasks by phase and status
        orchestrator.update_task_status(understand_id, TaskStatus.IN_PROGRESS)
        in_progress_tasks = orchestrator.get_tasks_by_phase(CognitivePhase.UNDERSTAND, TaskStatus.IN_PROGRESS)
        assert len(in_progress_tasks) == 1
        assert in_progress_tasks[0].id == understand_id

    def test_get_tasks_by_worker(self, orchestrator):
        """Test getting tasks by worker type"""
        # Create tasks with different worker types
        requirements_id = orchestrator.create_task(
            title="Requirements Task",
            description="A requirements task",
            phase=CognitivePhase.UNDERSTAND,
            worker_type=WorkerType.REQUIREMENTS
        )
        
        planning_id = orchestrator.create_task(
            title="Planning Task",
            description="A planning task",
            phase=CognitivePhase.PLAN,
            worker_type=WorkerType.PLANNING
        )
        
        # Get tasks by worker type
        requirements_tasks = orchestrator.get_tasks_by_worker(WorkerType.REQUIREMENTS)
        assert len(requirements_tasks) == 1
        assert requirements_tasks[0].id == requirements_id
        
        planning_tasks = orchestrator.get_tasks_by_worker(WorkerType.PLANNING)
        assert len(planning_tasks) == 1
        assert planning_tasks[0].id == planning_id

    def test_get_subtasks(self, orchestrator):
        """Test getting subtasks"""
        # Create a parent task
        parent_id = orchestrator.create_task(
            title="Parent Task",
            description="A parent task",
            phase=CognitivePhase.UNDERSTAND
        )
        
        # Create subtasks
        subtask1_id = orchestrator.create_task(
            title="Subtask 1",
            description="A subtask",
            phase=CognitivePhase.UNDERSTAND,
            parent_id=parent_id
        )
        
        subtask2_id = orchestrator.create_task(
            title="Subtask 2",
            description="Another subtask",
            phase=CognitivePhase.UNDERSTAND,
            parent_id=parent_id
        )
        
        # Get subtasks
        subtasks = orchestrator.get_subtasks(parent_id)
        assert len(subtasks) == 2
        assert any(task.id == subtask1_id for task in subtasks)
        assert any(task.id == subtask2_id for task in subtasks)

    def test_set_current_phase(self, orchestrator):
        """Test setting the current phase"""
        # Default phase should be UNDERSTAND
        assert orchestrator.get_current_phase() == CognitivePhase.UNDERSTAND
        
        # Set the phase to PLAN
        orchestrator.set_current_phase(CognitivePhase.PLAN)
        assert orchestrator.get_current_phase() == CognitivePhase.PLAN
        
        # Set the phase to EXECUTE
        orchestrator.set_current_phase(CognitivePhase.EXECUTE)
        assert orchestrator.get_current_phase() == CognitivePhase.EXECUTE
        
        # Set the phase to REFLECT
        orchestrator.set_current_phase(CognitivePhase.REFLECT)
        assert orchestrator.get_current_phase() == CognitivePhase.REFLECT

    def test_update_development_context(self, orchestrator):
        """Test updating the development context"""
        # Update a context value
        orchestrator.update_development_context("test_key", "test_value")
        assert orchestrator.get_development_context("test_key") == "test_value"
        
        # Update another context value
        orchestrator.update_development_context("another_key", {"nested": "value"})
        assert orchestrator.get_development_context("another_key") == {"nested": "value"}
        
        # Get the entire context
        context = orchestrator.get_development_context()
        assert context["test_key"] == "test_value"
        assert context["another_key"] == {"nested": "value"}

    @pytest.mark.asyncio
    async def test_process_current_phase(self, orchestrator):
        """Test processing the current phase"""
        # Create a task in the current phase (UNDERSTAND)
        task_id = orchestrator.create_task(
            title="Test Task",
            description="A test task",
            phase=CognitivePhase.UNDERSTAND,
            worker_type=WorkerType.REQUIREMENTS
        )
        
        # Process the current phase
        result = await orchestrator.process_current_phase()
        
        # The phase should be completed and the task should be processed
        assert result is True
        task = orchestrator.get_task(task_id)
        assert task.status == TaskStatus.COMPLETED
        assert task.result is not None
        assert task.result["processed_by"] == WorkerType.REQUIREMENTS.value
        
        # The phase should have changed to PLAN
        assert orchestrator.get_current_phase() == CognitivePhase.PLAN

    @pytest.mark.asyncio
    async def test_run_cognitive_cycle(self, orchestrator):
        """Test running a complete cognitive cycle"""
        # Create tasks in each phase
        understand_id = orchestrator.create_task(
            title="Understand Task",
            description="An understand task",
            phase=CognitivePhase.UNDERSTAND,
            worker_type=WorkerType.REQUIREMENTS
        )
        
        plan_id = orchestrator.create_task(
            title="Plan Task",
            description="A plan task",
            phase=CognitivePhase.PLAN,
            worker_type=WorkerType.PLANNING
        )
        
        execute_id = orchestrator.create_task(
            title="Execute Task",
            description="An execute task",
            phase=CognitivePhase.EXECUTE,
            worker_type=WorkerType.IMPLEMENTATION
        )
        
        reflect_id = orchestrator.create_task(
            title="Reflect Task",
            description="A reflect task",
            phase=CognitivePhase.REFLECT,
            worker_type=WorkerType.EVALUATION
        )
        
        # Run the cognitive cycle
        await orchestrator.run_cognitive_cycle()
        
        # All tasks should be completed
        assert orchestrator.get_task(understand_id).status == TaskStatus.COMPLETED
        assert orchestrator.get_task(plan_id).status == TaskStatus.COMPLETED
        assert orchestrator.get_task(execute_id).status == TaskStatus.COMPLETED
        assert orchestrator.get_task(reflect_id).status == TaskStatus.COMPLETED
        
        # The phase should be back to UNDERSTAND
        assert orchestrator.get_current_phase() == CognitivePhase.UNDERSTAND 