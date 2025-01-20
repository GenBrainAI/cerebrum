from typing import Dict, Any, Optional
from pydantic import BaseModel, Field

class AgentFrameworkConfig(BaseModel):
    """Configuration for agent framework plugins."""
    
    name: str = Field(..., description="Name of the agent framework")
    version: str = Field(..., description="Version of the agent framework")
    description: str = Field(..., description="Description of the agent framework")
    settings: Dict[str, Any] = Field(default_factory=dict, description="Framework-specific settings")
    enabled: bool = Field(default=True, description="Whether the framework is enabled")
    priority: int = Field(default=0, description="Priority for framework selection") 