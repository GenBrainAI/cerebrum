"""
Unit tests for template-based goal decomposition.
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
    DecompositionTemplate, ResourceEstimate, SubGoal, DecomposedGoal
)

@pytest.fixture
def temp_dir():
    """Create a temporary directory for test templates."""
    temp_path = tempfile.mkdtemp()
    yield temp_path
    shutil.rmtree(temp_path)

@pytest.fixture
def mock_knowledge_system():
    """Create a mock knowledge system."""
    mock_system = MagicMock()
    
    async def mock_query_knowledge(*args, **kwargs):
        return {
            "semantic_items": [
                {"concept": "Machine Learning", "definition": "A field of AI"},
                {"concept": "Data Analysis", "definition": "Processing data"}
            ],
            "episodic_items": [],
            "procedural_items": []
        }
    
    mock_system.query_knowledge = mock_query_knowledge
    return mock_system

@pytest.fixture
def goal_decomposition_engine(temp_dir, mock_knowledge_system):
    """Create a GoalDecompositionEngine with test templates."""
    return GoalDecompositionEngine(
        knowledge_system=mock_knowledge_system,
        templates_dir=temp_dir
    )

@pytest.mark.asyncio
async def test_create_default_templates(goal_decomposition_engine, temp_dir):
    """Test that default templates are created."""
    # Default templates should have been created
    template_files = [f for f in os.listdir(temp_dir) if f.endswith(".json")]
    assert len(template_files) >= 3  # At least 3 default templates
    
    # Check we can access templates
    all_templates = await goal_decomposition_engine.get_available_templates()
    assert len(all_templates) >= 3
    
    # Check for expected template types
    template_types = set(t.goal_type for t in all_templates.values())
    assert GoalType.RESEARCH in template_types
    assert GoalType.DEVELOPMENT in template_types
    assert GoalType.ANALYSIS in template_types

@pytest.mark.asyncio
async def test_create_custom_template(goal_decomposition_engine):
    """Test creating a custom template."""
    # Create a custom template
    template_id = await goal_decomposition_engine.create_template(
        name="Custom Test Template",
        description="A test template",
        goal_type=GoalType.TESTING,
        subgoal_structure=[
            {
                "name": "Test Planning",
                "description": "Plan the tests",
                "priority": 10,
                "children": []
            },
            {
                "name": "Test Implementation",
                "description": "Implement the tests",
                "priority": 9,
                "dependencies": ["Test Planning"],
                "children": []
            },
            {
                "name": "Test Execution",
                "description": "Execute the tests",
                "priority": 8,
                "dependencies": ["Test Implementation"],
                "children": []
            }
        ],
        resource_estimates={
            "Test Planning": {"time_hours": 5, "complexity": 6, "risk_level": 3},
            "Test Implementation": {"time_hours": 10, "complexity": 7, "risk_level": 5},
            "Test Execution": {"time_hours": 3, "complexity": 4, "risk_level": 6}
        }
    )
    
    # Verify template was created
    all_templates = await goal_decomposition_engine.get_available_templates()
    assert template_id in all_templates
    
    # Verify template properties
    template = all_templates[template_id]
    assert template.name == "Custom Test Template"
    assert template.goal_type == GoalType.TESTING
    assert len(template.subgoal_structure) == 3
    
    # Verify template was saved to disk
    template_file = os.path.join(goal_decomposition_engine.templates_dir, f"{template_id}.json")
    assert os.path.exists(template_file)
    
    # Verify template content in file
    with open(template_file, "r") as f:
        template_data = json.load(f)
    
    assert template_data["name"] == "Custom Test Template"
    assert template_data["goal_type"] == "TESTING"

@pytest.mark.asyncio
async def test_delete_template(goal_decomposition_engine):
    """Test deleting a template."""
    # Create a template to delete
    template_id = await goal_decomposition_engine.create_template(
        name="Template to Delete",
        description="This template will be deleted",
        goal_type=GoalType.GENERAL,
        subgoal_structure=[{"name": "Task", "description": "A task", "priority": 5}],
        resource_estimates={"Task": {"time_hours": 1, "complexity": 1, "risk_level": 1}}
    )
    
    # Verify template exists
    templates_before = await goal_decomposition_engine.get_available_templates()
    assert template_id in templates_before
    
    # Delete the template
    deleted = await goal_decomposition_engine.delete_template(template_id)
    assert deleted is True
    
    # Verify template is gone
    templates_after = await goal_decomposition_engine.get_available_templates()
    assert template_id not in templates_after
    
    # Verify template file is gone
    template_file = os.path.join(goal_decomposition_engine.templates_dir, f"{template_id}.json")
    assert not os.path.exists(template_file)
    
    # Try deleting non-existent template
    deleted = await goal_decomposition_engine.delete_template("non-existent-id")
    assert deleted is False

@pytest.mark.asyncio
async def test_filter_templates_by_goal_type(goal_decomposition_engine):
    """Test filtering templates by goal type."""
    # Get all research templates
    research_templates = await goal_decomposition_engine.get_available_templates(GoalType.RESEARCH)
    
    # Verify all returned templates are research type
    assert all(t.goal_type == GoalType.RESEARCH for t in research_templates.values())
    
    # Get all development templates
    dev_templates = await goal_decomposition_engine.get_available_templates(GoalType.DEVELOPMENT)
    
    # Verify all returned templates are development type
    assert all(t.goal_type == GoalType.DEVELOPMENT for t in dev_templates.values())
    
    # Verify different sets are returned
    assert set(research_templates.keys()) != set(dev_templates.keys())

@pytest.mark.asyncio
async def test_template_based_decomposition(goal_decomposition_engine):
    """Test decomposing a goal using a template."""
    # Get available templates
    templates = await goal_decomposition_engine.get_available_templates(GoalType.RESEARCH)
    assert templates, "No research templates available for testing"
    
    # Select first template
    template_id = next(iter(templates.keys()))
    template = templates[template_id]
    
    # Create test goal
    test_goal = {
        "name": "Research ML Techniques",
        "description": "Research machine learning techniques for image classification",
        "type": "RESEARCH"
    }
    
    # Decompose using template
    decomposed_goal = await goal_decomposition_engine.decompose_goal(
        goal=test_goal,
        strategy=DecompositionStrategy.TOP_DOWN,
        template_id=template_id
    )
    
    # Verify goal was decomposed
    assert decomposed_goal is not None
    assert decomposed_goal.name == "Research ML Techniques"
    assert decomposed_goal.goal_type == GoalType.RESEARCH
    
    # Verify subgoals match template
    expected_subgoal_names = set(item["name"] for item in template.subgoal_structure)
    actual_subgoal_names = set(sg.name for sg in decomposed_goal.subgoals.values())
    assert expected_subgoal_names == actual_subgoal_names
    
    # Verify dependencies were properly set up
    for subgoal_template in template.subgoal_structure:
        if "dependencies" in subgoal_template:
            # Find the corresponding subgoal in decomposed_goal
            corresponding_subgoal = next(
                (sg for sg in decomposed_goal.subgoals.values() if sg.name == subgoal_template["name"]),
                None
            )
            assert corresponding_subgoal is not None
            
            # Get the IDs of the dependencies
            dependency_ids = [
                next(sg.id for sg in decomposed_goal.subgoals.values() if sg.name == dep_name)
                for dep_name in subgoal_template["dependencies"]
            ]
            
            # Verify all dependencies are set in resources.dependencies
            for dep_id in dependency_ids:
                assert dep_id in corresponding_subgoal.resources.dependencies

@pytest.mark.asyncio
async def test_domain_specific_strategy(goal_decomposition_engine):
    """Test domain-specific decomposition strategy."""
    # Create test goal
    test_goal = {
        "name": "Develop Web App",
        "description": "Develop a web application",
        "type": "DEVELOPMENT"
    }
    
    # Decompose using domain-specific strategy
    decomposed_goal = await goal_decomposition_engine.decompose_goal(
        goal=test_goal,
        strategy=DecompositionStrategy.DOMAIN_SPECIFIC
    )
    
    # Verify domain-specific strategy selected appropriate template
    assert decomposed_goal is not None
    assert decomposed_goal.name == "Develop Web App"
    assert decomposed_goal.goal_type == GoalType.DEVELOPMENT
    
    # Get names of all subgoals
    subgoal_names = [sg.name for sg in decomposed_goal.subgoals.values()]
    
    # Check for typical development phases in the subgoals
    assert any("Requirements" in name for name in subgoal_names)
    assert any("Design" in name for name in subgoal_names)
    assert any("Implementation" in name for name in subgoal_names)
    assert any("Testing" in name for name in subgoal_names)

@pytest.mark.asyncio
async def test_fallback_when_no_template_matches(goal_decomposition_engine):
    """Test fallback to top-down strategy when no template matches."""
    # Create a custom goal type that won't have a template
    test_goal = {
        "name": "Custom Goal",
        "description": "A goal with a custom type",
        "type": "DOCUMENTATION"  # Assuming no template for this type
    }
    
    # Decompose using domain-specific strategy
    decomposed_goal = await goal_decomposition_engine.decompose_goal(
        goal=test_goal,
        strategy=DecompositionStrategy.DOMAIN_SPECIFIC
    )
    
    # Verify goal was decomposed
    assert decomposed_goal is not None
    assert decomposed_goal.name == "Custom Goal"
    assert decomposed_goal.goal_type == GoalType.DOCUMENTATION
    
    # Should have used top-down strategy as fallback
    assert len(decomposed_goal.subgoals) > 0

@pytest.mark.asyncio
async def test_template_serialization(goal_decomposition_engine):
    """Test template serialization and deserialization."""
    # Create a template
    template = DecompositionTemplate(
        id="test-template",
        name="Test Template",
        description="Test template for serialization",
        goal_type=GoalType.TESTING,
        subgoal_structure=[{"name": "Test Task", "description": "A test task", "priority": 5}],
        resource_estimates={"Test Task": {"time_hours": 1, "complexity": 1, "risk_level": 1}}
    )
    
    # Serialize to dict
    template_dict = template.to_dict()
    
    # Verify dict values
    assert template_dict["id"] == "test-template"
    assert template_dict["name"] == "Test Template"
    assert template_dict["goal_type"] == "TESTING"
    
    # Deserialize back to template
    deserialized = DecompositionTemplate.from_dict(template_dict)
    
    # Verify deserialized template
    assert deserialized.id == template.id
    assert deserialized.name == template.name
    assert deserialized.goal_type == template.goal_type
    assert len(deserialized.subgoal_structure) == len(template.subgoal_structure)
    assert deserialized.resource_estimates == template.resource_estimates 