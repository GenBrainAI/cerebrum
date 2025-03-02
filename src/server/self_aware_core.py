"""
Cerebrum System Core for the Cerebrum framework.

This module provides the core integration point for Cerebrum's system components,
bringing together context management, system access, and codebase understanding
into a cohesive system that enables advanced capabilities.
"""

import os
import json
import logging
import asyncio
from pathlib import Path
from typing import Dict, List, Any, Optional, Union, Tuple
from datetime import datetime

from src.server.context.unified_context_manager import (
    UnifiedContextManager,
    ContextConfig
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

logger = logging.getLogger(__name__)

class CerebrumSystemCore:
    """
    Core integration point for Cerebrum system components.
    
    This class brings together the various components of the Cerebrum system,
    providing a unified interface for operations that require coordination
    between multiple components.
    
    Key capabilities:
    - Codebase understanding and navigation
    - System access and command execution
    - Context management and adaptation
    - Integrated system operations
    """
    
    def __init__(
        self,
        base_path: str = "persistent_state/cerebrum_system",
        codebase_root: str = ".",
        config: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize the Cerebrum System Core.
        
        Args:
            base_path: Base path for persistent storage
            codebase_root: Root directory of the codebase
            config: Configuration dictionary with settings for all components
        """
        self.base_path = base_path
        self.codebase_root = codebase_root
        self.config = config or {}
        
        # Ensure base path exists
        os.makedirs(base_path, exist_ok=True)
        
        # Extract component configs
        context_config = ContextConfig(**self.config.get("context", {}))
        security_config = SecurityConfig(**self.config.get("security", {}))
        
        vector_store_config = VectorStoreConfig(
            root_dir=codebase_root,
            store_dir=os.path.join(base_path, "vector_store"),
            **self.config.get("vector_store", {})
        )
        
        # Initialize the unified context manager
        self.context_manager = UnifiedContextManager(
            base_path=base_path,
            codebase_root=codebase_root,
            context_config=context_config,
            security_config=security_config,
            vector_store_config=vector_store_config
        )
        
        # Operation ID for the system
        self.operation_id = "cerebrum_system"
        
        # Initialize the operation
        # Don't automatically create a task in the constructor to make testing easier
        self._initialized = False
    
    async def initialize(self):
        """Initialize the system operation if not already initialized."""
        if not self._initialized:
            await self._initialize_operation()
            self._initialized = True
        return self._initialized
    
    async def _initialize_operation(self):
        """Initialize the system operation."""
        try:
            # Check if operation exists
            operations = await self.context_manager.list_operations()
            operation_exists = any(op.get("id") == self.operation_id for op in operations)
            
            if not operation_exists:
                # Create the operation
                await self.context_manager.create_operation(
                    operation_id=self.operation_id,
                    description="Cerebrum System Core",
                    operation_type="system",
                    metadata={
                        "created_at": datetime.now().isoformat(),
                        "system_type": "cerebrum_system",
                        "version": "1.0.0"
                    }
                )
                
                # Add initial context
                await self.context_manager.add_to_operation_context(
                    operation_id=self.operation_id,
                    content="Cerebrum System Core initialized.",
                    source="system",
                    priority=90,
                    metadata={
                        "type": "initialization",
                        "timestamp": datetime.now().isoformat()
                    }
                )
            
            # Initialize codebase index
            await self.context_manager.initialize_codebase_index(incremental=True)
            
        except Exception as e:
            logger.error(f"Error initializing system operation: {str(e)}")
    
    async def index_codebase(self, incremental: bool = True) -> Dict[str, Any]:
        """
        Index the codebase for semantic search.
        
        Args:
            incremental: Whether to perform an incremental update
            
        Returns:
            Dictionary with indexing statistics
        """
        return await self.context_manager.initialize_codebase_index(incremental=incremental)
    
    async def execute_command(
        self,
        command: str,
        working_directory: Optional[str] = None,
        environment_vars: Optional[Dict[str, str]] = None,
        timeout: Optional[int] = None,
        requires_approval: bool = True
    ) -> Union[CommandExecutionResult, str]:
        """
        Execute a terminal command.
        
        Args:
            command: The command to execute
            working_directory: Directory to execute the command in
            environment_vars: Environment variables for the command
            timeout: Timeout in seconds
            requires_approval: Whether the command requires approval
            
        Returns:
            Command execution result or approval ID
        """
        return await self.context_manager.execute_command(
            operation_id=self.operation_id,
            command=command,
            working_directory=working_directory,
            environment_vars=environment_vars,
            timeout=timeout,
            requires_approval=requires_approval,
            add_to_context=True,
            context_priority=60
        )
    
    async def search_code(
        self,
        query: str,
        top_k: int = 5
    ) -> List[CodeSnippet]:
        """
        Search the codebase for relevant code snippets.
        
        Args:
            query: The search query
            top_k: Number of results to return
            
        Returns:
            List of code snippets
        """
        return await self.context_manager.search_codebase(
            operation_id=self.operation_id,
            query=query,
            top_k=top_k,
            add_to_context=True,
            context_priority=70
        )
    
    async def get_file_content(
        self,
        file_path: str
    ) -> Optional[str]:
        """
        Get the content of a file.
        
        Args:
            file_path: Path to the file, relative to codebase root
            
        Returns:
            File content or None if file not found
        """
        return await self.context_manager.get_file_content(
            operation_id=self.operation_id,
            file_path=file_path,
            add_to_context=True,
            context_priority=65
        )
    
    async def get_context(
        self,
        max_tokens: Optional[int] = None,
        include_metadata: bool = False
    ) -> Union[str, Dict[str, Any]]:
        """
        Get the current context of the system.
        
        Args:
            max_tokens: Maximum number of tokens to include
            include_metadata: Whether to include metadata
            
        Returns:
            Context string or dictionary with metadata
        """
        return await self.context_manager.get_operation_context(
            operation_id=self.operation_id,
            max_tokens=max_tokens,
            include_metadata=include_metadata
        )
    
    async def add_to_context(
        self,
        content: str,
        source: str = "system",
        priority: int = 50,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Add information to the system context.
        
        Args:
            content: The content to add
            source: Source of the content
            priority: Priority of the content (0-100)
            metadata: Additional metadata
            
        Returns:
            ID of the added context item
        """
        return await self.context_manager.add_to_operation_context(
            operation_id=self.operation_id,
            content=content,
            source=source,
            priority=priority,
            metadata=metadata or {}
        )
    
    async def get_pending_approvals(self) -> List[Dict[str, Any]]:
        """
        Get pending command approvals.
        
        Returns:
            List of pending approvals
        """
        return await self.context_manager.get_pending_command_approvals()
    
    async def execute_approved_command(
        self,
        approval_id: str
    ) -> CommandExecutionResult:
        """
        Execute a previously approved command.
        
        Args:
            approval_id: ID of the approved command
            
        Returns:
            Command execution result
        """
        return await self.context_manager.execute_approved_command(
            operation_id=self.operation_id,
            approval_id=approval_id,
            add_to_context=True,
            context_priority=60
        )
    
    async def reject_command(
        self,
        approval_id: str
    ) -> bool:
        """
        Reject a pending command.
        
        Args:
            approval_id: ID of the command to reject
            
        Returns:
            True if successfully rejected
        """
        return await self.context_manager.reject_command(approval_id)
    
    async def get_codebase_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the indexed codebase.
        
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
        return await self.context_manager.refresh_codebase() 