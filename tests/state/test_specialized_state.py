import pytest
import asyncio
from pathlib import Path
import tempfile
import shutil
from uuid import UUID
import pytest_asyncio
from datetime import datetime
from uuid import uuid4
import json
from typing import Optional

from src.server.models.specialized_state import (
    SpecializedState, StateType, TaskGenerationState,
    ToolManagementState, AgentFrameworkState, StateMetadata
)
from src.server.views.state.state_manager import ViewStateManager

class MockPersistenceModel:
    """Mock persistence model for testing."""
    def __init__(self, state_dir: Path):
        self.state_dir = state_dir
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.states = {}  # In-memory storage for testing
        
    async def read_state(self, state_id: str) -> Optional[dict]:
        """Read state from in-memory storage."""
        return self.states.get(state_id)
        
    async def write_state(self, state_id: str, data: dict):
        """Write state to in-memory storage."""
        self.states[state_id] = data

@pytest_asyncio.fixture
async def state_manager():
    """Fixture providing a ViewStateManager instance with temporary directory."""
    test_dir = tempfile.mkdtemp()
    persistence_model = MockPersistenceModel(Path(test_dir))
    manager = ViewStateManager(persistence_model)
    yield manager
    shutil.rmtree(test_dir)

@pytest.mark.asyncio
async def test_create_specialized_state(state_manager):
    """Test creating new specialized state."""
    initial_data = {
        "active_view": "task_hierarchy",
        "tasks": [],
        "selected_task": None,
        "task_hierarchy": {},
        "task_details": {},
        "total_tasks": 0
    }
    
    state = await state_manager.create_specialized_state(
        state_type=StateType.TASK_GENERATION,
        name="Test State",
        initial_data=initial_data,
        metadata=StateMetadata()
    )
    
    # Verify state creation
    assert state is not None
    assert isinstance(state.id, UUID)
    assert state.state_type == StateType.TASK_GENERATION
    assert state.name == "Test State"
    assert state.data == initial_data
    assert isinstance(state.metadata, StateMetadata)

@pytest.mark.asyncio
async def test_state_persistence(state_manager):
    """Test state persistence and recovery."""
    # Create initial state data
    initial_data = {
        "key": "value",
        "active_view": "tools_catalog",
        "selected_tool": None,
        "tool_templates": {},
        "registered_tools": [],
        "active_tools": [],
        "last_created_tool": None,
        "total_tools": 0
    }
    
    # Create state
    state = await state_manager.create_specialized_state(
        state_type=StateType.TOOL_MANAGEMENT,
        name="Test State",
        initial_data=initial_data
    )
    
    # Verify state was created
    assert state is not None
    assert isinstance(state.id, UUID)
    assert state.state_type == StateType.TOOL_MANAGEMENT
    assert state.name == "Test State"
    assert state.data == initial_data
    
    # Store state ID for loading
    state_id = state.id
    
    # Load the state back
    loaded_state = await state_manager.load_specialized_state(state_id)
    
    # Verify loaded state matches original
    assert loaded_state is not None
    assert loaded_state.state_type == state.state_type
    assert loaded_state.name == state.name
    assert loaded_state.id == state.id
    assert loaded_state.data == state.data

@pytest.mark.asyncio
async def test_state_update(state_manager):
    """Test updating state data."""
    state = await state_manager.create_specialized_state(
        state_type=StateType.TASK_GENERATION,
        name="Test State"
    )
    original_update = state.metadata.updated_at
    await state_manager.update_state(state.id, {"new_key": "value"})
    
    # Load updated state
    updated_state = await state_manager.load_specialized_state(state.id)
    assert updated_state is not None
    assert updated_state.data["new_key"] == "value"
    assert updated_state.metadata.updated_at > original_update
    assert isinstance(updated_state.id, UUID)

def test_state_validation():
    """Test state validation constraints."""
    with pytest.raises(ValueError):
        TaskGenerationState(
            state_type=StateType.TOOL_MANAGEMENT,  # Wrong type
            name="Test"
        )

def test_metadata_versioning():
    """Test metadata versioning."""
    metadata = StateMetadata(version="2.0.0")
    state = TaskGenerationState(
        name="Test",
        metadata=metadata
    )
    assert state.metadata.version == "2.0.0"

def test_task_generation_state():
    """Test task generation state creation and updates."""
    state = TaskGenerationState(
        state_type=StateType.TASK_GENERATION,
        name="Test Task State",
        data={"test": "data"},
        metadata=StateMetadata()
    )
    
    assert state.state_type == StateType.TASK_GENERATION
    assert state.name == "Test Task State"
    assert state.data == {"test": "data"}
    assert isinstance(state.metadata, StateMetadata)

def test_tool_management_state():
    """Test tool management state creation and updates."""
    state = ToolManagementState(
        state_type=StateType.TOOL_MANAGEMENT,
        name="Test Tool State",
        data={"test": "data"},
        metadata=StateMetadata()
    )
    
    assert state.state_type == StateType.TOOL_MANAGEMENT
    assert state.name == "Test Tool State"
    assert state.data == {"test": "data"}
    assert isinstance(state.metadata, StateMetadata)

def test_agent_framework_state():
    """Test agent framework state creation and updates."""
    state = AgentFrameworkState(
        state_type=StateType.AGENT_FRAMEWORK,
        name="Test Agent State",
        data={"test": "data"},
        metadata=StateMetadata()
    )
    
    assert state.state_type == StateType.AGENT_FRAMEWORK
    assert state.name == "Test Agent State"
    assert state.active_view == "agentic_config"
    assert isinstance(state.frameworks, list)
    assert isinstance(state.task_context, dict)
    assert isinstance(state.metadata, StateMetadata)

@pytest.mark.asyncio
async def test_state_update_data():
    """Test state update functionality."""
    state = TaskGenerationState(
        state_type=StateType.TASK_GENERATION,
        name="Test State",
        data={"initial": "data"},
        metadata=StateMetadata()
    )
    
    await state.update({"new": "data"})
    assert state.data == {"initial": "data", "new": "data"}
    assert isinstance(state.metadata.updated_at, datetime)

def test_state_metadata():
    """Test state metadata handling."""
    metadata = StateMetadata(
        version="2.0.0",
        tags=["test", "demo"],
        description="Test state"
    )
    
    state = TaskGenerationState(
        state_type=StateType.TASK_GENERATION,
        name="Test State",
        data={},
        metadata=metadata
    )
    
    assert state.metadata.version == "2.0.0"
    assert state.metadata.tags == ["test", "demo"]
    assert state.metadata.description == "Test state"
    assert isinstance(state.metadata.created_at, datetime)
    assert isinstance(state.metadata.updated_at, datetime)

def test_metadata_versioning():
    """Test metadata versioning."""
    metadata = StateMetadata(version="2.0.0")
    state = TaskGenerationState(
        state_type=StateType.TASK_GENERATION,
        name="Test",
        data={},
        metadata=metadata
    )
    assert state.metadata.version == "2.0.0"

@pytest.mark.asyncio
async def test_create_different_state_types(state_manager):
    """Test creating different types of specialized states."""
    # Test Tool Management State
    tool_state_data = {
        "active_view": "tools_catalog",
        "selected_tool": None,
        "tool_templates": {},
        "registered_tools": [],
        "active_tools": [],
        "last_created_tool": None,
        "total_tools": 0
    }
    
    tool_state = await state_manager.create_specialized_state(
        state_type=StateType.TOOL_MANAGEMENT,
        name="Test Tool State",
        initial_data=tool_state_data,
        metadata=StateMetadata()
    )
    
    assert tool_state is not None
    assert tool_state.state_type == StateType.TOOL_MANAGEMENT
    
    # Test Agent Framework State
    agent_state_data = {
        "active_view": "agentic_config",
        "selected_agent": None,
        "agent_configs": {},
        "active_agents": [],
        "total_agents": 0
    }
    
    agent_state = await state_manager.create_specialized_state(
        state_type=StateType.AGENT_FRAMEWORK,
        name="Test Agent State",
        initial_data=agent_state_data,
        metadata=StateMetadata()
    )
    
    assert agent_state is not None
    assert agent_state.state_type == StateType.AGENT_FRAMEWORK
