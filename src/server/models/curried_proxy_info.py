from uuid import UUID, uuid4
from typing import Dict, List, Any, Optional
from pydantic import BaseModel, Field

class ToolInfo(BaseModel):
    """Simplified representation of a tool for serialization"""
    name: str
    type: str  # 'tool', 'function', 'class_method', 'crewai'
    tool_data: Dict[str, Any]  # Serializable tool data

class CurriedProxyInfo(BaseModel):
    """Sidecar model for storing CurriedProxy data"""
    id: UUID = Field(default_factory=uuid4)
    tools: List[ToolInfo] = Field(default_factory=list)
    name_counter: Dict[str, int] = Field(default_factory=dict)

    class Config:
        arbitrary_types_allowed = True
