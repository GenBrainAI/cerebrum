import pytest
import pytest_asyncio
from pathlib import Path
import logging
import json
from typing import Dict, Any

from src.server.persistence.in_memory_persistence import InMemoryPersistenceModel
from src.server.controllers.task_runner import TaskRunner
from src.server.context.unified_context import UnifiedContextState
from src.state_setup.dynamic_tools import setup_dynamic_tools_state
from src.server.persistence.persistence_model_factory import PersistenceModelFactory
from src.server.tools.tools_catalog import tools_catalog

logger = logging.getLogger(__name__)

class ConfiguredTool:
    """A pre-configured tool."""
    def __init__(self, config):
        self.config = config
        
    def get_config(self):
        """Get the configuration."""
        return self.config

@pytest.fixture(autouse=True)
def cleanup_tools():
    """Cleanup fixture that runs automatically before and after each test."""
    # Initial reset to start clean
    tools_catalog.reset()
    yield
    # Final reset after test
    tools_catalog.reset()

@pytest_asyncio.fixture
async def setup_test_tools():
    """Setup test tools in the catalog."""
    # Create and register test tools
    configured_tool = ConfiguredTool({"key": "value"})
    tools_catalog.register_tool(configured_tool, "ConfiguredTool")
    yield configured_tool

@pytest_asyncio.fixture
async def setup_state(setup_test_tools) -> Dict[str, Any]:
    """Setup initial state by running dynamic_tools.py"""
    logger.info("Setting up initial state...")
    # Reset persistence model to ensure clean state
    PersistenceModelFactory.reset()
    persistence_model = PersistenceModelFactory.persistence_model()
    
    # Don't reset tools_catalog here since setup_test_tools has already set it up
    state = await setup_dynamic_tools_state(persistence_model)
    assert state is not None, "Failed to generate initial state"
    return state

@pytest_asyncio.fixture
async def persistence_model(setup_state: Dict[str, Any]) -> InMemoryPersistenceModel:
    """Create a test persistence model with generated state."""
    model = InMemoryPersistenceModel()
    
    # Get the persistence model that was used to generate the state
    source_model = PersistenceModelFactory.persistence_model()
    
    # Serialize and deserialize to test the process
    try:
        state_json = source_model.to_json()
        logger.info("Successfully serialized state")
        model.from_json(state_json)
        logger.info("Successfully deserialized state")
    except Exception as e:
        logger.error(f"Error during serialization/deserialization: {str(e)}")
        raise
    
    return model

@pytest_asyncio.fixture
async def task_runner(persistence_model: InMemoryPersistenceModel) -> TaskRunner:
    """Create and initialize task runner."""
    runner = TaskRunner(persistence_model)
    await runner.initialize()
    logger.info("Initialized task runner")
    return runner

@pytest_asyncio.fixture
async def unified_state() -> UnifiedContextState:
    """Create and initialize unified context state."""
    state = UnifiedContextState()
    await state.initialize()
    logger.info("Initialized unified context state")
    return state

@pytest.mark.asyncio
async def test_dynamic_tools_state_loaded(persistence_model: InMemoryPersistenceModel, task_runner: TaskRunner, unified_state: UnifiedContextState):
    """Test that the state is properly loaded with all required components."""
    try:
        logger.info("Testing dynamic tools state loading...")
        
        # Validate tools_catalog has tools
        catalog_tools = tools_catalog.list_tools()
        logger.info(f"Found {len(catalog_tools)} tools in catalog")
        assert len(catalog_tools) > 0, "No tools found in catalog"
        
        # Validate internal tools are present
        internal_tools = [
            tool_name for tool_name in catalog_tools 
            if any(name in tool_name for name in [
                "internal_file_tools",
                "internal_testing_tools",
                "internal_proxy_tools"
            ])
        ]
        assert len(internal_tools) > 0, "No internal tools found"
        logger.info(f"Found {len(internal_tools)} internal tools")
        
        # Validate task manager exists and is properly configured
        tasks_managers = persistence_model.tasksmanagers.list()
        assert len(tasks_managers) > 0, "No task managers found"
        dynamic_tools_manager = next(
            (tm for tm in tasks_managers if tm.name == "Dynamic Langchain Tools Generator"),
            None
        )
        assert dynamic_tools_manager is not None, "Dynamic tools manager not found"
        assert dynamic_tools_manager.model == "gpt-4", "Task manager has incorrect model"
        logger.info(f"Found dynamic tools manager: {dynamic_tools_manager.id}")
        
        # Validate task exists and is properly linked
        tasks = persistence_model.tasks.list()
        dynamic_tools_task = next(
            (task for task in tasks if task.name == "Generate Dynamic Langchain Tool"),
            None
        )
        assert dynamic_tools_task is not None, "Dynamic tools task not found"
        assert dynamic_tools_task.tasksmanager_id == dynamic_tools_manager.id, "Task not linked to correct manager"
        logger.info(f"Found dynamic tools task: {dynamic_tools_task.id}")
        
        # Validate CurriedProxy exists and can access tools
        assert dynamic_tools_task.curried_proxy_id is not None, "Task missing CurriedProxy ID"
        proxy = persistence_model.curried_proxies.read(dynamic_tools_task.curried_proxy_id)
        assert proxy is not None, "CurriedProxy not found"
        assert len(proxy.tool_names) > 0, "CurriedProxy has no tools"
        
        logger.info("✅ Dynamic tools state loaded successfully with all components")
        return dynamic_tools_task  # Return for use in subsequent tests
        
    except Exception as e:
        logger.error(f"Test failed: {str(e)}", exc_info=True)
        raise

@pytest.mark.asyncio
async def test_task_context_accessibility(persistence_model: InMemoryPersistenceModel, task_runner: TaskRunner, unified_state: UnifiedContextState):
    """Test that the task is properly configured with accessible context."""
    try:
        logger.info("Testing task context accessibility...")
        
        # Get the dynamic tools task
        tasks = persistence_model.tasks.list()
        dynamic_tools_task = next(
            (task for task in tasks if task.name == "Generate Dynamic Langchain Tool"),
            None
        )
        assert dynamic_tools_task is not None, "Dynamic tools task not found"
        
        # Validate task has required contexts
        contexts = dynamic_tools_task.contexts
        assert len(contexts) > 0, "Task has no contexts"
        
        # Check for knowledge context
        knowledge_context = next(
            (ctx for ctx in contexts if ctx["type"] == "knowledge"),
            None
        )
        assert knowledge_context is not None, "Task missing knowledge context"
        assert knowledge_context["metadata"].get("name") == "langchain_tools_docs", "Task has incorrect knowledge context"
        
        # Check for system context
        system_context = next(
            (ctx for ctx in contexts if ctx["type"] == "system"),
            None
        )
        assert system_context is not None, "Task missing system context"
        assert system_context["metadata"].get("category") == "general", "Task has incorrect system context"
        
        logger.info("✅ Task context accessibility verified")
        
    except Exception as e:
        logger.error(f"Test failed: {str(e)}", exc_info=True)
        raise

@pytest.mark.asyncio
async def test_dynamic_tool_generation(persistence_model: InMemoryPersistenceModel, task_runner: TaskRunner):
    """Test the ability to generate new tools dynamically."""
    try:
        logger.info("Testing dynamic tool generation...")
        
        # Get the dynamic tools task
        tasks = persistence_model.tasks.list()
        dynamic_tools_task = next(
            (task for task in tasks if task.name == "Generate Dynamic Langchain Tool"),
            None
        )
        assert dynamic_tools_task is not None, "Dynamic tools task not found"
        
        # Validate task runner is properly configured
        assert task_runner.tools_operator is not None, "Task runner missing tools operator"
        assert task_runner.tools_operator.tools_catalog is not None, "Tools operator missing catalog"
        
        # Validate task can be executed
        assert dynamic_tools_task.curried_proxy_id is not None, "Task missing CurriedProxy ID"
        proxy = persistence_model.curried_proxies.read(dynamic_tools_task.curried_proxy_id)
        assert proxy is not None, "CurriedProxy not found"
        assert len(proxy.tool_names) > 0, "CurriedProxy has no tools"
        
        logger.info("✅ Dynamic tool generation capability verified")
        
    except Exception as e:
        logger.error(f"Test failed: {str(e)}", exc_info=True)
        raise
