
import json
from pydantic import BaseModel
from .in_memory_crud import InMemoryCrud, CrewAIConfigCrud, ToolCrud, ToolsetCrud, TasksManagerCrud, TaskCrud, MessageCrud
from .persistence_model import PersistenceModelBase

class InMemoryPersistenceModel(PersistenceModelBase):
    def __init__(self):
        super(InMemoryPersistenceModel, self).__init__()
        self._toolsets = ToolsetCrud()
        self._tools = ToolCrud()
        self._tasksmanagers = TasksManagerCrud()
        self._tasks = TaskCrud()
        self._messages = MessageCrud()
        self._crewai_config = CrewAIConfigCrud()

        # For general dict non pydantic
        self.collections: Dict[str, InMemoryCrud[BaseModel]] = {}


    def to_json(self) -> str:
        # Serialize each CRUD object to a JSON string
        try:
            obj = {
                "toolsets": self._toolsets.to_json(),
                "tools": self._tools.to_json(),
                "tasksmanagers": self._tasksmanagers.to_json(),
                "tasks": self._tasks.to_json(),
                "messages": self._messages.to_json(),
                "crewai_config": self._crewai_config.to_json(),
            }
            json_str = json.dumps(obj, indent=4)
            return json_str
        except Exception as e:
            print(f"Failed to serialize InMemoryPersistenceModel: {e}")
            raise e        

    def from_json(self, json_str: str):
        # Deserialize each CRUD object from a JSON string
        data = json.loads(json_str)
        self._toolsets.from_json(data["toolsets"])
        self._tools.from_json(data["tools"])
        self._tasksmanagers.from_json(data["tasksmanagers"])
        self._tasks.from_json(data["tasks"])
        self._crewai_config.from_json(data["crewai_config"])
        self._autogen_config.from_json(data["autogen_config"])

    @property
    def tools(self) -> ToolCrud:
        return self._tools

    @property
    def toolsets(self) -> ToolsetCrud:
        return self._toolsets

    @property
    def tasksmanagers(self) -> TasksManagerCrud:
        return self._tasksmanagers

    @property
    def tasks(self) -> TaskCrud:
        return self._tasks

    @property
    def messages(self) -> MessageCrud:
        return self._messages

    @property
    def crewai_config(self) -> CrewAIConfigCrud:
        return self._crewai_config



