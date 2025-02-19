"""Metadata system for the Context Catalog."""

from datetime import datetime
from typing import Dict, List, Optional, Any
from enum import Enum
from pydantic import BaseModel, Field


class SourceType(str, Enum):
    """Types of context sources."""
    
    KNOWLEDGE_BASE = "knowledge_base"
    VECTOR_STORE = "vector_store"
    CODE = "code"
    SYSTEM = "system"


class DataType(str, Enum):
    """Types of data stored in contexts."""
    
    TEXT = "text"
    CODE = "code"
    DOCUMENTATION = "documentation"
    VECTOR = "vector"
    BINARY = "binary"
    JSON = "json"


class AccessLevel(str, Enum):
    """Access control levels."""
    
    PUBLIC = "public"
    PRIVATE = "private"
    SHARED = "shared"
    SYSTEM = "system"


class StorageBackend(str, Enum):
    """Available storage backends."""
    
    FILE = "file"
    S3 = "s3"
    DATABASE = "database"
    MEMORY = "memory"


class StorageInfo(BaseModel):
    """Information about where and how context data is stored."""
    
    backend: StorageBackend
    location: str
    format: str
    size: Optional[int] = None
    checksum: Optional[str] = None
    encryption_info: Optional[Dict[str, Any]] = None
    compression: Optional[str] = None
    additional_metadata: Dict[str, Any] = Field(default_factory=dict)


class AccessControl(BaseModel):
    """Access control configuration for context entries."""
    
    level: AccessLevel = AccessLevel.PRIVATE
    owner_id: str
    allowed_users: List[str] = Field(default_factory=list)
    allowed_groups: List[str] = Field(default_factory=list)
    expiration: Optional[datetime] = None
    additional_rules: Dict[str, Any] = Field(default_factory=dict)


class ContextMetadata(BaseModel):
    """Rich metadata for context entries."""
    
    source_type: SourceType
    data_type: DataType
    domain: str
    purpose: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    version: str = "1.0.0"
    tags: List[str] = Field(default_factory=list)
    storage_info: StorageInfo
    validation_rules: Optional[Dict[str, Any]] = None
    access_control: AccessControl
    description: Optional[str] = None
    additional_metadata: Dict[str, Any] = Field(default_factory=dict)

    def update_timestamp(self) -> None:
        """Update the updated_at timestamp."""
        self.updated_at = datetime.utcnow()

    def add_tag(self, tag: str) -> None:
        """Add a new tag if it doesn't exist."""
        if tag not in self.tags:
            self.tags.append(tag)
            self.update_timestamp()

    def remove_tag(self, tag: str) -> None:
        """Remove a tag if it exists."""
        if tag in self.tags:
            self.tags.remove(tag)
            self.update_timestamp()

    def update_validation_rules(self, rules: Dict[str, Any]) -> None:
        """Update validation rules."""
        self.validation_rules = rules
        self.update_timestamp()

    def update_access_control(self, access_control: AccessControl) -> None:
        """Update access control settings."""
        self.access_control = access_control
        self.update_timestamp() 