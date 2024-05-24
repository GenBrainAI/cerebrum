from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import date, datetime

class ToolModel(BaseModel):
    name: str
    description: str

class AgentModel(BaseModel):
    role: str
    goal: str
    backstory: str
    tools: List[ToolModel]

class TaskModel(BaseModel):
    description: str
    expected_output: str
    agent_role: str

class CreateCrewRequest(BaseModel):
    company_description: str
    company_domain: str
    hiring_needs: str
    specific_benefits: str
    agents: List[AgentModel]
    tasks: List[TaskModel]

class CrewInfo(BaseModel):
    id: Optional[str] = Field(alias="id", default=None)
    crew_info: Optional[CreateCrewRequest]  = Field(alias="crew_info", default=None)
    created_at: Optional[datetime] = Field(alias="created_at", default=None)
    updated_at: Optional[datetime] = Field(alias="updated_at", default=None)
