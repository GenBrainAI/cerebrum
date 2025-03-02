#!/usr/bin/env python
"""
Setup script for initializing the vector store.

This script initializes the vector store by indexing the codebase.
Run this script after cloning the repository to set up the vector store.
"""

import os
import sys
import asyncio
import argparse
import logging
from pathlib import Path

# Add the parent directory to the path so we can import our modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.server.cerebrum_system_core import CerebrumSystemCore

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('setup_vector_store.log')
    ]
)

logger = logging.getLogger(__name__)

async def setup_vector_store(
    codebase_root: str = ".",
    base_path: str = "persistent_state/cerebrum_system",
    incremental: bool = False
) -> None:
    """
    Set up the vector store by indexing the codebase.
    
    Args:
        codebase_root: Path to the codebase root directory
        base_path: Path to the base directory for persistent state
        incremental: Whether to perform incremental indexing
    """
    logger.info(f"Setting up vector store for codebase at {codebase_root}")
    
    # Initialize the core
    core = CerebrumSystemCore(
        base_path=base_path,
        codebase_root=codebase_root
    )
    
    # Index the codebase
    logger.info("Indexing the codebase...")
    result = await core.index_codebase(incremental=incremental)
    
    # Log the results
    logger.info(f"Indexing completed:")
    logger.info(f"  Total files: {result.get('total_files', 0)}")
    logger.info(f"  Indexed files: {result.get('indexed_files', 0)}")
    logger.info(f"  Skipped files: {result.get('skipped_files', 0)}")
    logger.info(f"  Unchanged files: {result.get('unchanged_files', 0)}")
    logger.info(f"  Errors: {result.get('errors', 0)}")
    logger.info(f"  Time taken: {result.get('time_taken', 0):.2f} seconds")
    
    # Get codebase stats
    stats = await core.get_codebase_stats()
    logger.info(f"Codebase statistics:")
    logger.info(f"  Total files: {stats.get('total_files', 0)}")
    logger.info(f"  Total lines: {stats.get('total_lines', 0)}")
    logger.info(f"  Total size: {stats.get('total_size', 0) / (1024 * 1024):.2f} MB")
    logger.info(f"  Languages: {', '.join(stats.get('languages', []))}")

def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(description="Set up the vector store by indexing the codebase")
    parser.add_argument(
        "--codebase-root",
        type=str,
        default=".",
        help="Path to the codebase root directory"
    )
    parser.add_argument(
        "--base-path",
        type=str,
        default="persistent_state/cerebrum_system",
        help="Path to the base directory for persistent state"
    )
    parser.add_argument(
        "--incremental",
        action="store_true",
        help="Perform incremental indexing"
    )
    
    args = parser.parse_args()
    
    # Run the setup
    asyncio.run(setup_vector_store(
        codebase_root=args.codebase_root,
        base_path=args.base_path,
        incremental=args.incremental
    ))

if __name__ == "__main__":
    main() 