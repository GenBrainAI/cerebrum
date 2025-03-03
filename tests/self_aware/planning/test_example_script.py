"""
Unit tests for the Goal Decomposition Engine example script.
"""

import pytest
import asyncio
import os
import json
import sys
import importlib.util
from unittest.mock import MagicMock, patch, AsyncMock, call
import tempfile
import shutil
from pathlib import Path

# Import the example script directly using importlib
EXAMPLE_SCRIPT_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), 
                                 "examples", "goal_decomposition_example.py")

# Check if the file exists
if not os.path.exists(EXAMPLE_SCRIPT_PATH):
    raise FileNotFoundError(f"Example script not found at {EXAMPLE_SCRIPT_PATH}")

# Load the module
spec = importlib.util.spec_from_file_location("goal_decomposition_example", EXAMPLE_SCRIPT_PATH)
example_script = importlib.util.module_from_spec(spec)
sys.modules["goal_decomposition_example"] = example_script
spec.loader.exec_module(example_script)

from src.server.planning.goal_decomposition import (
    GoalDecompositionEngine,
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
            resources=resources,
            children_ids=[]
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
        name="Implement AI-Powered Code Review System",
        description="Develop a system that can automatically review code changes, identify potential issues, and suggest improvements.",
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
    mock.initialize = AsyncMock()
    mock.decompose_goal = AsyncMock(return_value=decomposed_goal_dict)
    mock.prioritize_subgoals = AsyncMock(return_value=root_ids)
    mock.estimate_goal_resources = AsyncMock(return_value={
        "time_hours": 6.0,
        "complexity": 5,
        "knowledge_requirements": ["python", "testing"],
        "dependencies": [],
        "risk_level": 3
    })
    mock.validate_goal_decomposition = AsyncMock(return_value={
        "valid": True,
        "errors": [],
        "warnings": ["Goal decomposition has fewer than 2 subgoals"]
    })
    
    return mock

class TestExampleScript:
    """Test suite for the Goal Decomposition Engine example script."""
    
    @pytest.mark.asyncio
    async def test_main_function(self, mock_self_aware_system):
        """Test the main function of the example script."""
        # Create a temporary directory for output
        temp_dir = tempfile.mkdtemp()
        output_dir = os.path.join(temp_dir, "examples", "output")
        os.makedirs(output_dir, exist_ok=True)
        
        # Patch the SelfAwareSystem class and other functions
        with patch('goal_decomposition_example.SelfAwareSystem', return_value=mock_self_aware_system), \
             patch('goal_decomposition_example.os.makedirs', MagicMock()), \
             patch('goal_decomposition_example.print', MagicMock()), \
             patch('goal_decomposition_example.open', MagicMock()), \
             patch('goal_decomposition_example.json.dump', MagicMock()), \
             patch('goal_decomposition_example.print_tree', MagicMock()):
            
            # Run the main function
            await example_script.main()
            
            # Verify that the SelfAwareSystem methods were called
            mock_self_aware_system.initialize.assert_called_once()
            mock_self_aware_system.decompose_goal.assert_called_once()
            mock_self_aware_system.prioritize_subgoals.assert_called_once()
            mock_self_aware_system.estimate_goal_resources.assert_called_once()
            mock_self_aware_system.validate_goal_decomposition.assert_called_once()
        
        # Clean up
        shutil.rmtree(temp_dir)
    
    def test_print_tree_function(self):
        """Test the print_tree function of the example script."""
        # Create a sample subgoals dictionary
        subgoals = {
            "1": {
                "name": "Root Subgoal",
                "children_ids": ["2", "3"]
            },
            "2": {
                "name": "Child Subgoal 1",
                "children_ids": []
            },
            "3": {
                "name": "Child Subgoal 2",
                "children_ids": ["4"]
            },
            "4": {
                "name": "Grandchild Subgoal",
                "children_ids": []
            }
        }
        
        # Patch the print function
        with patch('builtins.print') as mock_print:
            # Call the print_tree function
            example_script.print_tree(subgoals, "1", 0)
            
            # Verify that print was called with the correct arguments
            expected_calls = [
                call("- Root Subgoal"),
                call("  - Child Subgoal 1"),
                call("  - Child Subgoal 2"),
                call("    - Grandchild Subgoal")
            ]
            mock_print.assert_has_calls(expected_calls, any_order=False)
    
    def test_example_script_imports(self):
        """Test that the example script imports the necessary modules."""
        # Check that the example script imports the necessary modules
        with open(EXAMPLE_SCRIPT_PATH, "r") as f:
            content = f.read()
        
        assert "import asyncio" in content, "asyncio import not found in example script"
        assert "import json" in content, "json import not found in example script"
        assert "import os" in content, "os import not found in example script"
        assert "from datetime import datetime" in content, "datetime import not found in example script"
        assert "from src.server.self_aware_integration import SelfAwareSystem" in content, "SelfAwareSystem import not found in example script"
        assert "from src.server.planning.goal_decomposition import" in content, "goal_decomposition import not found in example script"
    
    def test_example_script_structure(self):
        """Test the structure of the example script."""
        # Check that the example script has the necessary functions
        with open(EXAMPLE_SCRIPT_PATH, "r") as f:
            content = f.read()
        
        assert "async def main():" in content, "main function not found in example script"
        assert "def print_tree(" in content, "print_tree function not found in example script"
        assert "if __name__ == \"__main__\":" in content, "main guard not found in example script"
        assert "asyncio.run(main())" in content, "asyncio.run(main()) not found in example script"
    
    def test_example_script_output_directory(self):
        """Test that the example script creates the output directory."""
        # Check that the example script creates the output directory
        with open(EXAMPLE_SCRIPT_PATH, "r") as f:
            content = f.read()
        
        assert "os.makedirs(\"examples/output\", exist_ok=True)" in content, "Output directory creation not found in example script"
        assert "with open(\"examples/output/decomposed_goal.json\", \"w\") as f:" in content, "Output file creation not found in example script" 