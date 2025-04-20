import json
from pydantic.json import pydantic_encoder
from typing import Dict, List, TypeVar, Generic, Type, Optional, Any, Union
from pydantic import BaseModel

from .crud_interface import CrudInterface
from ..models.tasks_manager import TasksManager
from ..models.toolset import Tool, Toolset
from ..models.task import Task
from ..models.message import Message
from ..models.agent import CrewAIConfig
from ..controllers.curried_proxy import CurriedProxy
from ..models.curried_proxy_info import CurriedProxyInfo
from ..controllers.task_flow_manager import TaskFlow
from uuid import uuid4
from datetime import datetime
import logging

T = TypeVar('T', bound=BaseModel)

class InMemoryCrud(CrudInterface[T], Generic[T]):
    def __init__(self, model_class: Type[T]):
        self.storage: Dict[str, T] = {}
        self._model_class = model_class
        self.logger = logging.getLogger(f"{__name__}.{model_class.__name__}")
        self.logger.info(f"Initialized InMemoryCrud for {model_class.__name__}")

    # T is pydantic model
    def create(self, item: T) -> T:
        """Create a new item or store an existing one.
        
        If the item already has an ID (e.g. during deserialization), that ID will be preserved.
        Only generates a new ID for completely new items.
        """
        # First try to get ID from the item itself
        item_id = getattr(item, 'id', None)
        
        if item_id is None:
            # Only generate new ID if this is a completely new item
            item_id = str(uuid4())
            try:
                item.id = item_id
            except Exception:
                self.logger.warning(f"Failed to set id on new item {item}")
                raise
            
            # Set created_at only for new items
            if not hasattr(item, 'created_at'):
                try:
                    item.created_at = datetime.now()
                except Exception:
                    pass

        # Store the item with its ID (either existing or new)
        self.storage[str(item_id)] = item
        self.logger.debug(f"Created item {item_id} in {self._model_class.__name__} (type: {type(item)})")
        return item

    def to_json(self) -> str:
        # Convert storage to use string keys instead of UUIDs
        string_keyed_storage = {
            str(k): v for k, v in self.storage.items()
        }
        # Serialize the storage dictionary to JSON
        return json.dumps(string_keyed_storage, default=pydantic_encoder)

    def from_json(self, json_data: Union[str, Dict]) -> None:
        """
        Deserialize JSON string or dictionary back to items.
        
        Args:
            json_data: The JSON string or dictionary to deserialize.
        """
        try:
            if isinstance(json_data, str):
                data = json.loads(json_data)
            elif isinstance(json_data, dict):
                data = json_data # Already a dictionary
            else:
                raise TypeError(f"Input must be str or dict, not {type(json_data)}")

            self.clear()
            for item_id, item_data in data.items():
                # Ensure item_data is a dictionary before creating model
                if isinstance(item_data, dict):
                    # Dynamically create model instance if model_class is set
                    if self._model_class:
                        try:
                            item_instance = self._model_class(**item_data)
                            self.create(item_instance) # Use create to handle ID properly
                        except Exception as e:
                            self.logger.error(f"Error creating model instance for ID {item_id} ({self._model_class.__name__}): {e}")
                            # Store raw data on error if model instantiation fails
                            self.storage[item_id] = item_data
                    else:
                         # If no model_class, store raw data dictionary
                         self.storage[item_id] = item_data
                else:
                     self.logger.warning(f"Skipping non-dict item data for ID {item_id}: {type(item_data)}")
        except json.JSONDecodeError as e:
            self.logger.error(f"Error decoding JSON for {self._model_class.__name__}: {e}")
            raise
        except Exception as e:
            self.logger.error(f"Error loading from JSON/Dict for {self._model_class.__name__}: {e}")
            raise

    @property
    def model_class(self):
        # Return the Pydantic model class associated with this CRUD class
        return self._model_class

    def read(self, item_id: str) -> T:
        item = self.storage.get(item_id)
        if item is not None:
            self.logger.debug(f"Read item {item_id} from {self._model_class.__name__} (type: {type(item)})")
        else:
            self.logger.debug(f"Item {item_id} not found in {self._model_class.__name__}")
        return item

    def update(self, item_id: str, item: T) -> T:
        """Update an item in the storage or create it if it doesn't exist.
        
        Args:
            item_id: The ID of the item to update
            item: The updated item
            
        Returns:
            The updated item if successful, None otherwise
        """
        try:
            # Make sure item_id is a string
            str_item_id = str(item_id)
            
            # Check if the item exists
            if str_item_id not in self.storage:
                self.logger.warning(f"⚠️ Warning: Item {str_item_id} not found in {self._model_class.__name__} storage. Creating new.")
                # Create the item instead
                return self.create(item)
            
            # Set the updated_at timestamp if the attribute exists
            if hasattr(item, 'updated_at'):
                from datetime import datetime
                try:
                    item.updated_at = datetime.now()
                except Exception as e:
                    self.logger.error(f"❌ Error setting updated_at timestamp: {str(e)}")
            
            # Update the item in storage
            self.storage[str_item_id] = item
            self.logger.debug(f"Updated item {str_item_id} in {self._model_class.__name__} (type: {type(item)})")
            
            return item
        except Exception as e:
            self.logger.error(f"❌ Error updating {self._model_class.__name__} item {item_id}: {str(e)}")
            import traceback
            self.logger.error(traceback.format_exc())
            return None

    def delete(self, item_id: str) -> None:
        self.storage.pop(item_id, None)

    def list(self) -> List[T]:
        return list(self.storage.values())

    def clear(self) -> None:
        """Clear all items."""
        count = len(self.storage)
        self.storage.clear()
        self.logger.info(f"Cleared {count} items from {self._model_class.__name__}")


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
                try:
                    valid_items.append(Task.parse_obj(item))
                except Exception as e:
                    self.logger.warning(f"Failed to convert dict to Task: {str(e)}")
            elif isinstance(item, Task):
                valid_items.append(item)
                
        return valid_items

    def read(self, item_id: str) -> Task:
        """Override read to ensure proper Task instance is returned with normalized messages."""
        item = super().read(item_id)
        if item is None:
            return None
            
        if isinstance(item, dict):
            try:
                item = Task.parse_obj(item)
            except Exception as e:
                self.logger.error(f"Error parsing Task from dict: {str(e)}")
                return item
        
        # Ensure messages are normalized
        if isinstance(item, Task):
            try:
                item.normalize_messages()
            except Exception as e:
                self.logger.error(f"Error normalizing messages for Task {item_id}: {str(e)}")
                
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

    def create(self, item: CurriedProxy) -> CurriedProxy:
        """Override create to handle the special case for CurriedProxy."""
        # First try to get ID from the item itself
        item_id = getattr(item, 'id', None)
        
        if item_id is None:
            # Only generate new ID if this is a completely new item
            item_id = str(uuid4())
            try:
                item.id = item_id
            except Exception:
                self.logger.warning(f"Failed to set id on new item {item}")
                raise
            
        # Store the item with its ID (either existing or new)
        self.storage[str(item_id)] = item
        self.logger.debug(f"Created item {item_id} in CurriedProxyCrud (type: {type(item)})")
        return item

    def to_json(self) -> str:
        """
        Convert the storage to JSON using CurriedProxyInfo
        """
        info_dict = {}
        for proxy_id, proxy in self.storage.items():
            # Convert UUID to string for JSON serialization
            info_dict[str(proxy_id)] = proxy.to_info().model_dump()
        return json.dumps(info_dict, default=pydantic_encoder)

    def from_json(self, data):
        """
        Restore CurriedProxy instances from JSON using CurriedProxyInfo
        
        Args:
            data: Either a JSON string or a pre-parsed dictionary
        """
        try:
            # Check if data is already a dictionary
            if isinstance(data, dict):
                info_dict = data
                self.logger.debug(f"CurriedProxyCrud: Data is already a dictionary, using directly")
            else:
                info_dict = json.loads(data)
                self.logger.debug(f"CurriedProxyCrud: Parsed JSON string into dictionary")
            
            self.storage = {}
            for proxy_id, info_data in info_dict.items():
                try:
                    proxy_info = CurriedProxyInfo(**info_data)
                    proxy = CurriedProxy.from_info(proxy_info)
                    self.storage[proxy_id] = proxy
                except Exception as item_error:
                    self.logger.error(f"Error creating CurriedProxy for ID {proxy_id}: {str(item_error)}")
                    # Continue processing other items
            
            return self.storage
        except json.JSONDecodeError as e:
            self.logger.error(f"❌ Error in CurriedProxyCrud.from_json: JSON decoding error: {str(e)}")
        except TypeError as e:
            self.logger.error(f"❌ Error in CurriedProxyCrud.from_json: {str(e)}")
        except Exception as e:
            self.logger.error(f"❌ Error in CurriedProxyCrud.from_json: {str(e)}")
            # Safe way to print data for debugging
            try:
                data_type = type(data)
                if isinstance(data, dict):
                    self.logger.debug(f"   Data is a dictionary with {len(data)} keys")
                else:
                    data_preview = str(data)[:200] + "..." if len(str(data)) > 200 else str(data)
                    self.logger.debug(f"   Data type: {data_type}")
                    self.logger.debug(f"   Data preview: {data_preview}")
            except Exception as print_error:
                self.logger.warning(f"   Unable to print data details: {print_error}")
        
        return self.storage

class TaskFlowCrud(InMemoryCrud[TaskFlow]):
    def __init__(self):
        super().__init__(TaskFlow)
