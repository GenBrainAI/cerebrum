from typing import Dict, Any, Optional, List
import logging
from datetime import datetime
import asyncio

from ..models.message import Message
from ..models.tasks_manager import TasksManager
from ..models.task import Task
from ..controllers.tools_operator import ToolsOperator
from ..controllers.operator import ToolsOperator as APIOperator
from ..controllers.curried_proxy import CurriedProxy
from ..controllers.crew_runner import run_crew_task
from ..context.context_provider import ContextProvider
from ..context.context_analytics import ContextAnalytics
from ..controllers.task_tree_controller import TaskNode
from ..persistence.persistence_model import PersistenceModelBase
from .task_observability import TaskObservabilityManager, ObservabilityLevel
from ..plugins.plugin_manager import PluginManager

logger = logging.getLogger(__name__)

class TaskExecutionError(Exception):
    """Exception raised when task execution fails."""
    pass

class TaskExecutor:
    """Wrapper class for Task that provides execution functionality."""
    
    def __init__(self, task: Task, task_runner: 'TaskRunner'):
        self.task = task
        self.task_runner = task_runner
        self.observability = TaskObservabilityManager(task.id)

    async def run(self, context: Dict[str, Any]) -> str:
        """Execute the task with the given context."""
        try:
            with self.observability:
                tasksmanager = self.task_runner.persistence_model.tasksmanagers.read(self.task.tasksmanager_id)
                result = await self.task_runner._run_standard_task(
                    task=self.task,
                    running_extra_params=context,
                    tasksmanager=tasksmanager
                )
                return result.get("response", "")
        except Exception as e:
            raise TaskExecutionError(f"Task execution failed: {str(e)}")

    def __getattr__(self, name: str) -> Any:
        """Forward attribute access to the wrapped task."""
        return getattr(self.task, name)

    @property
    def id(self) -> str:
        """Explicitly forward id property to task."""
        return self.task.id

    @property
    def name(self) -> str:
        """Explicitly forward name property to task."""
        return self.task.name

    @property
    def tasksmanager_id(self) -> str:
        """Explicitly forward tasksmanager_id property to task."""
        return self.task.tasksmanager_id

class TaskRunner:
    """Runner for executing tasks."""

    def __init__(self, persistence_model: PersistenceModelBase):
        """Initialize TaskRunner with persistence model."""
        self.persistence_model = persistence_model
        self.tools_operator = ToolsOperator()
        self.operator = APIOperator()
        self.observability_managers: Dict[str, TaskObservabilityManager] = {}
        self.context_provider = ContextProvider(persistence_model)
        self.context_analytics = ContextAnalytics()
        self._active_observability_managers = {}
        self._active_tasks = set()  # Track currently running tasks
        self._task_locks = {}  # Locks for each task
        self._task_results = {}  # Store task results
        self._task_errors = {}  # Store task errors
        self._task_status = {}  # Store task status
        self._plugin_manager = None  # Plugin manager instance
        self._initialized = False

    async def initialize(self):
        """Initialize the task runner components."""
        if self._initialized:
            return

        logger.info("🚀 Initializing TaskRunner")
        try:
            # Initialize operator if not already initialized
            if not hasattr(self, 'operator') or not self.operator:
                logger.info("⚙️ Initializing ToolsOperator")
                self.operator = APIOperator(api_provider="openai")
                logger.info("✅ ToolsOperator initialized")
            
            # Initialize context provider if needed
            if not self.context_provider:
                logger.info("📚 Initializing ContextProvider")
                self.context_provider = ContextProvider()
                logger.info("✅ ContextProvider initialized")

            # Initialize plugin manager
            if not self._plugin_manager:
                logger.info("🔌 Initializing PluginManager")
                self._plugin_manager = PluginManager()
                logger.info("✅ PluginManager initialized")

            # Load default plugins
            logger.info("🔌 Loading default plugins...")
            from pathlib import Path
            from ..plugins.agent_framework_config import AgentFrameworkConfig

            # Get plugins directory
            plugins_dir = Path(__file__).parent.parent / "plugins"
            
            # Load CrewAI plugin
            crewai_config = AgentFrameworkConfig(
                name="crewai",
                version="1.0.0",
                description="CrewAI framework integration",
                settings={
                    "model": "gpt-4",
                    "temperature": 0.7,
                    "max_tokens": 2000
                }
            )
            
            crewai_path = plugins_dir / "crewai_plugin.py"
            if crewai_path.exists():
                success = await self._plugin_manager.load_plugin(
                    str(crewai_path),
                    crewai_config
                )
                if success:
                    logger.info("✅ CrewAI plugin loaded successfully")
                else:
                    logger.error("❌ Failed to load CrewAI plugin")
            else:
                logger.warning("⚠️ CrewAI plugin file not found")
            
            self._initialized = True
            logger.info("✅ TaskRunner initialization complete")
            
        except Exception as e:
            error_msg = f"Failed to initialize TaskRunner: {str(e)}"
            logger.error(error_msg)
            raise RuntimeError(error_msg)

    async def _update_task_status(self, task: Task, status: str, error: Optional[str] = None):
        """Update task status and error message."""
        try:
            task.status = status
            task.error = error
            task.updated_at = datetime.now()
            self.persistence_model.tasks.update(task)
        except Exception as e:
            logger.error(f"❌ Failed to update task status: {str(e)}")

    def get_task_observability(self, task_id: str) -> Optional[TaskObservabilityManager]:
        """Get the observability manager for a task."""
        return self._active_observability_managers.get(task_id)

    def _initialize_observability(self, task_id: str) -> TaskObservabilityManager:
        """Initialize observability for a task."""
        if task_id not in self._active_observability_managers:
            logger.info(f"📊 Creating new observability manager for task {task_id}")
            observability = TaskObservabilityManager(task_id)
            self._active_observability_managers[task_id] = observability
            observability.start_capture()
            logger.info("✅ Observability manager created and started")
        return self._active_observability_managers[task_id]

    async def run_task(
        self,
        tasksmanager_id: str,
        task_id: str,
        running_extra_params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Run a task with the given ID."""
        try:
            # Initialize if not already done
            if not self._initialized:
                await self.initialize()

            # Get task and manager
            task = self.persistence_model.tasks.read(task_id)
            manager = self.persistence_model.tasksmanagers.read(tasksmanager_id)
            
            if not task or not manager:
                logger.error(f"Task {task_id} or manager {tasksmanager_id} not found")
                return {"status": "error", "error": "Task or manager not found"}

            # Create observability manager
            observability = self._initialize_observability(task_id)

            try:
                # Update task status to running
                await self._update_task_status(task, "running")

                # Get curried proxy for tools
                curried_proxy = self._get_or_create_curried_proxy(task, manager)
                print(f"\n🔧 Using curried proxy with {len(curried_proxy.list_tools())} tools")
                
                # Initialize messages with system messages
                messages = task.get_system_messages()

                # Add messages from running params
                if running_extra_params and "messages" in running_extra_params:
                    messages.extend(running_extra_params["messages"])
                
                # Prepare messages with context
                messages = await self.context_provider.prepare_task_messages(
                    task_id=task.id,
                    messages=messages
                )

                # Execute completion using manager's model
                print("\n🤖 Executing completion with curried proxy")
                response = await self.operator.completion(
                    tasksmanager_id=task.tasksmanager_id,
                    task_id=task.id,
                    messages=messages,
                    model=manager.model,
                    curried_proxy=curried_proxy
                )
                print("✅ Completion executed successfully")

                # Update task status
                await self._update_task_status(task, "completed")
                
                return {"status": "completed", "response": response}

            except Exception as e:
                error_msg = str(e)
                await self._update_task_status(task, "error", error_msg)
                return {"status": "error", "error": error_msg}

            finally:
                if task_id in self._active_observability_managers:
                    self._active_observability_managers[task_id].stop_capture()
                    del self._active_observability_managers[task_id]

        except Exception as e:
            error_msg = f"Failed to run task: {str(e)}"
            logger.error(f"❌ {error_msg}")
            return {"status": "error", "error": error_msg}

    async def _run_standard_task(
        self,
        task: Task,
        running_extra_params: Optional[Dict[str, Any]],
        tasksmanager: TasksManager
    ) -> Dict[str, Any]:
        """Run a standard (non-CrewAI) task."""
        logger.info(f"🔄 Running standard task: {task.name}")
        
        # Merge task data with extra params
        task_data = task.dict()
        if running_extra_params:
            task_data.update(running_extra_params)
            
        # Get the appropriate plugin based on the task's framework
        framework = task_data.get("framework", "default")
        plugin = self._plugin_manager.get_plugin(framework)
        
        if not plugin:
            raise Exception(f"Plugin for framework '{framework}' not found")
            
        # Create agent and execute task
        agent = await plugin.create_agent(task_data)
        result = await plugin.execute_task(agent, task_data)
        
        # Update task with result
        task.status = "completed"
        task.result = result
        self.persistence_model.tasks.update(task)
        
        return result

    async def _run_crewai_task(
        self,
        task: Task,
        tasksmanager: TasksManager,
        running_extra_params: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Execute a CrewAI task with context support."""
        try:
            logger.info(f"\n🤖 Running CrewAI task: {task.id}")
            
            # Get contexts for crew task
            query = running_extra_params.get("query") if running_extra_params else None
            logger.info(f"🔍 Getting contexts with query: {query}")
            contexts = await self.context_provider.get_task_contexts(
                task_id=task.id,
                query=query
            )
            logger.info(f"✅ Found {len(contexts)} contexts")

            # Add contexts to running params
            context_params = {"contexts": contexts}
            running_params = {**(running_extra_params or {}), **context_params}
            logger.info(f"🔧 Running params: {running_params}")

            # Run the crew task
            logger.info("\n🚀 Executing crew task")
            result = await run_crew_task(task.id, running_params)
            logger.info("✅ Crew task executed successfully")
            
            return result

        except Exception as e:
            error_msg = f"Error in CrewAI task execution: {str(e)}"
            logger.error(error_msg)
            logger.info(f"❌ {error_msg}")
            raise

    def _get_or_create_curried_proxy(
        self,
        task: Task,
        tasksmanager: TasksManager
    ) -> CurriedProxy:
        """Get existing curried proxy or create new one with tools."""
        logger.info(f"\n🔍 Getting curried proxy for task: {task.id}")
        
        curried_proxy = None
        if task.curried_proxy_id:
            logger.info(f"🔄 Loading existing proxy with ID: {task.curried_proxy_id}")
            curried_proxy = self.persistence_model.curried_proxies.read(task.curried_proxy_id)
            if curried_proxy:
                logger.info("✅ Successfully loaded existing proxy")
            else:
                logger.info("⚠️ Failed to load existing proxy")
        
        if not curried_proxy:
            logger.info("🆕 Creating new curried proxy")
            curried_proxy = CurriedProxy()
            
        # Add tools from both tasksmanager and task
        tasksmanager_toolsets = getattr(tasksmanager, 'toolsets', []) or []
        task_toolsets = getattr(task, 'toolsets', []) or []
        
        logger.info(f"📦 Found {len(tasksmanager_toolsets)} manager toolsets and {len(task_toolsets)} task toolsets")
        
        # Add tools to proxy
        self._add_tools_to_proxy(curried_proxy, tasksmanager_toolsets + task_toolsets)
        
        # Log registered tools
        tools = curried_proxy.list_tools()
        logger.info(f"🛠️ Registered tools in proxy: {', '.join(tools) if tools else 'None'}")
                
        return curried_proxy

    def _add_tools_to_proxy(self, curried_proxy: CurriedProxy, toolset_ids: list) -> None:
        """Add tools from toolsets to curried proxy."""
        import re

        def sanitize_name(name: str) -> str:
            """Sanitize name to match pattern ^[a-zA-Z0-9_-]+$"""
            # Replace any character that isn't alphanumeric, hyphen, or underscore with underscore
            sanitized = re.sub(r'[^a-zA-Z0-9_-]', '_', name)
            # Ensure name starts with a letter or underscore
            if sanitized and sanitized[0].isdigit():
                sanitized = f"_{sanitized}"
            return sanitized

        for toolset_id in toolset_ids:
            toolset = self.persistence_model.toolsets.read(toolset_id)
            if toolset and toolset.tool_ids:
                for tool_id in toolset.tool_ids:
                    tool = self.persistence_model.tools.read(tool_id)
                    if tool:
                        # Sanitize the toolset name before concatenation
                        sanitized_toolset_name = sanitize_name(toolset.name)
                        tool_name = f"{sanitized_toolset_name}_{tool.function.name}"
                        curried_proxy.add_tool(tool_name, tool)

    async def completion(
        self, 
        tasksmanager_id: str, 
        task_id: str, 
        messages: List[Message], 
        model: Optional[str] = None,
        curried_proxy: Optional[CurriedProxy] = None
    ) -> str:
        """Execute a completion task."""
        return await self.operator.completion(
            tasksmanager_id=tasksmanager_id,
            task_id=task_id,
            messages=messages,
            model=model,
            curried_proxy=curried_proxy
        )

    async def run_sequential_tasks(
        self, 
        task_ids: List[str], 
        initial_context: Dict
    ) -> List[Dict]:
        """Run tasks in sequence, passing context forward"""
        responses = []
        current_context = initial_context.copy()
        
        for task_id in task_ids:
            task = self.persistence_model.tasks.read(task_id)
            node = TaskNode(task)
            
            response = await node.run(current_context)
            result = {
                "task_id": task_id,
                "response": response,
                "timestamp": datetime.now().isoformat()
            }
            
            responses.append(result)
            current_context["previous_response"] = response
            
        return responses

    def wrap_task(self, task: Task) -> TaskExecutor:
        """Wrap a Task model in a TaskExecutor."""
        return TaskExecutor(task, self)