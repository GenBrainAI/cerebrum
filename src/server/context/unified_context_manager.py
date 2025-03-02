"""
Unified Context Manager for the Self-Aware Cerebrum system.

This module provides a central hub for context management across the system,
integrating the Adaptive Context Manager, Terminal Command Executor, and
Codebase Vector Store into a cohesive context management system.
"""

import os
import json
import logging
import asyncio
from pathlib import Path
from typing import Dict, List, Any, Optional, Union, Tuple
from datetime import datetime

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
from src.server.context.chroma_vector_store import (
    ChromaVectorStore,
    VectorStoreConfig
)

logger = logging.getLogger(__name__)

class UnifiedContextManager:
    """
    Central hub for context management across the Self-Aware Cerebrum system.
    
    Integrates multiple specialized context providers:
    - Adaptive Context Manager: For general context storage and retrieval
    - Terminal Command Executor: For executing and tracking terminal commands
    - Codebase Vector Store: For semantic search of the codebase
    
    This class provides a unified interface for all context operations,
    ensuring consistent context management across the system.
    """
    
    def __init__(
        self,
        base_path: str = "persistent_state",
        codebase_root: str = ".",
        context_config: Optional[ContextConfig] = None,
        security_config: Optional[SecurityConfig] = None,
        vector_store_config: Optional[VectorStoreConfig] = None
    ):
        """
        Initialize the Unified Context Manager.
        
        Args:
            base_path: Base path for persistent state
            codebase_root: Root directory of the codebase
            context_config: Configuration for the context manager
            security_config: Configuration for the terminal command executor
            vector_store_config: Configuration for the vector store
        """
        self.base_path = Path(base_path)
        self.codebase_root = Path(codebase_root)
        
        # Create base directories
        self.base_path.mkdir(exist_ok=True, parents=True)
        
        # Initialize context manager
        self.context_manager = AdaptiveContextManager(
            base_path=self.base_path / "context_manager",
            config=context_config
        )
        
        # Initialize terminal command executor
        self.command_executor = TerminalCommandExecutor(
            base_path=self.base_path / "command_executor",
            security_config=security_config
        )
        
        # Initialize vector store with ChromaDB
        self.vector_store_dir = self.base_path / "vector_store"
        self.vector_store_dir.mkdir(exist_ok=True)
        
        self.vector_store = ChromaVectorStore(
            config=VectorStoreConfig(
                persist_directory=str(self.vector_store_dir),
                collection_name="unified_context",
                embedding_model="text-embedding-3-small"
            ),
            base_path=str(self.vector_store_dir)
        )
        
        # Dictionary to store operation metadata
        self.operations = {}
        
        logger.info(f"Unified Context Manager initialized with base path: {self.base_path}")
    
    async def initialize_codebase_index(self, incremental: bool = True) -> Dict[str, Any]:
        """Initialize or update the codebase vector store."""
        logger.info(f"Initializing codebase index (incremental={incremental})")
        
        result = await self.vector_store.index_directory(
            directory=self.codebase_root,
            incremental=incremental,
            collection_name="codebase",
            file_types=[".py", ".md", ".txt", ".json", ".yaml", ".yml"]
        )
        
        return result
    
    async def create_operation(
        self,
        operation_id: str,
        description: str,
        operation_type: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Create a new operation with its own context.
        
        Args:
            operation_id: Unique identifier for the operation
            description: Human-readable description of the operation
            operation_type: Type of operation (e.g., "research", "development")
            metadata: Additional metadata for the operation
            
        Returns:
            str: The operation ID
        """
        # Create context for the operation
        await self.context_manager.create_context(operation_id)
        
        # Store operation metadata
        self.operations[operation_id] = {
            "id": operation_id,
            "description": description,
            "type": operation_type,
            "created_at": datetime.now().isoformat(),
            "last_active": datetime.now().isoformat(),
            "metadata": metadata or {}
        }
        
        # Save operation metadata to disk
        await self._save_operation_metadata(operation_id)
        
        logger.info(f"Created new operation: {operation_id} ({operation_type})")
        return operation_id
    
    async def add_to_operation_context(
        self,
        operation_id: str,
        content: Union[str, ContextItem],
        source: Optional[str] = None,
        priority: int = 50,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Add content to an operation's context.
        
        Args:
            operation_id: The operation ID
            content: The content to add (string or ContextItem)
            source: Source identifier (required if content is a string)
            priority: Item priority (0-100)
            metadata: Additional metadata
            
        Returns:
            str: The context item ID
        """
        # Update operation last active timestamp
        if operation_id in self.operations:
            self.operations[operation_id]["last_active"] = datetime.now().isoformat()
            await self._save_operation_metadata(operation_id)
        
        # Add to adaptive context
        return await self.context_manager.add_to_context(
            operation_id,
            content,
            source=source,
            priority=priority,
            metadata=metadata
        )
    
    async def get_operation_context(
        self,
        operation_id: str,
        max_tokens: Optional[int] = None,
        include_metadata: bool = False
    ) -> Union[str, Dict[str, Any]]:
        """
        Get the context for an operation.
        
        Args:
            operation_id: The operation ID
            max_tokens: Maximum tokens to return
            include_metadata: Whether to include metadata
            
        Returns:
            Union[str, Dict[str, Any]]: The context as a string or with metadata
        """
        # Update operation last active timestamp
        if operation_id in self.operations:
            self.operations[operation_id]["last_active"] = datetime.now().isoformat()
            await self._save_operation_metadata(operation_id)
        
        # Get from adaptive context
        return await self.context_manager.get_context(
            operation_id,
            max_tokens=max_tokens,
            include_metadata=include_metadata
        )
    
    async def execute_command(
        self,
        operation_id: str,
        command: str,
        working_directory: Optional[str] = None,
        environment_vars: Optional[Dict[str, str]] = None,
        timeout: Optional[int] = None,
        requires_approval: bool = True,
        add_to_context: bool = True,
        context_priority: int = 50
    ) -> Union[CommandExecutionResult, str]:
        """
        Execute a terminal command and optionally add the result to the operation context.
        
        Args:
            operation_id: The operation ID
            command: The command to execute
            working_directory: The working directory for the command
            environment_vars: Environment variables for the command
            timeout: Timeout in seconds
            requires_approval: Whether the command requires approval
            add_to_context: Whether to add the result to the operation context
            context_priority: Priority for the context item (0-100)
            
        Returns:
            Union[CommandExecutionResult, str]: The execution result or approval ID
        """
        # Update operation last active timestamp
        if operation_id in self.operations:
            self.operations[operation_id]["last_active"] = datetime.now().isoformat()
            await self._save_operation_metadata(operation_id)
        
        # Execute command
        result = await self.command_executor.execute_command(
            command,
            working_directory=working_directory,
            environment_vars=environment_vars,
            timeout=timeout,
            requires_approval=requires_approval
        )
        
        # If result is an approval ID, return it
        if isinstance(result, str):
            return result
        
        # Add result to context if requested
        if add_to_context:
            # Format command result as text
            context_content = f"""
Command: {result.command}
Working Directory: {result.working_directory}
Exit Code: {result.exit_code}
Execution Time: {result.execution_time:.2f}s

STDOUT:
{result.stdout}

STDERR:
{result.stderr}
"""
            
            # Add to context
            await self.add_to_operation_context(
                operation_id,
                context_content,
                source="terminal_command",
                priority=context_priority,
                metadata={
                    "command_id": result.command_id,
                    "exit_code": result.exit_code,
                    "execution_time": result.execution_time,
                    "command": result.command
                }
            )
        
        return result
    
    async def execute_approved_command(
        self,
        operation_id: str,
        approval_id: str,
        add_to_context: bool = True,
        context_priority: int = 50
    ) -> CommandExecutionResult:
        """
        Execute a previously approved command.
        
        Args:
            operation_id: The operation ID
            approval_id: The approval ID
            add_to_context: Whether to add the result to the operation context
            context_priority: Priority for the context item (0-100)
            
        Returns:
            CommandExecutionResult: The execution result
        """
        # Update operation last active timestamp
        if operation_id in self.operations:
            self.operations[operation_id]["last_active"] = datetime.now().isoformat()
            await self._save_operation_metadata(operation_id)
        
        # Execute approved command
        result = await self.command_executor.execute_approved_command(approval_id)
        
        # Add result to context if requested
        if add_to_context:
            # Format command result as text
            context_content = f"""
Command: {result.command}
Working Directory: {result.working_directory}
Exit Code: {result.exit_code}
Execution Time: {result.execution_time:.2f}s

STDOUT:
{result.stdout}

STDERR:
{result.stderr}
"""
            
            # Add to context
            await self.add_to_operation_context(
                operation_id,
                context_content,
                source="terminal_command",
                priority=context_priority,
                metadata={
                    "command_id": result.command_id,
                    "exit_code": result.exit_code,
                    "execution_time": result.execution_time,
                    "command": result.command
                }
            )
        
        return result
    
    async def search_codebase(
        self,
        operation_id: str,
        query: str,
        top_k: int = 5,
        add_to_context: bool = True,
        context_priority: int = 60
    ) -> List[Dict[str, Any]]:
        """Search the codebase using semantic search."""
        logger.info(f"Searching codebase for: {query}")
        
        results = await self.vector_store.search(
            query=query,
            collection_name="codebase",
            limit=top_k
        )
        
        if add_to_context and results:
            # Format the results for context
            context_content = f"Codebase search results for query: {query}\n\n"
            for i, result in enumerate(results):
                context_content += f"Result {i+1}:\n"
                context_content += f"File: {result.get('metadata', {}).get('file_path', 'Unknown')}\n"
                context_content += f"Content:\n{result.get('content', '')}\n\n"
            
            # Add to operation context
            await self.add_to_operation_context(
                operation_id=operation_id,
                content=context_content,
                source="codebase_search",
                priority=context_priority,
                metadata={
                    "query": query,
                    "result_count": len(results)
                }
            )
        
        return results
    
    async def get_file_content(
        self,
        operation_id: str,
        file_path: str,
        add_to_context: bool = True,
        context_priority: int = 55
    ) -> Optional[str]:
        """
        Get the content of a file from the codebase.
        
        Args:
            operation_id: The operation ID
            file_path: The path to the file
            add_to_context: Whether to add the file content to the operation context
            context_priority: Priority for the context item (0-100)
            
        Returns:
            Optional[str]: The file content, or None if not found
        """
        # Update operation last active timestamp
        if operation_id in self.operations:
            self.operations[operation_id]["last_active"] = datetime.now().isoformat()
            await self._save_operation_metadata(operation_id)
        
        # Get file content
        content = self.vector_store.get_file_content(file_path)
        
        # Add to context if requested and found
        if add_to_context and content:
            # Determine language from file extension
            _, ext = os.path.splitext(file_path)
            # Get language from extension directly
            language = ext.lstrip('.').lower() or 'text'
            
            # Format file content as text
            context_content = f"File: {file_path}\n\n```{language}\n{content}\n```"
            
            # Add to context
            await self.add_to_operation_context(
                operation_id,
                context_content,
                source="file_content",
                priority=context_priority,
                metadata={
                    "file_path": file_path,
                    "language": language,
                    "size": len(content)
                }
            )
        
        return content
    
    async def list_operations(self) -> List[Dict[str, Any]]:
        """
        List all operations.
        
        Returns:
            List[Dict[str, Any]]: List of operation metadata
        """
        operations = []
        
        # Get all operation metadata files
        metadata_dir = self.base_path / "operations"
        if metadata_dir.exists():
            for path in metadata_dir.glob("*.json"):
                try:
                    with open(path, 'r') as f:
                        metadata = json.load(f)
                        operations.append(metadata)
                except Exception as e:
                    logger.error(f"Error loading operation metadata from {path}: {str(e)}")
        
        # Add active operations that might not be saved yet
        for operation_id, metadata in self.operations.items():
            if not any(op["id"] == operation_id for op in operations):
                operations.append(metadata)
        
        return operations
    
    async def get_operation_metadata(self, operation_id: str) -> Optional[Dict[str, Any]]:
        """
        Get metadata for an operation.
        
        Args:
            operation_id: The operation ID
            
        Returns:
            Optional[Dict[str, Any]]: The operation metadata, or None if not found
        """
        # Check active operations first
        if operation_id in self.operations:
            return self.operations[operation_id]
        
        # Check saved operations
        metadata_path = self.base_path / "operations" / f"{operation_id}.json"
        if metadata_path.exists():
            try:
                with open(metadata_path, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error loading operation metadata for {operation_id}: {str(e)}")
        
        return None
    
    async def delete_operation(self, operation_id: str) -> bool:
        """
        Delete an operation and all its associated data.
        
        Args:
            operation_id: The operation ID
            
        Returns:
            bool: True if successful
        """
        success = True
        
        # Delete context
        context_success = await self.context_manager.delete_context(operation_id)
        if not context_success:
            logger.warning(f"Failed to delete context for operation {operation_id}")
            success = False
        
        # Remove from active operations
        if operation_id in self.operations:
            del self.operations[operation_id]
        
        # Delete metadata file
        metadata_path = self.base_path / "operations" / f"{operation_id}.json"
        if metadata_path.exists():
            try:
                metadata_path.unlink()
            except Exception as e:
                logger.error(f"Error deleting operation metadata for {operation_id}: {str(e)}")
                success = False
        
        logger.info(f"Deleted operation: {operation_id}")
        return success
    
    async def _save_operation_metadata(self, operation_id: str) -> None:
        """
        Save operation metadata to disk.
        
        Args:
            operation_id: The operation ID
        """
        if operation_id not in self.operations:
            return
        
        # Create operations directory if it doesn't exist
        operations_dir = self.base_path / "operations"
        operations_dir.mkdir(exist_ok=True)
        
        # Save metadata
        metadata_path = operations_dir / f"{operation_id}.json"
        with open(metadata_path, 'w') as f:
            json.dump(self.operations[operation_id], f, indent=2)
    
    async def get_pending_command_approvals(self) -> List[Dict[str, Any]]:
        """
        Get all pending command approvals.
        
        Returns:
            List[Dict[str, Any]]: List of pending approvals
        """
        return self.command_executor.get_pending_approvals()
    
    async def reject_command(self, approval_id: str) -> bool:
        """
        Reject a pending command.
        
        Args:
            approval_id: The approval ID
            
        Returns:
            bool: True if successful
        """
        return self.command_executor.reject_command(approval_id)
    
    async def get_command_execution_history(
        self,
        limit: Optional[int] = None,
        filter_successful: Optional[bool] = None
    ) -> List[CommandExecutionResult]:
        """
        Get command execution history.
        
        Args:
            limit: Maximum number of results to return
            filter_successful: Filter by success status
            
        Returns:
            List[CommandExecutionResult]: List of execution results
        """
        return self.command_executor.get_execution_history(
            limit=limit,
            filter_successful=filter_successful
        )
    
    async def get_codebase_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the codebase vector store.
        
        Returns:
            Dict[str, Any]: Statistics about the vector store
        """
        return self.vector_store.get_stats()
    
    async def refresh_codebase(self) -> Dict[str, Any]:
        """
        Refresh the codebase vector store with the latest changes.
        
        Returns:
            Dict[str, Any]: Statistics about the refresh operation
        """
        return await self.vector_store.refresh()
        
    async def add_context_to_task(
        self,
        task_id: str,
        content: str,
        context_type: str = "system",
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Add context to a task.
        
        This is a compatibility method for the old UnifiedContextManager interface.
        It adds the content to a context named after the task ID.
        
        Args:
            task_id: The task ID
            content: The content to add
            context_type: The type of context (system, user, etc.)
            metadata: Additional metadata
            
        Returns:
            str: The context item ID
        """
        # Create context if it doesn't exist
        try:
            await self.context_manager.create_context(task_id)
        except ValueError:
            # Context already exists
            pass
            
        # Add to context
        return await self.context_manager.add_to_context(
            task_id,
            content,
            source=context_type,
            priority=metadata.get("priority", 50) if metadata else 50,
            metadata=metadata
        ) 