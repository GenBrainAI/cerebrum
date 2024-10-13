from pydantic import BaseModel

class GitHubConfig(BaseModel):
    access_token: str
    repo_name: str