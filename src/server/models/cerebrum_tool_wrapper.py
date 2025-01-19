from __future__ import annotations
from typing import Any, Dict, List, Optional, Union, Type, get_type_hints, Callable
from pydantic import BaseModel
import logging
import inspect
import docstring_parser
from enum import Enum
from datetime import datetime, timedelta
from .schema import ResolvedSchema, ParameterSchema
from .tools_descriptors import (
    ToolType,
    ParameterInfo,
    ReturnInfo,
    ToolMetadata,
    DocstringInfo
)
from .tools_catalog import ToolsCatalog
import time

class CerebrumToolWrapper:
    """Wrapper for tools that provides execution metrics and validation."""
    
    def __init__(self):
        self.catalog = ToolsCatalog()
        self._logger = logging.getLogger(__name__)

    def register_tool(self, tool: Any, name: Optional[str] = None) -> str:
        """Register a tool with the catalog."""
        return self.catalog.register_tool(tool, name)

    async def execute_tool(self, tool_name: str, kwargs: Dict[str, Any]) -> Any:
        """Execute a tool with the given name and arguments."""
        return await self.catalog.execute_tool(tool_name, kwargs)

    def get_tool_metrics(self, tool_name: Optional[str] = None) -> Dict[str, Any]:
        """Get execution metrics for one or all tools."""
        return self.catalog.get_tool_metrics(tool_name)

    def get_tool_instance(self, name: str) -> Any:
        """Get or create an instance of a tool."""
        return self.catalog.get_tool_instance(name)

    @classmethod
    def reset(cls):
        """Reset the catalog state. Should only be used in tests."""
        ToolsCatalog.reset() 