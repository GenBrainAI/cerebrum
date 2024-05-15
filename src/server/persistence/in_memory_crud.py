import json
from pydantic.json import pydantic_encoder
from typing import Dict, List, TypeVar, Generic, Type
from pydantic import BaseModel

from .crud_interface import CrudInterface
from ..models.tasks_manager import TasksManager
from ..models.toolset import Tool, Toolset
from ..models.task import Task
from ..models.message import Message
from uuid import uuid4
from datetime import datetime

T = TypeVar('T', bound=BaseModel)

class InMemoryCrud(CrudInterface[T], Generic[T]):
    def __init__(self, model_class: Type[T]):
        self.storage: Dict[str, T] = {}
        self._model_class = model_class

    def create(self, item: T) -> T:
        # take id from payload -- otherwise generate
        item_id = item.id if hasattr(item,'id') and item.id is not None else str(uuid4())

        created_at = datetime.now()
        
        if isinstance(item, dict):  # If item is a dictionary
            item['id'] = item_id
            item['created_at'] = created_at
        else:  # Assume item is a Pydantic model or similar
            try:
                setattr(item, 'id', item_id)
            except AttributeError:
                pass  
            try:
                setattr(item, 'created_at', created_at)
            except AttributeError:
                pass  
                
        self.storage[item_id] = item
        return item

    def to_json(self) -> str:
        # Serialize the storage dictionary to JSON
        return json.dumps(self.storage, default=pydantic_encoder)

    def from_json(self, data: str):
        try:
            # Deserialize JSON data to storage dictionary
            items = json.loads(data)
            self.storage = {k: self._model_class.parse_obj(v) for k, v in items.items()}
        except Exception as e:
            print(str(e))
            # raise e


    @property
    def model_class(self):
        # Return the Pydantic model class associated with this CRUD class
        return self._model_class

    def read(self, item_id: str) -> T:
        return self.storage.get(item_id)

    def update(self, item_id: str, item: T) -> T:
        if item_id in self.storage:
            self.storage[item_id] = item
        return item

    def delete(self, item_id: str) -> None:
        self.storage.pop(item_id, None)

    def list(self) -> List[T]:
        return list(self.storage.values())


# Concrete CRUD classes
class ToolCrud(InMemoryCrud[Tool]):
    def __init__(self):
        super().__init__(Tool)

class ToolsetCrud(InMemoryCrud[Toolset]):
    def __init__(self):
        super().__init__(Toolset)

class TasksManagerCrud(InMemoryCrud[TasksManager]):
    def __init__(self):
        super().__init__(TasksManager)

class TaskCrud(InMemoryCrud[Task]):
    def __init__(self):
        super().__init__(Task)


class MessageCrud(InMemoryCrud[Message]):
    def __init__(self):
        super().__init__(Message)
