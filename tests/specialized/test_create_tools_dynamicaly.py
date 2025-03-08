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
import logging
import json
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime
import traceback
from unittest.mock import patch, MagicMock, AsyncMock

from src.server.models.task import Task
from src.server.models.tasks_manager import TasksManager
from src.server.persistence.in_memory_persistence import InMemoryPersistenceModel
from src.server.persistence.persistence_model_factory import PersistenceModelFactory
from src.server.controllers.task_runner import TaskRunner
from src.server.tools.tools_catalog import ToolsCatalog
from src.server.controllers.curried_proxy import CurriedProxy
from src.state_setup.dynamic_tools import setup_dynamic_tools_state
from src.server.tools.tools_metrics import ToolExecutionMetrics
from src.server.models.agent import CrewAIConfig, CreateCrewRequest, AgentModel, ToolModel
from src.server.models.persistence_models import StorageType
from src.server.context.context_provider import ContextProvider
from crewai.tools import BaseTool as CrewAITool
from pydantic import BaseModel, Field, create_model, ConfigDict

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Constants for test configuration
DYNAMIC_TOOLS_STATE_FILE = "state/specialized/dynamic_tools_state.json"

@pytest.fixture(scope="module")
def test_state():
    """Fixture to share state between tests."""
    return {
        "tool_metrics": ToolExecutionMetrics(),
        "persistence_model": None,
        "generated_state": None,
        "crewai_config": None,
        "state_file": None,
        "local_model": None
    }

@pytest.fixture(scope="module")
def temp_state_file(tmp_path_factory):
    """Create a temporary state file path."""
    tmp_path = tmp_path_factory.mktemp("dynamic_tools")
    return str(tmp_path / "test_state.json")

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
        self._context_content = {}  # Store context content
        
    def __call__(self, **kwargs) -> Dict[str, Any]:
        """Make the tool callable."""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                return loop.create_task(self._arun(**kwargs))
            else:
                return asyncio.run(self._arun(**kwargs))
        except Exception as e:
            return {"error": str(e)}
        
    async def _arun(self, **kwargs) -> Dict[str, Any]:
        """Mock async execution that returns test data."""
        try:
            self._execution_metrics.start_time = datetime.now()
            
            if self.name == "internal_file_tools.read_documentation":
                # Check if we have context content for this file path
                file_path = kwargs.get('file_path', '')
                if "langchain_tools_guide" in file_path:
                    return {"content": """# Langchain Tool Creation Guide
                    Tools in Langchain must:
                    1. Implement _run and _arun methods
                    2. Include proper type hints
                    3. Handle errors appropriately
                    4. Support async operations
                    5. Include comprehensive documentation
                    """}
                elif "tool_example" in file_path:
                    return {"content": """
                    from langchain.tools import BaseTool
                    from pydantic import BaseModel, Field
                    
                    class CalculatorInput(BaseModel):
                        operation: str = Field(description="The math operation to perform")
                        numbers: List[float] = Field(description="Numbers to operate on")
                        
                    class CalculatorTool(BaseTool):
                        name = "calculator"
                        description = "Perform mathematical calculations"
                        args_schema = CalculatorInput
                        
                        def _run(self, operation: str, numbers: List[float]) -> float:
                            if operation == "add":
                                return sum(numbers)
                            elif operation == "multiply":
                                return math.prod(numbers)
                            raise ValueError(f"Unknown operation: {operation}")
                            
                        async def _arun(self, operation: str, numbers: List[float]) -> float:
                            return self._run(operation, numbers)
                    """}
                else:
                    return {"content": "# No documentation found for this path"}
                    
            elif self.name == "internal_credentials_tools.load_credentials":
                result = {"credentials": {"API_KEY": "test_key", "DATABASE_URL": "test_url"}}
                
            elif self.name == "internal_file_tools.save_implementation":
                code = kwargs.get('code', '')
                tool_name = kwargs.get('tool_name', 'test')
                file_path = f"/tmp/{tool_name}.py"
                
                logger.info(f"Mock save_implementation called with tool_name={tool_name}")
                logger.info(f"Attempting to save to {file_path}")
                
                try:
                    # Actually save the file
                    with open(file_path, 'w') as f:
                        f.write(code)
                    logger.info(f"Successfully saved implementation to {file_path}")
                except Exception as e:
                    logger.error(f"Failed to save implementation: {str(e)}")
                    raise
                
                result = {"path": file_path}
                
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

    def add_context(self, file_path: str, content: str):
        """Add context content for a specific file path."""
        self._context_content[file_path] = content

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

@pytest.fixture(scope="module", autouse=True)
def setup_mock_tools():
    """Set up mock tools for testing."""
    # Register mock tools in the catalog
    for name, tool in MOCK_TOOLS.items():
        tools_catalog.register_instance(tool, name)
    
    yield MOCK_TOOLS
    
    # Cleanup
    tools_catalog.reset()

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

@pytest.mark.order(1)
@pytest.mark.asyncio
async def test_dynamic_tools_state_generation(test_state, temp_state_file):
    """Test step 1: Generate dynamic tools state."""
    try:
        logger.info("Step 1: Generating dynamic tools state...")
        
        # Reset persistence model to ensure clean state
        PersistenceModelFactory.reset()
        persistence_model = PersistenceModelFactory.persistence_model()
        
        # Generate state with mocked storage location
        with patch('src.state_setup.dynamic_tools.StorageLocation') as mock_storage_location:
            mock_storage_location.return_value.type = StorageType.file
            mock_storage_location.return_value.location = str(Path(temp_state_file).parent)
            mock_storage_location.return_value.state_name = Path(temp_state_file).name
            
            state = await setup_dynamic_tools_state(persistence_model, temp_state_file)
            
        assert state is not None, "Failed to generate initial state"
        
        # Store state for next tests
        test_state['generated_state'] = state
        test_state['persistence_model'] = persistence_model
        test_state['state_file'] = temp_state_file
        
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
    """Test step 2: Load state into local persistence."""
    try:
        logger.info("Step 2: Loading state into local persistence...")
        
        # Get state file path from previous test
        temp_state_file = test_state['state_file']
        assert Path(temp_state_file).exists(), f"State file not found at {temp_state_file}"
        
        # Create new persistence model for local state
        local_model = PersistenceModelFactory.persistence_model()
        
        # Load state with mocked storage location
        with patch('src.state_setup.dynamic_tools.StorageLocation') as mock_storage_location:
            mock_storage_location.return_value.type = StorageType.file
            mock_storage_location.return_value.location = str(Path(temp_state_file).parent)
            mock_storage_location.return_value.state_name = Path(temp_state_file).name
            
            await setup_dynamic_tools_state(local_model, temp_state_file)
        
        # Store local model for next tests
        test_state['local_model'] = local_model

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

@pytest.mark.order(5)
@pytest.mark.asyncio
async def test_tool_argument_schemas(test_state):
    """Test tool argument schemas are properly defined."""
    try:
        logger.info("Testing tool argument schemas...")
        
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

@pytest.mark.order(6)
@pytest.mark.asyncio
async def test_crewai_invocation(test_state):
    """Test CrewAI execution."""
    try:
        logger.info("Invoking CrewAI execution...")
        
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
                "model": "gpt-4o-mini",
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
        
        # Mock the plugin manager and CrewAI plugin
        from src.server.plugins.plugin_manager import PluginManager
        
        # Create a mock plugin that returns a successful result
        mock_plugin = MagicMock()
        # Use AsyncMock for async methods
        mock_plugin.create_agent = AsyncMock(return_value=MagicMock())
        mock_plugin.execute_task = AsyncMock(return_value={
            "status": "success",
            "response": "Task completed successfully",
            "generated_tool": {
                "name": tool_request['name'],
                "description": f"Generated {tool_request['name']} implementation"
            }
        })
        
        # Create a mock plugin manager
        runner._plugin_manager = MagicMock(spec=PluginManager)
        runner._plugin_manager.get_plugin = MagicMock(return_value=mock_plugin)
        
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
        logger.error(f"Test failed: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        raise

@pytest.mark.order(7)
@pytest.mark.asyncio
async def test_crewai_invocation_with_context(test_state):
    """Test CrewAI execution with context management."""
    try:
        logger.info("Invoking CrewAI execution with context...")
        
        # Import mocking utilities
        from unittest.mock import MagicMock, AsyncMock
        from src.server.plugins.plugin_manager import PluginManager
        
        # Initialize persistence model and context provider
        persistence_model = InMemoryPersistenceModel()
        context_provider = ContextProvider()
        
        # Create curried proxy with tools
        curried_proxy = CurriedProxy()
        for name, tool in MOCK_TOOLS.items():
            curried_proxy.add_tool(name, tool)
        curried_proxy = persistence_model.curried_proxies.create(curried_proxy)
        
        # Create CrewAI config using the predefined CREWAI_CONFIG
        crewai_config = CrewAIConfig(
            create_crew=CreateCrewRequest(**CREWAI_CONFIG),
            model_config={
                "model": "gpt-4o-mini",
                "temperature": 0.7,
                "max_tokens": 2000
            }
        )
        crewai_config = persistence_model.crewai_config.create(crewai_config)
        
        # Create task manager with context
        task_manager = TasksManager(
            name="Dynamic Tools Manager with Context",
            description="Manager for dynamic tools generation tasks with context",
            crewai_config_id=crewai_config.id,
            use_context=True  # Enable context usage
        )
        task_manager = persistence_model.tasksmanagers.create(task_manager)
        
        # Create task with context enabled
        tool_request = TOOL_GENERATION_REQUESTS[0]
        task = Task(
            name=f"Generate {tool_request['name']} with Context",
            description=f"Generate a tool: {tool_request['name']}",
            tasksmanager_id=task_manager.id,
            crewai_config_id=crewai_config.id,
            curried_proxy_id=str(curried_proxy.id),
            agent_role="Senior Software Architect",
            use_context=True,  # Enable context usage
            inherit_manager_context=True,  # Inherit context from manager
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
        task = persistence_model.tasks.create(task)
        
        # Add Langchain documentation context
        docs_content = """# Langchain Tool Creation Guide
        Tools in Langchain must:
        1. Implement _run and _arun methods
        2. Include proper type hints
        3. Handle errors appropriately
        4. Support async operations
        5. Include comprehensive documentation
        """
        
        # Mock the context provider methods
        context_provider.add_context_to_task = MagicMock(return_value="context-id-123")
        context_provider.get_contexts = AsyncMock(return_value=[
            {
                "id": "context-id-123",
                "type": "documentation",
                "source_id": "langchain-docs",
                "content": docs_content,
                "metadata": {"source": "documentation"},
                "priority": 80
            }
        ])
        
        # Initialize TaskRunner with mocked context provider
        runner = TaskRunner(persistence_model)
        runner.context_provider = context_provider
        
        # Mock the plugin manager and CrewAI plugin
        from unittest.mock import MagicMock, AsyncMock
        from src.server.plugins.plugin_manager import PluginManager
        
        # Create a mock plugin that returns a successful result
        mock_plugin = MagicMock()
        # Use AsyncMock for async methods
        mock_plugin.create_agent = AsyncMock(return_value=MagicMock())
        mock_plugin.execute_task = AsyncMock(return_value={
            "status": "success",
            "response": "Task completed successfully with context",
            "generated_tool": {
                "name": tool_request['name'],
                "description": f"Generated {tool_request['name']} implementation with context"
            }
        })
        
        # Create a mock plugin manager
        runner._plugin_manager = MagicMock(spec=PluginManager)
        runner._plugin_manager.get_plugin = MagicMock(return_value=mock_plugin)
        
        # Execute the task
        result = await runner.run_task(
            tasksmanager_id=task_manager.id,
            task_id=task.id,
            running_extra_params={
                "messages": [
                    {
                        "role": "user",
                        "content": f"Create a {tool_request['name']} with numpy for mathematical operations"
                    }
                ]
            }
        )
        
        # Store state for verification
        test_state['context_task_result'] = result
        
        # Verify execution was successful
        assert result is not None, "Task execution result is None"
        assert isinstance(result, dict), "Task execution result is not a dictionary"
        assert 'status' in result, "Task execution result missing status field"
        assert result['status'] in ["completed", "success"], f"Task execution failed with status: {result['status']}"
        
        logger.info("✅ CrewAI execution with context completed successfully")
        return test_state
        
    except Exception as e:
        logger.error(f"Test failed: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        raise
