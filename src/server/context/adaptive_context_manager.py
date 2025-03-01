"""
Adaptive Context Manager for the Self-Aware Cerebrum system.

This module provides a dynamic context management system that can adapt to different
AI engines and operational needs. It handles context storage, retrieval, compression,
and prioritization to optimize context usage across the system.
"""

import os
import json
import hashlib
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Union, Tuple
from dataclasses import dataclass, field
import tiktoken

logger = logging.getLogger(__name__)

@dataclass
class ContextItem:
    """Represents a single context item with content and metadata."""
    id: str
    content: str
    source: str
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    modified_at: str = field(default_factory=lambda: datetime.now().isoformat())
    token_count: int = 0
    priority: int = 50  # 0-100, higher is more important
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Initialize token count if not provided."""
        if self.token_count == 0:
            self.token_count = count_tokens(self.content)

@dataclass
class CompressionStrategy:
    """Defines a strategy for compressing context."""
    name: str
    description: str
    compression_fn: callable
    priority_threshold: int = 0  # Items with priority below this may be compressed
    token_threshold: int = 0  # Apply when context exceeds this token count
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class ContextConfig:
    """Configuration for the Adaptive Context Manager."""
    base_path: str = "persistent_state/context/adaptive"
    default_model: str = "gpt-4"
    max_tokens: int = 8192
    default_compression_strategy: str = "summarize"
    enable_history: bool = True
    history_max_items: int = 100
    metadata_schema: Dict[str, Any] = field(default_factory=dict)

def count_tokens(text: str, model: str = "gpt-4") -> int:
    """Count the number of tokens in a text string."""
    try:
        encoding = tiktoken.encoding_for_model(model)
        return len(encoding.encode(text))
    except Exception as e:
        logger.warning(f"Error counting tokens: {str(e)}. Using character-based estimate.")
        # Fallback to character-based estimate (rough approximation)
        return len(text) // 4

class AdaptiveContextManager:
    """
    Manages and optimizes context for various AI engines and operational needs.
    
    Dynamically adjusts context representation, compression, and prioritization
    based on the current task requirements and target AI engine capabilities.
    """
    
    def __init__(self, config: Optional[ContextConfig] = None):
        """Initialize the Adaptive Context Manager."""
        self.config = config or ContextConfig()
        self.base_path = Path(self.config.base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)
        
        # Initialize storage directories
        self.contexts_dir = self.base_path / "contexts"
        self.history_dir = self.base_path / "history"
        self.contexts_dir.mkdir(exist_ok=True)
        self.history_dir.mkdir(exist_ok=True)
        
        # Active contexts and compression strategies
        self.active_contexts: Dict[str, Dict[str, ContextItem]] = {}
        self.compression_strategies: Dict[str, CompressionStrategy] = {}
        
        # Register default compression strategies
        self._register_default_strategies()
        
        logger.info(f"Adaptive Context Manager initialized with base path: {self.base_path}")
    
    def _register_default_strategies(self) -> None:
        """Register default compression strategies."""
        # Simple truncation strategy
        self.register_compression_strategy(
            CompressionStrategy(
                name="truncate",
                description="Simple truncation of context items",
                compression_fn=self._truncate_compression,
                priority_threshold=30,
                token_threshold=self.config.max_tokens * 0.8
            )
        )
        
        # Summarization strategy
        self.register_compression_strategy(
            CompressionStrategy(
                name="summarize",
                description="Summarize context items",
                compression_fn=self._summarize_compression,
                priority_threshold=60,
                token_threshold=self.config.max_tokens * 0.9
            )
        )
    
    def register_compression_strategy(self, strategy: CompressionStrategy) -> None:
        """Register a new compression strategy."""
        self.compression_strategies[strategy.name] = strategy
        logger.info(f"Registered compression strategy: {strategy.name}")
    
    def _truncate_compression(self, context_item: ContextItem, max_tokens: int) -> ContextItem:
        """Simple truncation compression strategy."""
        if context_item.token_count <= max_tokens:
            return context_item
        
        encoding = tiktoken.encoding_for_model(self.config.default_model)
        tokens = encoding.encode(context_item.content)
        truncated_tokens = tokens[:max_tokens]
        truncated_content = encoding.decode(truncated_tokens)
        
        # Create new context item with truncated content
        compressed_item = ContextItem(
            id=context_item.id,
            content=truncated_content,
            source=context_item.source,
            created_at=context_item.created_at,
            modified_at=datetime.now().isoformat(),
            token_count=max_tokens,
            priority=context_item.priority,
            metadata={
                **context_item.metadata,
                "compression": {
                    "strategy": "truncate",
                    "original_tokens": context_item.token_count,
                    "compressed_tokens": max_tokens,
                    "compression_ratio": max_tokens / context_item.token_count
                }
            }
        )
        
        return compressed_item
    
    def _summarize_compression(self, context_item: ContextItem, max_tokens: int) -> ContextItem:
        """
        Summarization compression strategy.
        
        Note: This is a placeholder. In a real implementation, this would use an LLM
        to generate a summary of the content.
        """
        # For now, just truncate as a fallback
        # In a real implementation, this would call an LLM to summarize
        truncated = self._truncate_compression(context_item, max_tokens)
        
        # Update metadata to reflect summarization attempt
        truncated.metadata["compression"]["strategy"] = "summarize_fallback_to_truncate"
        
        return truncated
    
    async def create_context(
        self, 
        operation_id: str, 
        initial_content: Optional[List[ContextItem]] = None,
        engine_type: Optional[str] = None,
        max_tokens: Optional[int] = None
    ) -> str:
        """
        Create a new managed context for an operation.
        
        Args:
            operation_id: Unique identifier for the operation
            initial_content: Optional initial context items
            engine_type: Target AI engine type
            max_tokens: Maximum tokens for this context
            
        Returns:
            str: The operation ID
        """
        if operation_id in self.active_contexts:
            logger.warning(f"Context already exists for operation {operation_id}. Returning existing context.")
            return operation_id
        
        self.active_contexts[operation_id] = {}
        
        # Add initial content if provided
        if initial_content:
            for item in initial_content:
                await self.add_to_context(operation_id, item)
        
        # Save context metadata
        context_metadata = {
            "id": operation_id,
            "created_at": datetime.now().isoformat(),
            "last_modified": datetime.now().isoformat(),
            "engine_type": engine_type or self.config.default_model,
            "max_tokens": max_tokens or self.config.max_tokens,
            "item_count": len(self.active_contexts[operation_id]),
            "total_tokens": sum(item.token_count for item in self.active_contexts[operation_id].values())
        }
        
        # Save metadata to disk
        metadata_path = self.contexts_dir / f"{operation_id}_metadata.json"
        with open(metadata_path, 'w') as f:
            json.dump(context_metadata, f, indent=2)
        
        logger.info(f"Created new context for operation {operation_id}")
        return operation_id
    
    async def add_to_context(
        self, 
        operation_id: str, 
        context_item: Union[ContextItem, str],
        source: Optional[str] = None,
        priority: int = 50,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Add a context item to an operation's context.
        
        Args:
            operation_id: The operation ID
            context_item: Either a ContextItem object or a string content
            source: Source identifier (required if context_item is a string)
            priority: Item priority (0-100)
            metadata: Additional metadata
            
        Returns:
            str: The context item ID
        """
        # Create context if it doesn't exist
        if operation_id not in self.active_contexts:
            await self.create_context(operation_id)
        
        # Convert string to ContextItem if needed
        if isinstance(context_item, str):
            if not source:
                raise ValueError("Source must be provided when adding string content")
            
            item_id = hashlib.md5(f"{operation_id}:{source}:{context_item}".encode()).hexdigest()
            context_item = ContextItem(
                id=item_id,
                content=context_item,
                source=source,
                priority=priority,
                metadata=metadata or {}
            )
        
        # Add to active contexts
        self.active_contexts[operation_id][context_item.id] = context_item
        
        # Save context item to disk
        item_path = self.contexts_dir / f"{operation_id}_{context_item.id}.json"
        with open(item_path, 'w') as f:
            json.dump({
                "id": context_item.id,
                "content": context_item.content,
                "source": context_item.source,
                "created_at": context_item.created_at,
                "modified_at": context_item.modified_at,
                "token_count": context_item.token_count,
                "priority": context_item.priority,
                "metadata": context_item.metadata
            }, f, indent=2)
        
        # Update context metadata
        await self._update_context_metadata(operation_id)
        
        # Check if compression is needed
        await self._check_and_apply_compression(operation_id)
        
        logger.info(f"Added context item {context_item.id} to operation {operation_id}")
        return context_item.id
    
    async def get_context(
        self, 
        operation_id: str,
        max_tokens: Optional[int] = None,
        include_metadata: bool = False
    ) -> Union[str, Dict[str, Any]]:
        """
        Get the full context for an operation.
        
        Args:
            operation_id: The operation ID
            max_tokens: Maximum tokens to return
            include_metadata: Whether to include metadata
            
        Returns:
            Union[str, Dict[str, Any]]: The context as a string or with metadata
        """
        if operation_id not in self.active_contexts:
            # Try to load from disk
            if not await self._load_context_from_disk(operation_id):
                raise ValueError(f"Context not found for operation {operation_id}")
        
        # Sort context items by priority (highest first)
        sorted_items = sorted(
            self.active_contexts[operation_id].values(),
            key=lambda x: x.priority,
            reverse=True
        )
        
        # Apply token limit if specified
        if max_tokens:
            included_items = []
            current_tokens = 0
            
            for item in sorted_items:
                if current_tokens + item.token_count <= max_tokens:
                    included_items.append(item)
                    current_tokens += item.token_count
                else:
                    # If we can't include the full item, we're done
                    break
            
            sorted_items = included_items
        
        # Combine context items
        combined_content = "\n\n".join(item.content for item in sorted_items)
        
        if include_metadata:
            return {
                "content": combined_content,
                "items": [
                    {
                        "id": item.id,
                        "source": item.source,
                        "priority": item.priority,
                        "token_count": item.token_count,
                        "metadata": item.metadata
                    }
                    for item in sorted_items
                ],
                "total_tokens": sum(item.token_count for item in sorted_items),
                "item_count": len(sorted_items)
            }
        
        return combined_content
    
    async def get_context_item(
        self, 
        operation_id: str, 
        item_id: str
    ) -> Optional[ContextItem]:
        """
        Get a specific context item.
        
        Args:
            operation_id: The operation ID
            item_id: The context item ID
            
        Returns:
            Optional[ContextItem]: The context item if found
        """
        if operation_id not in self.active_contexts:
            # Try to load from disk
            if not await self._load_context_from_disk(operation_id):
                return None
        
        return self.active_contexts[operation_id].get(item_id)
    
    async def update_context_item(
        self, 
        operation_id: str, 
        item_id: str, 
        content: Optional[str] = None,
        priority: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Update a context item.
        
        Args:
            operation_id: The operation ID
            item_id: The context item ID
            content: New content (if None, keep existing)
            priority: New priority (if None, keep existing)
            metadata: New metadata (if None, keep existing)
            
        Returns:
            bool: True if successful
        """
        if operation_id not in self.active_contexts:
            # Try to load from disk
            if not await self._load_context_from_disk(operation_id):
                return False
        
        if item_id not in self.active_contexts[operation_id]:
            return False
        
        item = self.active_contexts[operation_id][item_id]
        
        # Update fields if provided
        if content is not None:
            item.content = content
            item.token_count = count_tokens(content)
        
        if priority is not None:
            item.priority = max(0, min(100, priority))  # Ensure 0-100 range
        
        if metadata is not None:
            item.metadata.update(metadata)
        
        item.modified_at = datetime.now().isoformat()
        
        # Save updated item to disk
        item_path = self.contexts_dir / f"{operation_id}_{item_id}.json"
        with open(item_path, 'w') as f:
            json.dump({
                "id": item.id,
                "content": item.content,
                "source": item.source,
                "created_at": item.created_at,
                "modified_at": item.modified_at,
                "token_count": item.token_count,
                "priority": item.priority,
                "metadata": item.metadata
            }, f, indent=2)
        
        # Update context metadata
        await self._update_context_metadata(operation_id)
        
        # Check if compression is needed
        await self._check_and_apply_compression(operation_id)
        
        logger.info(f"Updated context item {item_id} in operation {operation_id}")
        return True
    
    async def remove_from_context(
        self, 
        operation_id: str, 
        item_id: str
    ) -> bool:
        """
        Remove a context item.
        
        Args:
            operation_id: The operation ID
            item_id: The context item ID
            
        Returns:
            bool: True if successful
        """
        if operation_id not in self.active_contexts:
            # Try to load from disk
            if not await self._load_context_from_disk(operation_id):
                return False
        
        if item_id not in self.active_contexts[operation_id]:
            return False
        
        # Remove from active contexts
        del self.active_contexts[operation_id][item_id]
        
        # Remove from disk
        item_path = self.contexts_dir / f"{operation_id}_{item_id}.json"
        if item_path.exists():
            item_path.unlink()
        
        # Update context metadata
        await self._update_context_metadata(operation_id)
        
        logger.info(f"Removed context item {item_id} from operation {operation_id}")
        return True
    
    async def delete_context(self, operation_id: str) -> bool:
        """
        Delete an entire context.
        
        Args:
            operation_id: The operation ID
            
        Returns:
            bool: True if successful
        """
        if operation_id in self.active_contexts:
            del self.active_contexts[operation_id]
        
        # Remove all context files from disk
        deleted = False
        for path in self.contexts_dir.glob(f"{operation_id}_*.json"):
            path.unlink()
            deleted = True
        
        if deleted:
            logger.info(f"Deleted context for operation {operation_id}")
            return True
        else:
            logger.warning(f"No context found to delete for operation {operation_id}")
            return False
    
    async def _load_context_from_disk(self, operation_id: str) -> bool:
        """
        Load context from disk.
        
        Args:
            operation_id: The operation ID
            
        Returns:
            bool: True if successful
        """
        # Check if metadata exists
        metadata_path = self.contexts_dir / f"{operation_id}_metadata.json"
        if not metadata_path.exists():
            return False
        
        # Initialize context dictionary
        self.active_contexts[operation_id] = {}
        
        # Load all context items
        for path in self.contexts_dir.glob(f"{operation_id}_*.json"):
            if path == metadata_path:
                continue
            
            try:
                with open(path, 'r') as f:
                    data = json.load(f)
                
                item = ContextItem(
                    id=data["id"],
                    content=data["content"],
                    source=data["source"],
                    created_at=data["created_at"],
                    modified_at=data["modified_at"],
                    token_count=data["token_count"],
                    priority=data["priority"],
                    metadata=data["metadata"]
                )
                
                self.active_contexts[operation_id][item.id] = item
            except Exception as e:
                logger.error(f"Error loading context item from {path}: {str(e)}")
        
        logger.info(f"Loaded context for operation {operation_id} with {len(self.active_contexts[operation_id])} items")
        return True
    
    async def _update_context_metadata(self, operation_id: str) -> None:
        """
        Update context metadata on disk.
        
        Args:
            operation_id: The operation ID
        """
        if operation_id not in self.active_contexts:
            return
        
        # Load existing metadata
        metadata_path = self.contexts_dir / f"{operation_id}_metadata.json"
        metadata = {}
        
        if metadata_path.exists():
            try:
                with open(metadata_path, 'r') as f:
                    metadata = json.load(f)
            except Exception as e:
                logger.error(f"Error loading metadata for {operation_id}: {str(e)}")
        
        # Update metadata
        metadata.update({
            "last_modified": datetime.now().isoformat(),
            "item_count": len(self.active_contexts[operation_id]),
            "total_tokens": sum(item.token_count for item in self.active_contexts[operation_id].values())
        })
        
        # Save updated metadata
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)
    
    async def _check_and_apply_compression(self, operation_id: str) -> None:
        """
        Check if compression is needed and apply if necessary.
        
        Args:
            operation_id: The operation ID
        """
        if operation_id not in self.active_contexts:
            return
        
        # Load metadata to get max_tokens
        metadata_path = self.contexts_dir / f"{operation_id}_metadata.json"
        max_tokens = self.config.max_tokens
        
        if metadata_path.exists():
            try:
                with open(metadata_path, 'r') as f:
                    metadata = json.load(f)
                    max_tokens = metadata.get("max_tokens", max_tokens)
            except Exception as e:
                logger.error(f"Error loading metadata for {operation_id}: {str(e)}")
        
        # Calculate total tokens
        total_tokens = sum(item.token_count for item in self.active_contexts[operation_id].values())
        
        # Check if compression is needed
        if total_tokens <= max_tokens:
            return
        
        # Get compression strategy
        strategy_name = self.config.default_compression_strategy
        if strategy_name not in self.compression_strategies:
            logger.warning(f"Compression strategy {strategy_name} not found. Using truncate.")
            strategy_name = "truncate"
        
        strategy = self.compression_strategies[strategy_name]
        
        # Sort items by priority (lowest first)
        sorted_items = sorted(
            self.active_contexts[operation_id].values(),
            key=lambda x: x.priority
        )
        
        # Apply compression until under token limit
        for item in sorted_items:
            if item.priority >= strategy.priority_threshold:
                continue
            
            # Calculate tokens to remove
            tokens_to_remove = total_tokens - max_tokens
            if tokens_to_remove <= 0:
                break
            
            # Calculate max tokens for this item after compression
            max_item_tokens = max(10, item.token_count - tokens_to_remove)
            
            # Apply compression
            compressed_item = strategy.compression_fn(item, max_item_tokens)
            
            # Update item
            self.active_contexts[operation_id][item.id] = compressed_item
            
            # Save compressed item to disk
            item_path = self.contexts_dir / f"{operation_id}_{item.id}.json"
            with open(item_path, 'w') as f:
                json.dump({
                    "id": compressed_item.id,
                    "content": compressed_item.content,
                    "source": compressed_item.source,
                    "created_at": compressed_item.created_at,
                    "modified_at": compressed_item.modified_at,
                    "token_count": compressed_item.token_count,
                    "priority": compressed_item.priority,
                    "metadata": compressed_item.metadata
                }, f, indent=2)
            
            # Update total tokens
            total_tokens = sum(i.token_count for i in self.active_contexts[operation_id].values())
            
            if total_tokens <= max_tokens:
                break
        
        # Update metadata
        await self._update_context_metadata(operation_id)
        
        logger.info(f"Applied compression to context {operation_id}. New token count: {total_tokens}")
    
    async def list_contexts(self) -> List[Dict[str, Any]]:
        """
        List all available contexts.
        
        Returns:
            List[Dict[str, Any]]: List of context metadata
        """
        contexts = []
        
        # Get all metadata files
        for path in self.contexts_dir.glob("*_metadata.json"):
            try:
                with open(path, 'r') as f:
                    metadata = json.load(f)
                    contexts.append(metadata)
            except Exception as e:
                logger.error(f"Error loading metadata from {path}: {str(e)}")
        
        return contexts
    
    async def get_context_stats(self, operation_id: str) -> Dict[str, Any]:
        """
        Get statistics for a context.
        
        Args:
            operation_id: The operation ID
            
        Returns:
            Dict[str, Any]: Context statistics
        """
        if operation_id not in self.active_contexts:
            # Try to load from disk
            if not await self._load_context_from_disk(operation_id):
                raise ValueError(f"Context not found for operation {operation_id}")
        
        items = self.active_contexts[operation_id].values()
        total_tokens = sum(item.token_count for item in items)
        
        return {
            "operation_id": operation_id,
            "item_count": len(items),
            "total_tokens": total_tokens,
            "sources": list(set(item.source for item in items)),
            "priority_distribution": {
                "high": sum(1 for item in items if item.priority >= 70),
                "medium": sum(1 for item in items if 30 <= item.priority < 70),
                "low": sum(1 for item in items if item.priority < 30)
            },
            "compression_applied": any("compression" in item.metadata for item in items)
        } 