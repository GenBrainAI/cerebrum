# src/state_setup/initialize_states.py
import sys
from pathlib import Path
import asyncio
import os
import json

project_root = str(Path(__file__).parents[2])  # Go up one more level to reach project root
sys.path.append(project_root)

# from src.state_setup.tasks import setup_tasks_state
from src.state_setup.tools import setup_tools_state
from src.state_setup.agentic import setup_agentic_state
from src.server.models.persistence_models import StorageLocation, StorageType

async def initialize_all_states():
    """Initialize all states for the application."""
    
    # Create state directories
    state_root = Path("state")
    views_state = state_root / "views"
    specialized_state = state_root / "specialized"
    
    # Ensure directories exist
    for dir_path in [state_root, views_state, specialized_state]:
        dir_path.mkdir(parents=True, exist_ok=True)
    
    # Initialize states
    try:
        # print("Initializing task management state...")
        # task_ids = await setup_tasks_state()
        
        print("Initializing tools management state...")
        tool_ids = await setup_tools_state()
        
        print("Initializing agentic framework state...")
        agentic_ids = await setup_agentic_state()
        
        # Create state registry
        state_registry = {
            "task_management": {
                "state_file": "specialized/task_management_state.json",
                "ids": task_ids
            },
            "tools_management": {
                "state_file": "specialized/tools_management_state.json",
                "ids": tool_ids
            },
            "agentic_framework": {
                "state_file": "specialized/agentic_framework_state.json",
                "ids": agentic_ids
            }
        }
        
        # Save state registry
        registry_location = StorageLocation(
            type=StorageType.file,
            location=str(state_root / "specialized"),
            state_name="state_registry.json"
        )
        
        # Write registry directly to file
        registry_path = Path(registry_location.location) / registry_location.state_name
        with open(registry_path, 'w', encoding='utf-8') as f:
            json.dump(state_registry, f, indent=2)
        print("State registry saved successfully")
        
        return state_registry
        
    except Exception as e:
        print(f"Error initializing states: {str(e)}")
        raise

def get_state_paths():
    """Get paths for state files."""
    return {
        "root": Path("state"),
        "views": Path("state/views"),
        "specialized": Path("state/specialized"),
        "registry": Path("state/specialized/state_registry.json")
    }

if __name__ == "__main__":
    asyncio.run(initialize_all_states())