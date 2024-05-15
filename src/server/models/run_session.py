from typing import Any, Optional

from pydantic import BaseModel, Field
from enum import Enum

class TaskRunSession(BaseModel):
    task_id: str
    tasksmanager_id: str
    response: Optional[Any] = Field(None, description="Response from the task run")


class TasksManagerRunSession(BaseModel):
    tasksmanager_id: str

class TasksManagerTaskState(str, Enum):
    RUNNING = 'Running'
    PAUSED = 'Paused'
    STOPPED = 'Stopped'
    BREAKPOINT = 'Breakpoint'

class TasksManagerTaskSequenceState(BaseModel):
    tasksmanager_id: str
    current_task_id: str
    state: TasksManagerTaskState
    next_task_id: str = Field(None, description="The ID of the next task to be run, if any")
