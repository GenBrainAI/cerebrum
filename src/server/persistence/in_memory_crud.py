import json
from pydantic.json import pydantic_encoder
from typing import Dict, List, TypeVar, Generic, Type
from pydantic import BaseModel

from .crud_interface import CrudInterface
from ..models.tasks_manager import TasksManager
from ..models.toolset import Tool, Toolset
from ..models.task import Task
from ..models.message import Message
from ..models.agent import CrewAIConfig
from ..controllers.curried_proxy import CurriedProxy
from ..models.curried_proxy_info import CurriedProxyInfo
from uuid import uuid4
from datetime import datetime

T = TypeVar('T', bound=BaseModel)

class InMemoryCrud(CrudInterface[T], Generic[T]):
    def __init__(self, model_class: Type[T]):
        self.storage: Dict[str, T] = {}
        self._model_class = model_class

    # T is pydantic model
    def create(self, item: T) -> T:
        item_id = str(uuid4())
        created_at = datetime.now()
        try:
            item.id = item_id
        except Exception:
            print("Failed to set id", item)
            pass  
        try:
            item.created_at = created_at
        except Exception:
            pass  

        self.storage[item_id] = item
        return item

    def to_json(self) -> str:
        # Serialize the storage dictionary to JSON
        return json.dumps(self.storage, default=pydantic_encoder)

    # def from_json_old(self, data: str):
    #     try:
    #         # Deserialize JSON data to storage dictionary
    #         items = json.loads(data)
    #         self.storage = {k: self._model_class.parse_obj(v) for k, v in items.items()}
    #     except Exception as e:
    #         print(str(e))
    #         # raise e

    def from_json(self, data: str):
        """Deserialize JSON data to storage dictionary with validation."""
        try:
            items = json.loads(data)
            new_storage = {}
            
            print(f"\n🔍 Loading {self._model_class.__name__} items:")
            for k, v in items.items():
                try:
                    # Log the item before parsing
                    print(f"  📝 Processing {k}:")
                    print(f"    Type before parsing: {type(v)}")
                    
                    # Try to parse each item individually
                    parsed_item = self._model_class.parse_obj(v)
                    
                    # Log the parsed item
                    print(f"    Type after parsing: {type(parsed_item)}")
                    print(f"    Is instance of {self._model_class.__name__}: {isinstance(parsed_item, self._model_class)}")
                    
                    new_storage[k] = parsed_item
                except Exception as e:
                    print(f"❌ Failed to parse item {k}: {str(e)}")
                    print(f"   Raw item data: {v}")
                    raise  # Re-raise to catch invalid items
                    
            self.storage = new_storage
            
        except Exception as e:
            print(f"❌ Error in from_json for {self._model_class.__name__}: {str(e)}")
            print(f"   Raw data: {data[:200]}...")  # Print first 200 chars of raw data
            raise

    @property
    def model_class(self):
        # Return the Pydantic model class associated with this CRUD class
        return self._model_class

    def read(self, item_id: str) -> T:
        item = self.storage.get(item_id)
        if item is not None:
            print(f"\n📖 Reading {self._model_class.__name__} {item_id}:")
            print(f"  Type: {type(item)}")
            print(f"  Is instance of {self._model_class.__name__}: {isinstance(item, self._model_class)}")
        return item

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
    
    def list(self) -> List[Task]:
        """Override list to ensure all items are proper Task instances."""
        items = super().list()
        valid_items = []
        
        for item in items:
            if isinstance(item, dict):
                print(f"Warning: Found raw dict instead of Task: {item}")
                try:
                    # Try to convert dict to Task
                    valid_items.append(Task.parse_obj(item))
                except Exception as e:
                    print(f"Failed to convert dict to Task: {str(e)}")
            elif isinstance(item, Task):
                valid_items.append(item)
            else:
                print(f"Warning: Invalid item type {type(item)}: {item}")
                
        return valid_items

    def read(self, item_id: str) -> Task:
        """Override read to ensure proper Task instance is returned."""
        item = super().read(item_id)
        if item is None:
            return None
            
        if isinstance(item, dict):
            print(f"⚠️ Converting dict to Task for id {item_id}")
            try:
                return Task.parse_obj(item)
            except Exception as e:
                print(f"❌ Failed to convert dict to Task: {str(e)}")
                return item
        elif not isinstance(item, Task):
            print(f"⚠️ Unexpected type for Task: {type(item)}")
            
        return item

class MessageCrud(InMemoryCrud[Message]):
    def __init__(self):
        super().__init__(Message)

class CrewAIConfigCrud(InMemoryCrud[CrewAIConfig]):
    def __init__(self):
        super().__init__(CrewAIConfig)

class CurriedProxyCrud(InMemoryCrud[CurriedProxy]):
    def __init__(self):
        super().__init__(CurriedProxy)

    def to_json(self) -> str:
        """
        Convert the storage to JSON using CurriedProxyInfo
        """
        info_dict = {}
        for proxy_id, proxy in self.storage.items():
            info_dict[proxy_id] = proxy.to_info().dict()
        return json.dumps(info_dict, default=pydantic_encoder)

    def from_json(self, json_str: str):
        """
        Restore CurriedProxy instances from JSON using CurriedProxyInfo
        """
        try:
            info_dict = json.loads(json_str)
            self.storage = {}
            for proxy_id, info_data in info_dict.items():
                proxy_info = CurriedProxyInfo(**info_data)
                proxy = CurriedProxy.from_info(proxy_info)
                self.storage[proxy_id] = proxy
        except Exception as e:
            print(f"Error deserializing CurriedProxy: {str(e)}")
            raise e
