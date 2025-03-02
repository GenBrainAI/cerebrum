#!/usr/bin/env python
"""
Initialization script for the Self-Aware Cerebrum system.

This script initializes all components of the Self-Aware Cerebrum system,
including the vector store, parameter manager, knowledge system, and more.
"""

import os
import sys
import asyncio
import argparse
import logging
from pathlib import Path

# Add the parent directory to the path so we can import our modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.server.self_aware_integration import SelfAwareSystem
from scripts.setup_vector_store import setup_vector_store

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('initialize_self_aware.log')
    ]
)

logger = logging.getLogger(__name__)

async def initialize_self_aware(
    codebase_root: str = ".",
    base_path: str = "persistent_state/self_aware",
    setup_vector: bool = True,
    incremental: bool = False
) -> SelfAwareSystem:
    """
    Initialize the Self-Aware Cerebrum system.
    
    Args:
        codebase_root: Path to the codebase root directory
        base_path: Path to the base directory for persistent state
        setup_vector: Whether to set up the vector store
        incremental: Whether to perform incremental indexing for the vector store
        
    Returns:
        SelfAwareSystem: The initialized self-aware system
    """
    logger.info(f"Initializing Self-Aware Cerebrum system")
    logger.info(f"Codebase root: {codebase_root}")
    logger.info(f"Base path: {base_path}")
    
    # Create base directory if it doesn't exist
    os.makedirs(base_path, exist_ok=True)
    
    # Set up vector store if requested
    if setup_vector:
        logger.info("Setting up vector store...")
        vector_result = await setup_vector_store(
            codebase_root=codebase_root,
            base_path=os.path.join(base_path, "vector_store"),
            incremental=incremental
        )
        logger.info(f"Vector store setup completed: {vector_result}")
    
    # Initialize the Self-Aware System
    logger.info("Initializing Self-Aware System...")
    system = SelfAwareSystem(storage_path=base_path)
    
    # Initialize the system
    await system.initialize()
    
    logger.info("Self-Aware Cerebrum system initialization completed successfully")
    return system

def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(description="Initialize the Self-Aware Cerebrum system")
    parser.add_argument(
        "--codebase-root",
        type=str,
        default=".",
        help="Path to the codebase root directory"
    )
    parser.add_argument(
        "--base-path",
        type=str,
        default="persistent_state/self_aware",
        help="Path to the base directory for persistent state"
    )
    parser.add_argument(
        "--skip-vector",
        action="store_true",
        help="Skip vector store setup"
    )
    parser.add_argument(
        "--incremental",
        action="store_true",
        help="Perform incremental indexing for the vector store"
    )
    
    args = parser.parse_args()
    
    # Run the initialization
    asyncio.run(initialize_self_aware(
        codebase_root=args.codebase_root,
        base_path=args.base_path,
        setup_vector=not args.skip_vector,
        incremental=args.incremental
    ))

if __name__ == "__main__":
    main() 