"""
Unit tests for the integration of the Goal Decomposition Engine with the Self-Aware System.
"""

import pytest
import asyncio
from unittest.mock import MagicMock, patch, AsyncMock
import os
import tempfile
import shutil
from typing import Dict, Any, List

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
    TaskStatus
)

@pytest.fixture
def mock_knowledge_system():
    """Create a mock knowledge system."""
    mock = MagicMock()
    mock.initialize = AsyncMock(return_value=True)
    mock.query_semantic_memory = AsyncMock(return_value=[
        {"id": "1", "content": "Test knowledge item 1"},
        {"id": "2", "content": "Test knowledge item 2"}
    ])
    mock.add_episodic_memory = MagicMock(return_value="memory_id")
    return mock

@pytest.fixture
def mock_parameter_manager():
    """Create a mock parameter manager."""
    mock = MagicMock()
    mock.initialize = AsyncMock(return_value=True)
    return mock

@pytest.fixture
def mock_cognitive_orchestrator():
    """Create a mock cognitive orchestrator."""
    mock = MagicMock()
    mock.initialize = AsyncMock(return_value=True)
    
    # Create a mock planning worker
    planning_worker = MagicMock()
    planning_worker.process_task = AsyncMock(return_value=MagicMock(
        status=TaskStatus.COMPLETED,
        result={
            "plan_created": True,
            "decomposed_goal_id": "test_goal_id",
            "subgoal_count": 3,
            "prioritized_subgoals": ["subgoal_0", "subgoal_1", "subgoal_2"],
            "resource_estimate": {
                "time_hours": 6.0,
                "complexity": 5,
                "knowledge_requirements": ["python", "testing"],
                "dependencies": [],
                "risk_level": 3
            },
            "critical_path": ["subgoal_0", "subgoal_1", "subgoal_2"]
        }
    ))
    
    # Set up the workers dictionary
    mock.workers = {
        WorkerType.PLANNING: [planning_worker]
    }
    
    # Set up other methods
    mock.create_task = MagicMock(return_value="task_id")
    mock.get_task = MagicMock(return_value=MagicMock(
        id="task_id",
        title="Test Task",
        description="A test task",
        phase=CognitivePhase.PLAN,
        worker_type=WorkerType.PLANNING,
        status=TaskStatus.PENDING
    ))
    
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
    
    return mock

@pytest.fixture
async def self_aware_system(mock_knowledge_system, mock_parameter_manager, mock_cognitive_orchestrator, mock_goal_decomposition_engine):
    """Create a SelfAwareSystem instance with mocked components."""
    # Create a temporary directory for storage
    temp_dir = tempfile.mkdtemp()
    
    # Create the system with patched components
    with patch('src.server.self_aware_integration.KnowledgeIntegrationSystem', return_value=mock_knowledge_system), \
         patch('src.server.self_aware_integration.AIParameterManager', return_value=mock_parameter_manager), \
         patch('src.server.self_aware_integration.CognitiveLoopOrchestrator', return_value=mock_cognitive_orchestrator), \
         patch('src.server.self_aware_integration.GoalDecompositionEngine', return_value=mock_goal_decomposition_engine), \
         patch('src.server.self_aware_integration.SelfAwareSystem.register_specialized_workers', new_callable=AsyncMock):
        
        system = SelfAwareSystem(storage_path=temp_dir)
        
        # Initialize the system
        await system.initialize()
        
        yield system
        
        # Clean up
        shutil.rmtree(temp_dir)

class TestSelfAwareIntegration:
    """Test suite for the integration of the Goal Decomposition Engine with the Self-Aware System."""
    
    @pytest.mark.asyncio
    async def test_decompose_goal(self, self_aware_system, mock_goal_decomposition_engine):
        """Test the decompose_goal method of the SelfAwareSystem."""
        # Create a test goal
        test_goal = {
            "name": "Test Goal",
            "description": "A test goal",
            "type": "DEVELOPMENT",
            "metadata": {
                "priority": "high",
                "owner": "test_user"
            }
        }
        
        # Decompose the goal
        result = await self_aware_system.decompose_goal(
            goal=test_goal,
            strategy="TOP_DOWN"
        )
        
        # Verify the result
        assert result is not None
        assert isinstance(result, dict)
        assert result["id"] == "test_goal_id"
        assert result["name"] == "Test Goal"
        assert result["goal_type"] == "DEVELOPMENT"
        assert result["strategy"] == "TOP_DOWN"
        assert "subgoals" in result
        assert len(result["subgoals"]) == 3
        assert "root_subgoal_ids" in result
        assert len(result["root_subgoal_ids"]) == 3
        
        # Verify that the mock was called correctly
        mock_goal_decomposition_engine.decompose_goal.assert_called_once()
        call_args = mock_goal_decomposition_engine.decompose_goal.call_args[1]
        assert call_args["goal"] == test_goal
        assert call_args["strategy"] == DecompositionStrategy.TOP_DOWN
    
    @pytest.mark.asyncio
    async def test_get_decomposed_goal(self, self_aware_system, mock_goal_decomposition_engine):
        """Test the get_decomposed_goal method of the SelfAwareSystem."""
        # Get a decomposed goal
        result = await self_aware_system.get_decomposed_goal("test_goal_id")
        
        # Verify the result
        assert result is not None
        assert isinstance(result, dict)
        assert result["id"] == "test_goal_id"
        assert result["name"] == "Test Goal"
        
        # Verify that the mock was called correctly
        mock_goal_decomposition_engine.get_decomposed_goal.assert_called_once_with("test_goal_id")
    
    @pytest.mark.asyncio
    async def test_prioritize_subgoals(self, self_aware_system, mock_goal_decomposition_engine):
        """Test the prioritize_subgoals method of the SelfAwareSystem."""
        # Prioritize subgoals
        result = await self_aware_system.prioritize_subgoals("test_goal_id")
        
        # Verify the result
        assert result is not None
        assert isinstance(result, list)
        assert len(result) == 3
        assert "subgoal_0" in result
        assert "subgoal_1" in result
        assert "subgoal_2" in result
        
        # Verify that the mock was called correctly
        mock_goal_decomposition_engine.prioritize_subgoals.assert_called_once_with("test_goal_id")
    
    @pytest.mark.asyncio
    async def test_estimate_goal_resources(self, self_aware_system, mock_goal_decomposition_engine):
        """Test the estimate_goal_resources method of the SelfAwareSystem."""
        # Estimate resources
        result = await self_aware_system.estimate_goal_resources("test_goal_id")
        
        # Verify the result
        assert result is not None
        assert isinstance(result, dict)
        assert result["time_hours"] == 6.0
        assert result["complexity"] == 5
        assert result["risk_level"] == 3
        assert "knowledge_requirements" in result
        assert "dependencies" in result
        
        # Verify that the mock was called correctly
        mock_goal_decomposition_engine.estimate_resources.assert_called_once_with("test_goal_id")
    
    @pytest.mark.asyncio
    async def test_validate_goal_decomposition(self, self_aware_system, mock_goal_decomposition_engine):
        """Test the validate_goal_decomposition method of the SelfAwareSystem."""
        # Validate decomposition
        result = await self_aware_system.validate_goal_decomposition("test_goal_id")
        
        # Verify the result
        assert result is not None
        assert isinstance(result, dict)
        assert result["valid"] is True
        assert "errors" in result
        assert "warnings" in result
        
        # Verify that the mock was called correctly
        mock_goal_decomposition_engine.validate_decomposition.assert_called_once_with("test_goal_id")
    
    @pytest.mark.asyncio
    async def test_planning_worker_integration(self, self_aware_system):
        """Test the integration of the Planning Worker with the Self-Aware System."""
        # Create a test task
        task = self_aware_system.cognitive_orchestrator.get_task("task_id")
        assert task is not None
        
        # Get the planning worker
        planning_worker = None
        for worker_type, workers in self_aware_system.cognitive_orchestrator.workers.items():
            if worker_type == WorkerType.PLANNING:
                # Get the first planning worker from the list
                planning_worker = workers[0] if workers else None
                break
        
        assert planning_worker is not None
        
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