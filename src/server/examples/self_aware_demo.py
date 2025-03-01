"""
Self-Aware Cerebrum Components Demonstration.

This script demonstrates the usage of the Self-Aware Cerebrum components:
- Adaptive Context Manager
- Terminal Command Executor
- Codebase Vector Store
- Unified Context Manager

It shows how these components can be used together to create a self-aware system
that can understand and modify its own codebase.
"""

import os
import sys
import asyncio
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional

# Add the project root to the Python path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent))

from src.server.context.adaptive_context_manager import (
    AdaptiveContextManager,
    ContextConfig,
    ContextItem
)
from src.server.system.terminal_command_executor import (
    TerminalCommandExecutor,
    SecurityConfig,
    CommandExecutionResult
)
from src.server.system.codebase_vector_store import (
    CodebaseVectorStore,
    VectorStoreConfig,
    CodeSnippet
)
from src.server.context.unified_context_manager import UnifiedContextManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def demonstrate_adaptive_context_manager():
    """Demonstrate the Adaptive Context Manager."""
    logger.info("=== Demonstrating Adaptive Context Manager ===")
    
    # Create a temporary directory for context storage
    temp_dir = Path("temp_context")
    temp_dir.mkdir(exist_ok=True)
    
    # Initialize context manager
    context_config = ContextConfig(
        base_path=str(temp_dir),
        default_model="gpt-4",
        max_tokens=8192
    )
    context_manager = AdaptiveContextManager(config=context_config)
    
    # Create a context
    operation_id = "demo_operation"
    await context_manager.create_context(operation_id)
    logger.info(f"Created context for operation: {operation_id}")
    
    # Add items to context
    item1_id = await context_manager.add_to_context(
        operation_id,
        "This is a high priority context item.",
        source="demo",
        priority=80,
        metadata={"type": "introduction"}
    )
    logger.info(f"Added high priority item: {item1_id}")
    
    item2_id = await context_manager.add_to_context(
        operation_id,
        "This is a medium priority context item with more details about the operation.",
        source="demo",
        priority=50,
        metadata={"type": "details"}
    )
    logger.info(f"Added medium priority item: {item2_id}")
    
    item3_id = await context_manager.add_to_context(
        operation_id,
        "This is a low priority context item that might be compressed if context gets too large.",
        source="demo",
        priority=20,
        metadata={"type": "background"}
    )
    logger.info(f"Added low priority item: {item3_id}")
    
    # Get context
    context = await context_manager.get_context(operation_id, include_metadata=True)
    logger.info(f"Retrieved context with {len(context['items'])} items")
    logger.info(f"Total tokens: {context['total_tokens']}")
    
    # Update an item
    await context_manager.update_context_item(
        operation_id,
        item2_id,
        content="This is an updated medium priority item with more relevant details.",
        priority=60
    )
    logger.info(f"Updated item: {item2_id}")
    
    # Get context again
    updated_context = await context_manager.get_context(operation_id, include_metadata=True)
    logger.info(f"Retrieved updated context with {updated_context['total_tokens']} tokens")
    
    # Get context stats
    stats = await context_manager.get_context_stats(operation_id)
    logger.info(f"Context stats: {stats}")
    
    # Clean up
    await context_manager.delete_context(operation_id)
    logger.info(f"Deleted context for operation: {operation_id}")

async def demonstrate_terminal_command_executor():
    """Demonstrate the Terminal Command Executor."""
    logger.info("=== Demonstrating Terminal Command Executor ===")
    
    # Create a temporary directory for command logs
    temp_dir = Path("temp_command_logs")
    temp_dir.mkdir(exist_ok=True)
    
    # Initialize command executor
    security_config = SecurityConfig(
        allowed_commands=["ls", "echo", "cat", "pwd"],
        blocked_commands=["rm", "sudo", "chmod"],
        log_directory=str(temp_dir),
        require_approval_for_risk_level="medium"
    )
    command_executor = TerminalCommandExecutor(config=security_config)
    
    # Execute a simple command
    logger.info("Executing a simple command...")
    result = await command_executor.execute_command(
        "echo 'Hello, Self-Aware Cerebrum!'",
        requires_approval=False
    )
    logger.info(f"Command result: {result.exit_code}")
    logger.info(f"Command output: {result.stdout.strip()}")
    
    # Execute a command with working directory
    logger.info("Executing a command with working directory...")
    result = await command_executor.execute_command(
        "pwd",
        working_directory="/tmp",
        requires_approval=False
    )
    logger.info(f"Working directory: {result.stdout.strip()}")
    
    # Execute a command with environment variables
    logger.info("Executing a command with environment variables...")
    result = await command_executor.execute_command(
        "echo $DEMO_VAR",
        environment_vars={"DEMO_VAR": "Self-Aware Value"},
        requires_approval=False
    )
    logger.info(f"Environment variable value: {result.stdout.strip()}")
    
    # Execute a command that requires approval
    logger.info("Executing a command that requires approval...")
    approval_id = await command_executor.execute_command(
        "echo 'Hello' | grep 'Hello'"  # Medium risk due to pipe
    )
    logger.info(f"Command requires approval: {approval_id}")
    
    # Get pending approvals
    approvals = command_executor.get_pending_approvals()
    logger.info(f"Pending approvals: {len(approvals)}")
    
    # Execute approved command
    logger.info("Executing approved command...")
    result = await command_executor.execute_approved_command(approval_id)
    logger.info(f"Approved command result: {result.exit_code}")
    logger.info(f"Approved command output: {result.stdout.strip()}")
    
    # Get execution history
    history = command_executor.get_execution_history()
    logger.info(f"Execution history: {len(history)} commands")
    
    # Clean up
    # Note: We're not removing the log directory as it contains useful logs

async def demonstrate_codebase_vector_store():
    """Demonstrate the Codebase Vector Store."""
    logger.info("=== Demonstrating Codebase Vector Store ===")
    
    # Create a temporary directory for the vector store
    temp_dir = Path("temp_vector_store")
    temp_dir.mkdir(exist_ok=True)
    
    # Get the project root directory
    project_root = Path(__file__).resolve().parent.parent.parent.parent
    
    # Initialize vector store
    vector_store_config = VectorStoreConfig(
        root_dir=str(project_root),
        store_dir=str(temp_dir),
        max_files=100  # Limit for demonstration
    )
    vector_store = CodebaseVectorStore(config=vector_store_config)
    
    # Index the codebase
    logger.info("Indexing the codebase...")
    stats = await vector_store.index_codebase(incremental=False)
    logger.info(f"Indexed {stats['indexed_files']} files")
    logger.info(f"Skipped {stats['skipped_files']} files")
    logger.info(f"Time taken: {stats['time_taken']:.2f} seconds")
    
    # Get codebase stats
    store_stats = vector_store.get_stats()
    logger.info(f"Total files in vector store: {store_stats['total_files']}")
    logger.info(f"Languages: {list(store_stats['languages'].keys())}")
    
    # Search the codebase
    logger.info("Searching for 'context manager'...")
    results = await vector_store.search("context manager")
    logger.info(f"Found {len(results)} results")
    
    # Display the first result
    if results:
        logger.info(f"Top result: {results[0].file_path}")
        logger.info(f"Relevance score: {results[0].relevance_score:.4f}")
        logger.info(f"Lines {results[0].start_line}-{results[0].end_line}")
        logger.info(f"Language: {results[0].language}")
        
        # Get full file content
        file_content = vector_store.get_file_content(results[0].file_path)
        if file_content:
            logger.info(f"File size: {len(file_content)} characters")
    
    # Clean up
    vector_store.clear()
    logger.info("Cleared vector store")

async def demonstrate_unified_context_manager():
    """Demonstrate the Unified Context Manager."""
    logger.info("=== Demonstrating Unified Context Manager ===")
    
    # Create a temporary directory for the unified context manager
    temp_dir = Path("temp_unified_context")
    temp_dir.mkdir(exist_ok=True)
    
    # Get the project root directory
    project_root = Path(__file__).resolve().parent.parent.parent.parent
    
    # Initialize unified context manager
    unified_manager = UnifiedContextManager(
        base_path=str(temp_dir),
        codebase_root=str(project_root)
    )
    
    # Initialize codebase index
    logger.info("Initializing codebase index...")
    stats = await unified_manager.initialize_codebase_index(incremental=False)
    logger.info(f"Indexed {stats['indexed_files']} files")
    
    # Create an operation
    operation_id = "demo_operation"
    logger.info(f"Creating operation: {operation_id}")
    await unified_manager.create_operation(
        operation_id=operation_id,
        description="Demonstration operation",
        operation_type="demo",
        metadata={"purpose": "demonstration"}
    )
    
    # Add content to operation context
    logger.info("Adding content to operation context...")
    await unified_manager.add_to_operation_context(
        operation_id=operation_id,
        content="This is a demonstration of the Unified Context Manager.",
        source="demo",
        priority=70
    )
    
    # Execute a command
    logger.info("Executing a command...")
    result = await unified_manager.execute_command(
        operation_id=operation_id,
        command="echo 'Hello from Unified Context Manager'",
        requires_approval=False
    )
    logger.info(f"Command output: {result.stdout.strip()}")
    
    # Search the codebase
    logger.info("Searching the codebase...")
    search_results = await unified_manager.search_codebase(
        operation_id=operation_id,
        query="unified context manager"
    )
    logger.info(f"Found {len(search_results)} results")
    
    # Get file content
    if search_results:
        logger.info(f"Getting content of file: {search_results[0].file_path}")
        file_content = await unified_manager.get_file_content(
            operation_id=operation_id,
            file_path=search_results[0].file_path
        )
        if file_content:
            logger.info(f"File size: {len(file_content)} characters")
    
    # Get operation context
    logger.info("Getting operation context...")
    context = await unified_manager.get_operation_context(
        operation_id=operation_id,
        include_metadata=True
    )
    logger.info(f"Context has {len(context['items'])} items")
    
    # List operations
    logger.info("Listing operations...")
    operations = await unified_manager.list_operations()
    logger.info(f"Found {len(operations)} operations")
    
    # Get command execution history
    logger.info("Getting command execution history...")
    history = await unified_manager.get_command_execution_history()
    logger.info(f"Command history has {len(history)} entries")
    
    # Get codebase stats
    logger.info("Getting codebase stats...")
    codebase_stats = await unified_manager.get_codebase_stats()
    logger.info(f"Codebase has {codebase_stats['total_files']} files")
    
    # Delete operation
    logger.info(f"Deleting operation: {operation_id}")
    await unified_manager.delete_operation(operation_id)
    
    # Clean up
    # Note: We're not removing the temp directory as it contains useful data

async def main():
    """Run all demonstrations."""
    logger.info("Starting Self-Aware Cerebrum Components Demonstration")
    
    try:
        await demonstrate_adaptive_context_manager()
        await demonstrate_terminal_command_executor()
        await demonstrate_codebase_vector_store()
        await demonstrate_unified_context_manager()
        
        logger.info("Demonstration completed successfully")
    except Exception as e:
        logger.error(f"Demonstration failed: {str(e)}", exc_info=True)
    finally:
        # Clean up temporary directories if needed
        # Note: We're keeping them for inspection
        pass

if __name__ == "__main__":
    asyncio.run(main()) 