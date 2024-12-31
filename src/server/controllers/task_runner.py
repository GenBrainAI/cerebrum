from typing import Dict, Any, Optional, List
import logging
from datetime import datetime
import asyncio

from ..models.message import Message
from ..models.tasks_manager import TasksManager
from ..models.task import Task
from ..controllers.operator import ToolsOperator
from ..controllers.curried_proxy import CurriedProxy
from ..controllers.crew_runner import run_crew_task
from ..context.context_provider import ContextProvider
from ..context.context_analytics import ContextAnalytics
from ..controllers.task_tree_controller import TaskNode
from ..persistence.persistence_model import PersistenceModelBase
from .task_observability import TaskObservabilityManager, ObservabilityLevel

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
                result = await self.task_runner._run_standard_task(
                    task=self.task,
                    tasksmanager=self.task_runner.persistence_model.tasksmanagers.read(self.task.tasksmanager_id),
                    running_extra_params=context
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
    """Runs tasks with proper context and observability."""
    
    def __init__(self, persistence_model: Any):
        """Initialize the task runner."""
        self.persistence_model = persistence_model
        self.context_provider = ContextProvider()
        self._active_observability_managers = {}
        self.logger = logging.getLogger(__name__)
        self.operator = None  # Will be initialized in initialize()

    async def initialize(self):
        """Initialize the task runner components."""
        print("\n🚀 Initializing TaskRunner")
        try:
            # Initialize operator if not already initialized
            if not hasattr(self, 'operator') or not self.operator:
                print("⚙️ Initializing ToolsOperator")
                # Initialize with default OpenAI provider
                self.operator = ToolsOperator(api_provider="openai")
                print("✅ ToolsOperator initialized")
            
            # Initialize context provider if needed
            if not self.context_provider:
                print("📚 Initializing ContextProvider")
                self.context_provider = ContextProvider()
                print("✅ ContextProvider initialized")
            
            print("✅ TaskRunner initialization complete")
            
        except Exception as e:
            error_msg = f"Failed to initialize TaskRunner: {str(e)}"
            print(f"❌ {error_msg}")
            raise RuntimeError(error_msg)

    def get_task_observability(self, task_id: str) -> Optional[TaskObservabilityManager]:
        """Get the observability manager for a task."""
        return self._active_observability_managers.get(task_id)

    def _initialize_observability(self, task_id: str) -> TaskObservabilityManager:
        """Initialize observability for a task."""
        if task_id not in self._active_observability_managers:
            print(f"📊 Creating new observability manager for task {task_id}")
            from ..controllers.task_observability import TaskObservabilityManager
            observability = TaskObservabilityManager(task_id)
            self._active_observability_managers[task_id] = observability
            observability.start_capture()
            print("✅ Observability manager created and started")
        return self._active_observability_managers[task_id]

    async def run_task(
        self,
        tasksmanager_id: str,
        task_id: str,
        running_extra_params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Run a task with the given ID."""
        observability = None
        try:
            print(f"\n🚀 Running task {task_id} from manager {tasksmanager_id}")
            
            # Get task and manager
            task = self.persistence_model.tasks.read(task_id)
            if not task:
                raise ValueError(f"Task {task_id} not found")
            
            manager = self.persistence_model.tasksmanagers.read(tasksmanager_id)
            if not manager:
                raise ValueError(f"Task manager {tasksmanager_id} not found")
            
            print(f"✅ Found task '{task.name}' and manager '{manager.name}'")
            
            # Initialize observability for this task
            observability = self._initialize_observability(task_id)
            
            # Start monitoring in background
            monitor_task = asyncio.create_task(observability.monitor_execution())
            
            try:
                # Log task execution start
                observability.add_entry(
                    f"Starting execution of task: {task.name}",
                    ObservabilityLevel.INFO
                )
                observability.add_execution_stats({
                    "task_id": task_id,
                    "manager_id": tasksmanager_id,
                    "start_time": datetime.now().isoformat(),
                    "status": "running"
                })
                
                # Determine task type and run appropriate handler
                result = None
                
                # Check for crew task in both old and new ways
                is_crew_task = (
                    hasattr(task, 'crewai_config_id') and task.crewai_config_id or
                    hasattr(task, 'crew_config') and task.crew_config
                )
                
                if is_crew_task:
                    print("🤖 Running CrewAI task")
                    from .crew_runner import run_crew_task
                    result = await run_crew_task(
                        task_id=task_id,
                        task_input=running_extra_params,
                        persistence_model=self.persistence_model
                    )
                else:
                    print("⚙️ Running standard task")
                    result = await self._run_standard_task(task, running_extra_params or {})
                
                # Log successful execution
                observability.add_entry(
                    f"Task completed successfully: {task.name}",
                    ObservabilityLevel.INFO
                )
                observability.add_execution_stats({
                    "task_id": task_id,
                    "manager_id": tasksmanager_id,
                    "end_time": datetime.now().isoformat(),
                    "status": "completed",
                    "result": str(result)
                })
                
                return result
                
            except Exception as e:
                error_msg = f"Task execution failed: {str(e)}"
                print(f"❌ {error_msg}")
                
                # Log error in observability
                observability.add_entry(
                    error_msg,
                    ObservabilityLevel.ERROR
                )
                observability.add_execution_stats({
                    "task_id": task_id,
                    "manager_id": tasksmanager_id,
                    "end_time": datetime.now().isoformat(),
                    "status": "failed",
                    "error": str(e)
                })
                
                return {"error": error_msg, "response": error_msg}
            
            finally:
                # Cancel monitoring task
                monitor_task.cancel()
                try:
                    await monitor_task
                except asyncio.CancelledError:
                    pass
                
                # Stop observability capture
                if observability:
                    observability.stop_capture()
                
        except Exception as e:
            error_msg = f"Task runner error: {str(e)}"
            print(f"❌ {error_msg}")
            if observability:
                observability.add_entry(error_msg, ObservabilityLevel.ERROR)
                observability.stop_capture()
            return {"error": error_msg, "response": error_msg}

    async def _run_standard_task(
        self,
        task: Task,
        running_extra_params: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Execute a standard task with context support."""
        try:
            # Get task manager for model info
            manager = self.persistence_model.tasksmanagers.read(task.tasksmanager_id)
            if not manager:
                raise ValueError(f"Task manager {task.tasksmanager_id} not found")

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
            
            return {"response": response}

        except Exception as e:
            error_msg = f"Error in standard task execution: {str(e)}"
            print(f"❌ {error_msg}")
            raise

    async def _run_crewai_task(
        self,
        task: Task,
        tasksmanager: TasksManager,
        running_extra_params: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Execute a CrewAI task with context support."""
        try:
            print(f"\n🤖 Running CrewAI task: {task.id}")
            
            # Get contexts for crew task
            query = running_extra_params.get("query") if running_extra_params else None
            print(f"🔍 Getting contexts with query: {query}")
            contexts = await self.context_provider.get_task_contexts(
                task_id=task.id,
                query=query
            )
            print(f"📚 Found {len(contexts)} contexts")

            # Add contexts to running params
            context_params = {"contexts": contexts}
            running_params = {**(running_extra_params or {}), **context_params}
            print(f"🔧 Running params: {running_params}")

            # Run the crew task
            print("\n🚀 Executing crew task")
            result = await run_crew_task(task.id, running_params)
            print("✅ Crew task executed successfully")
            
            return result

        except Exception as e:
            error_msg = f"Error in CrewAI task execution: {str(e)}"
            self.logger.error(error_msg)
            print(f"❌ {error_msg}")
            raise

    def _get_or_create_curried_proxy(
        self,
        task: Task,
        tasksmanager: TasksManager
    ) -> CurriedProxy:
        """Get existing curried proxy or create new one with tools."""
        print(f"\n🔍 Getting curried proxy for task: {task.id}")
        
        curried_proxy = None
        if task.curried_proxy_id:
            print(f"🔄 Loading existing proxy with ID: {task.curried_proxy_id}")
            curried_proxy = self.persistence_model.curried_proxies.read(task.curried_proxy_id)
            if curried_proxy:
                print("✅ Successfully loaded existing proxy")
            else:
                print("⚠️ Failed to load existing proxy")
        
        if not curried_proxy:
            print("🆕 Creating new curried proxy")
            curried_proxy = CurriedProxy()
            
        # Add tools from both tasksmanager and task
        tasksmanager_toolsets = getattr(tasksmanager, 'toolsets', []) or []
        task_toolsets = getattr(task, 'toolsets', []) or []
        
        print(f"📦 Found {len(tasksmanager_toolsets)} manager toolsets and {len(task_toolsets)} task toolsets")
        
        # Add tools to proxy
        self._add_tools_to_proxy(curried_proxy, tasksmanager_toolsets + task_toolsets)
        
        # Log registered tools
        tools = curried_proxy.list_tools()
        print(f"🛠️ Registered tools in proxy: {', '.join(tools) if tools else 'None'}")
                
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