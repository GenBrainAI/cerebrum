"""
Self-Aware Core component.

This module provides the core functionality for the Self-Aware System, allowing it to understand
and interact with its codebase, manage resources, and execute tasks in a safe and controlled manner.
"""

import os
import json
import logging
import asyncio
from pathlib import Path
from typing import Dict, List, Any, Optional, Union
from datetime import datetime

from src.server.context.unified_context_manager import UnifiedContextManager
from src.server.system.terminal_command_executor import CommandExecutionResult

logger = logging.getLogger(__name__)

class CerebrumSystemCore:
    """Core component for the Cerebrum System."""
    
    def __init__(self, base_path: Optional[str] = None, codebase_root: Optional[str] = None, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the Cerebrum System Core.
        
        Args:
            base_path: Base path for persistent storage
            codebase_root: Root path of the codebase
            config: Optional configuration dictionary
        """
        self.base_path = base_path or os.path.join(os.path.expanduser("~"), ".cerebrum", "system")
        os.makedirs(self.base_path, exist_ok=True)
        
        self.codebase_root = codebase_root or os.getcwd()
        self.config = config or {}
        
        self.context_manager = UnifiedContextManager(
            data_dir=os.path.join(self.base_path, "context"),
            persistence_model=None
        )
        
        # Initialize state
        self.pending_approvals: Dict[str, Dict[str, Any]] = {}
        
        # Initialization flag
        self._initialized = False
        
    async def initialize(self) -> bool:
        """
        Initialize the core system.
        
        Returns:
            bool: True if initialization was successful
        """
        # Check if system is already initialized
        if self._initialized:
            return True
            
        # Get existing operations
        operations = await self.context_manager.list_operations()
        
        # Create system operation if it doesn't exist
        operation_id = "cerebrum_system"
        operation_exists = any(op.get("id") == operation_id for op in operations)
        
        if not operation_exists:
            await self.context_manager.create_operation(
                operation_id=operation_id,
                description="Cerebrum System Core",
                operation_type="system",
                metadata={
                    "created_at": datetime.now().isoformat(),
                    "system_type": "cerebrum_system",
                    "version": "1.0.0"
                }
            )
            
            # Add initialization message to context
            await self.context_manager.add_to_operation_context(
                operation_id=operation_id,
                content="Cerebrum System Core initialized.",
                source="system",
                priority=90,
                metadata={
                    "type": "initialization",
                    "timestamp": datetime.now().isoformat()
                }
            )
        
        # Index the codebase (incremental)
        await self.context_manager.initialize_codebase_index(incremental=True)
        
        # Set initialization flag
        self._initialized = True
        
        return True
    
    async def initialize_operation(self, operation_id: Optional[str] = None) -> str:
        """
        Initialize and return the current operation ID.
        
        Args:
            operation_id: Optional operation ID to use
            
        Returns:
            str: Current operation ID
        """
        return await self.context_manager.create_operation(operation_id)
    
    async def index_codebase(self, incremental: bool = False) -> Dict[str, Any]:
        """
        Index the codebase for search and context.
        
        Args:
            incremental: Whether to perform incremental indexing
            
        Returns:
            Dict with indexing statistics
        """
        return await self.context_manager.initialize_codebase_index(incremental=incremental)
    
    async def execute_command(self, command: str, working_directory: Optional[str] = None, 
                             timeout: int = 30, requires_approval: bool = True) -> Union[str, CommandExecutionResult]:
        """
        Execute a terminal command.
        
        Args:
            command: Command to execute
            working_directory: Directory to execute command in
            timeout: Command timeout in seconds
            requires_approval: Whether the command requires approval
            
        Returns:
            CommandExecutionResult if executed, or approval ID string if pending approval
        """
        if requires_approval:
            approval_id = f"cmd_{datetime.now().strftime('%Y%m%d%H%M%S')}"
            self.pending_approvals[approval_id] = {
                "command": command,
                "working_directory": working_directory,
                "timeout": timeout,
                "submitted_at": datetime.now().isoformat(),
                "risk_level": "medium"  # Default risk level
            }
            return approval_id
        
        return await self.context_manager.execute_command(
            operation_id="cerebrum_system",
            command=command,
            working_directory=working_directory or self.codebase_root,
            timeout=timeout,
            requires_approval=requires_approval,
            add_to_context=True,
            context_priority=60,
            environment_vars=None
        )
    
    async def execute_approved_command(self, approval_id: str) -> CommandExecutionResult:
        """
        Execute a previously approved command.
        
        Args:
            approval_id: ID of the approved command
            
        Returns:
            CommandExecutionResult object
        """
        if approval_id not in self.pending_approvals:
            return CommandExecutionResult(
                command_id=approval_id,
                command="",
                exit_code=1,
                stdout="",
                stderr=f"No pending command with ID {approval_id}",
                success=False,
                execution_time=0
            )
        
        approval = self.pending_approvals.pop(approval_id)
        return await self.context_manager.execute_command(
            operation_id="cerebrum_system",
            command=approval["command"],
            working_directory=approval.get("working_directory") or self.codebase_root,
            timeout=approval.get("timeout", 30),
            requires_approval=False,
            add_to_context=True,
            context_priority=60,
            environment_vars=None
        )
    
    async def reject_command(self, approval_id: str) -> bool:
        """
        Reject a pending command.
        
        Args:
            approval_id: ID of the command to reject
            
        Returns:
            bool: True if command was rejected, False if not found
        """
        if approval_id in self.pending_approvals:
            self.pending_approvals.pop(approval_id)
            return True
        return False
    
    async def get_pending_approvals(self) -> List[Dict[str, Any]]:
        """
        Get list of pending command approvals.
        
        Returns:
            List of approval dictionaries
        """
        return [
            {"id": approval_id, **approval_data}
            for approval_id, approval_data in self.pending_approvals.items()
        ]
    
    async def search_code(self, query: str, top_k: int = 5) -> List[Any]:
        """
        Search the codebase for relevant code snippets.
        
        Args:
            query: Search query
            top_k: Number of results to return
            
        Returns:
            List of search results
        """
        return await self.context_manager.search_codebase(
            operation_id="cerebrum_system",
            query=query,
            top_k=top_k,
            add_to_context=True,
            context_priority=70
        )
    
    async def get_file_content(self, file_path: str) -> Optional[str]:
        """
        Get the content of a file.
        
        Args:
            file_path: Path to the file
            
        Returns:
            File content as string, or None if file not found
        """
        return await self.context_manager.get_file_content(
            operation_id="cerebrum_system",
            file_path=file_path,
            add_to_context=True,
            context_priority=65
        )
    
    async def get_context(self, max_tokens: int = 1000, include_metadata: bool = False) -> Union[str, Dict[str, Any]]:
        """
        Get the current context for the operation.
        
        Args:
            max_tokens: Maximum number of tokens to include
            include_metadata: Whether to include metadata
            
        Returns:
            Context as string or dictionary with metadata
        """
        return await self.context_manager.get_operation_context(
            operation_id="cerebrum_system",
            max_tokens=max_tokens,
            include_metadata=include_metadata
        )
    
    async def add_to_context(self, content: str, source_type: str = "user_input", metadata: Optional[Dict[str, Any]] = None, priority: Optional[int] = None) -> bool:
        """
        Add content to the current context.
        
        Args:
            content: Content to add
            source_type: Type of content source
            metadata: Optional metadata for the content
            priority: Priority level for the context item
            
        Returns:
            bool: True if content was added successfully
        """
        return await self.context_manager.add_to_operation_context(
            operation_id="cerebrum_system",
            content=content,
            source=source_type,
            priority=priority,
            metadata=metadata or {}
        )
    
    async def get_codebase_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the codebase.
        
        Returns:
            Dictionary with codebase statistics
        """
        return await self.context_manager.get_codebase_stats()
    
    async def refresh_codebase(self) -> Dict[str, Any]:
        """
        Refresh the codebase index.
        
        Returns:
            Dictionary with refresh statistics
        """
        return await self.index_codebase(incremental=True) 