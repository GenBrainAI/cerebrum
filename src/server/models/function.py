from pydantic import BaseModel, Field
from typing import Optional
from .toolset_credentials import ToolsetCredentials
from datetime import date, datetime


class Function(BaseModel):
    id: Optional[str] = None
    name: str 
    openapi: Optional[str] = None 
    url: Optional[str ] = None
    method: Optional[str] = None
    description: str
    credentials: Optional[ToolsetCredentials] = None 
    created_at: Optional[datetime] = Field(alias="created_at", default=None)
    updated_at: Optional[datetime] = Field(alias="updated_at", default=None)
