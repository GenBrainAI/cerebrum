from typing import Dict, Any, Optional, List
import logging
from datetime import datetime

from ..models.message import Message
from ..models.tasks_manager import TasksManager
from ..models.task import Task
from ..controllers.operator import ToolsOperator
from ..controllers.curried_proxy import CurriedProxy
from ..controllers.crew_runner import run_crew_task
from ..context.context_provider import ContextProvider
from ..context.crew_context_enhancer import CrewContextEnhancer, CrewContextConfig
from ..context.context_analytics import ContextAnalytics
from ..controllers.task_tree_controller import TaskNode

class TaskRunner:
    """Task runner with added context awareness through ContextProvider."""

    def __init__(self, persistence_model):
        self.persistence_model = persistence_model
        self.operator = ToolsOperator()
        self.context_provider = ContextProvider()
        self.context_analytics = ContextAnalytics()
        self.logger = logging.getLogger(__name__)

    async def run_task(
        self,
        tasksmanager_id: str,
        task_id: str,
        running_extra_params: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Run a task with integrated context support."""
        try:
            # Get task and tasksmanager
            task: Task = self.persistence_model.tasks.read(task_id)
            if task is None:
                raise ValueError(f"Task {task_id} not found")

            tasksmanager = self.persistence_model.tasksmanagers.read(tasksmanager_id)
            if tasksmanager is None:
                raise ValueError(f"TasksManager {tasksmanager_id} not found")

            if task.tasksmanager_id != tasksmanager_id:
                raise ValueError(f"Task {task_id} does not belong to TasksManager {tasksmanager_id}")

            # Determine execution path based on task type
            if task.crewai_info_id:
                return await self._run_crewai_task(task, tasksmanager, running_extra_params)
            else:
                return await self._run_standard_task(task, tasksmanager, running_extra_params)

        except Exception as e:
            self.logger.error(f"Error running task {task_id}: {str(e)}", exc_info=True)
            raise

    async def _run_standard_task(
        self,
        task: Task,
        tasksmanager: TasksManager,
        running_extra_params: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Execute a standard task with context support."""
        try:
            # Get contexts
            contexts = await self.context_provider.get_task_contexts(
                task_id=task.id,
                query=running_extra_params.get("query") if running_extra_params else None
            )
            
            success = False
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
                    messages=messages,
                    query=running_extra_params.get("query") if running_extra_params else None
                )

                # Execute completion
                response = await self.operator.completion(
                    tasksmanager_id=tasksmanager.id,
                    task_id=task.id,
                    messages=messages,
                    model=tasksmanager.model,
                    curried_proxy=curried_proxy
                )
                
                success = True
                return {"response": response}

            finally:
                # Record context usage
                await self.context_analytics.record_context_usage(
                    task_id=task.id,
                    success=success
                )

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