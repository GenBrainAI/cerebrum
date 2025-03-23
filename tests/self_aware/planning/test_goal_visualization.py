"""
Unit tests for goal tree visualization.
"""

import pytest
import os
import json
import asyncio
from unittest.mock import MagicMock, patch
import tempfile
import shutil
from pathlib import Path

from src.server.planning.goal_decomposition import (
    GoalDecompositionEngine, GoalType, DecompositionStrategy,
    ResourceEstimate, SubGoal, DecomposedGoal
)
from src.server.planning.goal_visualization import GoalTreeVisualization

@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files."""
    temp_path = tempfile.mkdtemp()
    yield temp_path
    shutil.rmtree(temp_path)

@pytest.fixture
def sample_decomposed_goal():
    """Create a sample decomposed goal for testing visualization."""
    # Create resource estimates
    res1 = ResourceEstimate(
        time_hours=10.0,
        complexity=6,
        knowledge_requirements=["Python", "Data Analysis"],
        dependencies=[],
        risk_level=3
    )
    
    res2 = ResourceEstimate(
        time_hours=8.0,
        complexity=5,
        knowledge_requirements=["Machine Learning"],
        dependencies=[],
        risk_level=4
    )
    
    res3 = ResourceEstimate(
        time_hours=12.0,
        complexity=7,
        knowledge_requirements=["Python", "Statistics"],
        dependencies=["sg1", "sg2"],
        risk_level=5
    )
    
    # Create subgoals
    sg1 = SubGoal(
        id="sg1",
        name="Data Collection",
        description="Collect necessary data for the research",
        goal_type=GoalType.RESEARCH,
        priority=8,
        resources=res1,
        children_ids=["sg3"]
    )
    
    sg2 = SubGoal(
        id="sg2",
        name="Data Preprocessing",
        description="Clean and preprocess the data",
        goal_type=GoalType.RESEARCH,
        priority=7,
        resources=res2,
        children_ids=["sg3"]
    )
    
    sg3 = SubGoal(
        id="sg3",
        name="Model Development",
        description="Develop a machine learning model",
        goal_type=GoalType.RESEARCH,
        priority=9,
        resources=res3,
        parent_id="sg1"  # This is artificial - in a real case would match one of the dependencies
    )
    
    # Calculate total resources
    total_res = ResourceEstimate(
        time_hours=30.0,
        complexity=7,
        knowledge_requirements=["Python", "Data Analysis", "Machine Learning", "Statistics"],
        dependencies=[],
        risk_level=5
    )
    
    # Create decomposed goal
    decomposed_goal = DecomposedGoal(
        id="goal1",
        name="Research Project",
        description="A sample research project for testing visualization",
        goal_type=GoalType.RESEARCH,
        strategy=DecompositionStrategy.TOP_DOWN,
        subgoals={"sg1": sg1, "sg2": sg2, "sg3": sg3},
        root_subgoal_ids=["sg1", "sg2"],
        total_resources=total_res,
        creation_time="2023-01-01T12:00:00"
    )
    
    return decomposed_goal

@pytest.mark.asyncio
async def test_create_json_export(temp_dir, sample_decomposed_goal):
    """Test JSON export creation."""
    # Create visualizer
    visualizer = GoalTreeVisualization(temp_dir)
    
    # Generate JSON export
    json_path = await visualizer.create_json_export(sample_decomposed_goal)
    
    # Verify JSON file was created
    assert os.path.exists(json_path)
    assert json_path.endswith(".json")
    
    # Verify contents
    with open(json_path, "r") as f:
        data = json.load(f)
    
    assert data["name"] == "Research Project"
    assert data["id"] == "goal1"
    assert len(data["children"]) == 2  # Two root subgoals
    
    # Verify tree structure
    root_names = [child["name"] for child in data["children"]]
    assert "Data Collection" in root_names
    assert "Data Preprocessing" in root_names
    
    # Find the child of Data Collection
    data_collection = next(child for child in data["children"] if child["name"] == "Data Collection")
    assert len(data_collection["children"]) == 1
    assert data_collection["children"][0]["name"] == "Model Development"

@pytest.mark.asyncio
async def test_create_svg_visualization(temp_dir, sample_decomposed_goal):
    """Test SVG visualization creation."""
    visualizer = GoalTreeVisualization(temp_dir)
    
    # Generate SVG
    svg_path = await visualizer.create_svg_visualization(sample_decomposed_goal)
    
    # Verify SVG file was created
    assert os.path.exists(svg_path)
    assert svg_path.endswith(".svg")
    
    # Verify file is not empty
    file_size = os.path.getsize(svg_path)
    assert file_size > 0
    
    # Basic check for SVG content
    with open(svg_path, "r") as f:
        content = f.read()
    
    assert "<?xml" in content
    assert "<svg" in content
    assert "Research Project" in content  # Title should be in SVG

@pytest.mark.asyncio
async def test_create_interactive_html(temp_dir, sample_decomposed_goal):
    """Test interactive HTML visualization creation."""
    visualizer = GoalTreeVisualization(temp_dir)
    
    # Generate HTML
    html_path = await visualizer.create_interactive_html(sample_decomposed_goal)
    
    # Verify HTML file was created
    assert os.path.exists(html_path)
    assert html_path.endswith(".html")
    
    # Verify file is not empty
    file_size = os.path.getsize(html_path)
    assert file_size > 0
    
    # Basic check for HTML content
    with open(html_path, "r") as f:
        content = f.read()
    
    assert "<!DOCTYPE html>" in content
    assert "<html" in content
    assert "Goal Tree: Research Project" in content
    assert "d3.v7.min.js" in content  # Should use D3.js
    assert "treeData" in content  # Should have tree data

@pytest.mark.asyncio
async def test_visualization_with_circular_dependencies(temp_dir):
    """Test visualization handles circular dependencies correctly."""
    # Create resource estimates
    res1 = ResourceEstimate(
        time_hours=5.0,
        complexity=6,
        knowledge_requirements=[],
        dependencies=[],
        risk_level=3
    )
    
    res2 = ResourceEstimate(
        time_hours=5.0,
        complexity=6,
        knowledge_requirements=[],
        dependencies=["sg1"],
        risk_level=3
    )
    
    # Create subgoals with circular dependency
    sg1 = SubGoal(
        id="sg1",
        name="Task 1",
        description="First task",
        goal_type=GoalType.GENERAL,
        priority=5,
        resources=res1,
        children_ids=["sg2"]
    )
    
    sg2 = SubGoal(
        id="sg2",
        name="Task 2",
        description="Second task",
        goal_type=GoalType.GENERAL,
        priority=5,
        resources=res2,
        parent_id="sg1",
        children_ids=["sg1"]  # Circular dependency
    )
    
    # Update first subgoal to complete circle
    sg1.parent_id = "sg2"
    
    # Create decomposed goal
    decomposed_goal = DecomposedGoal(
        id="goal2",
        name="Circular Goal",
        description="A goal with circular dependencies",
        goal_type=GoalType.GENERAL,
        strategy=DecompositionStrategy.TOP_DOWN,
        subgoals={"sg1": sg1, "sg2": sg2},
        root_subgoal_ids=["sg1"],  # Arbitrary choice of root
        total_resources=res1,
        creation_time="2023-01-01T12:00:00"
    )
    
    # Create visualizer
    visualizer = GoalTreeVisualization(temp_dir)
    
    # Test all visualization methods
    json_path = await visualizer.create_json_export(decomposed_goal)
    svg_path = await visualizer.create_svg_visualization(decomposed_goal)
    html_path = await visualizer.create_interactive_html(decomposed_goal)
    
    # Verify files were created
    assert os.path.exists(json_path)
    assert os.path.exists(svg_path)
    assert os.path.exists(html_path)
    
    # Check JSON for circular reference handling
    with open(json_path, "r") as f:
        data = json.load(f)
    
    # The JSON visualization should detect and handle circular references
    task1 = data["children"][0]
    assert task1["name"] == "Task 1"
    task2 = task1["children"][0]
    assert task2["name"] == "Task 2"
    
    # Task 2 should either have no children or a "Circular Reference" placeholder
    if task2["children"]:
        assert "Circular Reference" in [child.get("name") for child in task2["children"]] 