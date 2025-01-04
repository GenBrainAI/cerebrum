from __future__ import annotations
from typing import Any, Dict, List, Optional, Union, Type, get_type_hints, Callable
from pydantic import BaseModel
import logging
import inspect
import docstring_parser
from enum import Enum
from datetime import datetime, timedelta
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
from .internal_proxy_tools import InternalProxyTools
import time

load_dotenv()

class ToolExecutionMetrics:
    """Tracks execution metrics for a tool."""
    
    def __init__(self):
        self.start_time: Optional[datetime] = None
        self.end_time: Optional[datetime] = None
        self.success: bool = False
        self.error: Optional[str] = None
        self.input_params: Dict[str, Any] = {}
        self.output: Optional[Any] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to dictionary format."""
        return {
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration": (self.end_time - self.start_time).total_seconds() 
                      if self.start_time and self.end_time else None,
            "success": self.success,
            "error": self.error,
            "input_params": self.input_params,
            "output": str(self.output) if self.output is not None else None
        }

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
            self._execution_metrics: Dict[str, List[ToolExecutionMetrics]] = {}
            self._logger = logging.getLogger(__name__)
            self._initialize_default_tools()
            ToolsCatalog._initialized = True

    def register_tool(self, tool: Any, name: Optional[str] = None) -> str:
        """Register a tool with enhanced logging and validation."""
        tool_name = name or getattr(tool, '__name__', str(tool))
        
        try:
            self._logger.info(f"Registering tool: {tool_name}")
            self._logger.debug(f"Tool type: {type(tool)}")
            
            # Handle CrewAI tools
            if isinstance(tool, CrewAITool):
                metadata = self._create_crewai_tool_metadata(tool, tool_name)
                self._tools[tool_name] = metadata
                self._instances[tool_name] = create_crewai_tool(tool_name, metadata, self._proxy, self)
                return tool_name
            
            # Handle LangChain tools
            if isinstance(tool, LangChainTool):
                metadata = self._create_langchain_tool_metadata(tool, tool_name)
                self._tools[tool_name] = metadata
                self._instances[tool_name] = create_crewai_tool(tool_name, metadata, self._proxy, self)
                return tool_name
            
            # Handle class instances
            if not inspect.isclass(tool) and not inspect.isfunction(tool):
                metadata = self._create_class_instance_metadata(tool, tool_name)
                self._tools[tool_name] = metadata
                self._instances[tool_name] = tool
                return tool_name
            
            # Handle classes
            if inspect.isclass(tool):
                metadata = self._create_class_metadata(tool, tool_name)
                self._tools[tool_name] = metadata
                self._instances[tool_name] = tool()
                self._classes[tool_name] = tool  # Add class to _classes dictionary
                self.register_class(tool, tool_name)  # Register class methods
                return tool_name
            
            # Handle functions
            metadata = self._create_function_metadata(tool, tool_name)
            self._tools[tool_name] = metadata
            self._instances[tool_name] = tool
            self._functions[tool_name] = tool  # Add function to _functions dictionary
            return tool_name
            
        except Exception as e:
            self._logger.error(f"Failed to register tool {tool_name}: {str(e)}")
            raise

    def _validate_tool(self, tool: Any) -> bool:
        """Validate tool meets minimum requirements."""
        try:
            # Check for required attributes/methods based on tool type
            if inspect.isfunction(tool):
                # Function tools should have docstring and type hints
                if not tool.__doc__:
                    self._logger.warning(f"Tool function missing docstring")
                    return False
                    
            elif inspect.isclass(tool):
                # Class tools should have at least one public method
                methods = [m for m in dir(tool) if not m.startswith('_')]
                if not methods:
                    self._logger.warning(f"Tool class has no public methods")
                    return False
                    
            elif isinstance(tool, (CrewAITool, LangChainTool)):
                # AI tools should have name and description
                if not hasattr(tool, 'name') or not hasattr(tool, 'description'):
                    self._logger.warning(f"AI tool missing name or description")
                    return False
                    
            return True
            
        except Exception as e:
            self._logger.error(f"Tool validation failed: {str(e)}")
            return False

    async def execute_tool(self, tool_name: str, kwargs: Dict[str, Any]) -> Any:
        """Execute a tool with the given name and arguments."""
        try:
            # Get tool instance
            tool_instance = self.get_tool_instance(tool_name)
            if not tool_instance:
                raise ValueError(f"Tool {tool_name} not found")

            # Track tool execution start
            start_time = time.time()
            
            try:
                # Execute tool
                result = await tool_instance(**kwargs)
                
                # Track successful execution
                execution_time = time.time() - start_time
                self._track_tool_execution(
                    tool_name=tool_name,
                    execution_time=execution_time,
                    success=True,
                    error=None,
                    input_params=kwargs,
                    output=result
                )
                
                return result
                
            except Exception as e:
                # Track failed execution
                execution_time = time.time() - start_time
                self._track_tool_execution(
                    tool_name=tool_name,
                    execution_time=execution_time,
                    success=False,
                    error=str(e),
                    input_params=kwargs,
                    output=None
                )
                raise

        except Exception as e:
            error_msg = f"Error executing tool {tool_name}: {str(e)}"
            print(f"❌ {error_msg}")
            raise

    def _track_tool_execution(
        self,
        tool_name: str,
        execution_time: float,
        success: bool,
        error: Optional[str] = None,
        input_params: Optional[Dict[str, Any]] = None,
        output: Any = None
    ) -> None:
        """Track tool execution metrics."""
        if tool_name not in self._execution_metrics:
            self._execution_metrics[tool_name] = {
                "total_executions": 0,
                "successful_executions": 0,
                "failed_executions": 0,
                "average_duration": 0.0,
                "last_execution": None
            }
        
        metrics = self._execution_metrics[tool_name]
        metrics["total_executions"] += 1
        
        if success:
            metrics["successful_executions"] += 1
        else:
            metrics["failed_executions"] += 1
        
        # Update average duration
        old_avg = metrics["average_duration"]
        metrics["average_duration"] = (old_avg * (metrics["total_executions"] - 1) + execution_time) / metrics["total_executions"]
        
        # Store last execution details
        metrics["last_execution"] = {
            "start_time": datetime.now() - timedelta(seconds=execution_time),
            "end_time": datetime.now(),
            "duration": execution_time,
            "success": success,
            "error": error if error else None,
            "input_params": input_params or {},
            "output": str(output) if output is not None else None
        }

    def get_tool_metrics(self, tool_name: Optional[str] = None) -> Dict[str, Any]:
        """Get execution metrics for one or all tools."""
        if tool_name:
            if tool_name not in self._execution_metrics:
                return {}
            return self._execution_metrics[tool_name]
        
        return self._execution_metrics

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
        # Initialize internal tools first
        internal_file_tools = InternalFileTools()
        internal_testing_tools = InternalTestingTools()
        internal_proxy_tools = InternalProxyTools()
        
        self.register_tool(internal_file_tools, "internal_file_tools")
        self.register_tool(internal_testing_tools, "internal_testing_tools")
        self.register_tool(internal_proxy_tools, "internal_proxy_tools")
        
        # Initialize other default tools
        self.DEFAULT_TOOLS = {
            "WebsiteSearchTool": WebsiteSearchTool(),
            "SerperDevTool": SerperDevTool(),
            "FileReadTool": FileReadTool(
                file_path='job_description_example.md',
                description='A tool to read the job description example file.'
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

        # Register GitHubTool separately since it needs special initialization
        self.register_class(GitHubTool, "GitHubTool")
        # Create instance with required parameters
        self._instances["GitHubTool"] = GitHubTool(
            access_token=getenv("GITHUB_ACCESS_TOKEN"),
            repo_name=getenv("GITHUB_REPO_NAME", "GenBrainAI/cerebrum")
        )

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

    @classmethod
    def reset(cls):
        """Reset the catalog state. Should only be used in tests."""
        if cls._instance is not None:
            # Clear instance state
            cls._instance._tools.clear()
            cls._instance._instances.clear()
            cls._instance._functions.clear()
            cls._instance._classes.clear()
            
            # Re-initialize with internal tools
            cls._instance._initialize_default_tools()

    def _create_crewai_tool_metadata(self, tool: CrewAITool, tool_name: str) -> ToolMetadata:
        """Create metadata for a CrewAI tool."""
        return ToolMetadata(
            name=tool_name,
            description=tool.description,
            tool_type=ToolType.CREWAI_TOOL,
            parameters=self._extract_parameters(tool),
            returns=ReturnInfo(type_hint='Any', description=''),
            original_obj=tool
        )

    def _create_langchain_tool_metadata(self, tool: LangChainTool, tool_name: str) -> ToolMetadata:
        """Create metadata for a LangChain tool."""
        return ToolMetadata(
            name=tool_name,
            description=tool.description,
            tool_type=ToolType.LANGCHAIN_TOOL,
            parameters=self._extract_parameters(tool),
            returns=ReturnInfo(type_hint='Any', description=''),
            original_obj=tool
        )

    def _create_class_instance_metadata(self, tool: Any, tool_name: str) -> ToolMetadata:
        """Create metadata for a class instance."""
        return ToolMetadata(
            name=tool_name,
            description=getattr(tool, '__doc__', '') or '',
            tool_type=ToolType.CLASS_METHOD,
            parameters=self._extract_parameters(tool),
            returns=ReturnInfo(type_hint='Any', description=''),
            original_obj=tool
        )

    def _create_class_metadata(self, tool: Type, tool_name: str) -> ToolMetadata:
        """Create metadata for a class."""
        return ToolMetadata(
            name=tool_name,
            description=tool.__doc__ or '',
            tool_type=ToolType.CLASS_METHOD,
            parameters=self._extract_parameters(tool),
            returns=ReturnInfo(type_hint='Any', description=''),
            original_obj=tool
        )

    def _create_function_metadata(self, tool: Callable, tool_name: str) -> ToolMetadata:
        """Create metadata for a function."""
        return ToolMetadata(
            name=tool_name,
            description=tool.__doc__ or '',
            tool_type=ToolType.PYTHON_FUNCTION,
            parameters=self._extract_parameters(tool),
            returns=ReturnInfo(type_hint='Any', description=''),
            original_obj=tool
        )

    def _extract_parameters(self, tool: Any) -> List[ParameterInfo]:
        """Extract parameter information from a tool."""
        params = []
        
        try:
            if inspect.isclass(tool):
                # For classes, get signature of __init__
                sig = inspect.signature(tool.__init__)
            elif inspect.isfunction(tool) or inspect.ismethod(tool):
                # For functions and methods
                sig = inspect.signature(tool)
            elif hasattr(tool, '__call__'):
                # For callable objects
                sig = inspect.signature(tool.__call__)
            else:
                # For class instances, get all public methods
                methods = [m for m in dir(tool) if not m.startswith('_') and callable(getattr(tool, m))]
                for method_name in methods:
                    method = getattr(tool, method_name)
                    try:
                        method_sig = inspect.signature(method)
                        for name, param in method_sig.parameters.items():
                            if name == 'self':
                                continue
                            params.append(ParameterInfo(
                                name=f"{method_name}.{name}",
                                type_hint=str(param.annotation) if param.annotation != inspect.Parameter.empty else None,
                                description='',
                                default=param.default if param.default != inspect.Parameter.empty else None,
                                required=param.default == inspect.Parameter.empty
                            ))
                    except (ValueError, TypeError):
                        continue
                return params
            
            # Process signature for callable objects
            for name, param in sig.parameters.items():
                if name == 'self':
                    continue
                params.append(ParameterInfo(
                    name=name,
                    type_hint=str(param.annotation) if param.annotation != inspect.Parameter.empty else None,
                    description='',
                    default=param.default if param.default != inspect.Parameter.empty else None,
                    required=param.default == inspect.Parameter.empty
                ))
            
        except (ValueError, TypeError) as e:
            self._logger.warning(f"Could not extract parameters from {tool}: {str(e)}")
        
        return params

    def _register_class_methods(self, cls: Type, class_name: str) -> None:
        """Register all public methods of a class as individual tools."""
        for method_name, method in inspect.getmembers(cls, predicate=inspect.isfunction):
            if not method_name.startswith('_'):  # Only register public methods
                full_name = f"{class_name}.{method_name}"
                metadata = ToolMetadata(
                    tool_type=ToolType.CLASS_METHOD,
                    name=full_name,
                    description=method.__doc__ or "",
                    class_name=class_name,
                    method_name=method_name,
                    parameters=self._get_method_parameters(method),
                    return_info=self._get_method_return_info(method)
                )
                self._tools[full_name] = metadata

    def _get_method_parameters(self, method) -> List[ParameterInfo]:
        """Extract parameter information from a method."""
        params = []
        signature = inspect.signature(method)
        docstring = docstring_parser.parse(method.__doc__ or "")
        type_hints = get_type_hints(method)
        
        for name, param in signature.parameters.items():
            if name == 'self':
                continue
            param_type = type_hints.get(name, Any).__name__ if name in type_hints else 'Any'
            description = next((p.description for p in docstring.params if p.arg_name == name), "")
            params.append(ParameterInfo(name=name, type=param_type, description=description))
        
        return params

    def _get_method_return_info(self, method) -> ReturnInfo:
        """Extract return information from a method."""
        docstring = docstring_parser.parse(method.__doc__ or "")
        return_type = get_type_hints(method).get('return', Any).__name__
        description = docstring.returns.description if docstring.returns else ""
        return ReturnInfo(type=return_type, description=description)


# Create the global instance
tools_catalog = ToolsCatalog()

# Initialize and register internal tools
internal_file_tools = InternalFileTools()
internal_testing_tools = InternalTestingTools()

tools_catalog.register_tool(internal_file_tools, "internal_file_tools")
tools_catalog.register_tool(internal_testing_tools, "internal_testing_tools")