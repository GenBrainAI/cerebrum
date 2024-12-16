from typing import Dict, Any, Optional, Type
from pathlib import Path
import json
from datetime import datetime
import asyncio

from ..models.exceptions import StateError, StateNotFoundError
from ..models.specialized_state import (
    SpecializedState, StateType, TaskGenerationState,
    ToolManagementState, AgentFrameworkState, StateMetadata
)

class StateManager:
    """Manages specialized state persistence and loading."""
    
    def __init__(self, persistence_model):
        self.persistence_model = persistence_model
        
    async def create_specialized_state(self, state_type: StateType, name: str, initial_data: dict, metadata: Optional[StateMetadata] = None) -> SpecializedState:
        if metadata is None:
            metadata = StateMetadata()
            
        if state_type == StateType.TASK_GENERATION:
            state = TaskGenerationState(
                state_type=state_type,  # This was missing
                name=name,
                data=initial_data,
                metadata=metadata
            )
        elif state_type == StateType.TOOL_MANAGEMENT:
            state = ToolManagementState(
                state_type=state_type,
                name=name,
                data=initial_data,
                metadata=metadata
            )
        elif state_type == StateType.AGENT_FRAMEWORK:
            state = AgentFrameworkState(
                state_type=state_type,
                name=name,
                data=initial_data,
                metadata=metadata
            )
        else:
            raise ValueError(f"Unsupported state type: {state_type}")
            
        # Save the state
        await self.persistence_model.write_state(str(state.id), state.dict())
        return state
            
    async def load_specialized_state(self, state_id: str) -> Optional[SpecializedState]:
        """Load specialized state by ID."""
        try:
            # Read state data
            state_data = await self._read_state_data(state_id)
            if not state_data:
                return None
                
            # Map state types to their classes
            state_classes = {
                StateType.TASK_GENERATION: TaskGenerationState,
                StateType.TOOL_MANAGEMENT: ToolManagementState,
                StateType.AGENT_FRAMEWORK: AgentFrameworkState
            }
            
            state_type = StateType(state_data.get("state_type"))
            state_class = state_classes.get(state_type)
            
            if not state_class:
                raise StateError(f"Unknown state type: {state_type}")
                
            # Create and return state instance
            return state_class(**state_data)
            
        except Exception as e:
            raise StateError(f"Failed to load specialized state: {str(e)}")
            
    async def update_state(self, state_id: str, data: Dict[str, Any]) -> None:
        """Update specialized state data."""
        try:
            state = await self.load_specialized_state(state_id)
            if not state:
                raise StateNotFoundError(f"State not found: {state_id}")
                
            await state.update(data)
            await self._persist_specialized_state(state)
            
        except Exception as e:
            raise StateError(f"Failed to update state: {str(e)}")
            
    async def _generate_state_id(self) -> str:
        """Generate unique state ID."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"state_{timestamp}"
        
    async def _persist_specialized_state(self, state: SpecializedState) -> None:
        """Persist specialized state to storage."""
        try:
            state_data = state.dict()
            await self._write_state_data(state.id, state_data)
        except Exception as e:
            raise StateError(f"Failed to persist state: {str(e)}")
            
    async def _read_state_data(self, state_id: str) -> Optional[Dict[str, Any]]:
        """Read state data from storage."""
        try:
            # TODO: Implement actual storage read
            return {}
        except Exception as e:
            raise StateError(f"Failed to read state data: {str(e)}")
            
    async def _write_state_data(self, state_id: str, data: Dict[str, Any]) -> None:
        """Write state data to storage."""
        try:
            # TODO: Implement actual storage write
            pass
        except Exception as e:
            raise StateError(f"Failed to write state data: {str(e)}")