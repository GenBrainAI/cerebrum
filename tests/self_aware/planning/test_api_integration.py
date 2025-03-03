"""
Unit tests for the integration of the Goal Decomposition Engine with the Self-Aware System's API.
"""

import pytest
import asyncio
from unittest.mock import MagicMock, patch, AsyncMock
import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional

from src.server.self_aware_integration import SelfAwareSystem
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
    
    # Convert to dictionary for the return value
    decomposed_goal_dict = {
        "id": decomposed_goal.id,
        "name": decomposed_goal.name,
        "description": decomposed_goal.description,
        "goal_type": decomposed_goal.goal_type.name,
        "strategy": decomposed_goal.strategy.name,
        "subgoals": {k: v.to_dict() for k, v in decomposed_goal.subgoals.items()},
        "root_subgoal_ids": decomposed_goal.root_subgoal_ids,
        "total_resources": {
            "time_hours": decomposed_goal.total_resources.time_hours,
            "complexity": decomposed_goal.total_resources.complexity,
            "knowledge_requirements": decomposed_goal.total_resources.knowledge_requirements,
            "dependencies": decomposed_goal.total_resources.dependencies,
            "risk_level": decomposed_goal.total_resources.risk_level
        },
        "creation_time": decomposed_goal.creation_time,
        "status": decomposed_goal.status
    }
    
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
    
    # Add to_dict method to the decomposed goal
    decomposed_goal.to_dict = MagicMock(return_value=decomposed_goal_dict)
    
    return mock

@pytest.fixture
def self_aware_system(mock_knowledge_system, mock_goal_decomposition_engine):
    """Create a SelfAwareSystem instance with mocked components."""
    # Create the system
    system = SelfAwareSystem(storage_path="test_storage")
    
    # Set the mocked components directly
    system.knowledge_system = mock_knowledge_system
    system.goal_decomposition_engine = mock_goal_decomposition_engine
    
    return system

class TestAPIIntegration:
    """Test suite for the integration of the Goal Decomposition Engine with the Self-Aware System's API."""
    
    @pytest.mark.asyncio
    async def test_decompose_goal_api(self, self_aware_system, mock_goal_decomposition_engine):
        """Test the decompose_goal API method."""
        # Create a test goal
        test_goal = {
            "name": "Test Goal",
            "description": "A test goal for unit testing",
            "type": "DEVELOPMENT",
            "metadata": {
                "priority": "high",
                "owner": "test_user"
            }
        }
        
        # Call the API method
        result = await self_aware_system.decompose_goal(
            goal=test_goal,
            strategy="TOP_DOWN"
        )
        
        # Verify the result
        assert result is not None
        assert isinstance(result, dict)
        
        # Verify that the goal decomposition engine was called correctly
        mock_goal_decomposition_engine.decompose_goal.assert_called_once()
        call_args = mock_goal_decomposition_engine.decompose_goal.call_args[1]
        assert call_args["goal"] == test_goal
        assert call_args["strategy"] == DecompositionStrategy.TOP_DOWN
        
        # Verify that the knowledge system was called to record the operation
        self_aware_system.knowledge_system.add_episodic_memory.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_decomposed_goal_api(self, self_aware_system, mock_goal_decomposition_engine):
        """Test the get_decomposed_goal API method."""
        # Call the API method
        result = await self_aware_system.get_decomposed_goal("test_goal_id")
        
        # Verify the result
        assert result is not None
        assert isinstance(result, dict)
        
        # Verify that the goal decomposition engine was called correctly
        mock_goal_decomposition_engine.get_decomposed_goal.assert_called_once_with("test_goal_id")
    
    @pytest.mark.asyncio
    async def test_prioritize_subgoals_api(self, self_aware_system, mock_goal_decomposition_engine):
        """Test the prioritize_subgoals API method."""
        # Call the API method
        result = await self_aware_system.prioritize_subgoals("test_goal_id")
        
        # Verify the result
        assert result is not None
        assert isinstance(result, list)
        
        # Verify that the goal decomposition engine was called correctly
        mock_goal_decomposition_engine.prioritize_subgoals.assert_called_once_with("test_goal_id")
    
    @pytest.mark.asyncio
    async def test_estimate_goal_resources_api(self, self_aware_system, mock_goal_decomposition_engine):
        """Test the estimate_goal_resources API method."""
        # Call the API method
        result = await self_aware_system.estimate_goal_resources("test_goal_id")
        
        # Verify the result
        assert result is not None
        assert isinstance(result, dict)
        
        # Verify that the goal decomposition engine was called correctly
        mock_goal_decomposition_engine.estimate_resources.assert_called_once_with("test_goal_id")
    
    @pytest.mark.asyncio
    async def test_validate_goal_decomposition_api(self, self_aware_system, mock_goal_decomposition_engine):
        """Test the validate_goal_decomposition API method."""
        # Call the API method
        result = await self_aware_system.validate_goal_decomposition("test_goal_id")
        
        # Verify the result
        assert result is not None
        assert isinstance(result, dict)
        
        # Verify that the goal decomposition engine was called correctly
        mock_goal_decomposition_engine.validate_decomposition.assert_called_once_with("test_goal_id")
    
    @pytest.mark.asyncio
    async def test_decompose_goal_api_with_invalid_strategy(self, self_aware_system, mock_goal_decomposition_engine):
        """Test the decompose_goal API method with an invalid strategy."""
        # Create a test goal
        test_goal = {
            "name": "Test Goal",
            "description": "A test goal for unit testing",
            "type": "DEVELOPMENT"
        }
        
        # Call the API method with an invalid strategy
        # This should raise a ValueError
        with pytest.raises(ValueError, match="Invalid decomposition strategy: INVALID_STRATEGY"):
            await self_aware_system.decompose_goal(
                goal=test_goal,
                strategy="INVALID_STRATEGY"
            )
    
    @pytest.mark.asyncio
    async def test_decompose_goal_api_with_context(self, self_aware_system, mock_goal_decomposition_engine):
        """Test the decompose_goal API method with context."""
        # Create a test goal
        test_goal = {
            "name": "Test Goal",
            "description": "A test goal for unit testing",
            "type": "DEVELOPMENT"
        }
        
        # Create context
        context = {
            "keywords": ["test", "unit testing", "development"],
            "domain": "software"
        }
        
        # Call the API method with context
        result = await self_aware_system.decompose_goal(
            goal=test_goal,
            strategy="TOP_DOWN",
            context=context
        )
        
        # Verify the result
        assert result is not None
        assert isinstance(result, dict)
        
        # Verify that the goal decomposition engine was called with the context
        mock_goal_decomposition_engine.decompose_goal.assert_called_once()
        call_args = mock_goal_decomposition_engine.decompose_goal.call_args[1]
        assert call_args["goal"] == test_goal
        assert call_args["strategy"] == DecompositionStrategy.TOP_DOWN
        assert call_args["context"] == context
    
    @pytest.mark.asyncio
    async def test_api_error_handling(self, self_aware_system, mock_goal_decomposition_engine):
        """Test error handling in the API methods."""
        # Make the goal decomposition engine raise an exception
        mock_goal_decomposition_engine.decompose_goal.side_effect = Exception("Test error")
        
        # Create a test goal
        test_goal = {
            "name": "Test Goal",
            "description": "A test goal for unit testing",
            "type": "DEVELOPMENT"
        }
        
        # Call the API method and expect an exception
        with pytest.raises(Exception, match="Test error"):
            await self_aware_system.decompose_goal(
                goal=test_goal,
                strategy="TOP_DOWN"
            ) 