import os
from pathlib import Path
from typing import Optional, Dict

class StateLoader:
    """Utility class for loading state files."""
    
    @staticmethod
    def get_project_root() -> Path:
        """Get the project root directory."""
        current_file = Path(__file__).resolve()
        return current_file.parent.parent.parent.parent

    @staticmethod
    def get_state_file(filename: str) -> Optional[Path]:
        """Get the path to a state file in the specialized states directory."""
        try:
            root_dir = StateLoader.get_project_root()
            state_path = root_dir / "state" / "specialized" / filename
            print(f"Looking for state file at: {state_path}")
            return state_path if state_path.exists() else None
        except Exception as e:
            print(f"Error getting state file path: {str(e)}")
            return None

    @staticmethod
    def get_state_ids(state_type: str) -> Dict[str, str]:
        """Get state IDs from state file."""
        try:
            state_file = StateLoader.get_state_file(f"{state_type}_state.json")
            if state_file and state_file.exists():
                # Load and return IDs from state file
                import json
                with open(state_file, 'r') as f:
                    data = json.load(f)
                    return data.get('ids', {})
            return {}
        except Exception as e:
            print(f"Error loading state IDs: {str(e)}")
            return {}