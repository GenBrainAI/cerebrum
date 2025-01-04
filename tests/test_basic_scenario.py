from fastapi.testclient import TestClient
from src.server.models.message import Message
from src.server.utils.task_utils import find_file


def test_scenario(client: TestClient):
    # Read the content of the swagger YAML file
    with open(find_file("tests/calculator/calculator.yaml"), "r") as file:
        swagger_yaml_content = file.read()
    
    # Prepare toolset data for form submission
    toolset_data = {
        "name": ("", "Units Converter"),
        "description": ("", "API for unit conversions"),
        "credentials": ("", '{"auth_type":"Baerer","auth_key":"123"}'),
        "swagger_str": ("", swagger_yaml_content)
    }
    
    # Create toolset
    toolset_response = client.post("/toolsets", files=toolset_data)
    assert toolset_response.status_code == 201
    toolset_id = toolset_response.json()["id"]

    # Create tasksmanager
    tasksmanager_data = {
        "name": "Astronomy Expert",
        "model": "gpt-4o-mini",
        "description": "TasksManager for astronomy research",
    }
    tasksmanager_response = client.post("/tasksmanager", json=tasksmanager_data)
    assert tasksmanager_response.status_code == 201
    tasksmanager_id = tasksmanager_response.json()["id"]

    # Create task
    system_message = Message(
        role="system",
        content="You are an astronomy expert ready to answer questions about the solar system."
    )

    task_data = {
        "name": "Solar System Questions",
        "description": "Answer questions about the solar system",
        "tasksmanager_id": tasksmanager_id,
        "messages": [system_message.dict()],
        "toolsets": [toolset_id]
    }

    task_response = client.post("/task", json=task_data)
    assert task_response.status_code == 201
    task_id = task_response.json()["id"]

    # Run task with user message
    user_message = Message(
        role="user",
        content="What is the distance from Earth to the Moon in kilometers?"
    )
    run_task = {
        'caller_id': "UnitTestCaller",
        'messages': [user_message.dict()]
    }
    run_response = client.post(f"/task/{tasksmanager_id}/{task_id}/run", json=run_task)
    assert run_response.status_code == 200

    # Another use of this task 
    user_message = Message(
        role="user",
        content="What is the distance from Earth to the Sun in kilometers?"
    )
    run_task = {
        'caller_id': "UnitTestCaller",
        'messages': [user_message.dict()]
    }
    run_response = client.post(f"/task/{tasksmanager_id}/{task_id}/run", json=run_task)
    assert run_response.status_code == 200
