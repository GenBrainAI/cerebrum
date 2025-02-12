"""Storage management system for the Context Catalog."""

import os
import json
import hashlib
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from datetime import datetime

from .metadata import StorageInfo, StorageBackend
from .exceptions import StorageError


class StorageBackendBase(ABC):
    """Base class for storage backend implementations."""
    
    @abstractmethod
    async def store(
        self,
        data: Any,
        metadata: Dict[str, Any],
        config: Dict[str, Any]
    ) -> StorageInfo:
        """Store data and return storage information."""
        pass
    
    @abstractmethod
    async def retrieve(
        self,
        storage_info: StorageInfo
    ) -> Any:
        """Retrieve data using storage information."""
        pass
    
    @abstractmethod
    async def delete(
        self,
        storage_info: StorageInfo
    ) -> bool:
        """Delete data using storage information."""
        pass


class FileSystemBackend(StorageBackendBase):
    """File system storage backend implementation."""
    
    def __init__(self, base_path: str):
        self.base_path = base_path
        os.makedirs(base_path, exist_ok=True)
    
    def _generate_path(self, prefix: str) -> str:
        """Generate a unique file path."""
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        return os.path.join(
            self.base_path,
            f"{prefix}_{timestamp}.json"
        )
    
    def _calculate_checksum(self, data: str) -> str:
        """Calculate SHA-256 checksum of data."""
        return hashlib.sha256(data.encode()).hexdigest()
    
    async def store(
        self,
        data: Any,
        metadata: Dict[str, Any],
        config: Dict[str, Any]
    ) -> StorageInfo:
        """Store data in the file system."""
        try:
            file_path = self._generate_path(
                config.get("prefix", "context")
            )
            
            # Convert data to JSON string
            json_data = json.dumps(data)
            
            # Calculate checksum and size
            checksum = self._calculate_checksum(json_data)
            size = len(json_data.encode())
            
            # Write to file
            with open(file_path, 'w') as f:
                f.write(json_data)
            
            return StorageInfo(
                backend=StorageBackend.FILE,
                location=file_path,
                format="json",
                size=size,
                checksum=checksum,
                compression=None,
                additional_metadata=metadata
            )
        
        except Exception as e:
            raise StorageError(f"Failed to store data: {str(e)}")
    
    async def retrieve(
        self,
        storage_info: StorageInfo
    ) -> Any:
        """Retrieve data from the file system."""
        try:
            with open(storage_info.location, 'r') as f:
                data = json.load(f)
            
            # Verify checksum if provided
            if storage_info.checksum:
                current_checksum = self._calculate_checksum(
                    json.dumps(data)
                )
                if current_checksum != storage_info.checksum:
                    raise StorageError("Data integrity check failed")
            
            return data
        
        except Exception as e:
            raise StorageError(f"Failed to retrieve data: {str(e)}")
    
    async def delete(
        self,
        storage_info: StorageInfo
    ) -> bool:
        """Delete data from the file system."""
        try:
            os.remove(storage_info.location)
            return True
        except Exception as e:
            raise StorageError(f"Failed to delete data: {str(e)}")


class MemoryBackend(StorageBackendBase):
    """In-memory storage backend implementation."""
    
    def __init__(self):
        self.storage: Dict[str, Any] = {}
    
    async def store(
        self,
        data: Any,
        metadata: Dict[str, Any],
        config: Dict[str, Any]
    ) -> StorageInfo:
        """Store data in memory."""
        try:
            # Generate unique key
            key = f"memory_{datetime.utcnow().timestamp()}"
            
            # Store data
            self.storage[key] = data
            
            return StorageInfo(
                backend=StorageBackend.MEMORY,
                location=key,
                format="python",
                size=None,
                checksum=None,
                additional_metadata=metadata
            )
        
        except Exception as e:
            raise StorageError(f"Failed to store data in memory: {str(e)}")
    
    async def retrieve(
        self,
        storage_info: StorageInfo
    ) -> Any:
        """Retrieve data from memory."""
        try:
            return self.storage[storage_info.location]
        except KeyError:
            raise StorageError(f"Data not found: {storage_info.location}")
        except Exception as e:
            raise StorageError(f"Failed to retrieve data from memory: {str(e)}")
    
    async def delete(
        self,
        storage_info: StorageInfo
    ) -> bool:
        """Delete data from memory."""
        try:
            del self.storage[storage_info.location]
            return True
        except KeyError:
            return False
        except Exception as e:
            raise StorageError(f"Failed to delete data from memory: {str(e)}")


class ContextStorageManager:
    """Manages different storage backends for context data."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.backends: Dict[StorageBackend, StorageBackendBase] = {}
        
        # Initialize default backends
        self._init_default_backends()
    
    def _init_default_backends(self) -> None:
        """Initialize default storage backends."""
        # File system backend
        fs_path = self.config.get(
            "file_storage_path",
            os.path.join(os.getcwd(), "context_storage")
        )
        self.backends[StorageBackend.FILE] = FileSystemBackend(fs_path)
        
        # Memory backend
        self.backends[StorageBackend.MEMORY] = MemoryBackend()
    
    def register_backend(
        self,
        backend_type: StorageBackend,
        backend: StorageBackendBase
    ) -> None:
        """Register a new storage backend."""
        self.backends[backend_type] = backend
    
    async def store_context(
        self,
        context_id: str,
        data: Any,
        backend: StorageBackend,
        config: Optional[Dict[str, Any]] = None
    ) -> StorageInfo:
        """Store context data in specified backend."""
        if backend not in self.backends:
            raise StorageError(f"Storage backend not available: {backend}")
        
        metadata = {
            "context_id": context_id,
            "stored_at": datetime.utcnow().isoformat()
        }
        
        return await self.backends[backend].store(
            data,
            metadata,
            config or {}
        )
    
    async def retrieve_context(
        self,
        storage_info: StorageInfo
    ) -> Any:
        """Retrieve context data from storage."""
        if storage_info.backend not in self.backends:
            raise StorageError(
                f"Storage backend not available: {storage_info.backend}"
            )
        
        return await self.backends[storage_info.backend].retrieve(storage_info)
    
    async def delete_context(
        self,
        storage_info: StorageInfo
    ) -> bool:
        """Delete context data from storage."""
        if storage_info.backend not in self.backends:
            raise StorageError(
                f"Storage backend not available: {storage_info.backend}"
            )
        
        return await self.backends[storage_info.backend].delete(storage_info) 