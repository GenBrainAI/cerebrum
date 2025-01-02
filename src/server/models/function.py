from __future__ import annotations
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from .schema import ServerInfo, Info, ResolvedSchema, ParameterSchema, ResponseContent

class Function(BaseModel):
    """Function model for tool definitions"""
    name: str
    description: Optional[str] = None
    parameters: Dict[str, Dict[str, ParameterSchema]] = Field(default_factory=dict)
    responses: Dict[str, ResponseContent] = Field(default_factory=dict)
    credentials: Optional[Dict[str, Any]] = None
    toolsetId: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    url: Optional[str] = None
    method: Optional[str] = None
    servers: List[ServerInfo] = Field(default_factory=list)

    model_config = {
        "populate_by_name": True,
        "validate_assignment": True,
        "protected_namespaces": (),
        "arbitrary_types_allowed": True,
        "json_encoders": {
            datetime: lambda v: v.isoformat() if v else None
        }
    }

    def model_dump(self, **kwargs) -> Dict[str, Any]:
        """Custom model dump to handle datetime serialization"""
        data = super().model_dump(**kwargs)
        # Handle datetime fields
        if self.created_at:
            data["created_at"] = self.created_at.isoformat()
        if self.updated_at:
            data["updated_at"] = self.updated_at.isoformat()
        return data

    @classmethod
    def model_validate(cls, obj: Dict[str, Any]) -> Function:
        """Custom validation to handle datetime parsing"""
        if isinstance(obj, str):
            # If obj is a string, treat it as the function name
            return cls(name=obj)
        
        if not isinstance(obj, dict):
            raise ValueError(f"Expected dict or str, got {type(obj)}")
        
        # Parse datetime fields if they exist
        for field in ["created_at", "updated_at"]:
            if field in obj and isinstance(obj[field], str):
                try:
                    obj[field] = datetime.fromisoformat(obj[field])
                except (ValueError, TypeError):
                    obj[field] = None
        
        return super().model_validate(obj)

class OpenAPIFunction(Function):
    """OpenAPI-specific function model"""
    url: str
    method: str
    info: Info
    servers: List[ServerInfo]
    parameters: Optional[Dict[str, Dict[str, ParameterSchema]]] = None
    responses: Optional[Dict[str, ResponseContent]] = None

    model_config = {
        "populate_by_name": True,
        "validate_assignment": True,
        "protected_namespaces": (),
        "arbitrary_types_allowed": True,
        "json_encoders": {
            datetime: lambda v: v.isoformat() if v else None
        }
    }