"""
Unit tests for the CLI integration with the Goal Decomposition Engine.
"""

import pytest
import asyncio
import json
import os
from unittest.mock import MagicMock, patch, AsyncMock
import tempfile
import uuid

from src.server.cli import SelfAwareCLI
from src.server.planning.goal_decomposition import (
    GoalType,
    DecompositionStrategy,
    ResourceEstimate,
    SubGoal,
    DecomposedGoal
)

@pytest.fixture
def mock_self_aware_system():
    """Create a mock SelfAwareSystem."""
    mock = MagicMock()
    
    # Mock the decompose_goal method
    mock.decompose_goal = AsyncMock(return_value={
        "id": str(uuid.uuid4()),
        "name": "Test Goal",
        "description": "A test goal for unit testing",
        "goal_type": "DEVELOPMENT",
        "strategy": "TOP_DOWN",
        "subgoals_count": 3,
        "total_time_hours": 15.0,
        "max_complexity": 8,
        "risk_level": 6
    })
    
    # Mock the get_subgoals method
    mock.get_subgoals = AsyncMock(return_value=[
        {
            "id": str(uuid.uuid4()),
            "name": "Subgoal 1",
            "description": "First subgoal",
            "priority": 8,
            "time_hours": 5.0,
            "complexity": 7,
            "risk_level": 5,
            "knowledge_requirements": ["python", "testing"],
            "parent_id": None,
            "children_ids": [],
            "status": "pending"
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Subgoal 2",
            "description": "Second subgoal",
            "priority": 6,
            "time_hours": 3.0,
            "complexity": 5,
            "risk_level": 4,
            "knowledge_requirements": ["design", "documentation"],
            "parent_id": None,
            "children_ids": [],
            "status": "pending"
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Subgoal 3",
            "description": "Third subgoal",
            "priority": 9,
            "time_hours": 7.0,
            "complexity": 8,
            "risk_level": 6,
            "knowledge_requirements": ["algorithms", "optimization"],
            "parent_id": None,
            "children_ids": [],
            "status": "pending"
        }
    ])
    
    # Mock the prioritize_subgoals method
    mock.prioritize_subgoals = AsyncMock(return_value=[
        {
            "id": str(uuid.uuid4()),
            "name": "Subgoal 3",
            "description": "Third subgoal",
            "priority": 9,
            "time_hours": 7.0,
            "complexity": 8,
            "risk_level": 6,
            "knowledge_requirements": ["algorithms", "optimization"],
            "parent_id": None,
            "children_ids": [],
            "status": "pending"
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Subgoal 1",
            "description": "First subgoal",
            "priority": 8,
            "time_hours": 5.0,
            "complexity": 7,
            "risk_level": 5,
            "knowledge_requirements": ["python", "testing"],
            "parent_id": None,
            "children_ids": [],
            "status": "pending"
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Subgoal 2",
            "description": "Second subgoal",
            "priority": 6,
            "time_hours": 3.0,
            "complexity": 5,
            "risk_level": 4,
            "knowledge_requirements": ["design", "documentation"],
            "parent_id": None,
            "children_ids": [],
            "status": "pending"
        }
    ])
    
    # Mock the validate_decomposition method
    mock.validate_decomposition = AsyncMock(return_value={
        "valid": True,
        "errors": [],
        "warnings": ["Some subgoals have high complexity and may need further decomposition."]
    })
    
    return mock

@pytest.fixture
def cli(mock_self_aware_system):
    """Create a SelfAwareCLI instance with a mock SelfAwareSystem."""
    cli = SelfAwareCLI()
    cli.system = mock_self_aware_system
    return cli

class TestGoalDecompositionCLI:
    """Test suite for the CLI integration with the Goal Decomposition Engine."""
    
    @pytest.mark.asyncio
    async def test_decompose_goal_command_line_args(self, cli):
        """Test decomposing a goal using command line arguments."""
        # Create mock arguments
        args = MagicMock()
        args.goal_file = None
        args.name = "Test Goal"
        args.description = "A test goal for unit testing"
        args.type = "DEVELOPMENT"
        args.strategy = "TOP_DOWN"
        args.context_file = None
        args.output_file = None
        
        # Call the decompose_goal method
        result = await cli.decompose_goal(args)
        
        # Verify the result
        assert result is not None
        assert result["name"] == "Test Goal"
        assert result["goal_type"] == "DEVELOPMENT"
        assert result["strategy"] == "TOP_DOWN"
        
        # Verify that the system's decompose_goal method was called with the correct arguments
        cli.system.decompose_goal.assert_called_once_with(
            goal={"name": "Test Goal", "description": "A test goal for unit testing", "type": "DEVELOPMENT"},
            strategy="TOP_DOWN",
            context=None
        )
    
    @pytest.mark.asyncio
    async def test_decompose_goal_from_file(self, cli):
        """Test decomposing a goal from a file."""
        # Create a temporary goal file
        with tempfile.NamedTemporaryFile(mode='w+', delete=False) as temp_file:
            goal_data = {
                "name": "File Goal",
                "description": "A goal loaded from a file",
                "type": "RESEARCH"
            }
            json.dump(goal_data, temp_file)
            temp_file_path = temp_file.name
        
        try:
            # Create mock arguments
            args = MagicMock()
            args.goal_file = temp_file_path
            args.name = None
            args.description = None
            args.type = None
            args.strategy = "BOTTOM_UP"
            args.context_file = None
            args.output_file = None
            
            # Call the decompose_goal method
            result = await cli.decompose_goal(args)
            
            # Verify the result
            assert result is not None
            
            # Verify that the system's decompose_goal method was called with the correct arguments
            cli.system.decompose_goal.assert_called_once_with(
                goal=goal_data,
                strategy="BOTTOM_UP",
                context=None
            )
        finally:
            # Clean up the temporary file
            os.unlink(temp_file_path)
    
    @pytest.mark.asyncio
    async def test_decompose_goal_with_context_file(self, cli):
        """Test decomposing a goal with a context file."""
        # Create a temporary context file
        with tempfile.NamedTemporaryFile(mode='w+', delete=False) as temp_file:
            context_data = {
                "keywords": ["test", "unit testing", "development"],
                "template": {
                    "name": "Test Template",
                    "subgoals": [
                        {
                            "name": "Custom Subgoal",
                            "description": "A custom subgoal",
                            "priority": 8,
                            "time_hours": 5.0,
                            "complexity": 7,
                            "knowledge_requirements": ["testing"],
                            "dependencies": [],
                            "risk_level": 4
                        }
                    ]
                }
            }
            json.dump(context_data, temp_file)
            temp_file_path = temp_file.name
        
        try:
            # Create mock arguments
            args = MagicMock()
            args.goal_file = None
            args.name = "Test Goal"
            args.description = "A test goal for unit testing"
            args.type = "DEVELOPMENT"
            args.strategy = "TOP_DOWN"
            args.context_file = temp_file_path
            args.output_file = None
            
            # Call the decompose_goal method
            result = await cli.decompose_goal(args)
            
            # Verify the result
            assert result is not None
            
            # Verify that the system's decompose_goal method was called with the correct arguments
            cli.system.decompose_goal.assert_called_once_with(
                goal={"name": "Test Goal", "description": "A test goal for unit testing", "type": "DEVELOPMENT"},
                strategy="TOP_DOWN",
                context=context_data
            )
        finally:
            # Clean up the temporary file
            os.unlink(temp_file_path)
    
    @pytest.mark.asyncio
    async def test_decompose_goal_with_output_file(self, cli):
        """Test decomposing a goal with output to a file."""
        # Create a temporary output file
        with tempfile.NamedTemporaryFile(mode='w+', delete=False) as temp_file:
            temp_file_path = temp_file.name
        
        try:
            # Create mock arguments
            args = MagicMock()
            args.goal_file = None
            args.name = "Test Goal"
            args.description = "A test goal for unit testing"
            args.type = "DEVELOPMENT"
            args.strategy = "TOP_DOWN"
            args.context_file = None
            args.output_file = temp_file_path
            
            # Call the decompose_goal method
            result = await cli.decompose_goal(args)
            
            # Verify the result
            assert result is not None
            
            # Verify that the output file was created and contains the result
            with open(temp_file_path, 'r') as f:
                output_data = json.load(f)
            
            assert output_data["name"] == "Test Goal"
            assert output_data["goal_type"] == "DEVELOPMENT"
            assert output_data["strategy"] == "TOP_DOWN"
        finally:
            # Clean up the temporary file
            os.unlink(temp_file_path)
    
    @pytest.mark.asyncio
    async def test_get_subgoals_command(self, cli):
        """Test getting subgoals for a decomposed goal."""
        # Create mock arguments
        args = MagicMock()
        args.goal_id = "test-goal-id"
        args.output_file = None
        
        # Call the get_subgoals method
        result = await cli.get_subgoals(args)
        
        # Verify the result
        assert result is not None
        assert len(result) == 3
        assert result[0]["name"] == "Subgoal 1"
        assert result[1]["name"] == "Subgoal 2"
        assert result[2]["name"] == "Subgoal 3"
        
        # Verify that the system's get_subgoals method was called with the correct arguments
        cli.system.get_subgoals.assert_called_once_with("test-goal-id")
    
    @pytest.mark.asyncio
    async def test_prioritize_subgoals_command(self, cli):
        """Test prioritizing subgoals within a decomposed goal."""
        # Create mock arguments
        args = MagicMock()
        args.goal_id = "test-goal-id"
        args.output_file = None
        
        # Call the prioritize_subgoals method
        result = await cli.prioritize_subgoals(args)
        
        # Verify the result
        assert result is not None
        assert len(result) == 3
        assert result[0]["name"] == "Subgoal 3"  # Highest priority
        assert result[1]["name"] == "Subgoal 1"
        assert result[2]["name"] == "Subgoal 2"  # Lowest priority
        
        # Verify that the system's prioritize_subgoals method was called with the correct arguments
        cli.system.prioritize_subgoals.assert_called_once_with("test-goal-id")
    
    @pytest.mark.asyncio
    async def test_validate_decomposition_command(self, cli):
        """Test validating a goal decomposition."""
        # Create mock arguments
        args = MagicMock()
        args.goal_id = "test-goal-id"
        args.output_file = None
        
        # Call the validate_decomposition method
        result = await cli.validate_decomposition(args)
        
        # Verify the result
        assert result is not None
        assert result["valid"] is True
        assert len(result["errors"]) == 0
        assert len(result["warnings"]) == 1
        
        # Verify that the system's validate_decomposition method was called with the correct arguments
        cli.system.validate_decomposition.assert_called_once_with("test-goal-id") 