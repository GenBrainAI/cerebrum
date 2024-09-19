import pytest
from src.server.main import app
from starlette.testclient import TestClient
from src.server.models.persistence_models import StorageLocation, StorageType
from src.server.utils.task_utils import find_file

client = TestClient(app)

def test_create_entities_and_serialize_deserialize():
    # Define where the state will be saved (local file system for simplicity)
    local_storage = StorageLocation(type=StorageType.file, location="/tmp", state_name="test_state.json")

    bot_response = client.post("/tasksmanager", json={"name": "Test TasksManager"})
    assert bot_response.status_code == 201
    bot_id = bot_response.json()["id"]
    
    with open(find_file("tests/calculator/calculator.yaml"), "r") as file:
        swagger_string = file.read()

    toolset_data = {
        "name": ("", "Complex Numbers Calculator API"),
        "description": ("", "Provides Complex Numbers calculator functionalities"),
        "credentials": ("", '{"auth_type":"Baerer","auth_key":"123"}'),
        "swagger_str": ("", swagger_string)
    }

    toolset_response = client.post("/toolsets", files=toolset_data)
    assert toolset_response.status_code == 201
    toolset_id = toolset_response.json()["id"]

    task_response = client.post("/task", json={"name": "Test Task", "toolsets": [toolset_id]})
    assert task_response.status_code == 201
    task_id = task_response.json()["id"]

    # Serialize to JSON
    response = client.post("/state/save", json=local_storage.dict())
    assert response.status_code == 201

    # Deserialize from JSON
    response = client.post("/state/load", json={
        "location": local_storage.location, 
        "type": local_storage.type.value,
        "state_name": local_storage.state_name, 
        "return_as_json": True
    })
    assert response.status_code == 201

    loaded_bot_response = client.get(f"/tasksmanager/{bot_id}")
    assert loaded_bot_response.status_code == 200
    assert loaded_bot_response.json()['id'] == bot_id

    loaded_toolset_response = client.get(f"/toolsets/{toolset_id}")
    assert loaded_toolset_response.status_code == 200
    assert loaded_toolset_response.json()['id'] == toolset_id

    loaded_task_response = client.get(f"/task/{task_id}")
    assert loaded_task_response.status_code == 200
    assert loaded_task_response.json()['id'] == task_id