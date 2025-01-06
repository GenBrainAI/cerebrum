"""
Dynamic Tools Generation End-to-End Test Suite

This test suite validates the complete flow of dynamic tools generation, from state creation to tool loading.
Tests are executed in a specific order using pytest-order to ensure proper state progression.

Test Execution Order:
1. test_dynamic_tools_state_generation - Initial state setup
2. test_state_loading_to_local_persistence - State persistence validation
3. test_main_task_availability - Task configuration verification
4. test_tool_execution_patterns - Verify tool execution patterns
5. test_crewai_invocation - CrewAI execution test
6. test_crewai_output_collection - Output validation
"""

import pytest
import pytest_asyncio
from pathlib import Path
import logging
import json
from typing import Dict, Any, Optional
import os
import asyncio
from unittest.mock import MagicMock, patch
from datetime import datetime

from src.server.persistence.in_memory_persistence import InMemoryPersistenceModel
from src.server.controllers.task_runner import TaskRunner
from src.server.context.unified_context import UnifiedContextState
from src.state_setup.dynamic_tools import setup_dynamic_tools_state
from src.server.persistence.persistence_model_factory import PersistenceModelFactory
from src.server.models.tools_catalog import ToolsCatalog
from src.server.models.task import Task
from src.server.models.message import Message
from src.server.models.curried_proxy import CurriedProxy

logger = logging.getLogger(__name__)

# Create the global instance
tools_catalog = ToolsCatalog()

# Constants for test configuration
CREWAI_CONFIG = {
    "name": "Dynamic Tools Generator",
    "description": "A crew specialized in generating dynamic tools",
    "tasks": [
        {
            "name": "Tool Design",
            "description": "Design and implement the tool interface and requirements",
            "agent_role": "Tool Designer",
            "expected_output": "Tool implementation with tests",
            "tools": [
                {
                    "name": "internal_credentials_tools.load_credentials",
                    "description": "Load credentials from .env file"
                },
                {
                    "name": "internal_credentials_tools.validate_credentials",
                    "description": "Validate that required credentials are present"
                },
                {
                    "name": "internal_file_tools.read_documentation",
                    "description": "Read documentation files"
                },
                {
                    "name": "internal_file_tools.save_implementation",
                    "description": "Save tool implementation"
                },
                {
                    "name": "internal_file_tools.save_tests",
                    "description": "Save tool tests"
                }
            ]
        }
    ],
    "agents": [
        {
            "name": "Tool Designer",
            "role": "Senior Software Architect",
            "goal": "Design and implement robust and reusable tools",
            "backstory": "Expert in software design and architecture with extensive experience in tool development",
            "tools": [
                {
                    "name": "internal_credentials_tools.load_credentials",
                    "description": "Load credentials from .env file"
                },
                {
                    "name": "internal_credentials_tools.validate_credentials",
                    "description": "Validate that required credentials are present"
                },
                {
                    "name": "internal_file_tools.read_documentation",
                    "description": "Read documentation files"
                },
                {
                    "name": "internal_file_tools.save_implementation",
                    "description": "Save tool implementation"
                },
                {
                    "name": "internal_file_tools.save_tests",
                    "description": "Save tool tests"
                }
            ]
        }
    ]
}

TOOL_GENERATION_REQUESTS = [
    {
        "name": "MathTool",
        "description": """Create a mathematical tool that can:
        1. Perform basic arithmetic operations
        2. Calculate statistical measures (mean, median, mode)
        3. Handle matrix operations
        4. Provide proper error handling and type hints
        The tool should use numpy for efficient computations."""
    },
    {
        "name": "LangChainTool",
        "description": """Create a LangChain-based tool that can:
        1. Integrate with LangChain's core functionality
        2. Handle text processing tasks
        3. Provide proper error handling
        4. Include comprehensive documentation
        The tool should follow LangChain's best practices."""
    }
]

# Mock tool execution metrics for testing
class ToolExecutionMetrics:
    def __init__(self):
        self.calls = []
        self.errors = []
    
    def record_call(self, tool_name: str, args: Dict[str, Any]):
        self.calls.append({
            "tool": tool_name,
            "args": args,
            "timestamp": str(datetime.now())
        })
    
    def record_error(self, tool_name: str, error: str):
        self.errors.append({
            "tool": tool_name,
            "error": error,
            "timestamp": str(datetime.now())
        })

# Create mock internal tools for testing with execution metrics
class MockInternalTool:
    """Mock internal tool for testing."""

    def __init__(self, name: str, description: str, required_args: Optional[Dict[str, str]] = None):
        """Initialize the mock tool."""
        self.name = name
        self.description = description
        self._execution_metrics = ToolExecutionMetrics()
        self.required_args = required_args or {}
        self.__doc__ = description  # Set the docstring to the description

    async def __call__(self, **kwargs):
        """Execute the mock tool with the given arguments."""
        try:
            # Verify required arguments
            for arg_name, arg_type in self.required_args.items():
                if arg_name not in kwargs:
                    raise ValueError(f"Missing required argument: {arg_name}")
                if not isinstance(kwargs[arg_name], eval(arg_type)):
                    raise TypeError(f"Argument {arg_name} must be of type {arg_type}")
            
            self._execution_metrics.record_call(self.name, kwargs)
            return {"status": "success", "message": f"Mock execution of {self.name} with args: {kwargs}"}
        except Exception as e:
            self._execution_metrics.record_error(self.name, str(e))
            raise

# Create mock tools instances
MOCK_TOOLS_CONFIG = {
    "internal_credentials_tools.load_credentials": {
        "description": "Load credentials from .env file.",
        "required_args": {}
    },
    "internal_credentials_tools.validate_credentials": {
        "description": "Validate that required credentials are present.",
        "required_args": {
            "credentials": "dict"
        }
    },
    "internal_file_tools.read_documentation": {
        "description": "Read documentation files",
        "required_args": {
            "file_path": "str"
        }
    },
    "internal_file_tools.save_implementation": {
        "description": "Save tool implementation",
        "required_args": {
            "code": "str",
            "file_path": "str"
        }
    },
    "internal_file_tools.save_tests": {
        "description": "Save tool tests",
        "required_args": {
            "code": "str",
            "file_path": "str"
        }
    }
}

# Create mock tools instances
MOCK_TOOLS = {
    name: MockInternalTool(
        name=name,
        description=config["description"],
        required_args=config.get("required_args")
    )
    for name, config in MOCK_TOOLS_CONFIG.items()
}

@pytest.fixture(scope="module")
def test_state():
    """Fixture to share state between tests."""
    state = {
        "tool_metrics": ToolExecutionMetrics()
    }
    return state

@pytest.fixture(scope="module", autouse=True)
def setup_mock_tools():
    """Set up mock tools for testing."""
    # Register mock tools in the catalog
    for name, tool in MOCK_TOOLS.items():
        tools_catalog.register_tool(tool=tool, name=name)
    
    yield MOCK_TOOLS
    
    # Cleanup
    for name in MOCK_TOOLS:
        tools_catalog.unregister_tool(name)

# SECTION 1: Test Setup and Cleanup
@pytest.fixture(scope="module", autouse=True)
def cleanup_tools():
    """Cleanup fixture that runs automatically before and after each test."""
    # Don't reset before test since setup_dynamic_tools_state needs to register tools
    yield
    # Reset after test
    tools_catalog.reset()

@pytest.fixture(scope="module", autouse=True)
def ensure_generated_tools_dir():
    """Ensure the generated tools directory exists."""
    tools_dir = Path("src/server/tools/generated")
    tools_dir.mkdir(parents=True, exist_ok=True)
    # Create __init__.py if it doesn't exist
    init_file = tools_dir / "__init__.py"
    if not init_file.exists():
        init_file.touch()
    yield

# SECTION 2: State Generation and Setup
@pytest.mark.order(1)
@pytest.mark.asyncio
async def test_dynamic_tools_state_generation(test_state):
    """Test step 1: Generate dynamic tools state."""
    try:
        logger.info("Step 1: Generating dynamic tools state...")
        
        # Reset persistence model to ensure clean state
        PersistenceModelFactory.reset()
        persistence_model = PersistenceModelFactory.persistence_model()
        
        # Create CrewAI configuration
        from src.server.models.agent import CrewAIConfig, CreateCrewRequest
        crewai_config = CrewAIConfig(
            id="test_crewai_config",
            name="Dynamic Tools Generation",
            description="Configuration for generating dynamic tools",
            create_crew=CreateCrewRequest(**CREWAI_CONFIG)
        )
        persistence_model.crewai_config.create(crewai_config)
        
        # Generate state
        state = await setup_dynamic_tools_state(persistence_model)
        assert state is not None, "Failed to generate initial state"
        
        # Store state for next tests
        test_state['generated_state'] = state
        test_state['persistence_model'] = persistence_model
        test_state['crewai_config'] = crewai_config
        
        logger.info("✅ Dynamic tools state generated successfully")
        return test_state
        
    except Exception as e:
        logger.error(f"Test failed: {str(e)}", exc_info=True)
        raise

@pytest.mark.order(2)
@pytest.mark.asyncio
async def test_state_loading_to_local_persistence(test_state):
    """Test step 2: Load state to local persistence."""
    try:
        logger.info("Step 2: Loading state to local persistence...")
        
        # Get the source model with generated state
        source_model = test_state.get('persistence_model')
        assert source_model is not None, "Source model not found in test state"
        
        # Create new persistence model
        local_model = InMemoryPersistenceModel()
        
        # Copy CrewAI config
        crewai_config = test_state.get('crewai_config')
        local_model.crewai_config.create(crewai_config)
        
        # Serialize and deserialize state
        state_json = source_model.to_json()
        local_model.from_json(state_json)
        
        # Verify state was loaded
        tasks = local_model.tasks.list()
        assert len(tasks) > 0, "No tasks found in local persistence"
        
        # Store local model for next tests
        test_state['local_model'] = local_model
        
        logger.info("✅ State loaded to local persistence successfully")
        return test_state
        
    except Exception as e:
        logger.error(f"Test failed: {str(e)}", exc_info=True)
        raise
    
@pytest.mark.order(3)
@pytest.mark.asyncio
async def test_main_task_availability(test_state):
    """Test step 3: Verify main task is available and properly configured."""
    try:
        logger.info("Step 3: Verifying main task availability...")
        
        local_model = test_state.get('local_model')
        assert local_model is not None, "Local model not found in test state"
        
        # Find the dynamic tools task
        tasks = local_model.tasks.list()
        dynamic_tools_task = next(
            (task for task in tasks if task.name == "Generate Dynamic Langchain Tool"),
            None
        )
        assert dynamic_tools_task is not None, "Dynamic tools task not found"
        
        # Verify task configuration
        assert dynamic_tools_task.curried_proxy_id is not None, "Task missing CurriedProxy ID"
        assert dynamic_tools_task.crewai_config_id is not None, "Task missing CrewAI config ID"
        
        # Store task for next tests
        test_state['main_task'] = dynamic_tools_task
        
        logger.info("✅ Main task verified successfully")
        return test_state
        
    except Exception as e:
        logger.error(f"Test failed: {str(e)}", exc_info=True)
        raise

@pytest.mark.order(4)
@pytest.mark.asyncio
async def test_tool_execution_patterns(test_state):
    """Test step 4: Verify tool execution patterns and capture failures."""
    try:
        logger.info("Step 4: Testing tool execution patterns...")
        
        local_model = test_state.get('local_model')
        assert local_model is not None, "Local model not found in test state"
        
        # Create a curried proxy for testing
        curried_proxy = CurriedProxy()
        
        # Register all mock tools
        for name, tool in MOCK_TOOLS.items():
            curried_proxy.register_tool(name, tool)
        
        # Test tool execution patterns
        test_cases = [
            {
                "tool": "internal_credentials_tools.load_credentials",
                "args": {},
                "should_succeed": True
            },
            {
                "tool": "internal_credentials_tools.validate_credentials",
                "args": {},  # Missing required 'credentials' argument
                "should_succeed": False
            },
            {
                "tool": "internal_file_tools.save_implementation",
                "args": {"code": "test code"},  # Missing required 'file_path' argument
                "should_succeed": False
            }
        ]
        
        execution_results = []
        for test_case in test_cases:
            tool_name = test_case["tool"]
            args = test_case["args"]
            should_succeed = test_case["should_succeed"]
            
            try:
                result = await curried_proxy.execute(tool_name, args)
                execution_results.append({
                    "tool": tool_name,
                    "success": True,
                    "result": result
                })
                if not should_succeed:
                    assert False, f"Tool {tool_name} should have failed but succeeded"
            except Exception as e:
                execution_results.append({
                    "tool": tool_name,
                    "success": False,
                    "error": str(e)
                })
                if should_succeed:
                    assert False, f"Tool {tool_name} should have succeeded but failed: {str(e)}"
        
        # Store execution results for analysis
        test_state['tool_execution_results'] = execution_results
        
        # Verify execution metrics were recorded
        for tool_name, tool in MOCK_TOOLS.items():
            assert hasattr(tool, '_execution_metrics'), f"Tool {tool_name} missing execution metrics"
            assert isinstance(tool._execution_metrics, ToolExecutionMetrics), f"Invalid metrics type for {tool_name}"
        
        logger.info("✅ Tool execution patterns verified successfully")
        return test_state
        
    except Exception as e:
        logger.error(f"Test failed: {str(e)}", exc_info=True)
        raise

@pytest.mark.order(5)
@pytest.mark.asyncio
async def test_crewai_invocation(test_state):
    """Test step 5: Invoke CrewAI execution."""
    try:
        logger.info("Step 5: Invoking CrewAI execution...")
        
        local_model = test_state.get('local_model')
        main_task = test_state.get('main_task')
        assert local_model is not None, "Local model not found in test state"
        assert main_task is not None, "Main task not found in test state"
        
        # Initialize task runner
        runner = TaskRunner(local_model)
        await runner.initialize()
        
        # Add tool generation requests as messages
        task = local_model.tasks.read(main_task.id)
        if task.messages is None:
            task.messages = []
            
        # Add tool requests as system messages
        for tool_request in TOOL_GENERATION_REQUESTS:
            task.messages.append(Message(
                role="system",
                content=f"Generate tool: {tool_request['name']}\n\n{tool_request['description']}"
            ))
            
        # Add additional context as a system message
        task.messages.append(Message(
            role="system",
            content=json.dumps({
                "use_langchain_patterns": True,
                "required_capabilities": [
                    "web_search",
                    "mathematical_operations",
                    "data_validation"
                ],
                "implementation_requirements": {
                    "error_handling": True,
                    "type_hints": True,
                    "comprehensive_docstrings": True,
                    "unit_tests": True
                }
            }, indent=2)
        ))
        
        # Get the curried proxy and register mock tools
        curried_proxy = local_model.curried_proxies.read(task.curried_proxy_id)
        if curried_proxy is None:
            curried_proxy = CurriedProxy()
            task.curried_proxy_id = local_model.curried_proxies.create(curried_proxy).id
        
        # Register mock tools in the curried proxy
        for tool_name in ["internal_file_tools.read_documentation", 
                         "internal_file_tools.save_implementation", 
                         "internal_file_tools.save_tests"]:
            tool = tools_catalog.get_tool_instance(tool_name)
            if tool:
                curried_proxy.register_tool(tool_name, tool)
        
        # Update task and curried proxy
        local_model.tasks.update(task.id, task)
        local_model.curried_proxies.update(curried_proxy.id, curried_proxy)
        
        # Execute task through task runner
        result = await runner.run_task(
            tasksmanager_id=task.tasksmanager_id,
            task_id=task.id,
            running_extra_params={}
        )
        assert result is not None, "Task execution failed"
        assert 'error' not in result, f"Task execution error: {result.get('error')}"
        
        # Store result and runner for next tests
        test_state['execution_result'] = result
        test_state['task_runner'] = runner
        
        logger.info("✅ CrewAI execution completed successfully")
        return test_state
        
    except Exception as e:
        logger.error(f"Test failed: {str(e)}", exc_info=True)
        raise

@pytest.mark.order(6)
@pytest.mark.asyncio
async def test_crewai_output_collection(test_state):
    """Test step 6: Verify CrewAI output collection."""
    try:
        logger.info("Step 6: Verifying CrewAI output collection...")
        
        local_model = test_state.get('local_model')
        main_task = test_state.get('main_task')
        execution_result = test_state.get('execution_result')
        assert local_model is not None, "Local model not found in test state"
        assert main_task is not None, "Main task not found in test state"
        assert execution_result is not None, "Execution result not found in test state"
        
        # Check task execution logs
        task = local_model.tasks.read(main_task.id)
        assert task.execution_logs is not None, "Task execution logs not found"
        assert len(task.execution_logs) > 0, "No execution logs found in task"
        
        # Verify tool generation output
        completion_logs = [log for log in task.execution_logs if log.get('type') == 'info' and 'completed' in log.get('content', '')]
        assert len(completion_logs) > 0, "No completion logs found"
        
        logger.info("✅ CrewAI output collection verified successfully")
        return test_state
        
    except Exception as e:
        logger.error(f"Test failed: {str(e)}", exc_info=True)
        raise
