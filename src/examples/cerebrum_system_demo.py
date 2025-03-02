#!/usr/bin/env python3
"""
Cerebrum System Core Demo

This script demonstrates how to use the Cerebrum System Core to interact with
the Cerebrum framework's core capabilities, including codebase understanding,
command execution, and context management.
"""

import os
import sys
import asyncio
import logging
from pathlib import Path

# Add project root to Python path
project_root = str(Path(__file__).parents[2])  # Go up two levels to reach project root
sys.path.append(project_root)

from src.server.self_aware_core import CerebrumSystemCore

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def run_demo():
    """Run the Cerebrum System Core demo."""
    # Load configuration
    config_file = "config/cerebrum_system_config.json"
    if not os.path.exists(config_file):
        logger.error(f"Configuration file {config_file} not found")
        return
    
    # Initialize the Cerebrum System Core
    logger.info("Initializing Cerebrum System Core...")
    core = CerebrumSystemCore(
        base_path="persistent_state/cerebrum_system",
        codebase_root=".",
        config=None  # Will load from config file
    )
    
    # Initialize the core
    await core.initialize()
    
    # Example 1: Search the codebase
    logger.info("\n=== Example 1: Search the Codebase ===")
    search_query = "context management"
    logger.info(f"Searching for: {search_query}")
    results = await core.search_code(search_query)
    
    logger.info(f"Found {len(results)} results:")
    for i, result in enumerate(results):
        logger.info(f"Result {i+1}: {result.file_path} (lines {result.start_line}-{result.end_line})")
        logger.info(f"Snippet: {result.content[:100]}...")
    
    # Example 2: Execute a command
    logger.info("\n=== Example 2: Execute a Command ===")
    command = "ls -la"
    logger.info(f"Executing command: {command}")
    result = await core.execute_command(command, requires_approval=False)
    
    if isinstance(result, str):
        logger.info(f"Command submitted for approval. Approval ID: {result}")
    else:
        logger.info(f"Command output: {result.stdout[:500]}...")
    
    # Example 3: Add to context
    logger.info("\n=== Example 3: Add to Context ===")
    content = "This is an important piece of information that should be remembered."
    logger.info(f"Adding to context: {content}")
    context_id = await core.add_to_context(
        content=content,
        source="demo",
        priority=80,
        metadata={"type": "demo", "importance": "high"}
    )
    logger.info(f"Added to context with ID: {context_id}")
    
    # Example 4: Get context
    logger.info("\n=== Example 4: Get Context ===")
    context = await core.get_context(max_tokens=1000)
    logger.info(f"Context length: {len(context)}")
    logger.info(f"Context preview: {context[:200]}...")
    
    # Example 5: Get file content
    logger.info("\n=== Example 5: Get File Content ===")
    file_path = "src/server/self_aware_core.py"
    logger.info(f"Getting content of file: {file_path}")
    content = await core.get_file_content(file_path)
    
    if content:
        logger.info(f"File content length: {len(content)}")
        logger.info(f"File content preview: {content[:200]}...")
    else:
        logger.info(f"File not found: {file_path}")
    
    # Example 6: Get codebase statistics
    logger.info("\n=== Example 6: Get Codebase Statistics ===")
    stats = await core.get_codebase_stats()
    logger.info(f"Total Files: {stats.get('total_files', 0)}")
    logger.info(f"Total Lines: {stats.get('total_lines', 0)}")
    logger.info(f"Languages: {', '.join(stats.get('languages', []))}")
    
    logger.info("\nDemo completed successfully!")

if __name__ == "__main__":
    asyncio.run(run_demo()) 