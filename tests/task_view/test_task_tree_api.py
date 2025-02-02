import pytest
from fastapi.testclient import TestClient
from src.server.models.message import Message
from src.server.utils.task_utils import find_file
from src.server.controllers.tasks_tree_controller import ExecutionStrategy

def test_complex_calculator_tree(client: TestClient):
    # Read the calculator swagger YAML for complex number operations
    with open(find_file("tests/calculator/complex_calc.yml"), "r") as file:
        swagger_yaml_content = file.read()
    
    # Create toolset with calculator API
    toolset_data = {
        "name": ("", "Complex Calculator"),
        "description": ("", "API for complex number calculations"),
        "credentials": ("", '{"auth_type":"Bearer","auth_key":"test-key"}'),
        "swagger_str": ("", swagger_yaml_content)
    }
    toolset_response = client.post("/toolsets", files=toolset_data)
    assert toolset_response.status_code == 201
    toolset_id = toolset_response.json()["id"]

    # Create tasksmanager for complex calculations
    tasksmanager_data = {
        "name": "Complex Math Expert",
        "model": "gpt-4o-mini",
        "description": "TasksManager for complex number calculations",
        "create_crew": {
            "process_type": "sequential",
            "verbose": True
        }
    }
    tasksmanager_response = client.post("/tasksmanager", json=tasksmanager_data)
    assert tasksmanager_response.status_code == 201
    tasksmanager_id = tasksmanager_response.json()["id"]

    # Create root task (Aggregator)
    root_system_message = Message(
        role="system",
        content="""You are a math expert that compares results of complex number calculations.
        Compare the results provided and indicate if there are any differences.
        Provide ONLY the final result if they match, or highlight the differences if they don't.
        Do not include any explanations or additional text."""
    )
    root_task_data = {
        "name": "Complex Calculator Aggregator",
        "description": "Compare and aggregate complex calculation results",
        "tasksmanager_id": tasksmanager_id,
        "messages": [root_system_message.model_dump()],
        "toolsets": [toolset_id]
    }
    root_task_response = client.post("/task", json=root_task_data)
    assert root_task_response.status_code == 201
    root_task_id = root_task_response.json()["id"]

    # Create calculator task A
    calc_a_system_message = Message(
        role="system",
        content="""You are a math expert that performs complex number calculations.
        Use the calculator API to perform the requested calculations.
        Provide ONLY the numerical results without any explanation."""
    )
    calc_a_task_data = {
        "name": "Complex Calculator A",
        "description": "Perform complex calculations using method A",
        "tasksmanager_id": tasksmanager_id,
        "messages": [calc_a_system_message.model_dump()],
        "toolsets": [toolset_id]
    }
    calc_a_response = client.post("/task", json=calc_a_task_data)
    assert calc_a_response.status_code == 201
    calc_a_id = calc_a_response.json()["id"]

    # Create calculator task B
    calc_b_system_message = Message(
        role="system",
        content="""You are a math expert that performs complex number calculations.
        Use the calculator API to perform the requested calculations.
        Provide ONLY the numerical results without any explanation."""
    )
    calc_b_task_data = {
        "name": "Complex Calculator B",
        "description": "Perform complex calculations using method B",
        "tasksmanager_id": tasksmanager_id,
        "messages": [calc_b_system_message.model_dump()],
        "toolsets": [toolset_id]
    }
    calc_b_response = client.post("/task", json=calc_b_task_data)
    assert calc_b_response.status_code == 201
    calc_b_id = calc_b_response.json()["id"]

    # Set up task tree structure
    # Set root task
    root_response = client.post(
        f"/tasksmanager/{tasksmanager_id}/task/{root_task_id}/tree/root"
    )
    assert root_response.status_code == 200
    assert root_response.json()["root_id"] == root_task_id

    # Add calculator tasks as children
    relation_a = client.post(
        f"/tasksmanager/{tasksmanager_id}/task/tree/relation",
        json={
            "parent_id": root_task_id,
            "child_id": calc_a_id,
            "execution_strategy": ExecutionStrategy.PARALLEL.value
        }
    )
    assert relation_a.status_code == 200

    relation_b = client.post(
        f"/tasksmanager/{tasksmanager_id}/task/tree/relation",
        json={
            "parent_id": root_task_id,
            "child_id": calc_b_id,
            "execution_strategy": ExecutionStrategy.PARALLEL.value
        }
    )
    assert relation_b.status_code == 200

    # Configure execution for parallel processing
    config_response = client.post(
        f"/tasksmanager/{tasksmanager_id}/task/{root_task_id}/tree/config",
        json={
            "strategy": ExecutionStrategy.PARALLEL.value,
            "execute_children": True,
            "propagate_context": True,
            "max_retries": 3,
            "timeout": 180.0
        }
    )
    assert config_response.status_code == 200
    config_data = config_response.json()
    assert config_data["config"]["strategy"] == ExecutionStrategy.PARALLEL.value
    assert config_data["config"]["max_retries"] == 3
    assert config_data["config"]["timeout"] == 180.0

    # Run the calculation tree
    calculation_request = Message(
        role="user",
        content="""Calculate the following operations with complex numbers:
        1. (3 + 4i) * (2 - 3i)
        2. (1 + 2i) / (2 + i)
        Provide the results in the format: result1; result2"""
    )
    
    run_response = client.post(
        f"/task/{tasksmanager_id}/{root_task_id}/run",
        json={
            "caller_id": "test_complex_calculator",
            "messages": [calculation_request.model_dump()]
        }
    )
    assert run_response.status_code == 200
    
    # Verify the response structure
    result = run_response.json()
    assert "result" in result
    assert "tree_execution" in result
    assert result["tree_execution"] is True

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
