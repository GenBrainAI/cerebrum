"""
Unit tests for the integration of the Goal Decomposition Engine with the PlanningWorker.
"""

import pytest
import asyncio
from unittest.mock import MagicMock, patch, AsyncMock
import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional

from src.server.system.cognitive_loop import (
    PlanningWorker,
    CognitiveTask,
    CognitivePhase,
    WorkerType,
    TaskStatus,
    TaskPriority
)
from src.server.planning.goal_decomposition import (
    GoalDecompositionEngine,
    GoalType,
    DecompositionStrategy,
    ResourceEstimate,
    SubGoal,
    DecomposedGoal
)

@pytest.fixture
def mock_knowledge_system():
    """Create a mock knowledge system."""
    mock = MagicMock()
    mock.query_semantic_memory = AsyncMock(return_value=[
        {"id": "1", "content": "Test knowledge item 1"},
        {"id": "2", "content": "Test knowledge item 2"}
    ])
    return mock

@pytest.fixture
def mock_parameter_manager():
    """Create a mock parameter manager."""
    mock = MagicMock()
    mock.get_optimal_parameters = MagicMock(return_value={
        "temperature": 0.7,
        "max_tokens": 1000
    })
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
    mock.prioritize_subgoals = AsyncMock(return_value=root_ids)
    mock.estimate_resources = AsyncMock(return_value=total_resources)
    
    # Add get_critical_path method to the decomposed goal
    decomposed_goal.get_critical_path = MagicMock(return_value=["subgoal_0", "subgoal_1", "subgoal_2"])
    
    return mock

@pytest.fixture
def planning_worker(mock_knowledge_system, mock_parameter_manager, mock_goal_decomposition_engine):
    """Create a PlanningWorker instance with mocked components."""
    return PlanningWorker(
        knowledge_system=mock_knowledge_system,
        parameter_manager=mock_parameter_manager,
        goal_decomposition_engine=mock_goal_decomposition_engine
    )

@pytest.fixture
def planning_task():
    """Create a planning task."""
    return CognitiveTask(
        id=str(uuid.uuid4()),
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

class TestPlanningWorker:
    """Test suite for the PlanningWorker."""
    
    @pytest.mark.asyncio
    async def test_planning_worker_initialization(self, planning_worker, mock_knowledge_system, mock_parameter_manager, mock_goal_decomposition_engine):
        """Test the initialization of the PlanningWorker."""
        assert planning_worker.knowledge_system == mock_knowledge_system
        assert planning_worker.parameter_manager == mock_parameter_manager
        assert planning_worker.goal_decomposition_engine == mock_goal_decomposition_engine
    
    @pytest.mark.asyncio
    async def test_can_handle(self, planning_worker):
        """Test the can_handle method of the PlanningWorker."""
        # Create tasks with different characteristics
        planning_task = CognitiveTask(
            id=str(uuid.uuid4()),
            title="Plan Feature Implementation",
            description="Create a plan for implementing Feature Y",
            phase=CognitivePhase.PLAN,
            worker_type=WorkerType.PLANNING,
            priority=TaskPriority.HIGH
        )
        
        non_planning_task = CognitiveTask(
            id=str(uuid.uuid4()),
            title="Implement Feature",
            description="Implement Feature Y",
            phase=CognitivePhase.EXECUTE,
            worker_type=WorkerType.IMPLEMENTATION,
            priority=TaskPriority.HIGH
        )
        
        plan_phase_task = CognitiveTask(
            id=str(uuid.uuid4()),
            title="Create Plan",
            description="Create a plan for the project",
            phase=CognitivePhase.PLAN,
            worker_type=None,
            priority=TaskPriority.HIGH
        )
        
        # Test can_handle with different tasks
        assert await planning_worker.can_handle(planning_task) is True
        assert await planning_worker.can_handle(non_planning_task) is False
        assert await planning_worker.can_handle(plan_phase_task) is True
    
    @pytest.mark.asyncio
    async def test_process_task_with_goal_decomposition_engine(self, planning_worker, planning_task, mock_goal_decomposition_engine):
        """Test the process_task method of the PlanningWorker with a goal decomposition engine."""
        # Process the task
        processed_task = await planning_worker.process_task(planning_task)
        
        # Verify the result
        assert processed_task.status == TaskStatus.COMPLETED
        assert processed_task.result is not None
        assert processed_task.result["plan_created"] is True
        assert processed_task.result["decomposed_goal_id"] == "test_goal_id"
        assert processed_task.result["goal_name"] == "Test Goal"
        assert processed_task.result["subgoal_count"] == 3
        assert "prioritized_subgoals" in processed_task.result
        assert len(processed_task.result["prioritized_subgoals"]) == 3
        assert "resource_estimate" in processed_task.result
        assert processed_task.result["resource_estimate"]["time_hours"] == 6.0
        assert processed_task.result["resource_estimate"]["complexity"] == 5
        assert processed_task.result["resource_estimate"]["risk_level"] == 3
        assert "critical_path" in processed_task.result
        assert len(processed_task.result["critical_path"]) == 3
        
        # Verify that the goal decomposition engine was called correctly
        mock_goal_decomposition_engine.decompose_goal.assert_called_once()
        call_args = mock_goal_decomposition_engine.decompose_goal.call_args[1]
        assert call_args["goal"]["name"] == planning_task.title
        assert call_args["goal"]["description"] == planning_task.description
        assert call_args["goal"]["type"] == "DEVELOPMENT"
        
        # Import DecompositionStrategy for comparison
        assert call_args["strategy"] == DecompositionStrategy.TOP_DOWN
        
        assert call_args["context"] == planning_task.context
        
        mock_goal_decomposition_engine.prioritize_subgoals.assert_called_once_with("test_goal_id")
        mock_goal_decomposition_engine.estimate_resources.assert_called_once_with("test_goal_id")
    
    @pytest.mark.asyncio
    async def test_process_task_without_goal_decomposition_engine(self, mock_knowledge_system, mock_parameter_manager, planning_task):
        """Test the process_task method of the PlanningWorker without a goal decomposition engine."""
        # Create a planning worker without a goal decomposition engine
        planning_worker = PlanningWorker(
            knowledge_system=mock_knowledge_system,
            parameter_manager=mock_parameter_manager,
            goal_decomposition_engine=None
        )
        
        # Process the task
        processed_task = await planning_worker.process_task(planning_task)
        
        # Verify the result
        assert processed_task.status == TaskStatus.COMPLETED
        assert processed_task.result is not None
        assert processed_task.result["plan_created"] is True
        assert "steps" in processed_task.result
        assert len(processed_task.result["steps"]) > 0
        assert "note" in processed_task.result
        assert "Goal Decomposition Engine is not available" in processed_task.result["note"]
    
    @pytest.mark.asyncio
    async def test_process_task_with_error(self, planning_worker, planning_task, mock_goal_decomposition_engine):
        """Test the process_task method of the PlanningWorker when an error occurs."""
        # Make the goal decomposition engine raise an exception
        mock_goal_decomposition_engine.decompose_goal.side_effect = Exception("Test error")
        
        # Process the task
        processed_task = await planning_worker.process_task(planning_task)
        
        # Verify the result
        assert processed_task.status == TaskStatus.FAILED
        assert processed_task.error is not None
        assert "Error in planning task" in processed_task.error
        assert "Test error" in processed_task.error
    
    @pytest.mark.asyncio
    async def test_process_task_with_different_goal_types(self, planning_worker, mock_goal_decomposition_engine):
        """Test the process_task method of the PlanningWorker with different goal types."""
        # Create tasks with different goal types
        goal_types = ["RESEARCH", "ANALYSIS", "INTEGRATION", "OPTIMIZATION", "TESTING", "DOCUMENTATION", "GENERAL"]
        
        for goal_type in goal_types:
            # Create a task with the current goal type
            task = CognitiveTask(
                id=str(uuid.uuid4()),
                title=f"Plan {goal_type} Task",
                description=f"Create a plan for {goal_type} task",
                phase=CognitivePhase.PLAN,
                worker_type=WorkerType.PLANNING,
                priority=TaskPriority.HIGH,
                context={
                    "goal_type": goal_type,
                    "decomposition_strategy": "TOP_DOWN"
                }
            )
            
            # Process the task
            processed_task = await planning_worker.process_task(task)
            
            # Verify the result
            assert processed_task.status == TaskStatus.COMPLETED
            assert processed_task.result is not None
            assert processed_task.result["plan_created"] is True
            
            # Verify that the goal decomposition engine was called with the correct goal type
            call_args = mock_goal_decomposition_engine.decompose_goal.call_args[1]
            assert call_args["goal"]["type"] == goal_type
    
    @pytest.mark.asyncio
    async def test_process_task_with_different_strategies(self, planning_worker, mock_goal_decomposition_engine):
        """Test the process_task method of the PlanningWorker with different decomposition strategies."""
        # Import DecompositionStrategy for comparison
        from src.server.planning.goal_decomposition import DecompositionStrategy
        
        # Create tasks with different decomposition strategies
        strategies = ["TOP_DOWN", "BOTTOM_UP", "ITERATIVE", "DOMAIN_SPECIFIC"]
        strategy_enums = {
            "TOP_DOWN": DecompositionStrategy.TOP_DOWN,
            "BOTTOM_UP": DecompositionStrategy.BOTTOM_UP,
            "ITERATIVE": DecompositionStrategy.ITERATIVE,
            "DOMAIN_SPECIFIC": DecompositionStrategy.DOMAIN_SPECIFIC
        }
        
        for strategy in strategies:
            # Create a task with the current strategy
            task = CognitiveTask(
                id=str(uuid.uuid4()),
                title=f"Plan with {strategy} Strategy",
                description=f"Create a plan using {strategy} strategy",
                phase=CognitivePhase.PLAN,
                worker_type=WorkerType.PLANNING,
                priority=TaskPriority.HIGH,
                context={
                    "goal_type": "DEVELOPMENT",
                    "decomposition_strategy": strategy
                }
            )
            
            # Process the task
            processed_task = await planning_worker.process_task(task)
            
            # Verify the result
            assert processed_task.status == TaskStatus.COMPLETED
            assert processed_task.result is not None
            assert processed_task.result["plan_created"] is True
            
            # Verify that the goal decomposition engine was called with the correct strategy
            call_args = mock_goal_decomposition_engine.decompose_goal.call_args[1]
            assert call_args["strategy"] == strategy_enums[strategy] 