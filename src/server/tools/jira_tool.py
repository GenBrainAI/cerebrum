import json

from fastapi import requests
from requests.auth import HTTPBasicAuth

from src.server.controllers.jira import JiraConfig


class JiraTool:

    def __init__(self, config: JiraConfig):
        self.config = config
        if self.config.jira_api_token is None:
            raise ValueError("Jira API token cannot be None")
        if self.config.jira_url is None:
            raise ValueError("Jira URL cannot be None")

        self.jql_query = f'project = {self.config.project_key} AND labels = {self.config.tag} ORDER BY created DESC'

    def fetch_new_tickets(self):
        headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        }

        payload = {
            'jql': self.jql_query,
            'maxResults': 50,
            'fields': ['summary', 'status', 'assignee', 'created', 'updated']
        }

        response = requests.post(
            f'{self.config.jira_url}/rest/api/2/search',
            headers=headers,
            auth=HTTPBasicAuth(self.config.jira_username, self.config.jira_api_token),
            data=json.dumps(payload)
        )

        if response.status_code == 200:
            issues = response.json().get('issues', [])
            for issue in issues:
                self.process_ticket(issue)
        else:
            print(f"Failed to fetch issues. Status Code: {response.status_code}")
            print(f"Response: {response.text}")

    async def fetch_new_tickets(self):
        pass

    async def update_ticket_status(self, ticket_id, status):
        pass

