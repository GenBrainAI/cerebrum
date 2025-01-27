from typing import Dict, List, Optional
from datetime import datetime
from uuid import UUID, uuid4
from enum import Enum

class ScrapingTargetType(Enum):
    KNOWLEDGE_BASE = "knowledge_base"
    VECTOR_STORE = "vector_store"
    CODE = "code"
    MULTI = "multi"  # For when content should go to multiple targets

class ScrapingContentType(Enum):
    WEB = "web"
    REPOSITORY = "repository"
    DOCUMENTATION = "documentation"

class ScrapingSession:
    """Model for managing scraping sessions and their metadata."""
    
    def __init__(self,
                 name: str,
                 description: Optional[str] = None,
                 target_type: ScrapingTargetType = ScrapingTargetType.KNOWLEDGE_BASE,
                 content_type: ScrapingContentType = ScrapingContentType.WEB,
                 metadata: Optional[Dict] = None):
        self.id = str(uuid4())
        self.name = name
        self.description = description
        self.target_type = target_type
        self.content_type = content_type
        self.created_at = datetime.now().isoformat()
        self.updated_at = self.created_at
        self.metadata = metadata or {}
        self.entries: List[Dict] = []
        self.status = "active"
        
        # For multi-target sessions
        self.target_configs = {
            ScrapingTargetType.KNOWLEDGE_BASE: {
                "enabled": target_type in [ScrapingTargetType.KNOWLEDGE_BASE, ScrapingTargetType.MULTI],
                "domain": None,  # Set during scraping
                "task_ids": [],  # For task associations
                "tasksmanager_ids": []  # For task manager associations
            },
            ScrapingTargetType.VECTOR_STORE: {
                "enabled": target_type in [ScrapingTargetType.VECTOR_STORE, ScrapingTargetType.MULTI],
                "index_name": None,  # Set during scraping
                "chunk_size": 1000,
                "chunk_overlap": 200
            },
            ScrapingTargetType.CODE: {
                "enabled": target_type in [ScrapingTargetType.CODE, ScrapingTargetType.MULTI],
                "extract_functions": True,
                "extract_classes": True,
                "include_comments": True
            }
        }
    
    def add_entry(self, entry: Dict) -> None:
        """Add a new entry to the session."""
        entry["added_at"] = datetime.now().isoformat()
        entry["session_id"] = self.id
        self.entries.append(entry)
        self.updated_at = datetime.now().isoformat()
    
    def update_target_config(self, target_type: ScrapingTargetType, config: Dict) -> None:
        """Update configuration for a specific target type."""
        if target_type in self.target_configs:
            self.target_configs[target_type].update(config)
            self.updated_at = datetime.now().isoformat()
    
    def enable_target(self, target_type: ScrapingTargetType) -> None:
        """Enable a specific target type for this session."""
        if target_type in self.target_configs:
            self.target_configs[target_type]["enabled"] = True
            if self.target_type != ScrapingTargetType.MULTI:
                self.target_type = ScrapingTargetType.MULTI
            self.updated_at = datetime.now().isoformat()
    
    def disable_target(self, target_type: ScrapingTargetType) -> None:
        """Disable a specific target type for this session."""
        if target_type in self.target_configs:
            self.target_configs[target_type]["enabled"] = False
            # If only one target remains enabled, update target_type
            enabled_targets = [t for t, c in self.target_configs.items() if c["enabled"]]
            if len(enabled_targets) == 1:
                self.target_type = enabled_targets[0]
            self.updated_at = datetime.now().isoformat()
    
    def get_entries_by_type(self, content_type: Optional[str] = None) -> List[Dict]:
        """Get entries filtered by content type."""
        if not content_type:
            return self.entries
        return [e for e in self.entries if e.get("content_type") == content_type]
    
    def to_dict(self) -> Dict:
        """Convert session to dictionary format."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "target_type": self.target_type.value,
            "content_type": self.content_type.value,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "metadata": self.metadata,
            "entries": self.entries,
            "status": self.status,
            "target_configs": {k.value: v for k, v in self.target_configs.items()}
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> "ScrapingSession":
        """Create session from dictionary format."""
        session = cls(
            name=data["name"],
            description=data.get("description"),
            target_type=ScrapingTargetType(data["target_type"]),
            content_type=ScrapingContentType(data["content_type"]),
            metadata=data.get("metadata", {})
        )
        session.id = data["id"]
        session.created_at = data["created_at"]
        session.updated_at = data["updated_at"]
        session.entries = data["entries"]
        session.status = data["status"]
        
        # Restore target configs
        for target_type, config in data["target_configs"].items():
            session.target_configs[ScrapingTargetType(target_type)] = config
        
        return session 