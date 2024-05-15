from abc import ABC, abstractmethod
from typing import Dict, List, TypeVar, Generic
from pydantic import BaseModel
from uuid import uuid4
import time

# Type variable used for type hints
T = TypeVar('T', bound=BaseModel)

class CrudInterface(ABC, Generic[T]):
    @abstractmethod
    def create(self, item: T) -> T:
        pass

    @abstractmethod
    def read(self, item_id: str) -> T:
        pass

    @abstractmethod
    def update(self, item_id: str, item: T) -> T:
        pass

    @abstractmethod
    def delete(self, item_id: str) -> None:
        pass

    @abstractmethod
    def list(self) -> List[T]:
        pass