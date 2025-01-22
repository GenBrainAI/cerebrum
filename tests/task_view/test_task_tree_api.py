import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
import json
import time

from src.server.main import app
from src.server.persistence.persistence_model_factory import PersistenceModelFactory
from src.server.tools.tools_catalog import tools_catalog
from src.server.models.toolset import Tool
from src.server.models.function import Function
from src.server.models.schema import ParameterSchema, ResponseContent, ResolvedSchema

client = TestClient(app)

@pytest.fixture(autouse=True)
def cleanup_tools():
    """Clean up tools before and after each test."""
    tools_catalog.reset()
    yield
    tools_catalog.reset()

@pytest.fixture
def mock_calculator_api():
    """Mock the calculator API responses."""
    with patch('httpx.AsyncClient') as mock:
        mock_client = MagicMock()
        mock_client.post.side_effect = [
            MagicMock(status_code=200, json=lambda: {"result": {"real": 4, "imag": 2}}),  # multiply
            MagicMock(status_code=200, json=lambda: {"result": {"real": 1, "imag": 0.5}}),  # divide
        ]
        mock.return_value.__aenter__.return_value = mock_client
        yield mock

def test_complex_calculator_tree(mock_calculator_api):
    """Test creating and running a complex calculator task tree."""
    # Create toolset with calculator API
    with open("tests/calculator/complex_calc.yml", "r") as file:
        swagger_string = file.read()

    # Create toolset
    toolset_data = {
        "name": ("", "Complex Calculator"),
        "description": ("", "Complex number calculator API"),
        "credentials": ("", '{"auth_type":"Bearer","auth_key":"test-key"}'),
        "swagger_str": ("", swagger_string)
    }

    toolset_response = client.post("/toolsets", files=toolset_data)
    assert toolset_response.status_code == 201
    toolset_id = toolset_response.json()["id"]

    # Generate and register tools
    tools_response = client.post(f"/generate_tools/{toolset_id}")
    assert tools_response.status_code == 200
    tools = tools_response.json()

    # Register tools in catalog
    for tool_dict in tools:
        print(f"\nTool dict: {json.dumps(tool_dict, indent=2)}")
        # Convert parameters to proper format
        function_dict = tool_dict["function"]
        parameters = {}
        if "parameters" in function_dict:
            param_dict = function_dict["parameters"]
            if isinstance(param_dict, dict):
                # Create a requestBody parameter
                parameters["requestBody"] = {
                    "requestBody": ParameterSchema(
                        name="requestBody",
                        in_="body",
                        description=param_dict.get("description", "Request body schema"),
                        required=True,
                        schema=ResolvedSchema(
                            type=param_dict.get("type", "object"),
                            properties=param_dict.get("properties", {}),
                            required=param_dict.get("required", [])
                        )
                    )
                }

        # Create Function object
        function = Function(
            name=function_dict["name"],
            description=function_dict.get("description", ""),
            parameters=parameters,
            responses={},  # Empty responses for now
            url=function_dict.get("url"),
            method=function_dict.get("method"),
            credentials=function_dict.get("credentials"),
            toolsetId=function_dict.get("toolsetId")
        )

        # Create Tool object
        tool = Tool(function=function, type="function")
        tools_catalog.register_openapi_tool(tool)

    # Wait for tools to be registered
    time.sleep(0.1)  # 100ms should be enough

    # Create and store CrewAI configuration
    crewai_config_data = {
        "description": "Complex Calculator Crew for performing and verifying calculations",
        "agents": [
            {
                "role": "Calculator Aggregator",
                "goal": "Compare and verify calculation results",
                "backstory": "Expert in complex number calculations and result verification",
                "tools": [
                    {
                        "name": "fn0_postComplexmultiply",
                        "description": "Multiply two complex numbers"
                    },
                    {
                        "name": "fn0_postComplexdivide",
                        "description": "Divide two complex numbers"
                    }
                ],
                "verbose": True
            },
            {
                "role": "Calculator 0",
                "goal": "Perform complex number calculations accurately",
                "backstory": "Expert in complex number arithmetic and calculations",
                "tools": [
                    {
                        "name": "fn0_postComplexmultiply",
                        "description": "Multiply two complex numbers"
                    },
                    {
                        "name": "fn0_postComplexdivide",
                        "description": "Divide two complex numbers"
                    }
                ],
                "verbose": True
            },
            {
                "role": "Calculator 1",
                "goal": "Perform complex number calculations accurately",
                "backstory": "Expert in complex number arithmetic and calculations",
                "tools": [
                    {
                        "name": "fn0_postComplexmultiply",
                        "description": "Multiply two complex numbers"
                    },
                    {
                        "name": "fn0_postComplexdivide",
                        "description": "Divide two complex numbers"
                    }
                ],
                "verbose": True
            }
        ],
        "tasks": [
            {
                "description": "Compare and verify calculation results from different calculators",
                "expected_output": "Verification of calculation results",
                "agent_role": "Calculator Aggregator"
            },
            {
                "description": "Perform complex number calculations using method 0",
                "expected_output": "Result of complex number calculation",
                "agent_role": "Calculator 0"
            },
            {
                "description": "Perform complex number calculations using method 1",
                "expected_output": "Result of complex number calculation",
                "agent_role": "Calculator 1"
            }
        ],
        "tools_proxy_collection": {
            "toolsets": [
                {
                    "id": toolset_id,
                    "name": "Complex Calculator"
                }
            ],
            "functions": [],
            "objects": []
        }
    }

    # Create CrewAI configuration
    crewai_config_response = client.post("/agent/crewai", json=crewai_config_data)
    if crewai_config_response.status_code != 201:
        print(f"Error response: {crewai_config_response.json()}")
    assert crewai_config_response.status_code == 201
    crew_id = crewai_config_response.json()["crew_id"]
    curried_proxy_id = crewai_config_response.json()["curried_proxy_id"]

    # Create tasks manager
    tasksmanager_data = {
        "name": "Complex Calculator Manager",
        "model": "gpt-4",
        "description": "Manager for complex number calculations",
        "toolsets": [toolset_id]
    }
    tasksmanager_response = client.post("/tasksmanager", json=tasksmanager_data)
    assert tasksmanager_response.status_code == 201
    tasksmanager_id = tasksmanager_response.json()["id"]

    # Verify tasksmanager exists
    verify_response = client.get(f"/tasksmanager/{tasksmanager_id}")
    assert verify_response.status_code == 200

    # Create root task for aggregating results
    root_task_data = {
        "name": "Aggregate Calculator Results",
        "description": "Compare and verify results from different calculators",
        "tasksmanager_id": tasksmanager_id,
        "messages": [
            {
                "role": "system",
                "content": "You are a complex number calculator that verifies results from different calculation methods."
            }
        ],
        "toolsets": [toolset_id],
        "crewai_config_id": crew_id,
        "curried_proxy_id": curried_proxy_id,
        "agent_role": "Calculator Aggregator"
    }
    root_task_response = client.post("/task", json=root_task_data)
    assert root_task_response.status_code == 201
    root_task_id = root_task_response.json()["id"]

    # Create calculator tasks
    calculator_tasks = []
    for i in range(2):
        calculator_task_data = {
            "name": f"Calculate Complex Numbers {i}",
            "description": f"Perform complex number calculations using method {i}",
            "tasksmanager_id": tasksmanager_id,
            "messages": [
                {
                    "role": "system",
                    "content": f"You are a complex number calculator using method {i}."
                }
            ],
            "toolsets": [toolset_id],
            "crewai_config_id": crew_id,
            "curried_proxy_id": curried_proxy_id,
            "agent_role": f"Calculator {i}"
        }
        calculator_task_response = client.post("/task", json=calculator_task_data)
        assert calculator_task_response.status_code == 201
        calculator_tasks.append(calculator_task_response.json()["id"])

    # Set root task and add calculator tasks as children
    set_root_response = client.post(f"/tasksmanager/{tasksmanager_id}/task/{root_task_id}/tree/root")
    assert set_root_response.status_code == 200

    for task_id in calculator_tasks:
        add_child_response = client.post(f"/tasksmanager/{tasksmanager_id}/task/tree/relation", json={
            "parent_id": root_task_id,
            "child_id": task_id,
            "execution_strategy": "parallel"
        })
        assert add_child_response.status_code == 200

    # Configure execution for parallel processing
    execution_config = {
        "strategy": "parallel",
        "execute_children": True,
        "propagate_context": True,
        "max_retries": 3,
        "timeout": 180.0
    }
    config_response = client.post(f"/tasksmanager/{tasksmanager_id}/task/{root_task_id}/tree/config", json=execution_config)
    assert config_response.status_code == 200

    # Run the calculation tree
    calculation_request = {
        "caller_id": "test_complex_calculator",
        "messages": [
            {
                "role": "user",
                "content": "Calculate (2+1j) * (1+1j) and (4+2j) / (2+1j) using different methods and verify the results."
            }
        ]
    }
    run_response = client.post(f"/task/{tasksmanager_id}/{root_task_id}/run", json=calculation_request)
    assert run_response.status_code == 200

    # Check that tasks were completed
    tasks_response = client.get(f"/tasksmanager/{tasksmanager_id}/tasks")
    assert tasks_response.status_code == 200
    tasks = tasks_response.json()
    assert len(tasks) == 3  # Verify we have all three tasks

def test_tree_error_cases():
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
