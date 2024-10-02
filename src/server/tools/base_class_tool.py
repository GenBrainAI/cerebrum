from abc import ABC, abstractmethod
from typing import Any, Dict

class BaseClassTool(ABC):
    @abstractmethod
    async def __call__(self, method_name: str, arguments: Dict[str, Any]) -> Any:
        pass

    @abstractmethod
    def get_tool_descriptions(self) -> Dict[str, Any]:
        pass