"""Custom exceptions for the Context Catalog System."""


class ContextCatalogError(Exception):
    """Base exception for all context catalog errors."""
    pass


class StorageError(ContextCatalogError):
    """Raised when storage operations fail."""
    pass


class ValidationError(ContextCatalogError):
    """Raised when context validation fails."""
    pass


class AccessError(ContextCatalogError):
    """Raised when access control checks fail."""
    pass


class RelationshipError(ContextCatalogError):
    """Raised when relationship operations fail."""
    pass


class MetadataError(ContextCatalogError):
    """Raised when metadata operations fail."""
    pass


class RegistryError(ContextCatalogError):
    """Raised when registry operations fail."""
    pass 