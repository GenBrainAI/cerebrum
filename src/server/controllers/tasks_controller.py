from ..models.tasks_manager import TasksManager
from ..persistence.persistence_model_factory import PersistenceModelFactory


persistence_model = PersistenceModelFactory.persistence_model("inmemory")

async def create_tasksmanager(tasksmanager: TasksManager ) -> TasksManager:
    created_bot =  persistence_model.tasksmanagers.create(tasksmanager)
    return created_bot