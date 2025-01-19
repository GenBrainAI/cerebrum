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
6. test_crewai_output_verification - Output validation
"""

import pytest
from pathlib import Path
import logging
import json
from typing import Dict, Any, Optional, List
from datetime import datetime
import traceback
from src.server.models.task import Task
from src.server.models.tasks_manager import TasksManager
from src.server.persistence.in_memory_persistence import InMemoryPersistenceModel
from src.server.persistence.persistence_model_factory import PersistenceModelFactory
from src.server.controllers.task_runner import TaskRunner
from src.server.tools.tools_catalog import ToolsCatalog
from src.server.controllers.curried_proxy import CurriedProxy
from src.state_setup.dynamic_tools import setup_dynamic_tools_state
from src.server.models.message import Message
from src.server.tools.tools_metrics import ToolExecutionMetrics, CerebrumCrewAITool
from crewai.tools import BaseTool as CrewAITool
from pydantic import BaseModel, Field, create_model, ConfigDict
from src.server.models.agent import CrewAIConfig, CreateCrewRequest
import asyncio

logger = logging.getLogger(__name__)

# Constants for test configuration
DYNAMIC_TOOLS_STATE_FILE = "state/specialized/dynamic_tools_state.json"

def load_state_from_file(file_path: str) -> Dict[str, Any]:
    """Load state from a JSON file and initialize persistence model."""
    with open(file_path, "r") as f:
        state_json = f.read()
        persistence_model = InMemoryPersistenceModel()
        persistence_model.from_json(state_json)
        
        state_data = json.loads(state_json)
        # Extract IDs from collections
        tasksmanagers = json.loads(state_data["tasksmanagers"])
        tasks = json.loads(state_data["tasks"])
        crewai_config = json.loads(state_data["crewai_config"])
        curried_proxies = json.loads(state_data["curried_proxies"])
        
        # Get first ID from each collection
        return {
            "tasksmanager_id": next(iter(tasksmanagers.keys())),
            "task_id": next(iter(tasks.keys())),
            "crewai_config_id": next(iter(crewai_config.keys())),
            "curried_proxy_id": next(iter(curried_proxies.keys()))
        }

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
            "agent_role": "Senior Software Architect",
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

class MockToolArgsSchema(BaseModel):
    """Schema for mock tool arguments."""
    file_path: Optional[str] = Field(
        default=None,
        description="Path to the file to read"
    )
    code: Optional[str] = Field(
        default=None,
        description="Code to save"
    )
    credentials: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Credentials to validate"
    )
    description: Optional[str] = Field(
        default=None,
        description="Description of the operation"
    )

    class Config:
        extra = "allow"  # Allow extra fields to be passed

class MockInternalTool:
    """Mock implementation of internal tools for testing."""
    
    def __init__(self, name: str, description: str, required_args: Dict[str, str] = None):
        self.name = name
        self.description = description
        self.required_args = required_args or {}
        self._execution_metrics = ToolExecutionMetrics()
        
    def __call__(self, **kwargs) -> Dict[str, Any]:
        """Make the tool callable."""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If we're in a running event loop, create a new task
                return loop.create_task(self._arun(**kwargs))
            else:
                # If no event loop is running, we can use asyncio.run
                return asyncio.run(self._arun(**kwargs))
        except Exception as e:
            return {"error": str(e)}
        
    async def _arun(self, **kwargs) -> Dict[str, Any]:
        """Mock async execution that returns test data."""
        try:
            self._execution_metrics.start_time = datetime.now()
            
            if self.name == "internal_file_tools.read_documentation":
                result = {"content": "# Test Documentation\n\nThis is test documentation content."}
            elif self.name == "internal_credentials_tools.load_credentials":
                result = {"credentials": {"API_KEY": "test_key", "DATABASE_URL": "test_url"}}
            elif self.name == "internal_file_tools.save_implementation":
                result = {"path": f"/tmp/{kwargs.get('tool_name', 'test')}.py"}
            else:
                result = {"result": "success"}
                
            self._execution_metrics.success = True
            self._execution_metrics.output = result
            return result
            
        except Exception as e:
            self._execution_metrics.success = False
            self._execution_metrics.error = str(e)
            raise
        finally:
            self._execution_metrics.end_time = datetime.now()
            self._execution_metrics.input_params = kwargs

class CrewAIToolWrapper(CrewAITool):
    """A wrapper for CrewAI tools."""

    def __init__(self, name: str, description: str, parameters: List[Dict[str, Any]]):
        """Initialize the tool wrapper."""
        # Create field definitions from parameters
        field_definitions = {}
        for param in parameters:
            param_name = param['name']
            param_type = eval(param['type']) if isinstance(param['type'], str) else param['type']
            field_definitions[param_name] = (
                param_type,
                Field(
                    title=param_name.title(),
                    description=param['description'],
                    required=param.get('required', True)
                )
            )

        # Create schema class
        schema_class = create_model(
            f"{name}_schema",
            **field_definitions,
            __config__=ConfigDict(extra='forbid')
        )

        # Initialize base class
        super().__init__(
            name=name,
            description=description,
            args_schema=schema_class
        )

    def _run(self, **kwargs):
        """Run the tool."""
        return f"Running {self.name} with args: {kwargs}"

    async def _arun(self, **kwargs):
        """Run the tool asynchronously."""
        return self._run(**kwargs)

# Create mock tools instances
MOCK_TOOLS_CONFIG = {
    "internal_file_tools.read_documentation": {
        "description": "Read documentation files",
        "required_args": {
            "file_path": "str"
        }
    },
    "internal_credentials_tools.load_credentials": {
        "description": "Load credentials from .env file",
        "required_args": {}
    },
    "internal_file_tools.save_implementation": {
        "description": "Save tool implementation",
        "required_args": {
            "code": "str",
            "tool_name": "str"
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
        "tool_metrics": ToolExecutionMetrics(),
        "persistence_model": None,  # Will be set by first test
        "generated_state": None,    # Will be set by first test
        "crewai_config": None      # Will be set by first test
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
        
        # Generate state
        state = await setup_dynamic_tools_state(persistence_model)
        assert state is not None, "Failed to generate initial state"
        
        # Store state for next tests
        test_state['generated_state'] = state
        test_state['persistence_model'] = persistence_model
        
        # Get the CrewAI config that was created by setup_dynamic_tools_state
        crewai_configs = persistence_model.crewai_config.list()
        assert len(crewai_configs) > 0, "No CrewAI configurations found"
        test_state['crewai_config'] = crewai_configs[0]
        
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
        assert crewai_config is not None, "CrewAI config not found in test state"
        local_model.crewai_config.create(crewai_config)

        # Debug: List all task managers in source model
        task_managers = source_model.tasksmanagers.list()
        logger.info(f"Found {len(task_managers)} task managers in source model")
        for manager in task_managers:
            logger.info(f"Task manager in source: {manager.id}")

        # Debug: List all tasks in source model
        tasks = source_model.tasks.list()
        logger.info(f"Found {len(tasks)} tasks in source model")
        for task in tasks:
            logger.info(f"Task in source: {task.id} with manager {task.tasksmanager_id}")

        # Copy all tasks managers from source model first
        for manager in task_managers:
            # Create with the same ID
            logger.info(f"Creating task manager {manager.id}")
            # Create a copy of the manager to avoid modifying the original
            manager_copy = TasksManager(**manager.model_dump())
            manager_copy.id = manager.id  # Preserve the original ID
            created_manager = local_model.tasksmanagers.create(manager_copy)
            assert created_manager is not None, f"Failed to create task manager {manager.id}"
            assert created_manager.id == manager.id, f"Task manager ID mismatch: {created_manager.id} != {manager.id}"

            # Verify manager was created
            read_manager = local_model.tasksmanagers.read(manager.id)
            assert read_manager is not None, f"Failed to read task manager {manager.id} after creation"

        # Copy all tasks from source model
        for task in tasks:
            # Create a copy of the task to avoid modifying the original
            task_copy = Task(**task.model_dump())
            task_copy.id = task.id  # Preserve the original ID
            logger.info(f"Creating task {task_copy.id} with manager {task_copy.tasksmanager_id}")
            created_task = local_model.tasks.create(task_copy)
            assert created_task is not None, f"Failed to create task {task.id}"
            assert created_task.id == task.id, f"Task ID mismatch: {created_task.id} != {task.id}"
            assert created_task.tasksmanager_id == task.tasksmanager_id, f"Task manager ID mismatch: {created_task.tasksmanager_id} != {task.tasksmanager_id}"

            # Verify task was created
            read_task = local_model.tasks.read(task.id)
            assert read_task is not None, f"Failed to read task {task.id} after creation"
            assert read_task.tasksmanager_id == task.tasksmanager_id, f"Task manager ID mismatch after read: {read_task.tasksmanager_id} != {task.tasksmanager_id}"

        # Copy all curried proxies from source model
        proxies = source_model.curried_proxies.list()
        for proxy in proxies:
            # Create with the same ID
            proxy_copy = CurriedProxy(**proxy.model_dump())
            proxy_copy.id = proxy.id  # Preserve the original ID
            created_proxy = local_model.curried_proxies.create(proxy_copy)
            assert created_proxy is not None, f"Failed to create curried proxy {proxy.id}"
            assert created_proxy.id == proxy.id, f"Curried proxy ID mismatch: {created_proxy.id} != {proxy.id}"

        # Store local model for next tests
        test_state['local_model'] = local_model

        # Debug: List all task managers in local model
        local_managers = local_model.tasksmanagers.list()
        logger.info(f"Found {len(local_managers)} task managers in local model")
        for manager in local_managers:
            logger.info(f"Task manager in local: {manager.id}")

        # Debug: List all tasks in local model
        local_tasks = local_model.tasks.list()
        logger.info(f"Found {len(local_tasks)} tasks in local model")
        for task in local_tasks:
            logger.info(f"Task in local: {task.id} with manager {task.tasksmanager_id}")

        # Verify state was loaded
        assert len(local_tasks) > 0, "No tasks found in local persistence"

        # Verify task manager was loaded with correct ID
        task = local_tasks[0]
        assert task.tasksmanager_id is not None, "Task missing tasksmanager_id"
        task_manager = local_model.tasksmanagers.read(task.tasksmanager_id)
        assert task_manager is not None, f"Task manager {task.tasksmanager_id} not found"

        logger.info("✅ State loaded to local persistence successfully")
        return test_state

    except Exception as e:
        logger.error(f"Test failed: {str(e)}")
        traceback.print_exc()
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
    """Test step 4: Verify tool execution patterns."""
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

@pytest.mark.order(4.5)
@pytest.mark.asyncio
async def test_tool_argument_schemas(test_state):
    """Test step 4.5: Verify tool argument schemas are properly defined."""
    try:
        logger.info("Step 4.5: Testing tool argument schemas...")
        
        # Create a curried proxy for testing
        curried_proxy = CurriedProxy()
        
        # Get mock tool and create wrapper
        tool_name = "internal_file_tools.read_documentation"
        mock_tool = MOCK_TOOLS[tool_name]
        
        # Create parameters list from required_args
        parameters = [
            {
                "name": "file_path",
                "type": "str",
                "description": "Path to the file to read",
                "required": True
            },
            {
                "name": "kwargs",
                "type": "Dict[str, Any]",
                "description": "Additional keyword arguments",
                "required": False
            }
        ]
        
        crew_tool = CrewAIToolWrapper(
            name=tool_name,
            description=mock_tool.description,
            parameters=parameters
        )
        
        curried_proxy.register_tool(tool_name, crew_tool)
        
        # Get the tool metadata
        tool_metadata = curried_proxy.get_tool(tool_name)
        assert tool_metadata.original_obj is not None, "Tool metadata missing original tool"
        
        # Get the actual tool instance
        tool = tool_metadata.original_obj
        assert isinstance(tool, CrewAIToolWrapper), "Tool is not properly wrapped as a CrewAI tool"
        
        # Verify tool has proper argument schema
        assert hasattr(tool, 'args_schema'), "Tool missing args_schema"
        assert issubclass(tool.args_schema, BaseModel), "Tool args_schema is not a Pydantic model"
        
        # Verify schema properties
        schema = tool.args_schema.model_json_schema()
        assert 'properties' in schema, "Schema missing properties"
        assert 'file_path' in schema['properties'], "Schema missing file_path property"
        assert schema['properties']['file_path']['type'] == 'string', "file_path should be a string"
        
        logger.info("✅ Tool argument schemas verified successfully")
        return test_state
        
    except Exception as e:
        logger.error(f"Test failed: {str(e)}", exc_info=True)
        raise

@pytest.mark.order(4.6)
@pytest.mark.asyncio
async def test_dynamic_tools_state(test_state):
    """Test the setup of dynamic tools generation state."""
    try:
        # Initialize persistence model
        persistence_model = InMemoryPersistenceModel()
        
        # Load state from file
        with open(DYNAMIC_TOOLS_STATE_FILE, 'r') as f:
            state_data = json.load(f)
            
        # Extract IDs from collections
        tasksmanager_id = list(json.loads(state_data["tasksmanagers"]).keys())[0]
        task_id = list(json.loads(state_data["tasks"]).keys())[0]
        crewai_config_id = list(json.loads(state_data["crewai_config"]).keys())[0]
        curried_proxy_id = list(json.loads(state_data["curried_proxies"]).keys())[0]
        
        # Store state for next test
        test_state["tasksmanager_id"] = tasksmanager_id
        test_state["task_id"] = task_id
        test_state["crewai_config_id"] = crewai_config_id
        test_state["curried_proxy_id"] = curried_proxy_id
        test_state["persistence_model"] = persistence_model
        
        # Register mock tools
        for name, tool in MOCK_TOOLS.items():
            tools_catalog.register_tool(tool, name)
            
        # Create CurriedProxy and register tools
        curried_proxy = CurriedProxy()
        for name, tool in MOCK_TOOLS.items():
            curried_proxy.add_tool(name, tool)
            
        # Store CurriedProxy
        persistence_model.curried_proxies.create(curried_proxy)
        
        # Verify state
        assert tasksmanager_id is not None, "Missing tasksmanager_id in state"
        assert task_id is not None, "Missing task_id in state"
        assert crewai_config_id is not None, "Missing crewai_config_id in state"
        assert curried_proxy_id is not None, "Missing curried_proxy_id in state"
        
        print("✅ Dynamic tools state test passed")
        
    except Exception as e:
        print(f"❌ Dynamic tools state test failed: {str(e)}")
        raise

@pytest.mark.order(5)
@pytest.mark.asyncio
async def test_crewai_invocation(test_state):
    """Test step 5: Invoke CrewAI execution."""
    try:
        logger.info("Step 5: Invoking CrewAI execution...")
        
        # Initialize persistence model and curried proxy
        persistence_model = InMemoryPersistenceModel()
        curried_proxy = CurriedProxy()
        
        # Register internal tools from MOCK_TOOLS
        for name, tool in MOCK_TOOLS.items():
            curried_proxy.add_tool(name, tool)
        
        # Store curried proxy
        curried_proxy = persistence_model.curried_proxies.create(curried_proxy)
        assert curried_proxy is not None, "Failed to create curried proxy"
        
        # Create CrewAI config using the predefined CREWAI_CONFIG
        crewai_config = CrewAIConfig(
            create_crew=CreateCrewRequest(**CREWAI_CONFIG),
            model_config={
                "model": "gpt-4",
                "temperature": 0.7,
                "max_tokens": 2000
            }
        )
        
        # Create and store config
        crewai_config = persistence_model.crewai_config.create(crewai_config)
        assert crewai_config is not None, "Failed to create CrewAI config"
        
        # Create task manager
        task_manager = TasksManager(
            name="Dynamic Tools Manager",
            description="Manager for dynamic tools generation tasks",
            crewai_config_id=crewai_config.id
        )
        task_manager = persistence_model.tasksmanagers.create(task_manager)
        assert task_manager is not None, "Failed to create task manager"
        
        # Create task for tool generation using the first tool request
        tool_request = TOOL_GENERATION_REQUESTS[0]  # Using MathTool as example
        task = Task(
            name=f"Generate {tool_request['name']}",
            description=f"Generate a tool: {tool_request['name']}",
            tasksmanager_id=task_manager.id,
            crewai_config_id=crewai_config.id,
            curried_proxy_id=str(curried_proxy.id),
            agent_role="Senior Software Architect",
            input_data={
                "tool_request": tool_request,
                "use_langchain_patterns": True,
                "required_capabilities": [
                    "Mathematical operations",
                    "Error handling",
                    "Type hints",
                    "Documentation"
                ],
                "implementation_requirements": [
                    "Must use numpy for computations",
                    "Must validate input types",
                    "Must include proper error messages",
                    "Must be well-documented"
                ]
            }
        )
        
        # Create the task in persistence
        task = persistence_model.tasks.create(task)
        assert task is not None, "Failed to create task"
        
        # Initialize TaskRunner
        runner = TaskRunner(persistence_model)
        
        # Execute the task
        result = await runner.run_task(
            tasksmanager_id=task_manager.id,
            task_id=task.id
        )
        
        # Store state for verification
        test_state['task_result'] = result
        test_state['task_runner'] = runner
        test_state['persistence_model'] = persistence_model
        test_state['task'] = task
        test_state['curried_proxy'] = curried_proxy
        
        # Verify execution was successful
        assert result is not None, "Task execution result is None"
        assert isinstance(result, dict), "Task execution result is not a dictionary"
        assert 'status' in result, "Task execution result missing status field"
        assert result['status'] in ["completed", "success"], f"Task execution failed with status: {result['status']}"
        
        logger.info("✅ CrewAI execution completed successfully")
        return test_state
        
    except Exception as e:
        logger.error(f"Test failed: {str(e)}", exc_info=True)
        raise
