from __future__ import annotations
from typing import Dict, List, Optional
from pydantic import BaseModel, Field

class ServerInfo(BaseModel):
    url: str

class Info(BaseModel):
    title: str
    version: str
    description: Optional[str] = None

class ResolvedSchema(BaseModel):
    type: Optional[str] = None
    properties: Optional[Dict[str, 'ResolvedSchema']] = None
    items: Optional['ResolvedSchema'] = None
    description: Optional[str] = None
    required: Optional[List[str]] = None

    model_config = {
        "populate_by_name": True,
        "validate_assignment": True,
        "protected_namespaces": (),
        "arbitrary_types_allowed": True
    }

class ParameterSchema(BaseModel):
    name: Optional[str] = None
    in_: Optional[str] = Field(None, alias='in')
    description: Optional[str] = None
    required: Optional[bool] = None
    param_schema: ResolvedSchema = Field(alias='schema')

    model_config = {
        "populate_by_name": True,
        "validate_assignment": True,
        "protected_namespaces": (),
        "arbitrary_types_allowed": True
    }

class ResponseContent(BaseModel):
    description: str
    content: Dict[str, Dict[str, ResolvedSchema]]

    model_config = {
        "populate_by_name": True,
        "validate_assignment": True,
        "protected_namespaces": (),
        "arbitrary_types_allowed": True
    } 