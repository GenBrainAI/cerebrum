"""
Unit tests for the Goal Decomposition Engine methods in the Self-Aware System.
"""

import pytest
import asyncio
from unittest.mock import MagicMock, patch, AsyncMock
import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional

from src.server.planning.goal_decomposition import (
    GoalDecompositionEngine,
    GoalType,
    DecompositionStrategy,
    ResourceEstimate,
    SubGoal,
    DecomposedGoal,
    GoalDecompositionError,
    InvalidGoalError,
    CircularDependencyError
)

class TestGoalDecompositionMethods:
    """Test suite for the Goal Decomposition Engine methods."""
    
    @pytest.mark.asyncio
    async def test_decompose_goal_basic(self):
        """Test the basic functionality of the decompose_goal method."""
        # Create a mock knowledge system
        mock_knowledge_system = MagicMock()
        mock_knowledge_system.query_semantic_memory = AsyncMock(return_value=[
            {"id": "1", "content": "Test knowledge item 1"},
            {"id": "2", "content": "Test knowledge item 2"}
        ])
        
        # Create a goal decomposition engine
        engine = GoalDecompositionEngine(knowledge_system=mock_knowledge_system)
        
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
        
        # Decompose the goal
        decomposed_goal = await engine.decompose_goal(
            goal=test_goal,
            strategy=DecompositionStrategy.TOP_DOWN
        )
        
        # Verify the result
        assert decomposed_goal is not None
        assert decomposed_goal.name == test_goal["name"]
        assert decomposed_goal.description == test_goal["description"]
        assert decomposed_goal.goal_type == GoalType.DEVELOPMENT
        assert decomposed_goal.strategy == DecompositionStrategy.TOP_DOWN
        assert len(decomposed_goal.subgoals) > 0
        assert len(decomposed_goal.root_subgoal_ids) > 0
        assert decomposed_goal.total_resources is not None
        assert decomposed_goal.total_resources.time_hours > 0
        assert decomposed_goal.status == "pending"
        
        # Verify that the goal is stored in the engine
        assert decomposed_goal.id in engine.decomposed_goals
        
        # Verify that the decomposition history is updated
        assert len(engine.decomposition_history) == 1
        assert engine.decomposition_history[0]["goal_id"] == decomposed_goal.id
        assert engine.decomposition_history[0]["strategy"] == DecompositionStrategy.TOP_DOWN.name
        assert "timestamp" in engine.decomposition_history[0]
        assert "subgoal_count" in engine.decomposition_history[0]
        assert engine.decomposition_history[0]["subgoal_count"] == len(decomposed_goal.subgoals)
    
    @pytest.mark.asyncio
    async def test_decompose_goal_with_context(self):
        """Test decomposing a goal with additional context."""
        # Create a mock knowledge system
        mock_knowledge_system = MagicMock()
        mock_knowledge_system.query_semantic_memory = AsyncMock(return_value=[
            {"id": "1", "content": "Test knowledge item 1"},
            {"id": "2", "content": "Test knowledge item 2"}
        ])
        
        # Create a goal decomposition engine
        engine = GoalDecompositionEngine(knowledge_system=mock_knowledge_system)
        
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
        
        # Decompose the goal with context
        decomposed_goal = await engine.decompose_goal(
            goal=test_goal,
            strategy=DecompositionStrategy.TOP_DOWN,
            context=context
        )
        
        # Verify the result
        assert decomposed_goal is not None
        assert len(decomposed_goal.subgoals) > 0
        
        # Verify that the knowledge system was queried with the context
        mock_knowledge_system.query_semantic_memory.assert_called()
        call_args = mock_knowledge_system.query_semantic_memory.call_args_list[0][1]
        assert "test" in call_args["query"]
        assert "Test Goal" in call_args["query"]
    
    @pytest.mark.asyncio
    async def test_decompose_goal_validation(self):
        """Test goal validation during decomposition."""
        # Create a goal decomposition engine
        engine = GoalDecompositionEngine()
        
        # Test with invalid goal (not a dictionary)
        with pytest.raises(InvalidGoalError, match="Goal must be a dictionary"):
            await engine.decompose_goal("not a dict")
        
        # Test with invalid goal (no name)
        with pytest.raises(InvalidGoalError, match="Goal must have a name"):
            await engine.decompose_goal({})
        
        # Test with invalid goal type
        goal = {
            "name": "Test Goal",
            "type": "INVALID_TYPE"
        }
        
        # This should not raise an error, but use GENERAL type instead
        decomposed_goal = await engine.decompose_goal(goal)
        assert decomposed_goal.goal_type == GoalType.GENERAL
    
    @pytest.mark.asyncio
    async def test_get_decomposed_goal(self):
        """Test getting a decomposed goal by ID."""
        # Create a goal decomposition engine
        engine = GoalDecompositionEngine()
        
        # Create a test goal
        test_goal = {
            "name": "Test Goal",
            "description": "A test goal for unit testing",
            "type": "DEVELOPMENT"
        }
        
        # Decompose the goal
        decomposed_goal = await engine.decompose_goal(test_goal)
        
        # Get the decomposed goal
        retrieved_goal = await engine.get_decomposed_goal(decomposed_goal.id)
        
        # Verify the result
        assert retrieved_goal is not None
        assert retrieved_goal.id == decomposed_goal.id
        assert retrieved_goal.name == decomposed_goal.name
        assert retrieved_goal.description == decomposed_goal.description
        assert retrieved_goal.goal_type == decomposed_goal.goal_type
        assert retrieved_goal.strategy == decomposed_goal.strategy
        assert len(retrieved_goal.subgoals) == len(decomposed_goal.subgoals)
        
        # Test with non-existent ID
        non_existent_goal = await engine.get_decomposed_goal("non-existent-id")
        assert non_existent_goal is None
    
    @pytest.mark.asyncio
    async def test_prioritize_subgoals(self):
        """Test prioritizing subgoals."""
        # Create a goal decomposition engine
        engine = GoalDecompositionEngine()
        
        # Create a test goal
        test_goal = {
            "name": "Test Goal",
            "description": "A test goal for unit testing",
            "type": "DEVELOPMENT"
        }
        
        # Decompose the goal
        decomposed_goal = await engine.decompose_goal(test_goal)
        
        # Prioritize subgoals
        prioritized_ids = await engine.prioritize_subgoals(decomposed_goal.id)
        
        # Verify the result
        assert len(prioritized_ids) > 0
        assert len(prioritized_ids) == len(decomposed_goal.subgoals)
        
        # Verify that all subgoal IDs are included
        for subgoal_id in decomposed_goal.subgoals:
            assert subgoal_id in prioritized_ids
        
        # Test with non-existent ID
        non_existent_prioritized = await engine.prioritize_subgoals("non-existent-id")
        assert non_existent_prioritized == []
    
    @pytest.mark.asyncio
    async def test_estimate_resources(self):
        """Test estimating resources for a decomposed goal."""
        # Create a goal decomposition engine
        engine = GoalDecompositionEngine()
        
        # Create a test goal
        test_goal = {
            "name": "Test Goal",
            "description": "A test goal for unit testing",
            "type": "DEVELOPMENT"
        }
        
        # Decompose the goal
        decomposed_goal = await engine.decompose_goal(test_goal)
        
        # Estimate resources
        resources = await engine.estimate_resources(decomposed_goal.id)
        
        # Verify the result
        assert resources is not None
        assert resources.time_hours > 0
        assert resources.complexity > 0
        assert len(resources.knowledge_requirements) > 0
        assert resources.risk_level > 0
        
        # Verify that the resources match the decomposed goal's total resources
        assert resources.time_hours == decomposed_goal.total_resources.time_hours
        assert resources.complexity == decomposed_goal.total_resources.complexity
        assert set(resources.knowledge_requirements) == set(decomposed_goal.total_resources.knowledge_requirements)
        assert resources.risk_level == decomposed_goal.total_resources.risk_level
        
        # Test with non-existent ID - this should return a default ResourceEstimate with valid values
        non_existent_resources = await engine.estimate_resources("non-existent-id")
        assert non_existent_resources.time_hours == 0.0
        assert non_existent_resources.complexity == 1  # Changed from 0 to 1 to meet the validation requirement
        assert len(non_existent_resources.knowledge_requirements) == 0
        assert non_existent_resources.risk_level == 1  # Changed from 0 to 1 to meet the validation requirement
    
    @pytest.mark.asyncio
    async def test_validate_decomposition(self):
        """Test validating a goal decomposition."""
        # Create a goal decomposition engine
        engine = GoalDecompositionEngine()
        
        # Create a test goal
        test_goal = {
            "name": "Test Goal",
            "description": "A test goal for unit testing",
            "type": "DEVELOPMENT"
        }
        
        # Decompose the goal
        decomposed_goal = await engine.decompose_goal(test_goal)
        
        # Validate the decomposition
        validation = await engine.validate_decomposition(decomposed_goal.id)
        
        # Verify the result
        assert validation is not None
        assert "valid" in validation
        assert validation["valid"] is True
        assert "errors" in validation
        assert len(validation["errors"]) == 0
        assert "warnings" in validation
        
        # Test with non-existent ID
        non_existent_validation = await engine.validate_decomposition("non-existent-id")
        assert non_existent_validation["valid"] is False
        assert "Goal not found" in non_existent_validation["errors"]
    
    @pytest.mark.asyncio
    async def test_delete_decomposed_goal(self):
        """Test deleting a decomposed goal."""
        # Create a goal decomposition engine
        engine = GoalDecompositionEngine()
        
        # Create a test goal
        test_goal = {
            "name": "Test Goal",
            "description": "A test goal for unit testing",
            "type": "DEVELOPMENT"
        }
        
        # Decompose the goal
        decomposed_goal = await engine.decompose_goal(test_goal)
        
        # Verify that the goal exists
        assert decomposed_goal.id in engine.decomposed_goals
        
        # Delete the goal
        result = await engine.delete_decomposed_goal(decomposed_goal.id)
        
        # Verify the result
        assert result is True
        assert decomposed_goal.id not in engine.decomposed_goals
        
        # Test with non-existent ID
        non_existent_result = await engine.delete_decomposed_goal("non-existent-id")
        assert non_existent_result is False
    
    @pytest.mark.asyncio
    async def test_circular_dependency_detection(self):
        """Test detection of circular dependencies."""
        # Create a goal decomposition engine
        engine = GoalDecompositionEngine()
        
        # Create subgoals with circular dependencies
        subgoal1 = SubGoal(
            id="1",
            name="Subgoal 1",
            description="Test subgoal 1",
            goal_type=GoalType.DEVELOPMENT,
            priority=5,
            resources=ResourceEstimate(
                time_hours=1.0,
                complexity=5,
                knowledge_requirements=[],
                dependencies=["2"],
                risk_level=3
            ),
            children_ids=["2"]
        )
        
        subgoal2 = SubGoal(
            id="2",
            name="Subgoal 2",
            description="Test subgoal 2",
            goal_type=GoalType.DEVELOPMENT,
            priority=5,
            resources=ResourceEstimate(
                time_hours=1.0,
                complexity=5,
                knowledge_requirements=[],
                dependencies=["1"],
                risk_level=3
            ),
            parent_id="1",
            children_ids=["1"]
        )
        
        # Create a decomposed goal with circular dependencies
        decomposed_goal = DecomposedGoal(
            id="test_circular",
            name="Test Circular Dependencies",
            description="Test goal with circular dependencies",
            goal_type=GoalType.DEVELOPMENT,
            strategy=DecompositionStrategy.TOP_DOWN,
            subgoals={"1": subgoal1, "2": subgoal2},
            root_subgoal_ids=["1"],
            total_resources=ResourceEstimate(
                time_hours=2.0,
                complexity=5,
                knowledge_requirements=[],
                dependencies=[],
                risk_level=3
            ),
            creation_time=datetime.now().isoformat(),
            status="pending"
        )
        
        # Store the decomposed goal
        engine.decomposed_goals["test_circular"] = decomposed_goal
        
        # Validate the decomposition
        validation = await engine.validate_decomposition("test_circular")
        
        # Verify that circular dependencies are detected
        assert validation["valid"] is False
        assert any("Circular dependency" in error for error in validation["errors"])
    
    @pytest.mark.asyncio
    async def test_get_all_decomposed_goals(self):
        """Test getting all decomposed goals."""
        # Create a goal decomposition engine
        engine = GoalDecompositionEngine()
        
        # Create multiple test goals
        goal1 = {
            "name": "Test Goal 1",
            "description": "A test goal for unit testing",
            "type": "DEVELOPMENT"
        }
        
        goal2 = {
            "name": "Test Goal 2",
            "description": "Another test goal for unit testing",
            "type": "RESEARCH"
        }
        
        # Decompose the goals
        decomposed_goal1 = await engine.decompose_goal(goal1)
        decomposed_goal2 = await engine.decompose_goal(goal2)
        
        # Get all decomposed goals
        all_goals = await engine.get_all_decomposed_goals()
        
        # Verify the result
        assert len(all_goals) == 2
        assert decomposed_goal1.id in all_goals
        assert decomposed_goal2.id in all_goals
        assert all_goals[decomposed_goal1.id].name == "Test Goal 1"
        assert all_goals[decomposed_goal2.id].name == "Test Goal 2" 