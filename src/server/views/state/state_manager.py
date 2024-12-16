from typing import Optional, Dict, Any, List, Type, TypeVar
from pathlib import Path
import json
import logging
from datetime import datetime
from uuid import UUID

from ...models.specialized_state import (
    SpecializedState, StateType, TaskGenerationState,
    ToolGenerationState, AgenticFrameworkState, StateMetadata
)
from ..models.view_state import ViewState
from ..models.view_types import ViewType
from .view_serializer import ViewStateSerializer

T = TypeVar('T', bound=SpecializedState)

class ViewStateManager:
    """Enhanced state manager supporting specialized states"""
    
    def __init__(self, persistence_model, state_dir: Optional[Path] = None):
        self.persistence_model = persistence_model
        self.state_dir = state_dir or Path("state/views")
        self.specialized_dir = self.state_dir / "specialized"
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.specialized_dir.mkdir(parents=True, exist_ok=True)
        self.logger = logging.getLogger(__name__)
        self.specialized_states: Dict[UUID, SpecializedState] = {}
        
    async def create_specialized_state(
        self, 
        state_type: StateType,
        name: str,
        initial_data: Optional[Dict[str, Any]] = None,
        metadata: Optional[StateMetadata] = None
    ) -> SpecializedState:
        """Create a new specialized state"""
        state_class = self._get_state_class(state_type)
        state = state_class(
            state_type=state_type,
            name=name,
            data=initial_data or {},
            metadata=metadata or StateMetadata()
        )
        self.specialized_states[state.id] = state
        await self._persist_specialized_state(state)
        return state

    def _get_state_class(self, state_type: StateType) -> Type[SpecializedState]:
        """Get the appropriate state class for a state type"""
        return {
            StateType.TASK_GENERATION: TaskGenerationState,
            StateType.TOOL_GENERATION: ToolGenerationState,
            StateType.AGENTIC_FRAMEWORK: AgenticFrameworkState
        }.get(state_type, SpecializedState)

    async def _persist_specialized_state(self, state: SpecializedState) -> None:
        """Persist specialized state to file system"""
        try:
            file_path = self.specialized_dir / f"{state.id}.json"
            with open(file_path, 'w') as f:
                json.dump(state.dict(), f, indent=2, default=str)
        except Exception as e:
            self.logger.error(f"Error persisting specialized state {state.id}: {str(e)}")
            raise

    def save_state(self, view_type: ViewType, state: ViewState) -> bool:
        """Save view state to disk."""
        try:
            # Serialize state
            state_data = self.serializer.serialize(state)
            
            # Generate filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{view_type.value}_{timestamp}.json"
            filepath = self.state_dir / filename
            
            # Save to file
            with open(filepath, 'w') as f:
                json.dump(state_data, f, indent=2)
                
            # Update persistence model
            if hasattr(self.persistence_model, 'view_states'):
                self.persistence_model.view_states.create({
                    'type': view_type.value,
                    'filename': filename,
                    'created_at': timestamp,
                    'state': state_data
                })
                
            return True
            
        except Exception as e:
            print(f"Error saving view state: {str(e)}")
            return False
            
    def load_state(self, view_type: ViewType, filename: Optional[str] = None) -> Optional[ViewState]:
        """Load view state from disk."""
        try:
            # If filename not specified, load most recent state for view type
            if not filename:
                states = self.list_states(view_type)
                if not states:
                    return None
                filename = states[-1]['filename']  # Most recent state
                
            filepath = self.state_dir / filename
            
            # Load from file
            if filepath.exists():
                with open(filepath, 'r') as f:
                    state_data = json.load(f)
                return self.serializer.deserialize(state_data)
                
            return None
            
        except Exception as e:
            print(f"Error loading view state: {str(e)}")
            return None
            
    def list_states(self, view_type: Optional[ViewType] = None) -> List[Dict[str, Any]]:
        """List available view states."""
        try:
            # Get states from persistence model if available
            if hasattr(self.persistence_model, 'view_states'):
                states = self.persistence_model.view_states.list()
                if view_type:
                    states = [s for s in states if s['type'] == view_type.value]
                return sorted(states, key=lambda x: x['created_at'], reverse=True)
            
            # Otherwise read from filesystem
            pattern = f"{view_type.value}_*.json" if view_type else "*.json"
            files = list(self.state_dir.glob(pattern))
            
            return [
                {
                    'filename': f.name,
                    'type': f.name.split('_')[0],
                    'created_at': f.name.split('_')[1].replace('.json', '')
                }
                for f in sorted(files, key=lambda x: x.stat().st_mtime, reverse=True)
            ]
            
        except Exception as e:
            print(f"Error listing view states: {str(e)}")
            return [] 

    async def load_specialized_states(self) -> None:
        """Load all persisted specialized states"""
        try:
            for file_path in self.specialized_dir.glob("*.json"):
                with open(file_path, 'r') as f:
                    data = json.load(f)
                    state_type = StateType(data['state_type'])
                    state_class = self._get_state_class(state_type)
                    state = state_class(**data)
                    self.specialized_states[state.id] = state
        except Exception as e:
            self.logger.error(f"Error loading specialized states: {str(e)}")
            raise 

    async def update_state(self, state_id: UUID, data: Dict[str, Any]) -> None:
        """Update a specialized state by ID"""
        if state_id not in self.specialized_states:
            raise ValueError(f"No state found with ID {state_id}")
        
        state = self.specialized_states[state_id]
        await state.update(data)
        await self._persist_specialized_state(state)

    async def create_state(
        self, 
        state_type: StateType,
        name: str,
        version: str = "1.0.0",
        initial_data: Optional[Dict[str, Any]] = None
    ) -> SpecializedState:
        """Create a new state with version control"""
        metadata = StateMetadata(version=version)
        state = await self.create_specialized_state(
            state_type=state_type,
            name=name,
            initial_data=initial_data or {},
            metadata=metadata
        )
        return state