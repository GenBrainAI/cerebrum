from ..persistence.persistence_model import PersistenceModelBase
from .operator import ToolsOperator
from ..models.message import Message
from ..controllers.curried_proxy import CurriedProxy

class TaskRunner:
    def __init__(self, persistence_model: PersistenceModelBase):
        self.persistence_model = persistence_model
        self.operator = ToolsOperator()

    async def completion(self, tasksmanager_id: str, task_id: str, messages: [Message], model: str = None) -> str:
        tasksmanager = self.persistence_model.tasksmanagers.read(tasksmanager_id)
        if not tasksmanager:
            raise ValueError("tasksmanager not found")

        task = self.persistence_model.tasks.read(task_id)
        if not task:
            raise ValueError("Task not found")

        model = model or tasksmanager.model

        # Create CurriedProxy instance
        curried_proxy = CurriedProxy()
        
        # Add tools from tasksmanager and task
        self._add_tools_to_proxy(curried_proxy, tasksmanager.toolsets + task.toolsets)
        session_messages = messages

        messages = tasksmanager.messages
        messages += task.messages
        messages += session_messages

        result = await self.make_llm_call(tasksmanager_id, task_id, messages, model, curried_proxy)
        return result

    def _add_tools_to_proxy(self, curried_proxy: CurriedProxy, toolset_ids: list):
        for toolset_id in toolset_ids:
            toolset = self.persistence_model.toolsets.read(toolset_id)
            for tool_id in toolset.tool_ids:
                tool = self.persistence_model.tools.read(tool_id)
                curried_proxy.add_tool(f"{toolset.name}_{tool.function.name}", tool)

    async def make_llm_call(self, tasksmanager_id, task_id, messages, model, curried_proxy):
        return await self.operator.completion(tasksmanager_id, task_id, messages, model, curried_proxy)
