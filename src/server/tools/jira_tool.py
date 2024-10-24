from src.server.controllers.jira_controller import JiraController
from src.server.models.jira_config import JiraConfig
from src.server.tools.jira_service import JiraService

def fetch_jira_tickets(project_key: str = "CER"):
    config = JiraConfig(
        project_key=project_key,
        jira_url="https://genbrain-ai.atlassian.net",
        jira_username="egbert@genbrain.ai",
        jira_api_token="ATATT3xFfGF0ZenxOvcLAnH-r-DbF7JHTxOV1uQfWkUyD77od9jPXSF-VZl6QZHJJ3800oZG2IKJ-SahvE67Vw1yOYoG2feQu-qxFzIyRRPza05xv_DUdFWq_G_1BgWRd9laAM1zLt93ceJR_fMYP5-k2VGidJAWz7EA0Mrv3WUXNx-ZBSKcm74=D2372521",
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