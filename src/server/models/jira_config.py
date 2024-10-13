from pydantic import BaseModel, Field

class JiraConfig(BaseModel):
    project_key: str
    tag: str = ""
    team: str = ""
    jira_url: str
    jira_username: str
    jira_api_token: str
    task_id: str = ""
    schedule_interval: int = Field(default=60, ge=1, description="Schedule interval in minutes")
