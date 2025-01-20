import pytest
from fastapi.testclient import TestClient
from src.server.models.message import Message
from src.server.utils.task_utils import find_file
from src.server.controllers.tasks_tree_controller import ExecutionStrategy
from src.server.tools.tools_catalog import tools_catalog
import httpx
from unittest.mock import AsyncMock, patch

@pytest.fixture(autouse=True)
def cleanup_tools():
    """Cleanup fixture that runs automatically before and after each test."""
    tools_catalog.reset()
    yield
    tools_catalog.reset()

@pytest.fixture
def mock_calculator_api():
    """Mock the calculator API responses."""
    with patch('httpx.AsyncClient') as mock_client:
        # Mock the calculator API endpoints
        async def mock_post(*args, **kwargs):
            url = str(kwargs.get('url', args[0] if args else ''))
            if 'complex/multiply' in url:
                return httpx.Response(200, json={
                    "result": {"real": 18, "imag": -1}  # (3 + 4i) * (2 - 3i)
                })
            elif 'complex/divide' in url:
                if '1+2i' in str(kwargs.get('json')):
                    return httpx.Response(200, json={
                        "result": {"real": 0.8, "imag": 0.6}  # (1 + 2i) / (2 + i)
                    })
                else:
                    return httpx.Response(200, json={
                        "result": {"real": 2.0, "imag": 1.0}  # (5 + 6i) / (2 + 2i)
                    })
            return httpx.Response(404)

        mock_client.return_value.__aenter__.return_value.post = AsyncMock(side_effect=mock_post)
        yield mock_client

def test_complex_calculator_tree(client: TestClient, mock_calculator_api):
    # Read the calculator swagger YAML for complex number operations
    with open(find_file("tests/calculator/complex_calc.yml"), "r") as file:
        swagger_yaml_content = file.read()
    
    # Create toolset with calculator API
    toolset_data = {
        "name": ("", "Complex Calculator"),
        "description": ("", "API for complex number calculations"),
        "credentials": ("", '{"auth_type":"Bearer","auth_key":"123"}'),
        "swagger_str": ("", swagger_yaml_content)
    }
    toolset_response = client.post("/toolsets", files=toolset_data)
    assert toolset_response.status_code == 201
    toolset_id = toolset_response.json()["id"]

    # Create tasksmanager for complex calculations
    tasksmanager_data = {
        "name": "Complex Math Expert",
        "description": "TasksManager for complex number calculations",
    }
    tasksmanager_response = client.post("/tasksmanager", json=tasksmanager_data)
    assert tasksmanager_response.status_code == 201
    tasksmanager_id = tasksmanager_response.json()["id"]

    # Create root task (Aggregator)
    root_task_data = {
        "name": "Complex Calculator Aggregator",
        "description": "Compare and aggregate complex calculation results",
        "tasksmanager_id": tasksmanager_id,
        "messages": [
            {
                "role": "system",
                "content": "Compare the calculation results and verify they match between calculators."
            }
        ],
        "toolsets": [toolset_id],
        "framework": "crewai",
        "create_crew": {
            "name": "Complex Calculator Crew",
            "description": "A crew for complex number calculations",
            "agents": [
                {
                    "role": "Calculator Aggregator",
                    "goal": "Compare and verify calculation results",
                    "backstory": "Expert in complex number calculations and result verification",
                    "tools": []
                }
            ]
        }
    }
    root_task_response = client.post("/task", json=root_task_data)
    assert root_task_response.status_code == 201
    root_task_id = root_task_response.json()["id"]

    # Create calculator tasks
    calc_tasks = []
    for i in range(2):
        calc_task_data = {
            "name": f"Complex Calculator {i}",
            "description": f"Perform complex calculations using method {i}",
            "tasksmanager_id": tasksmanager_id,
            "messages": [
                {
                    "role": "system",
                    "content": "Perform complex number calculations using the calculator API."
                }
            ],
            "toolsets": [toolset_id],
            "framework": "crewai",
            "create_crew": {
                "name": f"Calculator Crew {i}",
                "description": "A crew for performing complex number calculations",
                "agents": [
                    {
                        "role": f"Calculator {i}",
                        "goal": "Perform complex number calculations accurately",
                        "backstory": "Expert in complex number arithmetic and calculations",
                        "tools": []
                    }
                ]
            }
        }
        calc_response = client.post("/task", json=calc_task_data)
        assert calc_response.status_code == 201
        calc_tasks.append(calc_response.json()["id"])

    # Set root task
    root_response = client.post(
        f"/tasksmanager/{tasksmanager_id}/task/{root_task_id}/tree/root"
    )
    assert root_response.status_code == 200
    assert root_response.json()["root_id"] == root_task_id

    # Add calculator tasks as children
    for calc_id in calc_tasks:
        relation = client.post(
            f"/tasksmanager/{tasksmanager_id}/task/tree/relation",
            json={
                "parent_id": root_task_id,
                "child_id": calc_id,
                "execution_strategy": "parallel"
            }
        )
        assert relation.status_code == 200

    # Configure execution for parallel processing
    config_response = client.post(
        f"/tasksmanager/{tasksmanager_id}/task/{root_task_id}/tree/config",
        json={
            "strategy": "parallel",
            "execute_children": True,
            "propagate_context": True,
            "max_retries": 3,
            "timeout": 60.0
        }
    )
    assert config_response.status_code == 200
    config_data = config_response.json()
    assert config_data["config"]["strategy"] == "parallel"
    assert config_data["config"]["max_retries"] == 3
    assert config_data["config"]["timeout"] == 60.0

    # Run the calculation tree
    calculation_request = {
        "caller_id": "test_complex_calculator",
        "messages": [
            {
                "role": "user",
                "content": "Calculate (3 + 4i) * (2 - 3i)"
            }
        ]
    }
    
    run_response = client.post(
        f"/task/{tasksmanager_id}/{root_task_id}/run",
        json=calculation_request
    )
    assert run_response.status_code == 200
    
    # Verify the response structure
    result = run_response.json()
    assert "result" in result
    assert "tree_execution" in result
    assert result["tree_execution"] is True
    
    # Get tree status
    status_response = client.get(
        f"/tasksmanager/{tasksmanager_id}/task/{root_task_id}/tree/status"
    )
    assert status_response.status_code == 200
    
    tree_status = status_response.json()
    assert len(tree_status["children"]) == 2
    assert all(child["status"] == "completed" for child in tree_status["children"])
    assert tree_status["status"] == "completed"

def test_tree_error_cases(client: TestClient):
    """Test various error cases in tree operations"""
    
    # Try operations with non-existent tasksmanager
    invalid_manager_id = "non-existent-manager"
    
    # Try to set root
    root_response = client.post(
        f"/tasksmanager/{invalid_manager_id}/task/any-task/tree/root"
    )
    assert root_response.status_code == 400
    error_detail = root_response.json()["detail"]
    assert error_detail["message"] == "TasksManager not found"
    assert error_detail["details"]["tasksmanager_id"] == invalid_manager_id

    # Try to add relation
    relation_response = client.post(
        f"/tasksmanager/{invalid_manager_id}/task/tree/relation",
        json={
            "parent_id": "task1",
            "child_id": "task2",
            "execution_strategy": "sequential"
        }
    )
    assert relation_response.status_code == 400
    error_detail = relation_response.json()["detail"]
    assert error_detail["message"] == "TasksManager not found"

    # Try to configure execution
    config_response = client.post(
        f"/tasksmanager/{invalid_manager_id}/task/any-task/tree/config",
        json={
            "strategy": "sequential",
            "execute_children": True,
            "propagate_context": True,
            "max_retries": 3,
            "timeout": 60.0
        }
    )
    assert config_response.status_code == 400
    error_detail = config_response.json()["detail"]
    assert error_detail["message"] == "TasksManager not found"
