from pydantic import BaseModel, Field
from typing import Optional, List, Dict
from .message import Message

class RunTask(BaseModel):
    caller_id: Optional[str] = Field(None, description="Caller ID")
    messages: Optional[List[Message]] = Field(None, description="Array of messages")
    running_extra_params: Optional[Dict] = Field({}, description="Dict of running configuration")
    task_config: Optional[Dict] = Field({}, description="Dict of task configuration")