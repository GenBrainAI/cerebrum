# Context Catalog System

The Context Catalog System is a comprehensive solution for managing, tracking, and utilizing different types of data contexts within Cerebrum. It provides a flexible and powerful way to store, organize, and relate different pieces of information while maintaining proper access control and usage tracking.

## Core Components

### 1. Context Registry
The central component that manages all context entries, their relationships, and usage statistics. It provides operations for:
- Registering new contexts
- Retrieving context information
- Updating existing contexts
- Managing relationships between contexts
- Tracking context usage

### 2. Metadata System
Rich metadata management for context entries, including:
- Source type (knowledge base, vector store, code, system)
- Data type (text, code, documentation, etc.)
- Domain and purpose information
- Access control settings
- Tags and versioning
- Custom validation rules

### 3. Storage Management
Flexible storage backend system supporting:
- File system storage
- In-memory storage
- Extensible backend interface for custom implementations
- Data integrity verification
- Configurable storage locations

## Key Features

### Access Control
- Role-based access control
- User and group permissions
- Time-based access expiration
- Owner privileges
- System-level access

### Relationship Management
- Dependency tracking
- Bidirectional relationships
- Relationship types
- Relationship queries

### Usage Tracking
- Access history
- Operation statistics
- User activity tracking
- Usage pattern analysis

## Usage Example

```python
from context_catalog.registry import ContextCatalogRegistry
from context_catalog.metadata import (
    ContextMetadata,
    StorageInfo,
    AccessControl,
    StorageBackend,
    SourceType,
    DataType,
    AccessLevel
)

# Initialize registry
registry = ContextCatalogRegistry({
    "file_storage_path": "context_storage"
})

# Create metadata
metadata = ContextMetadata(
    source_type=SourceType.KNOWLEDGE_BASE,
    data_type=DataType.TEXT,
    domain="example_domain",
    purpose="Example purpose",
    storage_info=StorageInfo(
        backend=StorageBackend.FILE,
        location="example",
        format="json"
    ),
    access_control=AccessControl(
        level=AccessLevel.PRIVATE,
        owner_id="user123"
    )
)

# Register context
context_id = await registry.register_context(
    content={"example": "data"},
    metadata=metadata,
    user_id="user123"
)

# Retrieve context
entry = await registry.get_context_info(
    context_id,
    include_relationships=True
)
```

## Installation

1. Add the context catalog package to your project:
```bash
cp -r src/context_catalog /path/to/your/project/src/
```

2. Install dependencies:
```bash
pip install pydantic
```

## Development

### Running Tests
```bash
pytest tests/context_catalog/
```

### Adding New Features

1. Storage Backends
```python
from context_catalog.storage import StorageBackendBase

class CustomBackend(StorageBackendBase):
    async def store(self, data, metadata, config):
        # Implementation
        pass
    
    async def retrieve(self, storage_info):
        # Implementation
        pass
    
    async def delete(self, storage_info):
        # Implementation
        pass
```

2. Custom Validation Rules
```python
def custom_validator(metadata: ContextMetadata) -> None:
    if not metadata.domain.startswith("custom_"):
        raise ValidationError("Invalid domain prefix")

registry._validate_metadata = custom_validator
```

## Best Practices

1. Context Management
- Use meaningful domain and purpose descriptions
- Apply appropriate tags for easy discovery
- Set reasonable access expiration times
- Clean up unused contexts

2. Relationships
- Document relationship purposes
- Maintain clean dependency graphs
- Remove obsolete relationships
- Track bidirectional dependencies

3. Storage
- Choose appropriate storage backends
- Monitor storage usage
- Implement cleanup policies
- Verify data integrity

4. Access Control
- Follow principle of least privilege
- Review access regularly
- Document access patterns
- Monitor unauthorized attempts

## Contributing

1. Fork the repository
2. Create a feature branch
3. Implement changes
4. Add tests
5. Create pull request

## License

MIT License - See LICENSE file for details 