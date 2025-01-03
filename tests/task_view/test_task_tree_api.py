import pytest
from fastapi.testclient import TestClient
from src.server.models.message import Message
from src.server.utils.task_utils import find_file
from src.server.controllers.tasks_tree_controller import ExecutionStrategy
from src.server.tools.tools_catalog import tools_catalog

@pytest.fixture(autouse=True)
def cleanup_tools():
    """Cleanup fixture that runs automatically before and after each test."""
    tools_catalog.reset()
    yield
    tools_catalog.reset()

def test_complex_calculator_tree(client: TestClient):
    # Read the calculator swagger YAML for complex number operations
    with open(find_file("tests/calculator/calculator.yaml"), "r") as file:
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
        "model": "gpt-4",
        "description": "TasksManager for complex number calculations",
    }
    tasksmanager_response = client.post("/tasksmanager", json=tasksmanager_data)
    assert tasksmanager_response.status_code == 201
    tasksmanager_id = tasksmanager_response.json()["id"]

    # Create root task (Aggregator)
    root_system_message = Message(
        role="system",
        content="""You are a math expert that compares results of complex number calculations.
        When you receive results from the calculator tasks, they will be in the format {"result": number}.
        Compare the results provided and indicate if there are any differences.
        Provide ONLY the final result if they match, or highlight the differences if they don't.
        Do not include any explanations or additional text."""
    )
    root_task_data = {
        "name": "Complex Calculator Aggregator",
        "description": "Compare and aggregate complex calculation results",
        "tasksmanager_id": tasksmanager_id,
        "messages": [root_system_message.dict()],
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
        For complex numbers like a + bi, split them into two numbers and use the calculator API twice:
        1. First calculate with the real parts (a)
        2. Then calculate with the imaginary parts (b)
        3. Combine the results in the format: {"result": real_result} for real parts and {"result": imag_result} for imaginary parts
        For example, to multiply (3 + 4i) * (2 - 3i):
        1. Real part: (3 * 2) - (4 * -3) = 6 + 12 = 18
        2. Imaginary part: (3 * -3) + (4 * 2) = -9 + 8 = -1
        Result: {"result": 18}; {"result": -1}
        Provide ONLY the numerical results without any explanation."""
    )
    calc_a_task_data = {
        "name": "Complex Calculator A",
        "description": "Perform complex calculations using method A",
        "tasksmanager_id": tasksmanager_id,
        "messages": [calc_a_system_message.dict()],
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
        For complex numbers like a + bi, split them into two numbers and use the calculator API twice:
        1. First calculate with the real parts (a)
        2. Then calculate with the imaginary parts (b)
        3. Combine the results in the format: {"result": real_result} for real parts and {"result": imag_result} for imaginary parts
        For example, to multiply (3 + 4i) * (2 - 3i):
        1. Real part: (3 * 2) - (4 * -3) = 6 + 12 = 18
        2. Imaginary part: (3 * -3) + (4 * 2) = -9 + 8 = -1
        Result: {"result": 18}; {"result": -1}
        Provide ONLY the numerical results without any explanation."""
    )
    calc_b_task_data = {
        "name": "Complex Calculator B",
        "description": "Perform complex calculations using method B",
        "tasksmanager_id": tasksmanager_id,
        "messages": [calc_b_system_message.dict()],
        "toolsets": [toolset_id]
    }
    calc_b_response = client.post("/task", json=calc_b_task_data)
    assert calc_b_response.status_code == 201
    calc_b_id = calc_b_response.json()["id"]

    # Set up task tree structure with error handling
    # 1. Try to set non-existent task as root (should fail)
    invalid_root_response = client.post(
        f"/tasksmanager/{tasksmanager_id}/task/invalid-task-id/tree/root"
    )
    assert invalid_root_response.status_code == 400
    error_detail = invalid_root_response.json()["detail"]
    assert error_detail["message"] == "Task not found"
    assert error_detail["details"]["task_id"] == "invalid-task-id"

    # 2. Set actual root task
    root_response = client.post(
        f"/tasksmanager/{tasksmanager_id}/task/{root_task_id}/tree/root"
    )
    assert root_response.status_code == 200
    assert root_response.json()["root_id"] == root_task_id

    # 3. Try to set same task as root again (should fail)
    duplicate_root_response = client.post(
        f"/tasksmanager/{tasksmanager_id}/task/{root_task_id}/tree/root"
    )
    assert duplicate_root_response.status_code == 400
    error_detail = duplicate_root_response.json()["detail"]
    assert error_detail["message"] == "Task is already part of a tree"
    assert error_detail["details"]["task_id"] == root_task_id

    # 4. Add calculator tasks as children with error handling
    # Try to add relation with invalid parent
    invalid_relation = client.post(
        f"/tasksmanager/{tasksmanager_id}/task/tree/relation",
        json={
            "parent_id": "invalid-parent",
            "child_id": calc_a_id,
            "execution_strategy": ExecutionStrategy.PARALLEL.value
        }
    )
    assert invalid_relation.status_code == 400
    error_detail = invalid_relation.json()["detail"]
    assert "One or both tasks not found" in error_detail["message"]
    assert not error_detail["details"]["parent_exists"]

    # Add valid relations
    relation_a = client.post(
        f"/tasksmanager/{tasksmanager_id}/task/tree/relation",
        json={
            "parent_id": root_task_id,
            "child_id": calc_a_id,
            "execution_strategy": "parallel"
        }
    )
    assert relation_a.status_code == 200

    relation_b = client.post(
        f"/tasksmanager/{tasksmanager_id}/task/tree/relation",
        json={
            "parent_id": root_task_id,
            "child_id": calc_b_id,
            "execution_strategy": "parallel"
        }
    )
    assert relation_b.status_code == 200

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
    calculation_request = Message(
        role="user",
        content="""Calculate the following operations with complex numbers:
        1. (3 + 4i) * (2 - 3i)
        2. (1 + 2i) / (2 + i)
        3. sqrt(4 + 9i)
        Provide the results in the format: result1; result2; result3"""
    )
    
    run_response = client.post(
        f"/task/{tasksmanager_id}/{root_task_id}/run",
        json={
            "caller_id": "test_complex_calculator",
            "messages": [calculation_request.dict()]
        }
    )
    assert run_response.status_code == 200
    
    # Verify the response structure
    result = run_response.json()
    assert "result" in result
    assert "tree_execution" in result
    assert result["tree_execution"] is True
    
    # Get tree status with error handling
    # Try to get status for non-existent task
    invalid_status = client.get(
        f"/tasksmanager/{tasksmanager_id}/task/invalid-task/tree/status"
    )
    assert invalid_status.status_code == 400
    error_detail = invalid_status.json()["detail"]
    assert error_detail["message"] == "Task not found in tree"

    # Get valid status
    status_response = client.get(
        f"/tasksmanager/{tasksmanager_id}/task/{root_task_id}/tree/status"
    )
    assert status_response.status_code == 200
    
    tree_status = status_response.json()
    assert len(tree_status["children"]) == 2
    assert all(child["status"] == "completed" for child in tree_status["children"])
    assert tree_status["status"] == "completed"

    # Print results for debugging
    print("\nCalculation Results:")
    print(result["result"])

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
