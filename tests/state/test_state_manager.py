import pytest
import asyncio
from pathlib import Path
import tempfile
import shutil
from uuid import UUID
import pytest_asyncio

from src.server.models.specialized_state import (
    StateType, SpecializedState, StateMetadata
)
from src.server.views.state.state_manager import ViewStateManager

@pytest_asyncio.fixture
async def state_manager():
    """Fixture providing a ViewStateManager instance with temporary directory."""
    test_dir = tempfile.mkdtemp()
    manager = ViewStateManager(None, Path(test_dir))
    await manager.load_specialized_states()
    yield manager
    shutil.rmtree(test_dir)

@pytest.mark.asyncio
async def test_state_creation(state_manager):
    """Test creating a new state."""
    state = await state_manager.create_state(
        state_type=StateType.TASK_GENERATION,
        name="Test State",
        initial_data={"key": "value"}
    )
    assert isinstance(state.id, UUID)
    assert state.state_type == StateType.TASK_GENERATION
    assert state.data["key"] == "value"

@pytest.mark.asyncio
async def test_state_versioning(state_manager):
    """Test state versioning."""
    version = "2.0.0"
    state = await state_manager.create_state(
        state_type=StateType.TASK_GENERATION,
        name="Test State",
        version=version
    )
    assert state.metadata.version == version

@pytest.mark.asyncio
async def test_state_update(state_manager):
    """Test updating state data."""
    state = await state_manager.create_state(
        state_type=StateType.TASK_GENERATION,
        name="Test State"
    )
    original_update = state.metadata.updated_at
    await state_manager.update_state(state.id, {"new_key": "value"})
    assert state.data["new_key"] == "value"
    assert state.metadata.updated_at > original_update

@pytest.mark.asyncio
async def test_state_persistence(state_manager):
    """Test state persistence and recovery."""
    # Create initial state
    state = await state_manager.create_state(
        state_type=StateType.TOOL_GENERATION,
        name="Test State"
    )
    
    # Create new manager instance to test loading
    new_manager = ViewStateManager(None, state_manager.state_dir)
    await new_manager.load_specialized_states()
    
    # Verify state was loaded
    loaded_state = new_manager.specialized_states.get(state.id)
    assert loaded_state is not None
    assert loaded_state.name == state.name