import pytest
import asyncio
from pathlib import Path
import tempfile
import shutil
from uuid import UUID
import pytest_asyncio
from datetime import datetime
from typing import Optional

from src.server.models.specialized_state import (
    SpecializedState, StateType, TaskGenerationState,
    ToolManagementState, AgentFrameworkState, StateMetadata
)
from src.server.views.state.state_manager import ViewStateManager
from src.server.models.exceptions import StateError, StateNotFoundError

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
async def test_state_creation(state_manager):
    """Test creating new state."""
    state = await state_manager.create_specialized_state(
        state_type=StateType.TASK_GENERATION,
        name="Test State",
        initial_data={"key": "value"}
    )
    assert isinstance(state.id, UUID)
    assert state.state_type == StateType.TASK_GENERATION
    assert state.data == {"key": "value"}

@pytest.mark.asyncio
async def test_state_loading(state_manager):
    """Test loading existing state."""
    # Create state first
    state = await state_manager.create_specialized_state(
        state_type=StateType.TASK_GENERATION,
        name="Test State",
        initial_data={"key": "value"}
    )
    
    # Load it back
    loaded_state = await state_manager.load_specialized_state(state.id)
    assert loaded_state is not None
    assert loaded_state.id == state.id
    assert loaded_state.name == state.name
    assert loaded_state.state_type == state.state_type

@pytest.mark.asyncio
async def test_state_update(state_manager):
    """Test updating state data."""
    # Create initial state
    state = await state_manager.create_specialized_state(
        state_type=StateType.TASK_GENERATION,
        name="Test State",
        initial_data={"key": "value"}
    )
    
    # Update it
    await state_manager.update_state(state.id, {"new_key": "value"})
    
    # Load and verify update
    updated_state = await state_manager.load_specialized_state(state.id)
    assert updated_state is not None
    assert updated_state.data["new_key"] == "value"

@pytest.mark.asyncio
async def test_invalid_state_type(state_manager):
    """Test error handling for invalid state type."""
    with pytest.raises(StateNotFoundError):
        await state_manager.create_specialized_state(
            state_type="invalid_type", 
            name="Test State",
            initial_data={"key": "value"}
        )

@pytest.mark.asyncio
async def test_state_not_found(state_manager):
    """Test error handling for non-existent state."""
    with pytest.raises(StateNotFoundError):
        await state_manager.update_state(
            UUID('00000000-0000-0000-0000-000000000000'),
            {"key": "value"}
        ) 