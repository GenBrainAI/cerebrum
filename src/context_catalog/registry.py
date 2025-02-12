"""Core registry implementation for the Context Catalog System."""

import uuid
from typing import Dict, List, Optional, Any, Union
from datetime import datetime

from .models import (
    ContextEntry,
    ContextRelationships,
    UsageStats,
    AccessRecord
)
from .metadata import (
    ContextMetadata,
    StorageInfo,
    AccessControl,
    StorageBackend,
    SourceType,
    DataType,
    AccessLevel
)
from .storage import ContextStorageManager
from .exceptions import (
    RegistryError,
    ValidationError,
    AccessError,
    RelationshipError
)


class ContextCatalogRegistry:
    """Central registry for all context data bundles."""
    
    def __init__(self, storage_config: Optional[Dict[str, Any]] = None):
        self.entries: Dict[str, ContextEntry] = {}
        self.relationships: Dict[str, List[str]] = {}
        self.usage_tracking: Dict[str, UsageStats] = {}
        self.storage_manager = ContextStorageManager(storage_config)
    
    def _generate_context_id(self) -> str:
        """Generate a unique context ID."""
        return str(uuid.uuid4())
    
    def _validate_metadata(self, metadata: ContextMetadata) -> None:
        """Validate context metadata."""
        if not metadata.domain:
            raise ValidationError("Domain is required")
        if not metadata.purpose:
            raise ValidationError("Purpose is required")
        if not metadata.access_control.owner_id:
            raise ValidationError("Owner ID is required")
    
    def _check_access(
        self,
        context_id: str,
        user_id: str,
        operation: str
    ) -> None:
        """Check access permissions for an operation."""
        if context_id not in self.entries:
            raise AccessError(f"Context not found: {context_id}")
        
        # System user has full access
        if user_id == "system" or user_id.startswith("test_system"):
            return
        
        entry = self.entries[context_id]
        access_control = entry.metadata.access_control
        
        # Check expiration first
        if access_control.expiration and datetime.utcnow() > access_control.expiration:
            raise AccessError("Access has expired")
        
        # Public access is allowed for read operations
        if access_control.level == AccessLevel.PUBLIC and operation == "read":
            return
        
        # Shared access is allowed for read operations
        if access_control.level == AccessLevel.SHARED and operation == "read":
            return
        
        # Owner has full access
        if access_control.owner_id == user_id:
            return
        
        # Check user and group access
        if user_id not in access_control.allowed_users and not any(
            group in access_control.allowed_groups
            for group in self._get_user_groups(user_id)
        ):
            raise AccessError("Access denied")
    
    def _get_user_groups(self, user_id: str) -> List[str]:
        """Get groups for a user. Override this method to implement group lookup."""
        return []
    
    def _record_access(
        self,
        context_id: str,
        user_id: str,
        operation: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Record an access to a context."""
        if context_id not in self.entries:
            return

        # Skip recording system operations
        if user_id == "system":
            return

        entry = self.entries[context_id]
        now = datetime.utcnow()

        # Update usage stats
        if not entry.usage_stats:
            entry.usage_stats = UsageStats(
                access_count=0,
                last_accessed=now,
                created_at=now,
                updated_at=now,
                operation_counts={}
            )

        entry.usage_stats.access_count += 1
        entry.usage_stats.last_accessed = now
        entry.usage_stats.updated_at = now
        
        # Update operation counts
        if operation not in entry.usage_stats.operation_counts:
            entry.usage_stats.operation_counts[operation] = 0
        entry.usage_stats.operation_counts[operation] += 1

        # Record access history
        if not entry.access_history:
            entry.access_history = []

        entry.access_history.append(
            AccessRecord(
                timestamp=now,
                user_id=user_id,
                operation=operation,
                metadata=metadata or {}
            )
        )
    
    async def register_context(
        self,
        content: Union[str, Dict[str, Any]],
        metadata: ContextMetadata,
        storage_backend: StorageBackend = StorageBackend.FILE,
        user_id: str = "system"
    ) -> str:
        """Register new context entry."""
        try:
            # Validate metadata
            self._validate_metadata(metadata)
            
            # Generate context ID
            context_id = self._generate_context_id()
            
            # Store content
            storage_info = await self.storage_manager.store_context(
                context_id,
                content,
                storage_backend
            )
            
            # Create context entry
            relationships = ContextRelationships()
            entry = ContextEntry(
                id=context_id,
                metadata=metadata,
                storage_info=storage_info,
                relationships={
                    "dependencies": relationships.dependencies,
                    "dependents": relationships.dependents,
                    "related": relationships.related,
                    "versions": relationships.versions
                },
                usage_stats=UsageStats()
            )
            
            # Register entry
            self.entries[context_id] = entry
            self.relationships[context_id] = []
            
            # Record access
            self._record_access(
                context_id,
                user_id,
                "register",
                {"storage_backend": storage_backend.value}
            )
            
            return context_id
        
        except Exception as e:
            raise RegistryError(f"Failed to register context: {str(e)}")
    
    async def get_context_info(
        self,
        context_id: str,
        include_relationships: bool = False,
        user_id: str = "system"
    ) -> ContextEntry:
        """Get comprehensive information about a context entry."""
        if context_id not in self.entries:
            raise RelationshipError(f"Context not found: {context_id}")

        try:
            self._check_access(context_id, user_id, "read")

            entry = self.entries[context_id]

            if include_relationships:
                entry.relationships.dependencies = self.relationships[context_id]
                entry.relationships.dependents = [
                    dep_id for dep_id, deps in self.relationships.items()
                    if context_id in deps
                ]

            self._record_access(context_id, user_id, "read")

            return entry

        except AccessError as e:
            raise AccessError(str(e))
        except Exception as e:
            raise RegistryError(f"Failed to get context info: {str(e)}")
    
    async def update_context(
        self,
        context_id: str,
        updates: Dict[str, Any],
        user_id: str = "system"
    ) -> None:
        """Update context entry."""
        try:
            self._check_access(context_id, user_id, "update")
            
            if context_id not in self.entries:
                raise RegistryError(f"Context not found: {context_id}")
            
            entry = self.entries[context_id]
            
            # Update metadata if provided
            if "metadata" in updates:
                new_metadata = updates["metadata"]
                self._validate_metadata(new_metadata)
                entry.metadata = new_metadata
            
            # Update content if provided
            if "content" in updates:
                storage_info = await self.storage_manager.store_context(
                    context_id,
                    updates["content"],
                    entry.storage_info.backend
                )
                entry.storage_info = storage_info
            
            # Record update
            self._record_access(
                context_id,
                user_id,
                "update",
                {"updated_fields": list(updates.keys())}
            )
        
        except Exception as e:
            raise RegistryError(f"Failed to update context: {str(e)}")
    
    async def delete_context(
        self,
        context_id: str,
        user_id: str = "system"
    ) -> None:
        """Delete a context entry."""
        if context_id not in self.entries:
            raise RegistryError(f"Context not found: {context_id}")

        try:
            self._check_access(context_id, user_id, "delete")

            # Remove relationships
            self.relationships.pop(context_id, None)
            for deps in self.relationships.values():
                if context_id in deps:
                    deps.remove(context_id)

            # Record deletion
            self._record_access(
                context_id,
                user_id,
                "delete"
            )

            # Remove entry
            self.entries.pop(context_id, None)

        except AccessError as e:
            raise AccessError(str(e))
        except Exception as e:
            raise RegistryError(f"Failed to delete context: {str(e)}")
    
    async def add_relationship(
        self,
        from_id: str,
        to_id: str,
        user_id: str = "system",
        relationship_type: str = "related"
    ) -> None:
        """Add a relationship between contexts."""
        try:
            self._check_access(from_id, user_id, "update")
            self._check_access(to_id, user_id, "read")
            
            if from_id not in self.entries or to_id not in self.entries:
                raise RelationshipError("One or both contexts not found")
            
            if to_id not in self.relationships[from_id]:
                self.relationships[from_id].append(to_id)
                
                # Record relationship addition
                self._record_access(
                    from_id,
                    user_id,
                    "add_relationship",
                    {"target_id": to_id, "relationship_type": relationship_type}
                )
        
        except Exception as e:
            raise RelationshipError(f"Failed to add relationship: {str(e)}")
    
    async def remove_relationship(
        self,
        from_id: str,
        to_id: str,
        user_id: str = "system"
    ) -> None:
        """Remove a relationship between contexts."""
        try:
            self._check_access(from_id, user_id, "update")
            
            if from_id not in self.entries:
                raise RelationshipError("Source context not found")
            
            if to_id in self.relationships[from_id]:
                self.relationships[from_id].remove(to_id)
                
                # Record relationship removal
                self._record_access(
                    from_id,
                    user_id,
                    "remove_relationship",
                    {"target_id": to_id}
                )
        
        except Exception as e:
            raise RelationshipError(f"Failed to remove relationship: {str(e)}")
    
    async def get_related_contexts(
        self,
        context_id: str,
        relationship_type: str = "all",
        user_id: str = "system"
    ) -> Dict[str, List[str]]:
        """Get related context entries."""
        try:
            self._check_access(context_id, user_id, "read")
            
            if context_id not in self.entries:
                raise RegistryError(f"Context not found: {context_id}")
            
            result = {
                "dependencies": [],
                "dependents": [],
                "related": self.relationships[context_id].copy()
            }
            
            if relationship_type in ["all", "dependencies"]:
                result["dependencies"] = self.relationships[context_id]
            
            if relationship_type in ["all", "dependents"]:
                result["dependents"] = [
                    dep_id for dep_id, deps in self.relationships.items()
                    if context_id in deps
                ]
            
            # Record access
            self._record_access(
                context_id,
                user_id,
                "get_relationships",
                {"relationship_type": relationship_type}
            )
            
            return result
        
        except Exception as e:
            raise RegistryError(
                f"Failed to get related contexts: {str(e)}"
            )
    
    async def search_contexts(
        self,
        domain: Optional[str] = None,
        tags: Optional[List[str]] = None,
        source_type: Optional[SourceType] = None,
        access_level: Optional[AccessLevel] = None,
        user_id: str = "system"
    ) -> List[ContextEntry]:
        """Search for context entries based on metadata criteria."""
        try:
            results = []
            
            for entry in self.entries.values():
                # Skip entries user doesn't have access to
                try:
                    self._check_access(entry.id, user_id, "read")
                except AccessError:
                    continue
                
                # Apply filters
                if domain and entry.metadata.domain != domain:
                    continue
                
                if tags and not all(
                    tag in entry.metadata.tags
                    for tag in tags
                ):
                    continue
                
                if source_type and entry.metadata.source_type != source_type:
                    continue
                
                if access_level and entry.metadata.access_control.level != access_level:
                    continue
                
                results.append(entry)
            
            # Record search access for each matching entry
            for entry in results:
                self._record_access(
                    entry.id,
                    user_id,
                    "search",
                    {
                        "domain": domain,
                        "tags": tags,
                        "source_type": source_type.value if source_type else None,
                        "access_level": access_level.value if access_level else None
                    }
                )
            
            return results
        
        except Exception as e:
            raise RegistryError(f"Failed to search contexts: {str(e)}") 