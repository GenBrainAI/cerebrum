import pytest
import asyncio
from pathlib import Path
import tempfile
import shutil
from uuid import UUID
import pytest_asyncio

from src.server.models.specialized_state import (
    StateType, SpecializedState, TaskGenerationState,
    ToolGenerationState, AgenticFrameworkState, StateMetadata
)
from src.server.views.state.state_manager import ViewStateManager

pytestmark = pytest.mark.asyncio

@pytest_asyncio.fixture
async def state_manager():
    """Fixture providing a ViewStateManager instance with temporary directory."""
    test_dir = tempfile.mkdtemp()
    manager = ViewStateManager(None, Path(test_dir))
    await manager.load_specialized_states()
    yield manager
    shutil.rmtree(test_dir)

@pytest.mark.asyncio
async def test_create_specialized_state(state_manager):
    """Test creating new specialized state."""
    state = await state_manager.create_specialized_state(
        state_type=StateType.TASK_GENERATION,
        name="Test State",
        initial_data={"key": "value"}
    )
    assert isinstance(state.id, UUID)
    assert state.state_type == StateType.TASK_GENERATION
    assert state.data["key"] == "value"

@pytest.mark.asyncio
async def test_state_persistence(state_manager):
    """Test state persistence and recovery."""
    # Create state
    state = await state_manager.create_specialized_state(
        state_type=StateType.TOOL_GENERATION,
        name="Test State"
    )
    
    # Create new manager instance to test loading
    new_manager = ViewStateManager(None, state_manager.state_dir)
    await new_manager.load_specialized_states()
    
    loaded_state = new_manager.specialized_states.get(state.id)
    assert loaded_state is not None
    assert loaded_state.name == state.name

@pytest.mark.asyncio
async def test_state_update(state_manager):
    """Test updating state data."""
    state = await state_manager.create_specialized_state(
        state_type=StateType.TASK_GENERATION,
        name="Test State"
    )
    original_update = state.metadata.updated_at
    await state_manager.update_state(state.id, {"new_key": "value"})
    assert state.data["new_key"] == "value"
    assert state.metadata.updated_at > original_update

@pytest.mark.asyncio
async def test_concurrent_updates(state_manager):
    """Test concurrent state updates."""
    state = await state_manager.create_specialized_state(
        state_type=StateType.TASK_GENERATION,
        name="Test"
    )
    
    # Simulate concurrent updates
    update1 = {"key1": "value1"}
    update2 = {"key2": "value2"}
    
    # Create coroutines for concurrent execution
    persist_coro = state_manager._persist_specialized_state(state)
    update_coro1 = state.update(update1)
    update_coro2 = state.update(update2)
    
    # Execute updates concurrently
    await asyncio.gather(
        persist_coro,
        update_coro1,
        update_coro2
    )
    
    # Verify updates
    assert state.data["key1"] == "value1"
    assert state.data["key2"] == "value2"
    
    # Verify persistence
    loaded_state = state_manager.specialized_states.get(state.id)
    assert loaded_state is not None
    assert loaded_state.data["key1"] == "value1"
    assert loaded_state.data["key2"] == "value2"

def test_state_validation():
    """Test state validation constraints."""
    with pytest.raises(ValueError):
        TaskGenerationState(
            state_type=StateType.TOOL_GENERATION,  # Wrong type
            name="Test"
        )

def test_metadata_versioning():
    """Test metadata versioning."""
    state = TaskGenerationState(
        state_type=StateType.TASK_GENERATION,
        name="Test",
        metadata=StateMetadata(version="2.0.0")
    )
    assert state.metadata.version == "2.0.0"
