"""Integration module for using the Context Catalog with Cerebrum."""

from typing import Dict, List, Optional, Any, Union
from datetime import datetime

from .registry import ContextCatalogRegistry
from .models import ContextEntry
from .metadata import (
    ContextMetadata,
    StorageInfo,
    AccessControl,
    StorageBackend,
    SourceType,
    DataType,
    AccessLevel
)


class CerebrumDataCatalog:
    """Integration class for using the Context Catalog with Cerebrum."""
    
    def __init__(
        self,
        storage_path: Optional[str] = None,
        default_owner: str = "system"
    ):
        """Initialize the data catalog."""
        self.registry = ContextCatalogRegistry({
            "file_storage_path": storage_path or "cerebrum_data"
        })
        self.default_owner = default_owner
    
    async def register_knowledge_base(
        self,
        content: Dict[str, Any],
        domain: str,
        purpose: str,
        tags: List[str],
        description: Optional[str] = None,
        access_level: AccessLevel = AccessLevel.PRIVATE,
        owner_id: Optional[str] = None
    ) -> str:
        """Register knowledge base content."""
        metadata = ContextMetadata(
            source_type=SourceType.KNOWLEDGE_BASE,
            data_type=DataType.TEXT,
            domain=domain,
            purpose=purpose,
            storage_info=StorageInfo(
                backend=StorageBackend.FILE,
                location=f"kb_{domain}",
                format="json"
            ),
            access_control=AccessControl(
                level=access_level,
                owner_id=owner_id or self.default_owner
            ),
            tags=tags,
            description=description
        )
        
        return await self.registry.register_context(
            content=content,
            metadata=metadata,
            user_id=owner_id or self.default_owner
        )
    
    async def register_vector_store(
        self,
        vectors: List[List[float]],
        documents: List[str],
        model_info: Dict[str, Any],
        domain: str,
        purpose: str,
        tags: List[str],
        description: Optional[str] = None,
        access_level: AccessLevel = AccessLevel.PRIVATE,
        owner_id: Optional[str] = None
    ) -> str:
        """Register vector store data."""
        content = {
            "vectors": vectors,
            "documents": documents,
            "model_info": model_info
        }
        
        metadata = ContextMetadata(
            source_type=SourceType.VECTOR_STORE,
            data_type=DataType.VECTOR,
            domain=domain,
            purpose=purpose,
            storage_info=StorageInfo(
                backend=StorageBackend.FILE,
                location=f"vectors_{domain}",
                format="json"
            ),
            access_control=AccessControl(
                level=access_level,
                owner_id=owner_id or self.default_owner
            ),
            tags=tags,
            description=description
        )
        
        return await self.registry.register_context(
            content=content,
            metadata=metadata,
            user_id=owner_id or self.default_owner
        )
    
    async def register_code_context(
        self,
        code: str,
        domain: str,
        purpose: str,
        tags: List[str],
        description: Optional[str] = None,
        access_level: AccessLevel = AccessLevel.PRIVATE,
        owner_id: Optional[str] = None
    ) -> str:
        """Register code context."""
        metadata = ContextMetadata(
            source_type=SourceType.CODE,
            data_type=DataType.CODE,
            domain=domain,
            purpose=purpose,
            storage_info=StorageInfo(
                backend=StorageBackend.FILE,
                location=f"code_{domain}",
                format="python"
            ),
            access_control=AccessControl(
                level=access_level,
                owner_id=owner_id or self.default_owner
            ),
            tags=tags,
            description=description
        )
        
        return await self.registry.register_context(
            content=code,
            metadata=metadata,
            user_id=owner_id or self.default_owner
        )
    
    async def register_system_context(
        self,
        content: Any,
        domain: str,
        purpose: str,
        data_format: str,
        tags: List[str],
        description: Optional[str] = None,
        access_level: AccessLevel = AccessLevel.PRIVATE,
        owner_id: Optional[str] = None
    ) -> str:
        """Register system context data."""
        metadata = ContextMetadata(
            source_type=SourceType.SYSTEM,
            data_type=DataType.BINARY,
            domain=domain,
            purpose=purpose,
            storage_info=StorageInfo(
                backend=StorageBackend.FILE,
                location=f"system_{domain}",
                format=data_format
            ),
            access_control=AccessControl(
                level=access_level,
                owner_id=owner_id or self.default_owner
            ),
            tags=tags,
            description=description
        )
        
        return await self.registry.register_context(
            content=content,
            metadata=metadata,
            user_id=owner_id or self.default_owner
        )
    
    async def find_by_domain(
        self,
        domain: str,
        user_id: str = "system"
    ) -> List[ContextEntry]:
        """Find all contexts in a domain."""
        results = []
        for entry in self.registry.entries.values():
            try:
                if entry.metadata.domain == domain:
                    self.registry._check_access(entry.id, user_id, "read")
                    self.registry._record_access(entry.id, user_id, "read")
                    results.append(entry)
            except AccessError:
                continue
        return results
    
    async def find_by_tags(
        self,
        tags: List[str],
        user_id: str = "system"
    ) -> List[ContextEntry]:
        """Find contexts with specific tags."""
        results = []
        for entry in self.registry.entries.values():
            try:
                if any(tag in entry.metadata.tags for tag in tags):
                    self.registry._check_access(entry.id, user_id, "read")
                    self.registry._record_access(entry.id, user_id, "read")
                    results.append(entry)
            except AccessError:
                continue
        return results
    
    async def find_knowledge_base(
        self,
        tags: Optional[List[str]] = None,
        domain: Optional[str] = None,
        user_id: str = "system"
    ) -> List[ContextEntry]:
        """Find knowledge base entries."""
        results = []
        for entry in self.registry.entries.values():
            try:
                if entry.metadata.source_type != SourceType.KNOWLEDGE_BASE:
                    continue
                
                if tags and not any(tag in entry.metadata.tags for tag in tags):
                    continue
                    
                if domain and entry.metadata.domain != domain:
                    continue

                self.registry._check_access(entry.id, user_id, "read")
                self.registry._record_access(entry.id, user_id, "read")
                results.append(entry)
            except AccessError:
                continue
        return results
    
    async def find_vector_store(
        self,
        tags: Optional[List[str]] = None,
        domain: Optional[str] = None,
        user_id: str = "system"
    ) -> List[ContextEntry]:
        """Find vector store entries."""
        results = []
        for entry in self.registry.entries.values():
            try:
                if entry.metadata.source_type != SourceType.VECTOR_STORE:
                    continue
                
                if tags and not any(tag in entry.metadata.tags for tag in tags):
                    continue
                    
                if domain and entry.metadata.domain != domain:
                    continue

                self.registry._check_access(entry.id, user_id, "read")
                self.registry._record_access(entry.id, user_id, "read")
                results.append(entry)
            except AccessError:
                continue
        return results
    
    async def link_contexts(
        self,
        from_id: str,
        to_id: str,
        user_id: Optional[str] = None
    ) -> None:
        """Create a relationship between contexts."""
        await self.registry.add_relationship(
            from_id,
            to_id,
            user_id=user_id or self.default_owner
        )
    
    async def get_usage_stats(
        self,
        context_id: str,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get usage statistics for a context."""
        entry = await self.registry.get_context_info(
            context_id,
            user_id=user_id or self.default_owner
        )
        return {
            "access_count": entry.usage_stats.access_count,
            "last_accessed": entry.usage_stats.last_accessed,
            "operation_counts": entry.usage_stats.operation_counts,
            "access_history": [
                {
                    "timestamp": record.timestamp,
                    "user_id": record.user_id,
                    "operation": record.operation
                }
                for record in entry.access_history
            ]
        }
    
    async def get_related_data(
        self,
        context_id: str,
        user_id: Optional[str] = None
    ) -> Dict[str, List[ContextEntry]]:
        """Get all data related to a context."""
        relationships = await self.registry.get_related_contexts(
            context_id,
            user_id=user_id or self.default_owner
        )
        
        result = {
            "dependencies": [],
            "dependents": [],
            "related": []
        }
        
        # Fetch full entries for all related contexts
        for rel_type, ids in relationships.items():
            for rel_id in ids:
                try:
                    entry = await self.registry.get_context_info(
                        rel_id,
                        user_id=user_id or self.default_owner
                    )
                    result[rel_type].append(entry)
                except Exception:
                    continue
        
        return result 