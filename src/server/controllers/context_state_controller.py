from pathlib import Path 
import json
import logging
from typing import Dict, Any, Optional
from datetime import datetime

from src.server.models.persistence_models import StorageLocation, StorageType

class ContextStateController:
    """Controller for managing context system state."""
    
    def __init__(self, base_path: str = "state"):
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)
        self.logger = logging.getLogger(__name__)

    def save_context_state(self, name: str, state_data: Dict[str, Any]) -> str:
        """
        Save context state to file.
        
        Args:
            name: Name for the state file
            state_data: Dictionary containing state data
            
        Returns:
            String message indicating success/failure
        """
        try:
            # Add metadata
            save_data = {
                "metadata": {
                    "saved_at": datetime.now().isoformat(),
                    "name": name,
                    "type": "context_state"
                },
                "state": state_data
            }

            # Ensure .json extension
            if not name.endswith('.json'):
                name = f"{name}.json"
                
            file_path = self.base_path / name
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(save_data, f, indent=2)
                
            return f"State saved successfully to {file_path}"
            
        except Exception as e:
            error_msg = f"Error saving context state: {str(e)}"
            self.logger.error(error_msg)
            raise ValueError(error_msg)

    def load_context_state(self, name: str) -> Dict[str, Any]:
        """
        Load context state from file.
        
        Args:
            name: Name of the state file to load
            
        Returns:
            Dictionary containing the loaded state
        """
        try:
            # Ensure .json extension
            if not name.endswith('.json'):
                name = f"{name}.json"
                
            file_path = self.base_path / name
            
            if not file_path.exists():
                raise FileNotFoundError(f"State file not found: {file_path}")
            
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            # Validate basic structure
            if 'metadata' not in data or 'state' not in data:
                raise ValueError("Invalid state file format")
                
            if data['metadata'].get('type') != 'context_state':
                raise ValueError("File is not a context state file")
                
            return data['state']
            
        except Exception as e:
            error_msg = f"Error loading context state: {str(e)}"
            self.logger.error(error_msg)
            raise ValueError(error_msg)

    def list_saved_states(self) -> Dict[str, Dict[str, Any]]:
        """
        List all saved context states with metadata.
        
        Returns:
            Dictionary mapping state names to their metadata
        """
        states = {}
        for file_path in self.base_path.glob("*.json"):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if 'metadata' in data and data['metadata'].get('type') == 'context_state':
                        states[file_path.stem] = data['metadata']
            except Exception as e:
                self.logger.warning(f"Error reading state file {file_path}: {str(e)}")
                continue
        return states

    def delete_state(self, name: str) -> bool:
        """
        Delete a saved state file.
        
        Args:
            name: Name of the state to delete
            
        Returns:
            True if deletion was successful
        """
        try:
            if not name.endswith('.json'):
                name = f"{name}.json"
                
            file_path = self.base_path / name
            if file_path.exists():
                file_path.unlink()
                return True
            return False
            
        except Exception as e:
            self.logger.error(f"Error deleting state file: {str(e)}")
            return False

# Create singleton instance
context_state_controller = ContextStateController()