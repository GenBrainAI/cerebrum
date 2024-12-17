from typing import Optional
from pathlib import Path
from ..services.state_manager import StateManager

class StateManagerFactory:
    """Factory for creating StateManager instances."""
    
    _instance: Optional[StateManager] = None
    
    @classmethod
    def get_instance(cls, state_dir: Optional[Path] = None) -> StateManager:
        """Get or create StateManager singleton."""
        if cls._instance is None:
            cls._instance = StateManager(state_dir=state_dir or Path("state/specialized"))
        return cls._instance
    
    @classmethod
    def reset(cls) -> None:
        """Reset the singleton instance (mainly for testing)."""
        cls._instance = None
