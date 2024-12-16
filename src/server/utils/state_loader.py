from pathlib import Path
import json
from typing import Dict, Any, Optional

class StateLoader:
    """Utility for loading application states."""
    
    @staticmethod
    def load_state_registry() -> Optional[Dict[str, Any]]:
        """Load the state registry."""
        registry_path = Path("state/state_registry.json")
        if registry_path.exists():
            with open(registry_path, 'r') as f:
                return json.load(f)
        return None
    
    @staticmethod
    def get_state_file(state_type: str) -> Optional[Path]:
        """Get state file path for a specific state type."""
        registry = StateLoader.load_state_registry()
        if registry and state_type in registry:
            return Path("state") / registry[state_type]["state_file"]
        return None
    
    @staticmethod
    def get_state_ids(state_type: str) -> Optional[Dict[str, str]]:
        """Get IDs for a specific state type."""
        registry = StateLoader.load_state_registry()
        if registry and state_type in registry:
            return registry[state_type]["ids"]
        return None