from src.server.controllers.jira import JiraTicketHandler, JiraConfig


def fetch_jira_tickets(project_key: str = "CER"):
    ticket_handler = JiraTicketHandler(
        JiraConfig(
            jira_api_token="ATATT3xFfGF0ZenxOvcLAnH-r-DbF7JHTxOV1uQfWkUyD77od9jPXSF-VZl6QZHJJ3800oZG2IKJ-SahvE67Vw1yOYoG2feQu-qxFzIyRRPza05xv_DUdFWq_G_1BgWRd9laAM1zLt93ceJR_fMYP5-k2VGidJAWz7EA0Mrv3WUXNx-ZBSKcm74=D2372521",
            project_key=project_key,
            tag="",
            team="",
            task_id="",
            tasksmanager_id="",
            jira_username="egbert@genbrain.ai",
            jira_url="https://genbrain-ai.atlassian.net",
            schedule_interval=0,
        )
    )

    return ticket_handler.fetch_new_tickets()
