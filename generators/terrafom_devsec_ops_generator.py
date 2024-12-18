import json
import requests
from typing import Dict, Any

# Usage:
# generator = TerrafomDevSecOpsGenerator(
#     config_path="path/to/config.json",
#     base_url="http://localhost:8080",  # Or wherever your Cerebrum API is hosted
#     jira_url="https://your-jira-instance.atlassian.net",
#     jira_username="your-username",
#     jira_api_token="your-api-token",
#     github_token="your-github-token",
#     github_repo="your-org/your-repo"
# )

# await generator.setup()
# result = await generator.run()


class TerrafomDevSecOpsGenerator:
    def __init__(self, config_path: str, base_url: str, jira_url: str, jira_username: str, jira_api_token: str, github_token: str, github_repo: str):
        with open(config_path, 'r') as config_file:
            self.config = json.load(config_file)

        self.base_url = base_url
        self.config_path = config_path
        self.crew_id = None
        self.task_id = None
        self.tasksmanager_id = None
        self.jira_url = jira_url
        self.jira_username = jira_username
        self.jira_api_token = jira_api_token
        self.github_token = github_token
        self.github_repo = github_repo

    async def setup(self):
        # Create crew using the agent API
        crew_response = requests.post(f"{self.base_url}/agent/crewai", json=self.config)
        crew_response.raise_for_status()
        crew_data = crew_response.json()
        self.crew_id = crew_data['crew_id']['id']
        self.curried_proxy_id = crew_data['curried_proxy_id']

        # Create tasksmanager
        tasksmanager_data = {
            "name": "DevOps Automation Manager",
            "model": "gpt-4",
            "description": "TasksManager for DevOps automation tasks",
        }
        tasksmanager_response = requests.post(f"{self.base_url}/tasksmanager", json=tasksmanager_data)
        tasksmanager_response.raise_for_status()
        self.tasksmanager_id = tasksmanager_response.json()["id"]

        # Create task
        task_data = {
            "name": "DevOps Automation",
            "description": "Automate DevOps tasks for microservices communication",
            "tasksmanager_id": self.tasksmanager_id,
            "crewai_config_id": self.crew_id,
            "curried_proxy_id": self.curried_proxy_id
        }
        task_response = requests.post(f"{self.base_url}/task", json=task_data)
        task_response.raise_for_status()
        self.task_id = task_response.json()["id"]

    async def run(self, additional_info: Dict[str, Any] = None):
        if not self.crew_id or not self.task_id:
            raise ValueError("Setup has not been completed. Call setup() first.")

        run_task_body = {
            'caller_id': "DevOpsAutomation",
            'messages': [],  # Add any necessary messages here
            'running_extra_params': additional_info or {}
        }

        response = requests.post(f"{self.base_url}/task/{self.tasksmanager_id}/{self.task_id}/run", json=run_task_body)
        response.raise_for_status()
        return response.json()['response']

    def save_state(self) -> Dict[str, Any]:
        return {
            'config_path': self.config_path,
            'base_url': self.base_url,
            'jira_url': self.jira_url,
            'jira_username': self.jira_username,
            'jira_api_token': self.jira_api_token,
            'github_token': self.github_token,
            'github_repo': self.github_repo,
            'crew_id': self.crew_id,
            'task_id': self.task_id,
            'tasksmanager_id': self.tasksmanager_id,
            'curried_proxy_id': self.curried_proxy_id
        }

    @classmethod
    def load_from_state(cls, state_data: Dict[str, Any]):
        instance = cls(
            config_path=state_data['config_path'],
            base_url=state_data['base_url'],
            jira_url=state_data['jira_url'],
            jira_username=state_data['jira_username'],
            jira_api_token=state_data['jira_api_token'],
            github_token=state_data['github_token'],
            github_repo=state_data['github_repo']
        )
        instance.crew_id = state_data['crew_id']
        instance.task_id = state_data['task_id']
        instance.tasksmanager_id = state_data['tasksmanager_id']
        instance.curried_proxy_id = state_data.get('curried_proxy_id')
        return instance