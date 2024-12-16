from typing import Optional, Dict, Any, List
from pathlib import Path
import json
import logging
from datetime import datetime
from uuid import UUID
from asyncio import Lock

from ..models.specialized_state import (
    SpecializedState, StateType, TaskGenerationState,
    ToolGenerationState, AgenticFrameworkState
)
from ..models.exceptions import (
    StateError, StateNotFoundError, StateValidationError,
    StateLockError, StateUpdateError
)

class StateManager:
    """Core service for managing application state."""
    
    def __init__(self, state_dir: Path = Path("state/specialized")):
        self.state_dir = state_dir
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.states: Dict[UUID, SpecializedState] = {}
        self.logger = logging.getLogger(__name__)
        self.locks: Dict[UUID, Lock] = {}
    
    async def create_state(
        self, 
        state_type: StateType,
        name: str,
        initial_data: Optional[Dict[str, Any]] = None
    ) -> SpecializedState:
        """Create and persist a new state."""
        state_class = self._get_state_class(state_type)
        state = state_class(
            state_type=state_type,
            name=name,
            data=initial_data or {}
        )
        self.states[state.id] = state
        await self._persist_state(state)
        return state
    
    async def get_state(self, state_id: UUID) -> Optional[SpecializedState]:
        """Retrieve a state by ID."""
        state = self.states.get(state_id)
        if not state:
            raise StateNotFoundError(f"State {state_id} not found")
        return state
    
    async def update_state(
        self, 
        state_id: UUID,
        data: Dict[str, Any]
    ) -> Optional[SpecializedState]:
        """Update state data with concurrency control."""
        try:
            await self._acquire_lock(state_id)
            state = await self.get_state(state_id)
            if not state:
                raise StateNotFoundError(f"State {state_id} not found")
            
            try:
                state.update(data)
            except Exception as e:
                raise StateUpdateError(f"Failed to update state: {str(e)}")
                
            await self._persist_state(state)
            return state
            
        except StateError:
            raise
        except Exception as e:
            raise StateError(f"State update failed: {str(e)}")
        finally:
            await self._release_lock(state_id)
    
    async def load_states(self) -> None:
        """Load all persisted states."""
        for file_path in self.state_dir.glob("*.json"):
            try:
                with open(file_path, 'r') as f:
                    data = json.load(f)
                    state_type = StateType(data['state_type'])
                    state_class = self._get_state_class(state_type)
                    state = state_class(**data)
                    self.states[state.id] = state
            except Exception as e:
                self.logger.error(f"Error loading state from {file_path}: {str(e)}")
    
    def _get_state_class(self, state_type: StateType) -> type:
        """Get appropriate state class for type."""
        return {
            StateType.TASK_GENERATION: TaskGenerationState,
            StateType.TOOL_GENERATION: ToolGenerationState,
            StateType.AGENTIC_FRAMEWORK: AgenticFrameworkState
        }[state_type]
    
    async def _persist_state(self, state: SpecializedState) -> None:
        """Persist state to filesystem."""
        try:
            file_path = self.state_dir / f"{state.id}.json"
            with open(file_path, 'w') as f:
                json.dump(state.dict(), f, indent=2, default=str)
        except Exception as e:
            self.logger.error(f"Error persisting state {state.id}: {str(e)}")
            raise 
    
    async def _acquire_lock(self, state_id: UUID) -> None:
        """Acquire lock for state updates."""
        if state_id not in self.locks:
            self.locks[state_id] = Lock()
        await self.locks[state_id].acquire()
    
    async def _release_lock(self, state_id: UUID) -> None:
        """Release state lock."""
        if state_id in self.locks:
            self.locks[state_id].release()
    
    async def update_state_version(
        self,
        state_id: UUID,
        new_version: str
    ) -> Optional[SpecializedState]:
        """Update state version."""
        try:
            await self._acquire_lock(state_id)
            state = await self.get_state(state_id)
            if state:
                state.metadata.version = new_version
                state.metadata.updated_at = datetime.now()
                await self._persist_state(state)
            return state
        finally:
            await self._release_lock(state_id)