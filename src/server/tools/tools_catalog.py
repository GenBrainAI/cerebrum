from __future__ import annotations
from typing import Any, Dict, List, Optional, Union, Type
from pydantic import BaseModel
import logging
import inspect
import docstring_parser
from enum import Enum
from ..models.schema import ResolvedSchema, ParameterSchema
from ..models.tools_descriptors import (
    ToolType,
    ParameterInfo,
    ReturnInfo,
    ToolMetadata,
    DocstringInfo
)
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
from ..models.toolset import Tool
from .internal_file_tools import InternalFileTools
from .internal_testing_tools import InternalTestingTools

load_dotenv()


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
            self._functions: Dict[str, Any] = {}  # Store functions
            self._classes: Dict[str, Type] = {}   # Store classes
            self._initialize_default_tools()
            ToolsCatalog._initialized = True

    def register_tool(self, tool: Any, name: Optional[str] = None) -> str:
        """Register a tool (object, function, or class) into the catalog.
        
        Args:
            tool: The tool to register
            name: Optional custom name for the tool
            
        Returns:
            The registered tool name
            
        Raises:
            ValueError: If tool type is not supported
        """
        tool_name = name or getattr(tool, '__name__', str(tool))
        
        try:
            if inspect.isfunction(tool):
                # Register function
                self._functions[tool_name] = tool
                self.register_function(tool, tool_name)
                
            elif inspect.isclass(tool):
                # Register class
                self._classes[tool_name] = tool
                self.register_class(tool, tool_name)
                
            elif isinstance(tool, (object,)) and not isinstance(tool, type):
                # Register instance
                self._instances[tool_name] = tool
                if hasattr(tool, '__class__'):
                    self.register_class(tool.__class__, tool_name)
                
            else:
                raise ValueError(f"Unsupported tool type: {type(tool)}")
                
            print(f"Registered tool: {tool_name} (type: {type(tool).__name__})")
            return tool_name
            
        except Exception as e:
            print(f"Error registering tool {tool_name}: {str(e)}")
            raise

    def list_tools_by_type(self) -> Dict[str, List[str]]:
        """List all registered tools grouped by type.
        
        Returns:
            Dictionary with tools grouped by type
        """
        return {
            "functions": list(self._functions.keys()),
            "classes": list(self._classes.keys()),
            "instances": list(self._instances.keys()),
        }

    def _initialize_default_tools(self):
        """Initialize the catalog with the default tools."""
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

        # Register each default tool
        for name, tool in self.DEFAULT_TOOLS.items():
            if isinstance(tool, (CrewAITool, LangChainTool)):
                self.register_ai_tool(tool, name)
            else:
                self.register_tool(tool, name)

    def _extract_docstring_info(self, obj: Any) -> tuple[str, List[ParameterInfo], ReturnInfo]:
        """Extract docstring information from an object.
        
        Supports both Google-style and Sphinx/reST docstring formats.
        """
        docstring = docstring_parser.parse(obj.__doc__ or "")
        
        # Get type hints safely
        try:
            type_hints = get_type_hints(obj)
            return_type = type_hints.get('return')
        except (NameError, TypeError):
            # Handle missing or invalid type hints
            type_hints = {}
            return_type = None
        
        # Get description
        description = docstring.short_description or ""
        if docstring.long_description:
            description += "\n\n" + docstring.long_description
        
        # Get parameters
        parameters = []
        try:
            signature = inspect.signature(obj)
        except (ValueError, TypeError):
            # Handle objects without signatures
            signature = None
        
        if signature:
            # Function to normalize parameter info from different formats
            def normalize_param_info(param_name: str, param: inspect.Parameter) -> ParameterInfo:
                try:
                    param_type = type_hints.get(param_name)
                except Exception:
                    param_type = None
                    
                param_doc = ""
                param_meta = None
                
                # Try Google-style params (Args:)
                google_style = next(
                    (p for p in docstring.params if p.arg_name == param_name),
                    None
                )
                if google_style:
                    param_doc = google_style.description
                else:
                    # Try Sphinx/reST style (:param:)
                    sphinx_style = next(
                        (p for p in docstring.params 
                        if p.arg_name == param_name or 
                        p.arg_name == f"param {param_name}" or
                        p.arg_name == f"parameter {param_name}"),
                        None
                    )
                    if sphinx_style:
                        param_doc = sphinx_style.description
                
                # Convert type to string representation safely
                type_str = None
                if param_type:
                    try:
                        if hasattr(param_type, '__origin__'):  # Handle generic types
                            origin = param_type.__origin__.__name__
                            args = ', '.join(arg.__name__ if hasattr(arg, '__name__') else str(arg) 
                                        for arg in param_type.__args__)
                            type_str = f"{origin}[{args}]"
                        else:
                            type_str = param_type.__name__ if hasattr(param_type, '__name__') else str(param_type)
                    except Exception:
                        type_str = str(param_type)
                
                return ParameterInfo(
                    name=param_name,
                    type_hint=type_str,
                    description=description,
                    default=param.default if param.default != inspect.Parameter.empty else None,
                    required=param.default == inspect.Parameter.empty
                )
            
            # Process parameters
            for param_name, param in signature.parameters.items():
                if param_name == 'self':  # Skip self parameter
                    continue
                try:
                    parameters.append(normalize_param_info(param_name, param))
                except Exception as e:
                    print(f"Error processing parameter {param_name}: {str(e)}")
                    continue
        
        # Get return info safely
        return_str = None
        return_desc = ""
        
        if return_type:
            try:
                if hasattr(return_type, '__origin__'):
                    origin = return_type.__origin__.__name__
                    args = ', '.join(arg.__name__ if hasattr(arg, '__name__') else str(arg) 
                                for arg in return_type.__args__)
                    return_str = f"{origin}[{args}]"
                else:
                    return_str = return_type.__name__ if hasattr(return_type, '__name__') else str(return_type)
            except Exception:
                return_str = str(return_type)
        
        # Try to get return description from docstring
        if docstring.returns:
            return_desc = docstring.returns.description
        else:
            # Try to find Sphinx/reST style return
            for meta in docstring.meta:
                if meta.args and meta.args[0] in ['return', 'returns']:
                    return_desc = meta.description
                    break
        
        return_info = ReturnInfo(
            type_hint=return_str,
            description=return_desc
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
        """Register a class and its methods as tools.
        
        Args:
            cls: The class to register
            name: Optional custom name for the class prefix
            
        Returns:
            List of registered tool names
        """
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
            
            # Also store under unqualified name if this is a single method class
            if len(inspect.getmembers(cls, predicate=lambda x: inspect.isfunction(x) and not x.__name__.startswith('_'))) == 1:
                self._tools[method_name] = metadata
                registered_names.append(method_name)
        
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
        """Get or create an instance of a tool.
        
        Args:
            name: Name of the tool to retrieve
            
        Returns:
            Tool instance or callable
            
        Raises:
            KeyError: If tool not found
        """
        # First check direct instance
        if name in self._instances:
            return self._instances[name]

        # Check metadata
        metadata = self._tools.get(name)
        if not metadata:
            # Try checking if this is a class method using full qualification
            if '.' in name:
                class_name, method_name = name.split('.')
                # Check if we have an instance for this class
                instance = self._instances.get(class_name)
                if instance:
                    return getattr(instance, method_name)
            raise KeyError(f"Tool '{name}' not found in catalog")

        if metadata.tool_type == ToolType.CLASS_METHOD:
            # Create class instance if needed
            if metadata.class_name not in self._instances:
                # Need to get the class from the method
                method = metadata.original_obj
                if hasattr(method, '__self__'):
                    # Method is bound to an instance
                    cls = method.__self__.__class__
                else:
                    # Method is unbound, get class from the method's module
                    cls = getattr(inspect.getmodule(method), metadata.class_name)
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
        """Create a catalog from a serialized dictionary.
        
        Args:
            data: Dictionary containing serialized tool data
            
        Returns:
            New ToolsCatalog instance with deserialized tools
        """
        catalog = cls()
        
        for name, tool_data in data["tools"].items():
            parameters = []
            for p in tool_data["parameters"]:
                # Keep type_hint as string
                type_hint = p["type_hint"] if p["type_hint"] else None
                
                parameters.append(ParameterInfo(
                    name=p["name"],
                    type_hint=type_hint,  # Pass the string directly
                    description=p["description"],
                    default=p["default"],
                    required=p["required"]
                ))
            
            # Keep return type hint as string
            returns = ReturnInfo(
                type_hint=tool_data["returns"]["type_hint"],
                description=tool_data["returns"]["description"]
            )
            
            metadata = ToolMetadata(
                name=tool_data["name"],
                description=tool_data["description"],
                tool_type=ToolType(tool_data["tool_type"]),
                parameters=parameters,
                returns=returns,
                original_obj=None,  # Will be reconstructed later if needed
                class_name=tool_data["class_name"],
                method_name=tool_data["method_name"],
                async_tool=tool_data["async_tool"]
            )
            
            catalog._tools[name] = metadata
        
        return catalog

    def _get_type_from_string(cls, type_hint_str: str) -> str:
        """Convert a type string to its string representation.
        
        Args:
            type_hint_str: String representation of a type
            
        Returns:
            Normalized string representation of the type
        """
        # Handle commonly used type hints
        type_mapping = {
            'str': 'str',
            'int': 'int',
            'float': 'float',
            'bool': 'bool',
            'list': 'List',
            'dict': 'Dict',
            'any': 'Any',
            'List': 'List',
            'Dict': 'Dict',
            'Any': 'Any',
            'Union': 'Union',
            'Optional': 'Optional'
        }
        
        # Check if it's a simple type
        if type_hint_str in type_mapping:
            return type_mapping[type_hint_str]
            
        # Handle generic types (like List[str], Dict[str, Any], etc.)
        if '[' in type_hint_str:
            base_type = type_hint_str.split('[')[0]
            if base_type in type_mapping:
                return type_hint_str  # Return the full generic type string
                
        # Default to the original string if no mapping found
        return type_hint_str

    def register_openapi_tool(self, tool: Tool, name: Optional[str] = None) -> str:
        """Register an OpenAPI tool from a Tool model instance."""
        tool_name = name or tool.function.name
        function = tool.function

        # Extract structured parameters for LLM understanding
        parameters = []
        if function.parameters:
            for param_location, params in function.parameters.items():
                if param_location == 'requestBody':
                    if isinstance(params, dict) and 'requestBody' in params:
                        request_body = params['requestBody']
                        if isinstance(request_body, ParameterSchema) and request_body.schema:
                            # Add the request body parameter itself
                            parameters.append(ParameterInfo(
                                name="requestBody",
                                type_hint=str(request_body.schema),
                                description=request_body.description or "Request body following schema",
                                required=request_body.required
                            ))
                            # Also extract individual parameters from the request body schema
                            for prop_name, prop_schema in request_body.schema.properties.items():
                                parameters.append(ParameterInfo(
                                    name=prop_name,
                                    type_hint=str(prop_schema.type),
                                    description=prop_schema.description or f"Parameter {prop_name}",
                                    required=prop_name in (request_body.schema.required or [])
                                ))
                    elif isinstance(params, ResolvedSchema) and params.properties:
                        # Add the request body parameter itself
                        parameters.append(ParameterInfo(
                            name="requestBody",
                            type_hint=str(params),
                            description="Request body following schema",
                            required=True
                        ))
                        # Also extract individual parameters from the schema
                        for prop_name, prop_schema in params.properties.items():
                            parameters.append(ParameterInfo(
                                name=prop_name,
                                type_hint=str(prop_schema.type),
                                description=prop_schema.description or f"Parameter {prop_name}",
                                required=prop_name in (params.required or [])
                            ))
                else:
                    # Handle path, query, and header parameters
                    for param_name, param_schema in params.items():
                        parameters.append(ParameterInfo(
                            name=param_name,
                            type_hint=param_schema.schema.type if hasattr(param_schema.schema, 'type') else 'Any',
                            description=param_schema.description or '',
                            required=getattr(param_schema, 'required', False)
                        ))

        metadata = ToolMetadata(
            name=tool_name,
            description=function.description or "",
            tool_type=ToolType.OPENAPI_TOOL,
            parameters=parameters,  # Structured parameters for LLM understanding
            schema=function.parameters,  # Original OpenAPI schema
            returns=ReturnInfo(
                type_hint='Dict[str, Any]',
                description=function.responses['200'].description if function.responses and '200' in function.responses else "Successful response"
            ),
            original_obj=tool,
            async_tool=True
        )

        self._tools[tool_name] = metadata
        return tool_name


# Create the global instance
tools_catalog = ToolsCatalog()

# Initialize and register internal tools
internal_file_tools = InternalFileTools()
internal_testing_tools = InternalTestingTools()

tools_catalog.register_tool(internal_file_tools, "internal_file_tools")
tools_catalog.register_tool(internal_testing_tools, "internal_testing_tools")