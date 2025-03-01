import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from unittest.mock import MagicMock

from src.server.api.routes.task_tree_flow_association import router
from src.server.models.task import Task
from src.server.models.task_tree_flow import TaskTreeFlow
from src.server.persistence.dependencies import get_persistence_model

# Create a FastAPI app and include our router
app = FastAPI()
app.include_router(router)

@pytest.fixture
def mock_persistence_model():
    mock = MagicMock()
    
    # Mock task
    task = Task(
        id="task-123",
        name="Test Task",
        tasksmanager_id="manager-123",
        description="A test task",
        tree_flow_id=None
    )
    mock.tasks.read.return_value = task
    
    # Mock tree flow
    tree_flow = TaskTreeFlow(
        id="tree-flow-123",
        name="Test Tree Flow",
        description="A test tree flow",
        tasksmanager_id="manager-123",
        nodes={},
        roots=[]
    )
    mock_collection = MagicMock()
    mock_collection.read.return_value = tree_flow
    mock.collection.return_value = mock_collection
    
    return mock

@pytest.fixture
def client(mock_persistence_model):
    # Override the dependency
    app.dependency_overrides[get_persistence_model] = lambda: mock_persistence_model
    
    # Create a test client
    test_client = TestClient(app)
    
    # Yield the client for testing
    yield test_client
    
    # Clean up after the test
    app.dependency_overrides = {}

def test_associate_task_with_tree_flow(client, mock_persistence_model):
    response = client.post("/manager-123/task/task-123/associate_tree_flow/tree-flow-123")
    
    assert response.status_code == 200
    assert response.json() == {
        "message": "Task task-123 associated with tree flow tree-flow-123",
        "task_id": "task-123",
        "tree_flow_id": "tree-flow-123"
    }
    
    # Verify the task was updated
    mock_persistence_model.tasks.update.assert_called_once()
    updated_task = mock_persistence_model.tasks.update.call_args[0][1]
    assert updated_task.tree_flow_id == "tree-flow-123"

def test_disassociate_task_from_tree_flow(client, mock_persistence_model):
    # Set the tree_flow_id for this test
    task = mock_persistence_model.tasks.read.return_value
    task.tree_flow_id = "tree-flow-123"
    
    response = client.post("/manager-123/task/task-123/disassociate_tree_flow")
    
    assert response.status_code == 200
    assert response.json() == {
        "message": "Task task-123 disassociated from tree flow tree-flow-123",
        "task_id": "task-123",
        "previous_tree_flow_id": "tree-flow-123"
    }
    
    # Verify the task was updated
    mock_persistence_model.tasks.update.assert_called_once()
    updated_task = mock_persistence_model.tasks.update.call_args[0][1]
    assert updated_task.tree_flow_id is None

def test_associate_task_not_found(client, mock_persistence_model):
    # Make the task not found
    mock_persistence_model.tasks.read.return_value = None
    
    response = client.post("/manager-123/task/task-123/associate_tree_flow/tree-flow-123")
    
    assert response.status_code == 404
    assert "not found" in response.json()["detail"]

def test_associate_tree_flow_not_found(client, mock_persistence_model):
    # Make the tree flow not found
    mock_persistence_model.collection.return_value.read.return_value = None
    
    response = client.post("/manager-123/task/task-123/associate_tree_flow/tree-flow-123")
    
    assert response.status_code == 404
    assert "not found" in response.json()["detail"] 