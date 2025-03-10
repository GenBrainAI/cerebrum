from enum import Enum
from typing import Dict, Any, Optional
from dataclasses import dataclass

class ViewType(Enum):
    """Enum for different view types."""
    TASK_HIERARCHY = "task_hierarchy"
    TOOLS_CATALOG = "tools_catalog"
    AGENTIC_CONFIG = "agentic_config"
    TASK_MANAGEMENT = "task_management"
    CHAT = "chat"

@dataclass
class ViewMetadata:
    title: str
    description: str
    task_id: Optional[str] = None
    manager_id: Optional[str] = None
