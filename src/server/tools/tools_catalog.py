from __future__ import annotations
from typing import Any, Dict, List, Optional, Type, Union, get_type_hints
from enum import Enum
import inspect
from dataclasses import dataclass
import docstring_parser
from os import getenv
from dotenv import load_dotenv
from crewai_tools import (
    BaseTool as CrewAITool,
    WebsiteSearchTool,
    FileReadTool,
    SerperDevTool
)
from langchain.tools import BaseTool as LangChainTool
from ..tools.file_tool import FileTool
from ..tools.github_tool import GitHubTool
from ..tools.microservices_tool import MicroservicesTool
from ..tools.sms_tool import SMSTool
import builtins

load_dotenv()

class ToolType(Enum):
    PYTHON_FUNCTION = "python_function"
    CLASS_METHOD = "class_method"
    CREWAI_TOOL = "crewai_tool"
    LANGCHAIN_TOOL = "langchain_tool"
    OPENAPI_TOOL = "openapi_tool"

@dataclass
class ParameterInfo:
    """Information about a tool parameter."""
    name: str
    type_hint: Optional[Type]
    description: str
    default: Any = None
    required: bool = True

@dataclass
class ReturnInfo:
    """Information about a tool's return value."""
    type_hint: Optional[Type]
    description: str

@dataclass
class ToolMetadata:
    """Metadata for a registered tool."""
    name: str
    description: str
    tool_type: ToolType
    parameters: List[ParameterInfo]
    returns: ReturnInfo
    original_obj: Any
    class_name: Optional[str] = None
    method_name: Optional[str] = None
    async_tool: bool = False

class ToolsCatalog:
    """Singleton catalog for all available tools."""
    
    _instance = None
    _initialized = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ToolsCatalog, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not ToolsCatalog._initialized:
            self._tools: Dict[str, ToolMetadata] = {}
            self._instances: Dict[str, Any] = {}
            self._initialize_default_tools()
            ToolsCatalog._initialized = True

    def _initialize_default_tools(self):
        """Initialize the catalog with the default tools from TOOLS dictionary."""
        self.DEFAULT_TOOLS = {
            "WebsiteSearchTool": WebsiteSearchTool(),
            "SerperDevTool": SerperDevTool(),
            "FileReadTool": FileReadTool(
                file_path='job_description_example.md',
                description='A tool to read the job description example file.'
            ),
            "GitHubTool": GitHubTool(
                access_token=getenv("GITHUB_ACCESS_TOKEN"),
                repo_name=getenv("GITHUB_REPO_NAME", "GenBrainAI/cerebrum")
            ),
            "save_file": FileTool(),
            "microservices_tool": MicroservicesTool(),
            "SMSTool": SMSTool(),
        }

        # Register each default tool and store its instance
        for name, tool in self.DEFAULT_TOOLS.items():
            if isinstance(tool, (CrewAITool, LangChainTool)):
                self.register_ai_tool(tool, name)
            elif inspect.isclass(type(tool)):
                # For class instances, store the instance before registration
                self._instances[name] = tool
                # Register the class of the instance
                self.register_class(tool.__class__, name)
            elif callable(tool):
                self.register_function(tool, name)
                
            # Store the instance in any case
            self._instances[name] = tool

    def _extract_docstring_info(self, obj: Any) -> tuple[str, List[ParameterInfo], ReturnInfo]:
        """Extract docstring information from an object."""
        docstring = docstring_parser.parse(obj.__doc__ or "")
        type_hints = get_type_hints(obj)
        return_type = type_hints.get('return')
        
        # Get description
        description = docstring.short_description or ""
        
        # Get parameters
        parameters = []
        signature = inspect.signature(obj)
        
        for param_name, param in signature.parameters.items():
            if param_name == 'self':  # Skip self parameter
                continue
                
            param_type = type_hints.get(param_name)
            param_doc = next((p.description for p in docstring.params if p.arg_name == param_name), "")
            
            parameters.append(ParameterInfo(
                name=param_name,
                type_hint=param_type,
                description=param_doc,
                default=param.default if param.default != inspect.Parameter.empty else None,
                required=param.default == inspect.Parameter.empty
            ))
            
        # Get return info
        return_info = ReturnInfo(
            type_hint=return_type,
            description=docstring.returns.description if docstring.returns else ""
        )
        
        return description, parameters, return_info

    def register_function(self, func: callable, name: Optional[str] = None) -> str:
        """Register a Python function as a tool."""
        tool_name = name or func.__name__
        description, parameters, return_info = self._extract_docstring_info(func)
        
        metadata = ToolMetadata(
            name=tool_name,
            description=description,
            tool_type=ToolType.PYTHON_FUNCTION,
            parameters=parameters,
            returns=return_info,
            original_obj=func,
            async_tool=inspect.iscoroutinefunction(func)
        )

        self._tools[tool_name] = metadata
        return tool_name

    def register_class(self, cls: Type, name: Optional[str] = None) -> List[str]:
        """Register a class and its methods as tools."""
        registered_names = []
        class_name = name or cls.__name__
        
        # Register each public method
        for method_name, method in inspect.getmembers(cls, predicate=inspect.isfunction):
            if method_name.startswith('_'):  # Skip private methods
                continue
                
            description, parameters, return_info = self._extract_docstring_info(method)
            qualified_name = f"{class_name}.{method_name}"
            
            metadata = ToolMetadata(
                name=qualified_name,
                description=description,
                tool_type=ToolType.CLASS_METHOD,
                parameters=parameters,
                returns=return_info,
                original_obj=method,
                class_name=class_name,
                method_name=method_name,
                async_tool=inspect.iscoroutinefunction(method)
            )

            self._tools[qualified_name] = metadata
            registered_names.append(qualified_name)
            
        # Also register the class itself under its base name if provided
        if name:
            self._tools[name] = self._tools[f"{class_name}.{registered_names[0].split('.')[-1]}"]

        return registered_names

    def register_ai_tool(self, tool: Union[CrewAITool, LangChainTool], name: Optional[str] = None) -> str:
        """Register a CrewAI or LangChain tool."""
        tool_name = name or tool.name
        
        if isinstance(tool, CrewAITool):
            tool_type = ToolType.CREWAI_TOOL
        else:
            tool_type = ToolType.LANGCHAIN_TOOL

        # Extract parameters from the _run method
        run_method = tool._run if hasattr(tool, '_run') else tool.run
        description, parameters, return_info = self._extract_docstring_info(run_method)
        
        # Use tool's description if available
        if hasattr(tool, 'description') and tool.description:
            description = tool.description

        metadata = ToolMetadata(
            name=tool_name,
            description=description,
            tool_type=tool_type,
            parameters=parameters,
            returns=return_info,
            original_obj=tool,
            async_tool=inspect.iscoroutinefunction(run_method)
        )

        self._tools[tool_name] = metadata
        return tool_name

    def get_tool(self, name: str) -> Optional[ToolMetadata]:
        """Get metadata for a registered tool."""
        return self._tools.get(name)

    def list_tools(self) -> List[str]:
        """List all registered tool names."""
        return list(self._tools.keys())

    def get_tool_instance(self, name: str) -> Any:
        """Get or create an instance of a tool."""
        # First check if we have a direct instance
        if name in self._instances:
            return self._instances[name]

        # Then check metadata
        metadata = self._tools.get(name)
        if not metadata:
            raise KeyError(f"Tool '{name}' not found in catalog")

        if metadata.tool_type == ToolType.CLASS_METHOD:
            # Create class instance if needed
            if metadata.class_name not in self._instances:
                cls = metadata.original_obj.__class__
                self._instances[metadata.class_name] = cls()
            
            # Return bound method
            instance = self._instances[metadata.class_name]
            return getattr(instance, metadata.method_name)
        
        return metadata.original_obj

    def to_dict(self) -> Dict:
        """Convert catalog to a dictionary for serialization."""
        return {
            "tools": {
                name: {
                    "name": metadata.name,
                    "description": metadata.description,
                    "tool_type": metadata.tool_type.value,
                    "parameters": [
                        {
                            "name": p.name,
                            "type_hint": str(p.type_hint) if p.type_hint else None,
                            "description": p.description,
                            "default": p.default,
                            "required": p.required
                        }
                        for p in metadata.parameters
                    ],
                    "returns": {
                        "type_hint": str(metadata.returns.type_hint) if metadata.returns.type_hint else None,
                        "description": metadata.returns.description
                    },
                    "class_name": metadata.class_name,
                    "method_name": metadata.method_name,
                    "async_tool": metadata.async_tool
                }
                for name, metadata in self._tools.items()
            }
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'ToolsCatalog':
        """Create a catalog from a serialized dictionary."""
        catalog = cls()
        
        for name, tool_data in data["tools"].items():
            parameters = []
            for p in tool_data["parameters"]:
                try:
                    type_hint = None
                    if p["type_hint"]:
                        type_hint = cls._get_type_from_string(p["type_hint"])
                except (AttributeError, NameError, TypeError):
                    type_hint = None
                parameters.append(ParameterInfo(
                    name=p["name"],
                    type_hint=type_hint,
                    description=p["description"],
                    default=p["default"],
                    required=p["required"]
                ))
            
            returns = ReturnInfo(
                type_hint=cls._get_type_from_string(tool_data["returns"]["type_hint"]) if tool_data["returns"]["type_hint"] else None,
                description=tool_data["returns"]["description"]
            )
            
            metadata = ToolMetadata(
                name=tool_data["name"],
                description=tool_data["description"],
                tool_type=ToolType(tool_data["tool_type"]),
                parameters=parameters,
                returns=returns,
                original_obj=None,  # Will need to be reconstructed
                class_name=tool_data["class_name"],
                method_name=tool_data["method_name"],
                async_tool=tool_data["async_tool"]
            )
            
            catalog._tools[name] = metadata
        
        return catalog

    def _get_type_from_string(type_hint_str: str):
        try:
            module_parts = type_hint_str.split('.')
            if len(module_parts) > 1:
                module_name = '.'.join(module_parts[:-1])
                type_name = module_parts[-1]
                module = importlib.import_module(module_name)
                return getattr(module, type_name)
            else:
                return getattr(builtins, type_hint_str)
        except (AttributeError, NameError, ImportError):
            return None
        
# Create the global instance
tools_catalog = ToolsCatalog()