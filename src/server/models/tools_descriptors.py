from enum import Enum
from typing import Any, List, Optional, Dict, Union
from pydantic import BaseModel, Field, ConfigDict

class ToolType(str, Enum):
    """Type of tool in the catalog."""
    PYTHON_FUNCTION = "python_function"
    CLASS_METHOD = "class_method"
    CREWAI_TOOL = "crewai_tool"
    LANGCHAIN_TOOL = "langchain_tool"
    OPENAPI_TOOL = "openapi_tool"
    AI_TOOL = "ai_tool"

class ParameterInfo(BaseModel):
    """Information about a tool parameter."""
    name: str
    type_hint: Optional[str]
    description: str
    default: Any = None
    required: bool = True

class ReturnInfo(BaseModel):
    """Information about a tool's return value."""
    type_hint: Optional[str]
    description: str

class DocstringInfo(BaseModel):
    """Complete parsed docstring information."""
    description: str
    parameters: List[ParameterInfo]
    returns: ReturnInfo


class ToolMetadata(BaseModel):
    """Metadata for a registered tool."""
    name: str
    description: str
    tool_type: ToolType
    parameters: List[ParameterInfo]  # For backward compatibility
    schema: Optional[Dict[str, Any]] = None  # For OpenAPI schema
    returns: ReturnInfo
    original_obj: Any
    class_name: Optional[str] = None
    method_name: Optional[str] = None
    async_tool: bool = False

    model_config = ConfigDict(
        populate_by_name=False,
        arbitrary_types_allowed=True
    )

class ToolContext(BaseModel):
    """Context for tool execution."""
    metadata: ToolMetadata
    proxy: Any
