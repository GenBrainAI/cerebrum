from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
import httpx
import pytest

from src.server.main import app
from src.server.models.message import Message
from src.server.utils.task_utils import find_file

client = TestClient(app)

@pytest.mark.unit
def test_create_toolset_with_swagger_string():
    with open(find_file("tests/calculator/calculator.yaml"), "r") as file:
        swagger_string = file.read()

    toolset_data = {
        "name": ("", "Calculator API"),
        "description": ("", "Provides basic calculator functionalities"),
        "credentials": ("", '{"auth_type":"Baerer","auth_key":"123"}'),
        "swagger_str": ("", swagger_string)
    }

    response = client.post("/toolsets", files=toolset_data)
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["name"] == "Calculator API"


@pytest.mark.unit
def test_run_task_with_calculator():
    with open(find_file("tests/calculator/complex_calc.yml"), "r") as file:
        swagger_string = file.read()

    toolset_data = {
        "name": ("", "Complex Numbers Calculator API"),
        "description": ("", "Provides Complex Numbers calculator functionalities"),
        "credentials": ("", '{"auth_type":"Baerer","auth_key":"123"}'),
        "swagger_str": ("", swagger_string)
    }

    response = client.post("/toolsets", files=toolset_data)
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    toolset_id = data["id"]

    # Create tasksmanager
    tasksmanager_data = {
        "name": "Complex Numbers Expert",
        "model": "gpt-4o-1106-preview",
        "description": "TasksManager for with complex numbers expertise",
    }

    tasksmanager_response = client.post("/tasksmanager", json=tasksmanager_data)
    assert tasksmanager_response.status_code == 201
    tasksmanager_id = tasksmanager_response.json()["id"]

    # Create a task that uses the calculator toolset
    # Create task
    system_message = Message(
        role="system",
        content="You are an complex numbers helper that call complex numbers calculator when ever you can."
    )
    task_data = {
        "name": "Add complex numbers",
        "description": "Adds two complex numbers",
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
        content="Please add hose two complex numbers 1+2i and 3+4i"
    )

    mock_response = httpx.Response(200, json={"result": {'real': 4, 'imag': 6}})
    with patch('httpx.AsyncClient.post', return_value=mock_response) as mock_post:
        run_task = {
            'caller_id': "UnitTestCaller",
            'messages': [user_message.dict()]
        }
        run_response = client.post(f"/task/{tasksmanager_id}/{task_id}/run", json=run_task)
        assert run_response.status_code == 200
        response_data = run_response.json()
        assert "response" in response_data
        # assert response_data["response"] == "The sum of the complex numbers \\(1+2i\\) and \\(3+4i\\) is \\(4+6i\\)."

        mock_post.assert_called_once_with(
            url='http://example_complex_calculator.com/complex/add',
            params={},
            headers={"Content-Type": "application/json", "Accept": "*/*"},
            json={'num1': {'real': 1, 'imag': 2}, 'num2': {'real': 3, 'imag': 4}}
        )


@pytest.mark.unit
def test_get_tasksmanager_toolsets():
    with open(find_file("tests/calculator/calculator.yaml"), "r") as file:
        swagger_string = file.read()

    toolset_data = {
        "name": ("", "Complex Numbers Calculator API"),
        "description": ("", "Provides Complex Numbers calculator functionalities"),
        "credentials": ("", '{"auth_type":"Baerer","auth_key":"123"}'),
        "swagger_str": ("", swagger_string)
    }

    response = client.post("/toolsets", files=toolset_data)
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    toolset_id = data["id"]

    tasksmanager_data = {
        "name": "Test TasksManager",
        "model": "Test Model",
        "description": "A test tasksmanager",
        "toolsets": [toolset_id]
    }
    tasksmanager_response = client.post("/tasksmanager", json=tasksmanager_data)
    assert tasksmanager_response.status_code == 201
    tasksmanager_id = tasksmanager_response.json()["id"]
    # Create a task that uses the calculator toolset
    # Create task
    system_message = Message(
        role="system",
        content="You are an complex numbers helper that call complex numbers calculator when ever you can."
    )
    task_data = {
        "name": "Add complex numbers",
        "description": "Adds two complex numbers",
        "tasksmanager_id": tasksmanager_id,
        "messages": [system_message.dict()],
        "toolsets": [toolset_id]
    }
    task_response = client.post("/task", json=task_data)
    assert task_response.status_code == 201

    # Fetch toolsets by id
    response = client.get(f"/toolsets/{toolset_id}")
    assert response.status_code == 200
    data = response.json()

    # Validate the response contains the created toolset
    assert data['id'] == toolset_id, "toolset not found"
