from typing import Dict, Any, Optional, List
import logging
from fastapi import HTTPException

from ..models.message import Message
from ..models.run_task import RunTask
from ..persistence.persistence_model import PersistenceModelBase
from ..controllers.operator import ToolsOperator
from ..controllers.curried_proxy import CurriedProxy
from .crew_runner import run_crew_task
from ..models.task import Task
from ..models.tasks_manager import TasksManager

class TaskRunner:
    def __init__(self, persistence_model: PersistenceModelBase):
        self.persistence_model = persistence_model
        self.operator = ToolsOperator()

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

    def _get_or_create_curried_proxy(self, task: Task, tasksmanager: TasksManager) -> CurriedProxy:
        """Get existing curried proxy or create a new one with tools."""
        curried_proxy = None
        if task.curried_proxy_id:
            curried_proxy = self.persistence_model.curried_proxies.read(task.curried_proxy_id)
        
        if not curried_proxy:
            curried_proxy = CurriedProxy()
            
        # Handle None values by defaulting to empty lists
        tasksmanager_toolsets = getattr(tasksmanager, 'toolsets', []) or []
        task_toolsets = getattr(task, 'toolsets', []) or []
        
        # Add tools from both tasksmanager and task
        self._add_tools_to_proxy(curried_proxy, tasksmanager_toolsets + task_toolsets)
                
        return curried_proxy

    async def debug_run_task(self, tasksmanager_id: str, task_id: str, running_extra_params: Optional[Dict] = None) -> Dict:

        print(f"Running task {task_id} with tasksmanager {tasksmanager_id} and running_extra_params {running_extra_params}")
        return {"response": "test"}

    async def run_task(self, tasksmanager_id: str, task_id: str, running_extra_params: Optional[Dict] = None) -> Dict:
        """Unified method to run a task, handling both CrewAI and standard tasks."""
        try:
            # Validate task and tasksmanager
            task = self.persistence_model.tasks.read(task_id)
            if task is None:
                raise ValueError(f"Task {task_id} not found")

            tasksmanager = self.persistence_model.tasksmanagers.read(tasksmanager_id)
            if tasksmanager is None:
                raise ValueError(f"TasksManager {tasksmanager_id} not found")

            if task.tasksmanager_id != tasksmanager_id:
                raise ValueError(f"Task {task_id} does not belong to TasksManager {tasksmanager_id}")

            # Determine task type and execute accordingly
            if task.crewai_info_id:
                # Run using CrewAI
                logging.info(f"Running task {task_id} with CrewAI")
                response = await run_crew_task(task.id, running_extra_params)
            else:
                # Run using standard completion
                logging.info(f"Running task {task_id} with standard completion")
                response = await self._run_standard_task(task, tasksmanager, running_extra_params)

            return response

        except Exception as e:
            logging.error(f"Error running task {task_id}: {str(e)}", exc_info=True)
            raise

    async def _run_standard_task(self, task: Task, tasksmanager: TasksManager, running_extra_params: Optional[Dict] = None) -> Dict:
        """Execute a task using standard completion with tool support."""
        try:
            # Get or create curried proxy with tools
            curried_proxy = self._get_or_create_curried_proxy(task, tasksmanager)
            
            # Initialize message list with system messages
            messages = task.get_system_messages()

            # Handle running_extra_params
            if running_extra_params:
                # Handle messages if present
                if 'messages' in running_extra_params:
                    input_messages = running_extra_params['messages']
                    # Convert each message to Message object if it's not already
                    for msg in input_messages:
                        if isinstance(msg, Message):
                            messages.append(msg)
                        elif isinstance(msg, dict):
                            messages.append(Message(**msg))
                        else:
                            raise ValueError(f"Invalid message format: {msg}")

                # Handle other parameters by converting them to a message
                other_params = {k: v for k, v in running_extra_params.items() if k != 'messages'}
                if other_params:
                    content = "\n".join([f"{k}: {v}" for k, v in other_params.items()])
                    messages.append(Message(role="user", content=content))

            # Run completion with tools
            response = await self.completion(
                tasksmanager_id=tasksmanager.id,
                task_id=task.id,
                messages=messages,
                model=tasksmanager.model,
                curried_proxy=curried_proxy
            )
            
            return {"response": response}

        except Exception as e:
            logging.error(f"Error running standard task: {str(e)}", exc_info=True)
            raise    
    
    async def completion(
        self, 
        tasksmanager_id: str, 
        task_id: str, 
        messages: List[Message], 
        model: Optional[str] = None,
        curried_proxy: Optional[CurriedProxy] = None
    ) -> str:
        """Execute a standard completion task with optional tools."""
        result = await self.operator.completion(
            tasksmanager_id=tasksmanager_id,
            task_id=task_id,
            messages=messages,
            model=model,
            curried_proxy=curried_proxy
        )
        return result