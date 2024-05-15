from ..persistence.persistence_model import PersistenceModelBase
from .operator import ToolsOperator
from ..models.message import Message

# Example usage of TaskRunner:
# persistence = YourActualPersistenceModel()  # Initialize this with your actual persistence model
# task_runner = TaskRunner(persistence)
# result = await task_runner.completion("tasksmanager_id_here", "task_id_here")
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

      result = await self.make_llm_call(tasksmanager_id, task_id, messages, model)
      return result

    async def make_llm_call(self, tasksmanager_id, task_id, messages, model):
      return await self.operator.completion(tasksmanager_id, task_id, messages, model)