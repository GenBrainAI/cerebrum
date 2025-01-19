from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock, AsyncMock
import httpx
import pytest
import asyncio
from typing import AsyncGenerator, Generator

from src.server.main import app
from src.server.models.message import Message
from src.server.utils.task_utils import find_file
from src.server.persistence.persistence_model_factory import PersistenceModelFactory

client = TestClient(app)

@pytest.fixture(autouse=True)
async def setup_teardown() -> AsyncGenerator[None, None]:
    """Setup and teardown for each test."""
    # Setup
    PersistenceModelFactory.reset()
    
    yield
    
    # Teardown
    PersistenceModelFactory.reset()
    await asyncio.sleep(0)  # Allow any pending tasks to complete

@pytest.fixture
def mock_httpx_client() -> Generator[MagicMock, None, None]:
    """Mock httpx client for API calls."""
    with patch('httpx.AsyncClient') as mock:
        mock_client = AsyncMock()
        mock.return_value.__aenter__.return_value = mock_client
        yield mock

@pytest.mark.unit
@pytest.mark.asyncio
async def test_create_toolset_with_swagger_string():
    """Test creating a toolset with swagger string."""
    with open(find_file("tests/calculator/calculator.yaml"), "r") as file:
        swagger_string = file.read()

    toolset_data = {
        "name": ("", "Calculator API"),
        "description": ("", "Provides basic calculator functionalities"),
        "credentials": ("", '{"auth_type":"Baerer","auth_key":"123"}'),
        "swagger_str": ("", swagger_string)
    }

    async with httpx.AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.post("/toolsets", files=toolset_data)
        assert response.status_code == 201
        data = response.json()
        assert "id" in data
        assert data["name"] == "Calculator API"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_run_task_with_calculator(mock_httpx_client):
    """Test running a task with calculator toolset."""
    with open(find_file("tests/calculator/complex_calc.yml"), "r") as file:
        swagger_string = file.read()

    toolset_data = {
        "name": ("", "ComplexNumbersCalculator"),
        "description": ("", "Provides Complex Numbers calculator functionalities"),
        "credentials": ("", '{"auth_type":"Baerer","auth_key":"123"}'),
        "swagger_str": ("", swagger_string)
    }

    # Get the mock client instance
    mock_client = mock_httpx_client.return_value.__aenter__.return_value

    # Set up mock responses for the API endpoints
    responses = [
        # First set of responses for the setup calls
        httpx.Response(201, json={"id": "test-toolset-id", "name": "ComplexNumbersCalculator"}),  # toolset creation
        httpx.Response(201, json={"id": "test-manager-id"}),  # tasksmanager creation
        httpx.Response(201, json={"id": "test-task-id"}),  # task creation
    ]

    async def mock_post(*args, **kwargs):
        # Debug print for each API call
        url = kwargs.get('url', args[0] if args else 'N/A')
        print(f"\nAPI Call - URL: {url}")
        print(f"Headers: {kwargs.get('headers', {})}")
        print(f"JSON: {kwargs.get('json', {})}")

        # Match responses based on URL
        if 'complex/add' in str(url):
            response = httpx.Response(200, json={"result": {'real': 4, 'imag': 6}})
        elif '/run' in str(url):
            response = httpx.Response(200, json={"response": "The sum of the complex numbers 1+2i and 3+4i is 4+6i."})
        else:
            response = responses.pop(0) if responses else httpx.Response(404, json={"error": "No more mock responses"})

        print(f"Response: {response.json()}")
        return response

    # Set up the mock client
    mock_client.post = AsyncMock(side_effect=mock_post)

    async with httpx.AsyncClient(app=app, base_url="http://test") as ac:
        # Create toolset
        response = await ac.post("/toolsets", files=toolset_data)
        assert response.status_code == 201
        toolset_id = response.json()["id"]

        # Create tasks manager
        response = await ac.post(f"/toolsets/{toolset_id}/tasksmanager")
        assert response.status_code == 201
        manager_id = response.json()["id"]

        # Create task
        task_data = {
            "messages": [
                {
                    "role": "system",
                    "content": "You are a helpful assistant that uses a calculator to perform complex number arithmetic."
                }
            ],
            "user_input": "Add the complex numbers 1+2i and 3+4i"
        }
        response = await ac.post(f"/tasksmanager/{manager_id}/tasks", json=task_data)
        assert response.status_code == 201
        task_id = response.json()["id"]

        # Run task
        response = await ac.post(f"/tasks/{task_id}/run")
        assert response.status_code == 200
        response_data = response.json()
        assert response_data["response"] == "The sum of the complex numbers 1+2i and 3+4i is 4+6i."


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_tasksmanager_toolsets():
    """Test getting toolsets for a tasksmanager."""
    with open(find_file("tests/calculator/calculator.yaml"), "r") as file:
        swagger_string = file.read()

    toolset_data = {
        "name": ("", "Complex Numbers Calculator API"),
        "description": ("", "Provides Complex Numbers calculator functionalities"),
        "credentials": ("", '{"auth_type":"Baerer","auth_key":"123"}'),
        "swagger_str": ("", swagger_string)
    }

    async with httpx.AsyncClient(app=app, base_url="http://test") as ac:
        # Create toolset
        response = await ac.post("/toolsets", files=toolset_data)
        assert response.status_code == 201
        data = response.json()
        assert "id" in data
        toolset_id = data["id"]

        # Create tasksmanager
        tasksmanager_data = {
            "name": "Test TasksManager",
            "model": "Test Model",
            "description": "A test tasksmanager",
            "toolsets": [toolset_id]
        }
        tasksmanager_response = await ac.post("/tasksmanager", json=tasksmanager_data)
        assert tasksmanager_response.status_code == 201
        tasksmanager_id = tasksmanager_response.json()["id"]

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
        task_response = await ac.post("/task", json=task_data)
        assert task_response.status_code == 201

        # Fetch toolsets by id
        response = await ac.get(f"/toolsets/{toolset_id}")
        assert response.status_code == 200
        data = response.json()

        # Validate the response contains the created toolset
        assert data['id'] == toolset_id, "toolset not found"
