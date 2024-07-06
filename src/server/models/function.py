from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List, Union
from datetime import datetime
from .toolset_credentials import ToolsetCredentials

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

ResolvedSchema.update_forward_refs()

class ParameterSchema(BaseModel):
    name: Optional[str] = None
    in_: Optional[str] = Field(None, alias='in')
    description: Optional[str] = None
    required: Optional[bool] = None
    schema: ResolvedSchema

class ResponseContent(BaseModel):
    description: str
    content: Dict[str, Dict[str, ResolvedSchema]]

class Function(BaseModel):
    id: Optional[str] = None
    name: str
    url: str
    method: str
    description: str
    info: Info
    servers: List[ServerInfo]
    parameters: Optional[Dict[str, Union[Dict[str, ParameterSchema], ResolvedSchema]]]
    responses: Optional[Dict[str, ResponseContent]]
    credentials: Optional[ToolsetCredentials] = None
    toolsetId: Optional[str] = None
    created_at: Optional[datetime] = Field(default=None)
    updated_at: Optional[datetime] = Field(default=None)

class Tool(BaseModel):
    id: Optional[str] = Field(alias="id", default=None)
    function: Function
    type: str = Field(alias="type", default="function")
    created_at: Optional[datetime] = Field(alias="created_at", default=None)
    updated_at: Optional[datetime] = Field(alias="updated_at", default=None)