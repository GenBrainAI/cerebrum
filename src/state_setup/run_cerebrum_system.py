import logging
import sys
from pathlib import Path
import json

# Add project root to Python path
project_root = str(Path(__file__).parents[2])  # Go up two levels to reach project root
sys.path.append(project_root)

import asyncio
import os
from typing import Dict, Any, Optional

from src.server.persistence.in_memory_persistence import InMemoryPersistenceModel
from src.server.persistence.persistence_model_factory import PersistenceModelFactory
from src.state_setup.cerebrum_system import load_persistence_state, setup_cerebrum_system_state
from src.server.self_aware_core import CerebrumSystemCore

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

async def run_cerebrum_system(state_file: str = "state/specialized/cerebrum_system_state.json") -> None:
    """Run the Cerebrum System Core with the state setup."""
    # Create a new persistence model
    persistence_model = InMemoryPersistenceModel()
    
    # Check if state file exists
    if os.path.exists(state_file):
        # Load state from file
        load_persistence_state(persistence_model, state_file)
        logger.info(f"Loaded state from {state_file}")
    else:
        # Set up new state
        state_info = await setup_cerebrum_system_state(persistence_model, state_file)
        logger.info(f"Created new state with tasks manager ID: {state_info['tasks_manager_id']}")
    
    # Get the configuration from the file
    config_file = "config/cerebrum_system_config.json"
    if os.path.exists(config_file):
        with open(config_file, "r") as f:
            config = json.loads(f.read())
        logger.info(f"Loaded configuration from {config_file}")
    else:
        logger.error(f"Configuration file {config_file} not found")
        return
    
    # Initialize the Cerebrum System Core
    core = CerebrumSystemCore(
        base_path=config.get("base_path", "persistent_state/cerebrum_system"),
        codebase_root=config.get("codebase_root", "."),
        config=config
    )
    
    # Explicitly initialize the core
    logger.info("Initializing Cerebrum System Core...")
    await core.initialize()
    
    # Index the codebase
    logger.info("Indexing codebase...")
    stats = await core.index_codebase(incremental=True)
    logger.info(f"Indexed {stats.get('indexed_files', 0)} files")
    
    # Get codebase statistics
    logger.info("Getting codebase statistics...")
    stats = await core.get_codebase_stats()
    logger.info(f"Total Files: {stats.get('total_files', 0)}")
    logger.info(f"Total Lines: {stats.get('total_lines', 0)}")
    
    # Add information to the context
    logger.info("Adding information to the context...")
    await core.add_to_context(
        content="Cerebrum System Core initialized and ready for use.",
        source="system",
        priority=90,
        metadata={
            "type": "initialization",
            "timestamp": asyncio.get_event_loop().time()
        }
    )
    
    # Get the context
    logger.info("Getting context...")
    context = await core.get_context(max_tokens=1000)
    logger.info(f"Context length: {len(context)}")
    
    logger.info("Cerebrum System Core is ready for use")
    
    # Return the core for further use
    return core

async def main():
    """Main entry point for running the Cerebrum System Core."""
    await run_cerebrum_system()

if __name__ == "__main__":
    asyncio.run(main()) 