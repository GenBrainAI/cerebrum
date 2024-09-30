import os
import tempfile
from fastapi.testclient import TestClient

from src.server.controllers.jira import JiraTicketHandler, JiraConfig
from src.server.models.message import Message

temp_dir = tempfile.gettempdir()
constructed_crew = {
    "agents": [
        {
            "role": "Technical writer",
            "verbose": True,
            "goal": "You need to add information to the Readme.md file according to the instructions you get from the ticket description",
            "backstory": "You are a software developer that adds information to Readme.md files and solves the tickets using github tools provided",
            "class_tools": [
                {"name": "GitHubTool", "description": "Tool for changing files on github repository"},
            ],
            "tools": [
                {"name": "save_file", "description": "Tool for storing local files"},
            ],
        }
    ],
    "tasks": [
        {
            "description": "You need to add information to the Readme.md file according to the instructions you get from the ticket description",
            "expected_output": f"add the text 'hello world' to the Readme.md file first line and commit it to the github repo GenBrainAI/cerebrum",
            "agent_role": "Technical writer"
        },
    ]
}

def test_jira(client: TestClient):
    response = client.post("/agent/crewai", json=constructed_crew)
    assert response.status_code == 200
    crewai_response = response.json()
    # print(crewai_response)

    tasksmanager_data = {
        "name": "File expert",
        "model": "gpt-4",
        "description": "make files",
    }

    tasksmanager_response = client.post("/tasksmanager", json=tasksmanager_data)
    assert tasksmanager_response.status_code == 201
    tasksmanager_id = tasksmanager_response.json()["id"]

    # Create task
    system_message = Message(
        role="system",
        content="You create new files based on input"
    )

    task_data = {
        "name": "Readme updated",
        "description": "Update the Readme.md file with the information provided",
        "tasksmanager_id": tasksmanager_id,
        "messages": [system_message.model_dump()],
        "crewai_info_id": crewai_response['crew_id']['id'],
        "curried_proxy_id": crewai_response['curried_proxy_id'],
    }

    task_response = client.post("/task", json=task_data)
    assert task_response.status_code == 201
    task_id = task_response.json()["id"]

    # Run task with user message
    user_message = Message(
        role="user",
        content=f"write the first line of the Readme.md file, write hello world and commit it to github"
    )

    run_task = {
        'caller_id': "UnitTestCaller",
        'messages': [user_message.model_dump()]
    }

    run_task_response = client.post(f"/task/{tasksmanager_id}/{task_id}/run", json=run_task)
    assert run_task_response.status_code == 200
    print(run_task_response.json())
