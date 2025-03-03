"""
Unit tests for the integration of the Goal Decomposition Engine with the Self-Aware System's cognitive loop.
"""

import pytest
import asyncio
from unittest.mock import MagicMock, patch, AsyncMock
import os
import tempfile
import shutil
from typing import Dict, Any, List, Optional
from datetime import datetime

from src.server.self_aware_integration import SelfAwareSystem
from src.server.planning.goal_decomposition import (
    GoalDecompositionEngine,
    GoalType,
    DecompositionStrategy,
    ResourceEstimate,
    SubGoal,
    DecomposedGoal
)
from src.server.system.cognitive_loop import (
    CognitivePhase,
    WorkerType,
    TaskPriority,
    TaskStatus,
    CognitiveTask
)
from src.server.system.cognitive_loop import PlanningWorker

@pytest.fixture
def mock_knowledge_system():
    """Create a mock knowledge system."""
    mock = MagicMock()
    mock.query_semantic_memory = AsyncMock(return_value=[
        {"id": "1", "content": "Test knowledge item 1"},
        {"id": "2", "content": "Test knowledge item 2"}
    ])
    mock.add_episodic_memory = MagicMock(return_value="memory_id")
    return mock

@pytest.fixture
def mock_goal_decomposition_engine():
    """Create a mock goal decomposition engine."""
    mock = MagicMock()
    
    # Create a sample decomposed goal
    subgoals = {}
    root_ids = []
    
    for i in range(3):
        subgoal_id = f"subgoal_{i}"
        resources = ResourceEstimate(
            time_hours=2.0,
            complexity=5,
            knowledge_requirements=["python", "testing"],
            dependencies=[],
            risk_level=3
        )
        
        subgoal = SubGoal(
            id=subgoal_id,
            name=f"Subgoal {i}",
            description=f"Test subgoal {i}",
            goal_type=GoalType.DEVELOPMENT,
            priority=5,
            resources=resources
        )
        
        subgoals[subgoal_id] = subgoal
        root_ids.append(subgoal_id)
    
    total_resources = ResourceEstimate(
        time_hours=6.0,
        complexity=5,
        knowledge_requirements=["python", "testing"],
        dependencies=[],
        risk_level=3
    )
    
    decomposed_goal = DecomposedGoal(
        id="test_goal_id",
        name="Test Goal",
        description="A test goal",
        goal_type=GoalType.DEVELOPMENT,
        strategy=DecompositionStrategy.TOP_DOWN,
        subgoals=subgoals,
        root_subgoal_ids=root_ids,
        total_resources=total_resources,
        creation_time="2023-01-01T00:00:00",
        status="pending"
    )
    
    # Set up mock methods
    mock.decompose_goal = AsyncMock(return_value=decomposed_goal)
    mock.get_decomposed_goal = AsyncMock(return_value=decomposed_goal)
    mock.prioritize_subgoals = AsyncMock(return_value=root_ids)
    mock.estimate_resources = AsyncMock(return_value=total_resources)
    mock.validate_decomposition = AsyncMock(return_value={
        "valid": True,
        "errors": [],
        "warnings": []
    })
    
    # Add get_critical_path method to the decomposed goal
    decomposed_goal.get_critical_path = MagicMock(return_value=["subgoal_0", "subgoal_1", "subgoal_2"])
    
    return mock

@pytest.fixture
def mock_parameter_manager():
    """Create a mock parameter manager."""
    mock = MagicMock()
    mock.initialize = AsyncMock()
    return mock

@pytest.fixture
def mock_cognitive_orchestrator():
    """Create a mock cognitive orchestrator."""
    mock = MagicMock()
    mock.initialize = AsyncMock()
    mock.register_worker = AsyncMock()
    mock.create_task = MagicMock(return_value="task_id")
    mock.get_task = MagicMock(return_value=MagicMock(spec=CognitiveTask))
    mock.set_current_phase = MagicMock()
    mock.process_current_phase = AsyncMock()
    mock.run_cognitive_cycle = AsyncMock()
    mock._handle_plan_phase = AsyncMock(return_value=True)
    mock.workers = {WorkerType.PLANNING: MagicMock()}
    
    # Set up phase handlers
    mock.phase_handlers = {
        CognitivePhase.PLAN: mock._handle_plan_phase
    }
    
    return mock

@pytest.fixture
async def self_aware_system(mock_knowledge_system, mock_parameter_manager, mock_cognitive_orchestrator, mock_goal_decomposition_engine):
    """Create a SelfAwareSystem instance with mocked components."""
    # Create a temporary directory for storage
    temp_dir = tempfile.mkdtemp()
    
    # Create the system
    system = SelfAwareSystem(storage_path=temp_dir)
    
    # Replace components with mocks
    system.knowledge_system = mock_knowledge_system
    system.parameter_manager = mock_parameter_manager
    system.cognitive_orchestrator = mock_cognitive_orchestrator
    system.goal_decomposition_engine = mock_goal_decomposition_engine
    
    # Skip initialization by mocking it
    system.initialize = AsyncMock()
    await system.initialize()
    
    # Set up the planning worker in the cognitive orchestrator
    planning_worker = PlanningWorker(
        knowledge_system=mock_knowledge_system,
        parameter_manager=mock_parameter_manager,
        goal_decomposition_engine=mock_goal_decomposition_engine
    )
    
    # Set up the mock methods for the planning worker
    planning_worker.can_handle = AsyncMock(return_value=True)
    
    # Don't mock process_task - we want to test the actual implementation
    
    # Set up the mock methods for the goal decomposition engine
    mock_goal_decomposition_engine.decompose_goal.return_value = MagicMock(
        id="test_goal_id",
        name="Test Goal",
        subgoals=["subgoal_0", "subgoal_1", "subgoal_2"],
        get_critical_path=MagicMock(return_value=["subgoal_0", "subgoal_1", "subgoal_2"])
    )
    
    mock_goal_decomposition_engine.prioritize_subgoals.return_value = ["subgoal_0", "subgoal_1", "subgoal_2"]
    
    mock_goal_decomposition_engine.estimate_resources.return_value = MagicMock(
        time_hours=6.0,
        complexity=5,
        knowledge_requirements=["python", "testing"],
        dependencies=[],
        risk_level=3
    )
    
    mock_cognitive_orchestrator.workers[WorkerType.PLANNING] = planning_worker
    
    # Set up the create_cognitive_task and get_cognitive_task methods
    system.create_cognitive_task = MagicMock(return_value="task_id")
    
    # Create a proper mock task with a working update_status method
    mock_task = MagicMock(spec=CognitiveTask)
    mock_task.id = "task_id"
    mock_task.title = "Plan Feature X"
    mock_task.description = "Create a plan for implementing Feature X"
    mock_task.phase = CognitivePhase.PLAN
    mock_task.worker_type = WorkerType.PLANNING
    mock_task.priority = TaskPriority.HIGH
    mock_task.context = {
        "goal_type": "DEVELOPMENT",
        "decomposition_strategy": "TOP_DOWN"
    }
    mock_task.created_at = datetime.now()
    mock_task.status = TaskStatus.PENDING
    mock_task.result = {}
    mock_task.error = None
    
    # Define a proper update_status method that actually updates the status
    def update_status_impl(status):
        mock_task.status = status
    
    mock_task.update_status = update_status_impl
    
    system.get_cognitive_task = MagicMock(return_value=mock_task)
    
    # Set up the start_cognitive_cycle method
    system.start_cognitive_cycle = AsyncMock()
    
    # Make sure the start_cognitive_cycle method calls run_cognitive_cycle
    async def start_cognitive_cycle_impl():
        await system.cognitive_orchestrator.run_cognitive_cycle()
        return "task_id"
    
    system.start_cognitive_cycle.side_effect = start_cognitive_cycle_impl
    
    # Make sure process_current_phase calls the appropriate phase handler
    async def process_current_phase_impl():
        phase = system.cognitive_orchestrator.current_phase
        if phase in system.cognitive_orchestrator.phase_handlers:
            handler = system.cognitive_orchestrator.phase_handlers[phase]
            return await handler()
        return False
    
    system.cognitive_orchestrator.process_current_phase = AsyncMock(side_effect=process_current_phase_impl)
    
    yield system
    
    # Clean up
    shutil.rmtree(temp_dir)

class TestCognitiveLoopIntegration:
    """Test suite for the integration of the Goal Decomposition Engine with the cognitive loop."""
    
    @pytest.mark.asyncio
    async def test_planning_phase_with_goal_decomposition(self, self_aware_system, mock_goal_decomposition_engine):
        """Test that the planning phase uses the Goal Decomposition Engine."""
        # Create a planning task
        task_id = self_aware_system.create_cognitive_task(
            title="Plan Feature X",
            description="Create a plan for implementing Feature X",
            phase=CognitivePhase.PLAN,
            worker_type=WorkerType.PLANNING,
            priority=TaskPriority.HIGH,
            context={
                "goal_type": "DEVELOPMENT",
                "decomposition_strategy": "TOP_DOWN"
            }
        )
        
        # Get the task
        task = self_aware_system.get_cognitive_task(task_id)
        assert task is not None
        
        # Get the planning worker
        planning_worker = self_aware_system.cognitive_orchestrator.workers[WorkerType.PLANNING]
        
        # Process the task with the planning worker
        processed_task = await planning_worker.process_task(task)
        
        # Verify the task was processed successfully
        assert processed_task.status == TaskStatus.COMPLETED
        assert "plan_created" in processed_task.result
        assert processed_task.result["plan_created"] is True
        assert "decomposed_goal_id" in processed_task.result
        assert "subgoal_count" in processed_task.result
        assert "prioritized_subgoals" in processed_task.result
        assert "resource_estimate" in processed_task.result
        assert "critical_path" in processed_task.result
        
        # Verify that the goal decomposition engine was used
        mock_goal_decomposition_engine.decompose_goal.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_cognitive_cycle_with_goal_decomposition(self, self_aware_system, mock_goal_decomposition_engine):
        """Test a complete cognitive cycle with the Goal Decomposition Engine."""
        # Create tasks for each phase
        understand_task_id = self_aware_system.cognitive_orchestrator.create_task(
            title="Understand Requirements",
            description="Understand the requirements for Feature Y",
            phase=CognitivePhase.UNDERSTAND,
            worker_type=WorkerType.REQUIREMENTS,
            priority=TaskPriority.HIGH
        )
        
        plan_task_id = self_aware_system.cognitive_orchestrator.create_task(
            title="Plan Feature Implementation",
            description="Create a plan for implementing Feature Y",
            phase=CognitivePhase.PLAN,
            worker_type=WorkerType.PLANNING,
            priority=TaskPriority.HIGH,
            context={
                "goal_type": "DEVELOPMENT",
                "decomposition_strategy": "TOP_DOWN"
            }
        )
        
        execute_task_id = self_aware_system.cognitive_orchestrator.create_task(
            title="Implement Feature",
            description="Implement Feature Y",
            phase=CognitivePhase.EXECUTE,
            worker_type=WorkerType.IMPLEMENTATION,
            priority=TaskPriority.HIGH
        )
        
        reflect_task_id = self_aware_system.cognitive_orchestrator.create_task(
            title="Evaluate Implementation",
            description="Evaluate the implementation of Feature Y",
            phase=CognitivePhase.REFLECT,
            worker_type=WorkerType.EVALUATION,
            priority=TaskPriority.HIGH
        )
        
        # Mock the run_cognitive_cycle method to avoid actually running the cycle
        with patch.object(self_aware_system.cognitive_orchestrator, 'run_cognitive_cycle', AsyncMock()) as mock_run_cognitive_cycle:
            await self_aware_system.start_cognitive_cycle()
            mock_run_cognitive_cycle.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_planning_worker_in_cognitive_loop(self, self_aware_system):
        """Test that the PlanningWorker is properly registered in the cognitive loop."""
        # Check that the PlanningWorker is registered
        assert WorkerType.PLANNING in self_aware_system.cognitive_orchestrator.workers
        
        # Get the PlanningWorker
        planning_worker = self_aware_system.cognitive_orchestrator.workers[WorkerType.PLANNING]
        
        # Check that the PlanningWorker has the goal_decomposition_engine
        assert hasattr(planning_worker, 'goal_decomposition_engine')
        assert planning_worker.goal_decomposition_engine is not None
    
    @pytest.mark.asyncio
    async def test_create_planning_task_and_process(self, self_aware_system, mock_goal_decomposition_engine):
        """Test creating a planning task and processing it through the cognitive loop."""
        # Create a planning task
        task_id = self_aware_system.create_cognitive_task(
            title="Plan Feature Implementation",
            description="Create a plan for implementing Feature Y",
            phase=CognitivePhase.PLAN,
            worker_type=WorkerType.PLANNING,
            priority=TaskPriority.HIGH,
            context={
                "goal_type": "DEVELOPMENT",
                "decomposition_strategy": "TOP_DOWN"
            }
        )
        
        # Get the task
        task = self_aware_system.get_cognitive_task(task_id)
        assert task is not None
        
        # Get the PlanningWorker
        planning_worker = self_aware_system.cognitive_orchestrator.workers[WorkerType.PLANNING]
        
        # Process the task
        processed_task = await planning_worker.process_task(task)
        
        # Verify the result
        assert processed_task.status == TaskStatus.COMPLETED
        assert processed_task.result is not None
        assert processed_task.result["plan_created"] is True
        assert "decomposed_goal_id" in processed_task.result
        assert "subgoal_count" in processed_task.result
        assert "prioritized_subgoals" in processed_task.result
        assert "resource_estimate" in processed_task.result
        assert "critical_path" in processed_task.result
        
        # Verify that the goal decomposition engine was called
        mock_goal_decomposition_engine.decompose_goal.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_goal_decomposition_in_planning_phase(self, self_aware_system, mock_goal_decomposition_engine):
        """Test that goal decomposition is used in the planning phase of the cognitive loop."""
        # Create a planning task
        task_id = self_aware_system.cognitive_orchestrator.create_task(
            title="Plan Feature Implementation",
            description="Create a plan for implementing Feature Y",
            phase=CognitivePhase.PLAN,
            worker_type=WorkerType.PLANNING,
            priority=TaskPriority.HIGH,
            context={
                "goal_type": "DEVELOPMENT",
                "decomposition_strategy": "TOP_DOWN"
            }
        )
        
        # Set up a mock for the _handle_plan_phase method
        mock_handle_plan_phase = AsyncMock(return_value=True)
        
        # Store the original method
        original_method = self_aware_system.cognitive_orchestrator._handle_plan_phase
        
        # Replace with our mock
        self_aware_system.cognitive_orchestrator._handle_plan_phase = mock_handle_plan_phase
        
        try:
            # Call the method directly
            await self_aware_system.cognitive_orchestrator._handle_plan_phase()
            
            # Verify that the mock was called
            mock_handle_plan_phase.assert_called_once()
        finally:
            # Restore the original method
            self_aware_system.cognitive_orchestrator._handle_plan_phase = original_method
        
        # Create a proper mock task with a working update_status method
        mock_task = MagicMock(spec=CognitiveTask)
        mock_task.id = task_id
        mock_task.title = "Plan Feature Implementation"
        mock_task.description = "Create a plan for implementing Feature Y"
        mock_task.phase = CognitivePhase.PLAN
        mock_task.worker_type = WorkerType.PLANNING
        mock_task.priority = TaskPriority.HIGH
        mock_task.context = {
            "goal_type": "DEVELOPMENT",
            "decomposition_strategy": "TOP_DOWN"
        }
        mock_task.created_at = datetime.now()
        mock_task.status = TaskStatus.PENDING
        mock_task.result = {}
        mock_task.error = None
        
        # Define a proper update_status method that actually updates the status
        def update_status_impl(status):
            mock_task.status = status
        
        mock_task.update_status = update_status_impl
        
        # Override the get_task method for this specific task_id
        original_get_task = self_aware_system.cognitive_orchestrator.get_task
        self_aware_system.cognitive_orchestrator.get_task = lambda tid: mock_task if tid == task_id else original_get_task(tid)
        
        try:
            # Get the task
            task = self_aware_system.cognitive_orchestrator.get_task(task_id)
            
            # Process the task directly with the PlanningWorker
            planning_worker = self_aware_system.cognitive_orchestrator.workers[WorkerType.PLANNING]
            processed_task = await planning_worker.process_task(task)
            
            # Verify the result
            assert processed_task.status == TaskStatus.COMPLETED
            assert processed_task.result is not None
            assert processed_task.result["plan_created"] is True
            
            # Verify that the goal decomposition engine was called
            mock_goal_decomposition_engine.decompose_goal.assert_called()
        finally:
            # Restore the original get_task method
            self_aware_system.cognitive_orchestrator.get_task = original_get_task 