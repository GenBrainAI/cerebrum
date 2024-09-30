from fastapi.testclient import TestClient
from src.server.models.message import Message
from src.server.models.agent import CreateCrewRequest, AgentModel, TaskModel
from src.server.utils.task_utils import find_file
from src.server.controllers.curried_proxy import CurriedProxy
import json

def test_crew_to_github_readme(client: TestClient):
    # Create tasksmanager
    tasksmanager_data = {
        "name": "GitHub Updater",
        "model": "gpt-4",
        "description": "TasksManager for GitHub operations",
    }
    tasksmanager_response = client.post("/tasksmanager", json=tasksmanager_data)
    assert tasksmanager_response.status_code == 201
    tasksmanager_id = tasksmanager_response.json()["id"]

    # Create CrewAI configuration
    crew_config = {
        "company_description": "GenBrain.ai Cerebrum Component",
        "company_domain": "genbrain.ai",
        "hiring_needs": "GitHub Operations Specialist",
        "specific_benefits": "Continuous learning and self-enhancement",
        "agents": [
            {
                "role": "GitHub Updater",
                "goal": "Update the README.md file in the GitHub repository with a 'hello github' message",
                "backstory": "You are an AI agent specializing in GitHub operations. Your task is to modify the README.md file in the specified repository, adding a 'hello github' message, and then commit these changes.",
                "verbose": True,
                "tools": [
                    {
                        "name": "GithubTool",
                        "description": "Tool for interacting with GitHub repositories"
                    }
                ]
            }
        ],
        "tasks": [
            {
                "description": "Add 'hello github' to the README.md file and commit the changes to the GitHub repository",
                "expected_output": "Confirmation that the README.md file has been updated and the changes have been committed to the repository",
                "agent_role": "GitHub Updater"
            }
        ]
    }

    # Create CrewAI configuration
    crew_response = client.post("/agent/crewai", json=crew_config)
    assert crew_response.status_code == 200
    crew_id = crew_response.json()["crew_id"]["id"]
    curried_proxy_id = crew_response.json()["curried_proxy_id"]

    # Create task
    task_data = {
        "name": "Update GitHub README",
        "description": "Add 'hello github' to the README.md file and commit the changes",
        "tasksmanager_id": tasksmanager_id,
        "crewai_info_id": crew_id,
        "curried_proxy_id": curried_proxy_id,
        "messages": [
            {
                "role": "system",
                "content": "You are an AI agent specializing in GitHub operations. Your task is to modify the README.md file in the specified repository, adding a 'hello github' message, and then commit these changes."
            }
        ]
    }

    task_response = client.post("/task", json=task_data)
    assert task_response.status_code == 201
    task_id = task_response.json()["id"]

    # Run task to update README
    run_task = {
        'caller_id': "UnitTestCaller",
        'messages': [
            {
                "role": "user",
                "content": "Please add 'hello github' to the README.md file in the GenBrainAI/cerebrum repository and commit the changes."
            }
        ]
    }
    run_response = client.post(f"/task/{tasksmanager_id}/{task_id}/run", json=run_task)
    assert run_response.status_code == 200

    # Verify the response
    response_content = run_response.json()['response']
    assert "README.md file has been updated" in response_content, "Failed to update README.md file"
    assert "Changes have been committed" in response_content, "Failed to commit changes"

    # Optionally, run another task to verify the changes
    verify_task = {
        'caller_id': "UnitTestCaller",
        'messages': [
            {
                "role": "user",
                "content": "Please check if 'hello github' is present in the README.md file of the GenBrainAI/cerebrum repository."
            }
        ]
    }
    verify_response = client.post(f"/task/{tasksmanager_id}/{task_id}/run", json=verify_task)
    assert verify_response.status_code == 200

    # Verify the verification response
    verify_content = verify_response.json()['response']
    assert "hello github" in verify_content, "The 'hello github' message was not found in README.md"