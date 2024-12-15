from typing import Optional, Dict, Any, List
from pathlib import Path
import json
from datetime import datetime

from ..models.view_state import ViewState
from ..models.view_types import ViewType
from .view_serializer import ViewStateSerializer

class ViewStateManager:
    """Manages persistence of view states."""
    
    def __init__(self, persistence_model, state_dir: Optional[Path] = None):
        self.persistence_model = persistence_model
        self.state_dir = state_dir or Path("state/views")
        self.serializer = ViewStateSerializer()
        self.state_dir.mkdir(parents=True, exist_ok=True)
        
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