"""
Base model for all Cerebrum models.
"""

from uuid import UUID, uuid4
from datetime import datetime
from typing import Optional
from pydantic import BaseModel as PydanticBaseModel, Field, ConfigDict

class BaseModel(PydanticBaseModel):
    """Base model for all Cerebrum models."""
    
    id: UUID = Field(default_factory=uuid4)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    
    model_config = ConfigDict(arbitrary_types_allowed=True) 