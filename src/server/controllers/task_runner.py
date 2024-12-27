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
from .task_observability import TaskObservabilityManager

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
    """Task runner with added context awareness through ContextProvider."""

    def __init__(self, persistence_model: PersistenceModelBase):
        self.persistence_model = persistence_model
        self.operator = ToolsOperator()
        self.context_provider = ContextProvider()
        self.context_analytics = ContextAnalytics()
        self.logger = logging.getLogger(__name__)
        self._active_observability_managers: Dict[str, TaskObservabilityManager] = {}

    async def initialize(self):
        """Initialize the task runner and its components."""
        try:
            # Initialize context provider
            await self.context_provider.initialize()
        except Exception as e:
            self.logger.error(f"Error initializing task runner: {str(e)}")
            raise

    async def run_task(
        self,
        tasksmanager_id: str,
        task_id: str,
        running_extra_params: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Run a task with integrated context support."""
        try:
            # Ensure context provider is initialized
            await self.initialize()

            # Get task and tasksmanager
            task: Task = self.persistence_model.tasks.read(task_id)
            if task is None:
                raise ValueError(f"Task {task_id} not found")

            tasksmanager = self.persistence_model.tasksmanagers.read(tasksmanager_id)
            if tasksmanager is None:
                raise ValueError(f"TasksManager {tasksmanager_id} not found")

            if task.tasksmanager_id != tasksmanager_id:
                raise ValueError(f"Task {task_id} does not belong to TasksManager {tasksmanager_id}")

            # Create observability manager for this task
            observability = TaskObservabilityManager(task_id)
            self._active_observability_managers[task_id] = observability

            try:
                with observability:
                    # Start monitoring in background
                    monitor_task = asyncio.create_task(observability.monitor_execution())

                    # Determine execution path based on task type
                    if task.crewai_config_id:
                        result = await self._run_crewai_task(task, tasksmanager, running_extra_params)
                    else:
                        result = await self._run_standard_task(task, tasksmanager, running_extra_params)

                    # Add final execution stats
                    if isinstance(result, dict):
                        observability.add_execution_stats(result)

                    return result

            finally:
                # Clean up
                monitor_task.cancel()
                del self._active_observability_managers[task_id]

        except Exception as e:
            self.logger.error(f"Error running task {task_id}: {str(e)}", exc_info=True)
            raise

    def get_task_observability(self, task_id: str) -> Optional[TaskObservabilityManager]:
        """Get the observability manager for a task if it exists."""
        return self._active_observability_managers.get(task_id)

    async def _run_standard_task(
        self,
        task: Task,
        tasksmanager: TasksManager,
        running_extra_params: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Execute a standard task with context support."""
        try:
            # Get curried proxy for tools
            curried_proxy = self._get_or_create_curried_proxy(task, tasksmanager)
            
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

            # Execute completion
            response = await self.operator.completion(
                tasksmanager_id=tasksmanager.id,
                task_id=task.id,
                messages=messages,
                model=tasksmanager.model,
                curried_proxy=curried_proxy
            )
            
            return {"response": response}

        except Exception as e:
            self.logger.error(f"Error in standard task execution: {str(e)}")
            raise

    async def _run_crewai_task(
        self,
        task: Task,
        tasksmanager: TasksManager,
        running_extra_params: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Execute a CrewAI task with context support."""
        try:
            # Get contexts for crew task
            query = running_extra_params.get("query") if running_extra_params else None
            contexts = await self.context_provider.get_task_contexts(
                task_id=task.id,
                query=query
            )

            # Add contexts to running params
            context_params = {"contexts": contexts}
            running_params = {**(running_extra_params or {}), **context_params}

            return await run_crew_task(task.id, running_params)

        except Exception as e:
            self.logger.error(f"Error in CrewAI task execution: {str(e)}")
            raise

    def _get_or_create_curried_proxy(
        self,
        task: Task,
        tasksmanager: TasksManager
    ) -> CurriedProxy:
        """Get existing curried proxy or create new one with tools."""
        curried_proxy = None
        if task.curried_proxy_id:
            curried_proxy = self.persistence_model.curried_proxies.read(task.curried_proxy_id)
        
        if not curried_proxy:
            curried_proxy = CurriedProxy()
            
        # Add tools from both tasksmanager and task
        tasksmanager_toolsets = getattr(tasksmanager, 'toolsets', []) or []
        task_toolsets = getattr(task, 'toolsets', []) or []
        
        self._add_tools_to_proxy(curried_proxy, tasksmanager_toolsets + task_toolsets)
                
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