from __future__ import annotations
from typing import Any, Dict, List, Optional, Type, Union, get_type_hints, Callable
import inspect
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
from ..tools.web_scraper_tool import WebScraperTool
from ..models.tools_descriptors import ToolMetadata, ParameterInfo, ReturnInfo, ToolType
from ..models.toolset import Tool
from ..models.function import ResolvedSchema
import logging
from enum import Enum
from src.server.tools.url_tools import URLTools

load_dotenv()

logger = logging.getLogger(__name__)

class ToolType(str, Enum):
    """Type of tool in the catalog."""
    PYTHON_FUNCTION = "python_function"
    CLASS_METHOD = "class_method"
    CREWAI_TOOL = "crewai_tool"
    LANGCHAIN_TOOL = "langchain_tool"
    OPENAPI_TOOL = "openapi_tool"
    AI_TOOL = "ai_tool"

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
            self._tool_instances: Dict[str, Any] = {}
            self._functions: Dict[str, Callable] = {}
            self._classes: Dict[str, Type] = {}
            self._openapi_tools: Dict[str, Tool] = {}
            self._ai_tools: Dict[str, Union[CrewAITool, LangChainTool]] = {}
            self._metadata = {}  # Initialize metadata dictionary
            self.DEFAULT_TOOLS = {}  # Store default tools for test isolation
            self._initialize_default_tools()
            ToolsCatalog._initialized = True
        else:
            self._initialize_default_tools()

    def _extract_docstring_info(self, obj: Any, name: str, tool_type: ToolType = ToolType.PYTHON_FUNCTION) -> ToolMetadata:
        """Extract metadata from a function or method's docstring."""
        docstring = inspect.getdoc(obj) or ""
        parsed_docstring = docstring_parser.parse(docstring)
        parameters = []
        param_descriptions = {param.arg_name: param.description for param in parsed_docstring.params}
        
        # Get signature if possible
        try:
            sig = inspect.signature(obj)
            for param_name, param in sig.parameters.items():
                if param_name not in ['self', 'cls']:
                    param_type = param.annotation if param.annotation != inspect.Parameter.empty else Any
                    parameters.append(ParameterInfo(
                        name=param_name,
                        type_hint=self._type_to_string(param_type),
                        required=param.default == inspect.Parameter.empty,
                        description=param_descriptions.get(param_name, f"Parameter {param_name}"),
                        default=None if param.default == inspect.Parameter.empty else param.default
                    ))
        except (ValueError, TypeError):
            pass

        # Get return type and description
        return_type = "Any"
        return_description = "Return value"
        try:
            sig = inspect.signature(obj)
            if sig.return_annotation != inspect.Parameter.empty:
                return_type = self._type_to_string(sig.return_annotation)
            if parsed_docstring.returns:
                return_description = parsed_docstring.returns.description
        except (ValueError, TypeError):
            pass

        # Check if the function/method is async
        is_async = inspect.iscoroutinefunction(obj)
        if not is_async and hasattr(obj, '__call__'):
            # Check if it's a callable object with an async __call__ method
            is_async = inspect.iscoroutinefunction(obj.__call__)

        # Combine short and long descriptions
        description = parsed_docstring.short_description or ""
        if parsed_docstring.long_description:
            description = description + "\n\n" + parsed_docstring.long_description

        return ToolMetadata(
            name=str(name),  # Ensure name is a string
            tool_type=tool_type,
            description=description or docstring,
            parameters=parameters,
            original_obj=obj,
            returns=ReturnInfo(
                type_hint=return_type,
                description=return_description
            ),
            async_tool=is_async
        )

    def register_tool(self, tool: Any, name: Optional[str] = None) -> str:
        """Register a tool in the catalog.
        
        Args:
            tool: The tool to register
            name: Optional name for the tool
            
        Returns:
            The registered tool name
        """
        if name is None:
            name = tool.__name__ if hasattr(tool, '__name__') else tool.__class__.__name__
            
        # Create metadata based on tool type
        if inspect.isfunction(tool):
            metadata = self._create_function_metadata(tool, name)
            self._tools[name] = metadata
            self._functions[name] = tool
        elif inspect.isclass(tool):
            metadata = self._create_class_metadata(name, tool)
            self._tools[name] = metadata
            self._classes[name] = tool
        elif isinstance(tool, (CrewAITool, LangChainTool)):
            metadata = self._create_ai_tool_metadata(name, tool)
            self._tools[name] = metadata
            self._ai_tools[name] = tool
        elif isinstance(tool, Tool):
            metadata = self._create_openapi_tool_metadata(name, tool)
            self._tools[name] = metadata
            self._openapi_tools[name] = tool
        else:
            # Store instance and its methods
            metadata = self._create_instance_metadata(name, tool)
            self._tools[name] = metadata
            self._tool_instances[name] = tool
            
            # Store the class in _classes if it's a class instance
            if not inspect.isclass(tool) and not inspect.isfunction(tool):
                self._classes[name] = tool.__class__
            
            # Register instance methods
            if hasattr(tool, '__dict__'):
                for method_name, method in inspect.getmembers(tool, predicate=inspect.ismethod):
                    if not method_name.startswith('_'):
                        method_qualified_name = f"{name}.{method_name}"
                        self._tool_instances[method_qualified_name] = method
                        
                        # Create metadata for the method
                        method_metadata = self._extract_docstring_info(method, method_qualified_name, ToolType.CLASS_METHOD)
                        method_metadata.class_name = name
                        method_metadata.method_name = method_name
                        self._tools[method_qualified_name] = method_metadata
                        
        return name

    def _create_method_metadata(self, method: Callable, method_name: str) -> ToolMetadata:
        """Create metadata for a method."""
        sig = inspect.signature(method)
        params = []
        for name, param in sig.parameters.items():
            if name == 'self':
                continue
            type_hint = param.annotation if param.annotation != inspect.Parameter.empty else Any
            # Convert type hint to string format
            type_str = str(type_hint)
            if type_str.startswith("<class '") and type_str.endswith("'>"):
                type_str = type_str[8:-2]  # Remove "<class '" and "'>"
            params.append(ParameterInfo(
                name=name,
                type_hint=type_str,
                required=param.default == inspect.Parameter.empty,
                description=f"Parameter {name}"
            ))
        return ToolMetadata(
            name=method_name,
            description=inspect.getdoc(method) or f"Method {method_name}",
            tool_type=ToolType.CLASS_METHOD,
            parameters=params,
            returns=ReturnInfo(type_hint="Any", description="Method return value"),
            original_obj=method,
            async_tool=inspect.iscoroutinefunction(method)
        )

    def register_function(self, func: callable, name: Optional[str] = None) -> str:
        """Register a Python function as a tool."""
        tool_name = name or func.__name__
        metadata = self._extract_docstring_info(func, tool_name, ToolType.PYTHON_FUNCTION)
        self._tools[tool_name] = metadata
        self._functions[tool_name] = func
        self._tool_instances[tool_name] = func
        return tool_name

    def register_class(self, cls: Type, name: Optional[str] = None) -> List[str]:
        """Register a Python class as a tool, including its methods."""
        class_name = name or cls.__name__
        registered_names = []

        # Register class methods
        for method_name, method in inspect.getmembers(cls, predicate=inspect.isfunction):
            if not method_name.startswith('_'):  # Skip private methods
                full_name = f"{class_name}.{method_name}"
                metadata = self._extract_docstring_info(method, full_name, ToolType.CLASS_METHOD)
                metadata.class_name = class_name
                metadata.method_name = method_name
                metadata.async_tool = inspect.iscoroutinefunction(method)
                
                self._tools[full_name] = metadata
                registered_names.append(full_name)

        return registered_names

    def register_instance(self, instance: Any, name: str) -> List[str]:
        """Register a class instance and its methods."""
        tool_names = []

        # Register the instance itself
        self._tool_instances[name] = instance
        
        # Extract docstring from the instance's class
        docstring = inspect.getdoc(instance.__class__) or ""
        
        # Create metadata for the instance
        if hasattr(instance, 'required_args'):
            # For tools with required_args (like MockInternalTool)
            parameters = []
            for param_name, param_type in instance.required_args.items():
                description = "Description of the content" if param_name == "description" else "Path to the file to read" if param_name == "file_path" else f"Required parameter {param_name}"
                parameters.append(ParameterInfo(
                    name=param_name,
                    type_hint=self._type_to_string(param_type),
                    required=True,
                    description=description
                ))
            
            self._tools[name] = ToolMetadata(
                name=name,
                tool_type=ToolType.AI_TOOL,
                description=docstring,
                parameters=parameters,
                original_obj=instance,
                returns=ReturnInfo(
                    type_hint="Any",
                    description="Return value"
                ),
                async_tool=inspect.iscoroutinefunction(instance) or (hasattr(instance, '__call__') and inspect.iscoroutinefunction(instance.__call__))
            )
        else:
            # For regular class instances
            metadata = self._extract_docstring_info(instance.__class__, name)
            metadata.tool_type = ToolType.CLASS_METHOD  # Override tool type for class instances
            self._tools[name] = metadata
        
        tool_names.append(name)

        # Register instance methods
        for method_name, method in inspect.getmembers(instance, inspect.ismethod):
            if not method_name.startswith('_'):  # Skip private methods
                full_name = f"{name}.{method_name}"
                self._tool_instances[full_name] = method
                
                # Extract method metadata
                metadata = self._extract_docstring_info(method, full_name, ToolType.CLASS_METHOD)
                metadata.class_name = name
                metadata.method_name = method_name
                metadata.async_tool = inspect.iscoroutinefunction(method)
                
                # Extract parameters from method
                sig = inspect.signature(method)
                parameters = []
                for param_name, param in sig.parameters.items():
                    if param_name not in ['self', 'cls']:
                        parameters.append(ParameterInfo(
                            name=param_name,
                            type_hint=self._type_to_string(param.annotation if param.annotation != inspect.Parameter.empty else Any),
                            required=param.default == inspect.Parameter.empty,
                            description=f"Parameter {param_name}"
                        ))
                metadata.parameters = parameters
                
                self._tools[full_name] = metadata
                tool_names.append(full_name)

        return tool_names

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
                                default=None if param.default == inspect.Parameter.empty else param.default,
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
                    default=None if param.default == inspect.Parameter.empty else param.default,
                    required=param.default == inspect.Parameter.empty
                ))
            
        except (ValueError, TypeError) as e:
            self._logger.warning(f"Could not extract parameters from {tool}: {str(e)}")
        
        return params

    def _type_to_string(self, type_hint: Any) -> str:
        """Convert a type hint to a string representation."""
        if hasattr(type_hint, "__name__"):
            return type_hint.__name__
        return str(type_hint)

    def register_ai_tool(self, tool: Union[CrewAITool, LangChainTool], name: Optional[str] = None) -> str:
        """Register an AI tool (CrewAI or LangChain) in the catalog.
        
        Args:
            tool: The AI tool to register
            name: Optional custom name for the tool
            
        Returns:
            The registered tool name
            
        Raises:
            ValueError: If the tool is not a valid CrewAI or LangChain tool
        """
        if not isinstance(tool, (CrewAITool, LangChainTool)):
            raise ValueError(f"Expected CrewAI or LangChain tool, got {type(tool)}")
            
        tool_name = name or tool.__class__.__name__
        
        # Store the tool instance
        self._tool_instances[tool_name] = tool
        self._ai_tools[tool_name] = tool
        
        # Extract parameters from args_schema if available
        parameters = []
        if hasattr(tool, 'required_args'):
            # For mock tools with required_args
            for param_name, param_type in tool.required_args.items():
                parameters.append(ParameterInfo(
                    name=param_name,
                    type_hint=param_type,
                    description=f"Required parameter {param_name}",
                    required=True
                ))
        elif hasattr(tool, 'args_schema'):
            schema = tool.args_schema
            if schema:
                for field_name, field in schema.model_fields.items():
                    parameters.append(ParameterInfo(
                        name=field_name,
                        type_hint=self._type_to_string(field.annotation),
                        description=field.description or f"Parameter {field_name}",
                        required=field.is_required(),
                        default=None if field.is_required() else field.default
                    ))
        
        # Create metadata
        description = tool.description if hasattr(tool, 'description') else ""
        metadata = ToolMetadata(
            name=tool_name,
            description=description,
            tool_type=ToolType.CREWAI_TOOL if isinstance(tool, CrewAITool) else ToolType.LANGCHAIN_TOOL,
            parameters=parameters,
            returns=ReturnInfo(type_hint="str", description="Result of the tool execution"),
            original_obj=tool,
            async_tool=hasattr(tool, '_arun')
        )
        
        # Store metadata
        self._tools[tool_name] = metadata
        
        return tool_name

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
                        schema = params['requestBody'].schema
                        # Add the full request body parameter
                        parameters.append(ParameterInfo(
                            name="requestBody",
                            type_hint="object",
                            description=params['requestBody'].description or "Request body schema",
                            required=params['requestBody'].required
                        ))
                        # Also add individual properties for granular access
                        if schema and schema.properties:
                            for prop_name, prop_schema in schema.properties.items():
                                parameters.append(ParameterInfo(
                                    name=prop_name,
                                    type_hint=prop_schema.type,
                                    description=prop_schema.description or '',
                                    required=prop_name in (schema.required or [])
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
        self._openapi_tools[tool_name] = tool
        self._tool_instances[tool_name] = tool
        return tool_name

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
        if name in self._tool_instances:
            return self._tool_instances[name]
            
        # Check functions
        if name in self._functions:
            return self._functions[name]
            
        # Check metadata
        metadata = self._tools.get(name)
        if not metadata:
            # Try checking if this is a method call using full qualification
            parts = name.split('.')
            if len(parts) >= 2:
                instance_name = '.'.join(parts[:-1])  # Everything except the last part
                method_name = parts[-1]  # Last part is the method name
                
                if instance_name in self._tool_instances:
                    instance = self._tool_instances[instance_name]
                    if hasattr(instance, method_name):
                        return getattr(instance, method_name)
            
            raise KeyError(f"Tool not found: {name}")
            
        # Create instance based on tool type
        if metadata.tool_type == ToolType.PYTHON_FUNCTION:
            return metadata.original_obj
        elif metadata.tool_type == ToolType.CLASS_METHOD:
            instance = metadata.original_obj()
            self._tool_instances[name] = instance
            return instance
        elif metadata.tool_type == ToolType.CREWAI_TOOL:
            return metadata.original_obj
        elif metadata.tool_type == ToolType.LANGCHAIN_TOOL:
            return metadata.original_obj
        elif metadata.tool_type == ToolType.OPENAPI_TOOL:
            return metadata.original_obj
        else:
            raise ValueError(f"Unknown tool type: {metadata.tool_type}")

    def list_tools_by_type(self) -> Dict[str, List[str]]:
        """List all tools grouped by type."""
        return {
            "functions": list(self._functions.keys()),
            "classes": list(self._classes.keys()),
            "instances": list(self._tool_instances.keys())  # Use _tool_instances instead of _instances
        }

    def list_tools(self) -> List[str]:
        """List all registered tool names."""
        return list(self._tools.keys())

    def get_tool(self, name: str) -> Optional[ToolMetadata]:
        """Get metadata for a registered tool."""
        return self._tools.get(name)

    def reset(self) -> None:
        """Reset the catalog to its initial state."""
        self._tools = {}
        self._tool_instances = {}  # Make sure this is initialized
        self._functions = {}
        self._classes = {}
        self._openapi_tools = {}
        self._ai_tools = {}
        self._initialize_default_tools()

    def _initialize_default_tools(self):
        """Initialize default tools."""
        try:
            # Initialize default tools only if they haven't been initialized
            if not self.DEFAULT_TOOLS:
                # Register CrewAI tools
                website_tool = WebsiteSearchTool()
                serper_tool = SerperDevTool()
                file_read_tool = FileReadTool()
                web_scraper_tool = WebScraperTool()
                self.register_ai_tool(website_tool, "WebsiteSearchTool")
                self.register_ai_tool(serper_tool, "SerperDevTool")
                self.register_ai_tool(file_read_tool, "FileReadTool")
                self.register_instance(web_scraper_tool, "WebScraperTool")
                
                # Register custom tools
                file_tool = FileTool()
                microservices_tool = MicroservicesTool()
                sms_tool = SMSTool()
                self.register_instance(file_tool, "FileTool")
                self.register_instance(microservices_tool, "MicroservicesTool")
                self.register_instance(sms_tool, "SMSTool")
                
                # Register GitHub tool if credentials are available
                github_token = getenv("GITHUB_TOKEN")
                repo_name = getenv("GITHUB_REPO")
                if github_token and repo_name:
                    github_tool = GitHubTool(github_token, repo_name)
                    self.register_instance(github_tool, "GitHubTool")
                
                # Register URL tools
                url_tools = URLTools()
                self.register_instance(url_tools, "URLTools")
                
                # Store current tools as defaults
                self.DEFAULT_TOOLS = {
                    'tools': self._tools.copy(),
                    'instances': self._tool_instances.copy(),
                    'functions': self._functions.copy(),
                    'classes': self._classes.copy(),
                    'openapi': self._openapi_tools.copy(),
                    'ai_tools': self._ai_tools.copy()
                }
        except Exception as e:
            logger.error(f"Error initializing default tools: {str(e)}")
            raise

    def unregister_tool(self, name: str) -> None:
        """Unregister a tool from the catalog.
        
        Args:
            name: Name of the tool to unregister
        """
        if name in self._tools:
            del self._tools[name]
        if name in self._tool_instances:
            del self._tool_instances[name]
        if name in self._functions:
            del self._functions[name]
        if name in self._classes:
            del self._classes[name]
        if name in self._openapi_tools:
            del self._openapi_tools[name]
        if name in self._ai_tools:
            del self._ai_tools[name]

    def _create_function_metadata(self, func: Callable, name: str) -> ToolMetadata:
        """Create metadata for a function.

        Args:
            func: The function to create metadata for
            name: Name for the function

        Returns:
            ToolMetadata for the function
        """
        logger.debug(f"Creating function metadata for: {name}")
        
        # Extract docstring info
        metadata = self._extract_docstring_info(func, name)
        
        # Create metadata
        return metadata

    def get_tool_metadata(self, name: str) -> Optional[ToolMetadata]:
        """Get metadata for a tool from the catalog."""
        # If metadata doesn't exist but tool does, create it
        if name not in self._metadata and name in self._tools:
            tool = self._tools[name]
            self._metadata[name] = self._create_tool_metadata(name, tool)
        return self._metadata.get(name)

    def _create_tool_metadata(self, name: str, tool: Any) -> ToolMetadata:
        """Create metadata for a tool."""
        # Extract tool information
        if inspect.isclass(tool):
            return self._create_class_metadata(name, tool)
        elif inspect.isfunction(tool) or inspect.ismethod(tool):
            return self._create_function_metadata(name, tool)
        else:
            return self._create_instance_metadata(name, tool)

    def _create_instance_metadata(self, name: str, tool: Any) -> ToolMetadata:
        """Create metadata for a tool instance.
        
        Args:
            name: Name of the tool
            tool: The tool instance
            
        Returns:
            ToolMetadata for the tool
        """
        # Extract docstring info
        metadata = self._extract_docstring_info(tool, name)
        
        # Get class name and method name if this is a method
        class_name = None
        method_name = None
        if '.' in name:
            class_name, method_name = name.split('.')
            
        # Update metadata with class and method names
        metadata.class_name = class_name
        metadata.method_name = method_name
        
        return metadata

    def update_tool_metadata(self, name: str, updates: Dict[str, Any]) -> None:
        """Update metadata for a registered tool.
        
        Args:
            name: Name of the tool to update
            updates: Dictionary of metadata fields to update
        """
        if name in self._tools:
            metadata = self._tools[name]
            for key, value in updates.items():
                if hasattr(metadata, key):
                    setattr(metadata, key, value)

    def to_dict(self) -> Dict[str, Any]:
        """Convert the catalog to a dictionary for serialization.
        
        Returns:
            A dictionary containing all tool metadata.
        """
        tools_dict = {}
        for name, metadata in self._tools.items():
            tools_dict[name] = metadata.model_dump()
        return {"tools": tools_dict}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ToolsCatalog':
        """Create a new catalog instance from a dictionary.
        
        Args:
            data: Dictionary containing tool metadata
            
        Returns:
            A new ToolsCatalog instance
        """
        catalog = cls()
        for name, metadata_dict in data.get("tools", {}).items():
            metadata = ToolMetadata(**metadata_dict)
            catalog._tools[name] = metadata
        return catalog

    def reset_to_defaults(self):
        """Reset the catalog to default tools."""
        if self.DEFAULT_TOOLS:
            self._tools = self.DEFAULT_TOOLS['tools'].copy()
            self._tool_instances = self.DEFAULT_TOOLS['instances'].copy()
            self._functions = self.DEFAULT_TOOLS['functions'].copy()
            self._classes = self.DEFAULT_TOOLS['classes'].copy()
            self._openapi_tools = self.DEFAULT_TOOLS['openapi'].copy()
            self._ai_tools = self.DEFAULT_TOOLS['ai_tools'].copy()

    def reload_all_tools(self) -> List[str]:
        """Reload all tools and return the list of registered tools."""
        self.reset()
        self._load_tools()
        return list(self._tools.keys())

    def _create_class_metadata(self, cls: Type, class_name: str) -> ToolMetadata:
        """Create metadata for a class."""
        return ToolMetadata(
            name=class_name,
            description=inspect.getdoc(cls) or f"Class {class_name}",
            tool_type=ToolType.CLASS,
            parameters=[],
            returns=ReturnInfo(type_hint="Any", description="Class instance"),
            original_obj=cls,
            async_tool=False
        )

    def _load_tools(self):
        """Load all tools from the catalog."""
        # Load default tools
        for tool_type, tools in self.DEFAULT_TOOLS.items():
            for tool in tools:
                self.register_tool(tool)

tools_catalog = ToolsCatalog() 