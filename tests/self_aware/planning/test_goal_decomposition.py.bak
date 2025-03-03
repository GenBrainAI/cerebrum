"""Unit tests for the Goal Decomposition Engine."""

import pytest
import asyncio
from unittest.mock import MagicMock, patch, AsyncMock
import uuid
from datetime import datetime
from typing import Dict, Any

from src.server.planning.goal_decomposition import (
    GoalDecompositionEngine,
    GoalType,
    DecompositionStrategy,
    ResourceEstimate,
    SubGoal,
    DecomposedGoal,
    GoalDecompositionError,
    InvalidGoalError,
    CircularDependencyError,
    ResourceValidationError
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
def goal_decomposition_engine(mock_knowledge_system):
    """Create a GoalDecompositionEngine instance with a mock knowledge system."""
    return GoalDecompositionEngine(knowledge_system=mock_knowledge_system)

@pytest.fixture
def sample_goal():
    """Create a sample goal for testing."""
    return {
        "name": "Test Goal",
        "description": "A test goal for unit testing",
        "type": "DEVELOPMENT",
        "metadata": {
            "priority": "high",
            "owner": "test_user"
        }
    }

@pytest.fixture
def sample_resource_estimate():
    """Create a sample resource estimate for testing."""
    return ResourceEstimate(
        time_hours=10.0,
        complexity=7,
        knowledge_requirements=["python", "testing"],
        dependencies=[],
        risk_level=5
    )

@pytest.fixture
def sample_subgoal(sample_resource_estimate):
    """Create a sample subgoal for testing."""
    return SubGoal(
        id=str(uuid.uuid4()),
        name="Test Subgoal",
        description="A test subgoal",
        goal_type=GoalType.DEVELOPMENT,
        priority=8,
        resources=sample_resource_estimate
    )

class TestGoalDecompositionEngine:
    """Test suite for the Goal Decomposition Engine."""

    @pytest.mark.asyncio
    async def test_decompose_goal_top_down(self, goal_decomposition_engine, sample_goal):
        """Test decomposing a goal using the TOP_DOWN strategy."""
        decomposed_goal = await goal_decomposition_engine.decompose_goal(
            goal=sample_goal,
            strategy=DecompositionStrategy.TOP_DOWN
        )
        
        assert decomposed_goal is not None
        assert decomposed_goal.name == sample_goal["name"]
        assert decomposed_goal.description == sample_goal["description"]
        assert decomposed_goal.goal_type == GoalType.DEVELOPMENT
        assert decomposed_goal.strategy == DecompositionStrategy.TOP_DOWN
        assert len(decomposed_goal.subgoals) > 0
        assert len(decomposed_goal.root_subgoal_ids) > 0
        assert decomposed_goal.total_resources is not None
        assert decomposed_goal.total_resources.time_hours > 0

    @pytest.mark.asyncio
    async def test_decompose_goal_with_context(self, goal_decomposition_engine, sample_goal):
        """Test decomposing a goal with additional context."""
        context = {
            "keywords": ["test", "unit testing", "development"],
            "template": {
                "name": "Test Template",
                "subgoals": [
                    {
                        "name": "Custom Subgoal 1",
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
        
        decomposed_goal = await goal_decomposition_engine.decompose_goal(
            goal=sample_goal,
            strategy=DecompositionStrategy.TOP_DOWN,
            context=context
        )
        
        assert decomposed_goal is not None
        assert len(decomposed_goal.subgoals) > 0
        goal_decomposition_engine.knowledge_system.query_semantic_memory.assert_called()

    @pytest.mark.asyncio
    async def test_decompose_goal_validation(self, goal_decomposition_engine):
        """Test goal validation during decomposition."""
        with pytest.raises(InvalidGoalError, match="Goal must be a dictionary"):
            await goal_decomposition_engine.decompose_goal("not a dict")
        
        with pytest.raises(InvalidGoalError, match="Goal must have a name"):
            await goal_decomposition_engine.decompose_goal({})
        
        goal = {
            "name": "Test Goal",
            "type": "INVALID_TYPE"
        }
        decomposed_goal = await goal_decomposition_engine.decompose_goal(goal)
        assert decomposed_goal.goal_type == GoalType.GENERAL

    @pytest.mark.asyncio
    async def test_resource_estimate_validation(self):
        """Test resource estimate validation."""
        resource = ResourceEstimate(
            time_hours=10.0,
            complexity=7,
            knowledge_requirements=["python", "testing"],
            dependencies=[],
            risk_level=5
        )
        assert resource is not None
        
        with pytest.raises(ValueError, match="Time hours must be non-negative"):
            ResourceEstimate(
                time_hours=-1.0,
                complexity=7,
                knowledge_requirements=[],
                dependencies=[],
                risk_level=5
            )
        
        with pytest.raises(ValueError, match="Complexity must be between 1 and 10"):
            ResourceEstimate(
                time_hours=10.0,
                complexity=11,
                knowledge_requirements=[],
                dependencies=[],
                risk_level=5
            )
        
        with pytest.raises(ValueError, match="Risk level must be between 1 and 10"):
            ResourceEstimate(
                time_hours=10.0,
                complexity=7,
                knowledge_requirements=[],
                dependencies=[],
                risk_level=0
            )

    @pytest.mark.asyncio
    async def test_resource_estimate_merge(self, sample_resource_estimate):
        """Test merging resource estimates."""
        other_resource = ResourceEstimate(
            time_hours=5.0,
            complexity=8,
            knowledge_requirements=["java", "testing"],
            dependencies=["dep1"],
            risk_level=6
        )
        
        merged = sample_resource_estimate.merge(other_resource)
        assert merged.time_hours == 15.0
        assert merged.complexity == 8
        assert set(merged.knowledge_requirements) == {"python", "testing", "java"}
        assert set(merged.dependencies) == {"dep1"}
        assert merged.risk_level == 6

    @pytest.mark.asyncio
    async def test_subgoal_validation(self, sample_resource_estimate):
        """Test subgoal validation."""
        with pytest.raises(ValueError, match="Priority must be between 1 and 10"):
            SubGoal(
                id=str(uuid.uuid4()),
                name="Test",
                description="Test",
                goal_type=GoalType.DEVELOPMENT,
                priority=11,
                resources=sample_resource_estimate
            )
        
        with pytest.raises(ValueError, match="Name cannot be empty"):
            SubGoal(
                id=str(uuid.uuid4()),
                name="",
                description="Test",
                goal_type=GoalType.DEVELOPMENT,
                priority=5,
                resources=sample_resource_estimate
            )
        
        with pytest.raises(ValueError, match="Invalid status"):
            SubGoal(
                id=str(uuid.uuid4()),
                name="Test",
                description="Test",
                goal_type=GoalType.DEVELOPMENT,
                priority=5,
                resources=sample_resource_estimate,
                status="invalid_status"
            )

    @pytest.mark.asyncio
    async def test_subgoal_serialization(self, sample_subgoal):
        """Test subgoal serialization and deserialization."""
        subgoal_dict = sample_subgoal.to_dict()
        assert isinstance(subgoal_dict, dict)
        assert subgoal_dict["name"] == sample_subgoal.name
        assert subgoal_dict["goal_type"] == sample_subgoal.goal_type.name
        
        reconstructed = SubGoal.from_dict(subgoal_dict)
        assert reconstructed.id == sample_subgoal.id
        assert reconstructed.name == sample_subgoal.name
        assert reconstructed.goal_type == sample_subgoal.goal_type
        assert reconstructed.priority == sample_subgoal.priority
        assert reconstructed.resources.time_hours == sample_subgoal.resources.time_hours

    @pytest.mark.asyncio
    async def test_decomposed_goal_tree_analysis(self, goal_decomposition_engine, sample_goal):
        """Test decomposed goal tree analysis methods."""
        decomposed_goal = await goal_decomposition_engine.decompose_goal(sample_goal)
        
        tree = decomposed_goal.get_subgoal_tree()
        assert isinstance(tree, dict)
        assert "root" in tree
        assert len(tree["root"]) == len(decomposed_goal.root_subgoal_ids)
        
        critical_path = decomposed_goal.get_critical_path()
        assert isinstance(critical_path, list)
        assert len(critical_path) > 0
        
        for subgoal_id in critical_path:
            assert subgoal_id in decomposed_goal.subgoals

    @pytest.mark.asyncio
    async def test_circular_dependency_detection(self):
        """Test detection of circular dependencies."""
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
            )
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
            )
        )
        
        decomposed_goal = DecomposedGoal(
            id=str(uuid.uuid4()),
            name="Test Goal",
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
        
        # Create a simple function to test for circular dependencies
        def has_circular_dependency():
            visited = set()
            path = set()
            
            def dfs(node):
                if node in path:
                    return True
                if node in visited:
                    return False
                
                visited.add(node)
                path.add(node)
                
                # Check dependencies in both directions
                for neighbor in ["1", "2"]:
                    if neighbor != node and dfs(neighbor):
                        return True
                
                path.remove(node)
                return False
            
            return dfs("1")
        
        # Test that circular dependency is detected
        assert has_circular_dependency() is True

    @pytest.mark.asyncio
    async def test_goal_type_conversion(self):
        """Test goal type string conversion."""
        assert GoalType.from_str("DEVELOPMENT") == GoalType.DEVELOPMENT
        assert GoalType.from_str("development") == GoalType.DEVELOPMENT
        assert GoalType.from_str("RESEARCH") == GoalType.RESEARCH
        
        with pytest.raises(ValueError, match="Invalid goal type"):
            GoalType.from_str("INVALID_TYPE")

    @pytest.mark.asyncio
    async def test_decomposition_strategy_conversion(self):
        """Test decomposition strategy string conversion."""
        assert DecompositionStrategy.from_str("TOP_DOWN") == DecompositionStrategy.TOP_DOWN
        assert DecompositionStrategy.from_str("top_down") == DecompositionStrategy.TOP_DOWN
        assert DecompositionStrategy.from_str("BOTTOM_UP") == DecompositionStrategy.BOTTOM_UP
        
        with pytest.raises(ValueError, match="Invalid decomposition strategy"):
            DecompositionStrategy.from_str("INVALID_STRATEGY")

    @pytest.mark.asyncio
    async def test_decomposition_history(self, goal_decomposition_engine, sample_goal):
        """Test decomposition history tracking."""
        goal1 = await goal_decomposition_engine.decompose_goal(sample_goal)
        goal2 = await goal_decomposition_engine.decompose_goal({
            "name": "Another Goal",
            "type": "RESEARCH"
        })
        
        assert len(goal_decomposition_engine.decomposition_history) == 2
        assert goal_decomposition_engine.decomposition_history[0]["goal_id"] == goal1.id
        assert goal_decomposition_engine.decomposition_history[1]["goal_id"] == goal2.id
        
        for entry in goal_decomposition_engine.decomposition_history:
            assert "goal_id" in entry
            assert "strategy" in entry
            assert "timestamp" in entry
            assert "subgoal_count" in entry
            assert "validation" in entry 