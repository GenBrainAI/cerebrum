from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Any, Dict
from enum import Enum

# Storage backend abstractions
class StorageType(str, Enum):
    s3 = "s3"
    file = "file"
    postgres = "postgres"

class StorageLocation(BaseModel):
    type: StorageType = Field(..., description="Type of the storage")
    location: str = Field(..., description="Location like bucket path, filepath, or table name")
    state_name: str = Field(..., description="The name of the state to save or retrieve")
