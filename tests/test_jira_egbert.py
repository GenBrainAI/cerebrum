import requests
from fastapi.testclient import TestClient

from src.server.controllers.jira import JiraTicketHandler, JiraConfig


def test_jira(client: TestClient):
    # Create tasksmanager
    tasksmanager_data = {
        "name": "Astronomy Expert",
        "model": "gpt-4",
        "description": "TasksManager for astronomy research",
    }

    tasksmanager_response = requests.post("http://localhost:8080/tasksmanager", json=tasksmanager_data)
    assert tasksmanager_response.status_code == 201
    tasksmanager_id = tasksmanager_response.json()["id"]

    task_data = {"name": "Test Task", "description": "Test Task Description", "taskmanager_id": tasksmanager_id}
    task_response = requests.post("http://localhost:8080/task", json=task_data)
    assert task_response.status_code == 201

    task_id = task_response.json()["id"]

    ticket_handler = JiraTicketHandler(JiraConfig(
        jira_api_token="ATATT3xFfGF0ZenxOvcLAnH-r-DbF7JHTxOV1uQfWkUyD77od9jPXSF-VZl6QZHJJ3800oZG2IKJ-SahvE67Vw1yOYoG2feQu-qxFzIyRRPza05xv_DUdFWq_G_1BgWRd9laAM1zLt93ceJR_fMYP5-k2VGidJAWz7EA0Mrv3WUXNx-ZBSKcm74=D2372521",
        project_key="CER",
        tag="",
        team="",
        task_id=task_id,
        tasksmanager_id=tasksmanager_id,
        jira_username="egbert@genbrain.ai",
        jira_url="https://genbrain-ai.atlassian.net",
        schedule_interval=0,
    ))

    tickets = ticket_handler.fetch_new_tickets()
    print(tickets)
