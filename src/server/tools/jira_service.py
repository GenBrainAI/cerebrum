import requests
from requests.auth import HTTPBasicAuth
from typing import List, Dict

class JiraService:
    def __init__(self, jira_url: str, username: str, api_token: str):
        self.jira_url = jira_url
        self.auth = HTTPBasicAuth(username, api_token)
        self.headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        }

    def fetch_tickets(self, project_key: str, max_results: int = 50) -> List[Dict]:
        jql_query = f'project = {project_key} ORDER BY created DESC'
        url = f'{self.jira_url}/rest/api/2/search'
        payload = {
            'jql': jql_query,
            'maxResults': max_results,
            'fields': ['summary', 'status', 'assignee', 'created', 'updated']
        }
        response = requests.post(url, headers=self.headers, auth=self.auth, json=payload)
        response.raise_for_status()
        return response.json().get('issues', [])

    def update_ticket_status(self, ticket_id: str, status: str) -> bool:
        url = f'{self.jira_url}/rest/api/2/issue/{ticket_id}/transitions'
        transitions_response = requests.get(url, headers=self.headers, auth=self.auth)
        transitions_response.raise_for_status()
        transitions = transitions_response.json()['transitions']
        
        for transition in transitions:
            if transition['to']['name'].lower() == status.lower():
                transition_id = transition['id']
                payload = {'transition': {'id': transition_id}}
                response = requests.post(url, headers=self.headers, auth=self.auth, json=payload)
                response.raise_for_status()
                return True
        return False