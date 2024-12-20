from typing import Optional, Dict, Any, List, Type, TypeVar
from uuid import UUID
import json
import logging
from datetime import datetime
from pathlib import Path

from ...models.specialized_state import (
    StateType, 
    ToolManagementState, 
    TaskGenerationState, 
    AgentFrameworkState,
    StateMetadata,
    SpecializedState
)
from ...models.exceptions import StateNotFoundError
from ..models.view_state import ViewState
from ..models.view_types import ViewType
from .view_serializer import ViewStateSerializer
from ...models.exceptions import StateNotFoundError
from ...controllers.task_runner import TaskRunner

T = TypeVar('T', bound=SpecializedState)

class ViewStateManager:
    def __init__(self, persistence_model):
        self.persistence_model = persistence_model
        self.task_runner = TaskRunner(persistence_model)
        self.state_dir = Path("state/views")
        self.specialized_dir = Path("state/specialized")
        self.sessions_dir = Path("state/sessions")
        self.states: Dict[UUID, SpecializedState] = {}
        self.logger = logging.getLogger(__name__)

    async def initialize(self):
        """Initialize the state manager and its components."""
        try:
            # Load specialized states first
            await self._load_specialized_states()
            
            # Initialize task runner
            await self.task_runner.initialize()
        except Exception as e:
            self.logger.error(f"Error initializing state manager: {str(e)}")
            raise

    async def _load_specialized_states(self):
        """Load all specialized states."""
        try:
            # Load task management state
            task_state = await self._load_state_file(
                self.specialized_dir / "task_management_state.json",
                StateType.TASK_GENERATION
            )
            if task_state:
                self.persistence_model.initialize_from_state(task_state)

            # Load tools state
            tools_state = await self._load_state_file(
                self.specialized_dir / "tools_management_state.json",
                StateType.TOOL_MANAGEMENT
            )
            if tools_state:
                self.persistence_model.initialize_from_state(tools_state)

            # Load agentic state
            agentic_state = await self._load_state_file(
                self.specialized_dir / "agentic_framework_state.json",
                StateType.AGENT_FRAMEWORK
            )
            if agentic_state:
                self.persistence_model.initialize_from_state(agentic_state)

        except Exception as e:
            self.logger.error(f"Error loading specialized states: {str(e)}")
            raise

    async def save_session_state(self, view_name: str, session_data: Dict[str, Any]) -> bool:
        """Save session-specific state (UI state, chat history, etc)."""
        try:
            filepath = self.sessions_dir / f"{view_name}_view_default.json"
            
            # Load existing session state
            existing_state = {}
            if filepath.exists():
                with open(filepath, 'r') as f:
                    existing_state = json.load(f)
            
            # Update with new session data
            existing_state.update({
                'chat_history': session_data.get('chat_history', []),
                'selected_node': session_data.get('selected_node'),
                'expanded_nodes': session_data.get('expanded_nodes', []),
                'last_access': datetime.now().isoformat()
            })
            
            # Save updated session state
            with open(filepath, 'w') as f:
                json.dump(existing_state, f, indent=2)
                
            return True
            
        except Exception as e:
            self.logger.error(f"Error saving session state: {str(e)}")
            return False

    async def create_specialized_state(
        self, 
        state_type: StateType, 
        name: str,
        initial_data: Optional[Dict[str, Any]] = None,
        metadata: Optional[StateMetadata] = None
    ) -> Optional[Any]:
        """Create a new specialized state."""
        try:
            if metadata is None:
                metadata = StateMetadata()
            
            initial_data = initial_data or {}
            
            # Create state instance based on type
            if state_type == StateType.TASK_GENERATION:
                state = TaskGenerationState(
                    state_type=state_type,
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
                raise StateNotFoundError(f"Unsupported state type: {state_type}")
            
            # Store state
            self.states[state.id] = state
            
            # Persist to file
            await self._persist_specialized_state(state)
            
            return state
            
        except StateNotFoundError:
            raise
        except Exception as e:
            self.logger.error(f"Error creating specialized state: {str(e)}")
            raise

    async def load_specialized_state(self, state_id: UUID) -> Optional[Any]:
        """Load a specialized state by ID."""
        try:
            # Check memory cache first
            if state_id in self.states:
                return self.states[state_id]
            
            # Look for state file in each type directory
            for state_type in StateType:
                state_type_dir = self.specialized_dir / state_type.value
                if not state_type_dir.exists():
                    continue
                    
                for state_file in state_type_dir.glob("*.json"):
                    with open(state_file, 'r') as f:
                        state_data = json.load(f)
                        if UUID(state_data["id"]) == state_id:
                            # Create appropriate state instance
                            if state_type == StateType.TOOL_MANAGEMENT:
                                state = ToolManagementState(**state_data)
                            elif state_type == StateType.TASK_GENERATION:
                                state = TaskGenerationState(**state_data)
                            elif state_type == StateType.AGENT_FRAMEWORK:
                                # Special handling for AgentFrameworkState
                                state_data.pop('state_type', None)  # Remove state_type only for AgentFrameworkState
                                state = AgentFrameworkState(**state_data)
                            else:
                                continue
                            
                            # Cache and return
                            self.states[state.id] = state
                            return state
            
            raise StateNotFoundError(f"No state found with ID {state_id}")
            
        except Exception as e:
            self.logger.error(f"Error loading specialized state: {str(e)}")
            raise
    
    async def update_state(self, state_id: UUID, data: Dict[str, Any]) -> None:
        """Update a specialized state by ID"""
        if state_id not in self.states:
            raise StateNotFoundError(f"No state found with ID {state_id}")
        
        state = self.states[state_id]
        await state.update(data)
        
        # Persist updated state
        state_file = self.state_dir / f"{state.state_type.value}_state.json"
        with open(state_file, 'w') as f:
            json.dump(state.dict(), f, indent=2, default=str)

    def _get_state_class(self, state_type: StateType) -> Type[SpecializedState]:
        """Get the appropriate state class for a state type"""
        return {
            StateType.TASK_GENERATION: TaskGenerationState,
            StateType.TOOL_MANAGEMENT: ToolManagementState,
            StateType.AGENT_FRAMEWORK: AgentFrameworkState
        }.get(state_type)

    async def _persist_specialized_state(self, state: SpecializedState) -> None:
        """Persist specialized state to file system"""
        try:
            # Create state-type specific directory if it doesn't exist
            state_type_dir = self.specialized_dir / state.state_type.value
            state_type_dir.mkdir(parents=True, exist_ok=True)
            
            # Save state to its type-specific directory
            file_path = state_type_dir / f"{state.id}.json"
            with open(file_path, 'w') as f:
                json.dump(state.dict(), f, indent=2, default=str)
        except Exception as e:
            self.logger.error(f"Error persisting specialized state {state.id}: {str(e)}")
            raise

    def load_state(self, view_type: ViewType, filename: Optional[str] = None) -> Optional[ViewState]:
        """Load view state from disk."""
        try:
            if not filename:
                states = self.list_states(view_type)
                if not states:
                    return None
                filename = states[-1]['filename']
                
            filepath = self.state_dir / filename
            
            if filepath.exists():
                with open(filepath, 'r') as f:
                    state_data = json.load(f)
                return self.serializer.deserialize(state_data)
            return None
            
        except Exception as e:
            self.logger.error(f"Error loading view state: {str(e)}")
            return None

    def list_states(self, view_type: Optional[ViewType] = None) -> List[Dict[str, Any]]:
        """List available view states."""
        try:
            if hasattr(self.persistence_model, 'view_states'):
                states = self.persistence_model.view_states.list()
                if view_type:
                    states = [s for s in states if s['type'] == view_type.value]
                return sorted(states, key=lambda x: x['created_at'], reverse=True)
            
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
            self.logger.error(f"Error listing view states: {str(e)}")
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
                    self.states[state.id] = state
        except Exception as e:
            self.logger.error(f"Error loading specialized states: {str(e)}")
            raise

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

    async def _load_state_file(self, filepath: Path, state_type: StateType) -> Optional[SpecializedState]:
        """Load state from file."""
        try:
            if filepath.exists():
                with open(filepath, 'r') as f:
                    state_data = json.load(f)
                    
                # Get appropriate state class
                state_class = self._get_state_class(state_type)
                if not state_class:
                    self.logger.error(f"No state class found for type {state_type}")
                    return None
                    
                # Create state instance
                state = state_class(**state_data)
                self.states[state.id] = state
                return state
                
            return None
            
        except Exception as e:
            self.logger.error(f"Error loading state file {filepath}: {str(e)}")
            return None