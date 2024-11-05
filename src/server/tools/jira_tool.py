from os import getenv
from dotenv import load_dotenv
from src.server.controllers.jira_controller import JiraController
from src.server.models.jira_config import JiraConfig
from src.server.tools.jira_service import JiraService

def fetch_jira_tickets(project_key: str = "DSO"):
    load_dotenv()  # Load environment variables from .env file
    
    config = JiraConfig(
        project_key=project_key,
        jira_url=getenv('JIRA_URL', 'https://genbrainai.atlassian.net'),
        jira_username=getenv('JIRA_USERNAME'),
        jira_api_token=getenv('JIRA_API_TOKEN'),
        task_id="",
        schedule_interval=0,
    )
    jira_service = JiraService(config.jira_url, config.jira_username, config.jira_api_token)
    controller = JiraController(config, jira_service)

    tickets = controller.fetch_new_tickets()
    
    # Transform tickets to match the expected format
    return [{'fields': {'summary': ticket.get('fields', {}).get('summary', '')}} for ticket in tickets]

class JiraTool:
    name: str = "JiraTool"
    description: str = "A tool to fetch Jira tickets"

    def _run(self, project_key: str = "CER"):
        return fetch_jira_tickets(project_key)