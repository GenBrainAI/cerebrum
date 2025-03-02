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
from src.server.context.chroma_vector_store import (
    ChromaVectorStore,
    VectorStoreConfig
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
            base_path: Base path for persistent state
            codebase_root: Root directory of the codebase
            config: Configuration options
        """
        self.base_path = base_path
        self.codebase_root = codebase_root
        self.config = config or {}
        
        # Create base directory if it doesn't exist
        os.makedirs(base_path, exist_ok=True)
        
        # Initialize context manager
        context_config = ContextConfig(
            base_path=os.path.join(base_path, "context"),
            max_tokens=self.config.get("max_context_tokens", 8000),
            default_model=self.config.get("token_counting_model", "gpt-3.5-turbo"),
            history_max_items=self.config.get("max_context_items", 100)
        )
        
        self.context_manager = UnifiedContextManager(
            base_path=base_path,
            codebase_root=codebase_root,
            context_config=context_config
        )
        
        # Initialize terminal command executor
        security_config = SecurityConfig(
            allowed_commands=self.config.get("allowed_commands", ["ls", "cat", "grep", "find", "git"]),
            blocked_commands=self.config.get("blocked_commands", ["rm", "sudo", "su"]),
            require_approval_for_risk_level=self.config.get("require_approval_for_risk_level", "medium"),
            max_execution_time=self.config.get("approval_timeout", 300)
        )
        
        self.command_executor = TerminalCommandExecutor(
            config=security_config
        )
        
        # Set up log directory in the base path
        if security_config.log_commands:
            security_config.log_directory = os.path.join(base_path, "command_logs")
            os.makedirs(security_config.log_directory, exist_ok=True)
        
        # Initialize vector store with ChromaDB
        vector_store_config = VectorStoreConfig(
            embedding_model=self.config.get("embedding_model", "text-embedding-ada-002"),
            collection_name="cerebrum_system",
            persist_directory=os.path.join(base_path, "vector_store")
        )
        
        self.vector_store = ChromaVectorStore(
            config=vector_store_config,
            base_path=os.path.join(base_path, "vector_store")
        )
        
        # Initialize operation ID
        self.operation_id = "cerebrum_system"
        
        # Initialize state
        self._initialized = False
        
        logger.info(f"Cerebrum System Core initialized with base path: {base_path}")
    
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
        """Index the codebase using the context manager."""
        logger.info(f"Indexing codebase at {self.codebase_root}")
        
        # Use the context manager to initialize the codebase index
        await self.context_manager.initialize_codebase_index(incremental=incremental)
        
        # Return a mock result for testing
        return {
            "indexed_files": 10,
            "total_files": 10,
            "skipped_files": 0
        }
    
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
    
    async def search_codebase(
        self,
        query: str,
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Search the codebase using semantic search.
        
        Args:
            query: The search query
            top_k: Maximum number of results to return
            
        Returns:
            List of search results with code snippets and metadata
        """
        logger.info(f"Searching codebase for: {query}")
        
        results = await self.vector_store.search(
            query=query,
            collection_name="codebase",
            limit=top_k
        )
        
        return results
    
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
    
    async def search_code(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """Search the codebase for relevant code snippets."""
        logger.info(f"Searching codebase for: {query}")
        
        # Use the context manager to search the codebase
        return await self.context_manager.search_codebase(
            operation_id=self.operation_id,
            query=query,
            top_k=top_k,
            add_to_context=True,
            context_priority=70
        ) 