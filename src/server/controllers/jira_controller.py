import requests
from ..models.jira_config import JiraConfig
from ..tools.jira_service import JiraService

class JiraController:
    name: str = "Jira Controller"
    description: str = "A controller to manage Jira tickets, process them, and integrate with other systems"

    def __init__(self, config: JiraConfig, jira_service: JiraService):
        self.config = config
        self.jira_service = jira_service

    def update_config(self, new_config: JiraConfig, new_jira_service: JiraService):
        self.config = new_config
        self.jira_service = new_jira_service

    def fetch_new_tickets(self):
        return self.jira_service.fetch_tickets(self.config.project_key)

    def process_ticket(self, ticket):
        ticket_id = ticket['id']
        ticket_key = ticket['key']

        # Set ticket status to 'In Progress'
        self.jira_service.update_ticket_status(ticket_id, 'In Progress')

        # Send ticket to task endpoint
        response = requests.post(f'http://localhost:8000/task/{self.config.task_id}/run', json=ticket)

        if response.status_code == 200:
            # Set ticket status to 'Done' if processing is successful
            self.jira_service.update_ticket_status(ticket_id, 'Done')
        else:
            print(f"Failed to process ticket {ticket_key}. Status Code: {response.status_code}")