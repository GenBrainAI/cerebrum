from __future__ import annotations
from typing import Any, Dict, List, Optional, Type, Union, Callable
import inspect
import docstring_parser
from os import getenv
from dotenv import load_dotenv
import logging
from enum import Enum
import traceback

# Third-party tools
from crewai.tools.base_tool import BaseTool as CrewAITool
from crewai_tools import (
    WebsiteSearchTool,
    FileReadTool,
    SerperDevTool
)
from langchain.tools import BaseTool as LangChainTool

# Internal tools
from src.server.tools.file_tool import FileTool
from src.server.tools.github_tool import GitHubTool
from src.server.tools.microservices_tool import MicroservicesTool
from src.server.tools.sms_tool import SMSTool
from src.server.tools.web_scraper_tool import WebScraperTool
from src.server.tools.url_tools import URLTools
from src.server.tools.internal_file_tools import InternalFileTools
from src.server.tools.internal_credentials_tools import InternalCredentialsTools
from src.server.tools.internal_testing_tools import InternalTestingTools
from src.server.tools.internal_proxy_tools import InternalProxyTools
from src.server.tools.py_exec import PyExec
from src.server.tools.general_tools.datetime_tools import DateTimeTools, get_current_datetime, is_future_date
from src.server.tools.general_tools.system_monitor_tools import SystemMonitorTools
from src.server.tools.general_tools.network_tools import NetworkTools

# Models
from src.server.models.tools_descriptors import ToolMetadata, ParameterInfo, ReturnInfo, ToolType
from src.server.models.toolset import Tool

# Load environment variables
load_dotenv()

# Initialize logger
logger = logging.getLogger(__name__)

# Note: ToolType is now imported from src.server.models.tools_descriptors
# and no longer defined here to avoid duplication

class ToolsCatalog:
    """Singleton catalog for all available tools."""
    
    _instance = None
    _initialized = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ToolsCatalog, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not self._initialized:
            self._logger = logging.getLogger(__name__)
            self._tools: Dict[str, ToolMetadata] = {}
            self._tool_instances: Dict[str, Any] = {}
            self._functions: Dict[str, Callable] = {}
            self._classes: Dict[str, Type] = {}
            self._openapi_tools: Dict[str, Tool] = {}
            self._ai_tools: Dict[str, Union[CrewAITool, LangChainTool]] = {}
            self._metadata = {}  # Initialize metadata dictionary
            self.DEFAULT_TOOLS = {}  # Store default tools for test isolation
            self._initialize_default_tools()
            self._initialized = True

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
                    # Use object instead of Any as the default type
                    param_type = param.annotation if param.annotation != inspect.Parameter.empty else object
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
        return_type = "object"  # Use object instead of Any
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
            name=str(name),
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

    def _create_instance_metadata(self, instance: Any, name: str) -> ToolMetadata:
        """Create metadata for a class instance.
        
        Args:
            instance: The instance to create metadata for
            name: Name for the instance
            
        Returns:
            ToolMetadata for the instance
        """
        # Get docstring from the instance's class
        docstring = inspect.getdoc(instance.__class__) or ""
        parsed_docstring = docstring_parser.parse(docstring)
        description = parsed_docstring.short_description or ""
        if parsed_docstring.long_description:
            description = description + "\n\n" + parsed_docstring.long_description
        
        # Get parameters from instance attributes or __init__
        parameters = []
        if hasattr(instance, '__init__'):
            sig = inspect.signature(instance.__init__)
            for param_name, param in sig.parameters.items():
                if param_name not in ['self', 'cls']:
                    param_type = param.annotation if param.annotation != inspect.Parameter.empty else object
                    parameters.append(ParameterInfo(
                        name=param_name,
                        type_hint=self._type_to_string(param_type),
                        required=param.default == inspect.Parameter.empty,
                        description=f"Parameter {param_name}",
                        default=None if param.default == inspect.Parameter.empty else param.default
                    ))
        
        # Create metadata using a dictionary to force keyword argument initialization
        metadata_args = {
            "name": name,
            "tool_type": ToolType.CLASS_METHOD,
            "description": description or docstring,
            "parameters": parameters,
            "original_obj": instance,
            "returns": ReturnInfo(
                type_hint="Any", 
                description="Instance object"
            ),
            "async_tool": inspect.iscoroutinefunction(instance) or (hasattr(instance, '__call__') and inspect.iscoroutinefunction(instance.__call__))
        }
        return ToolMetadata(**metadata_args)

    def register_instance(self, instance: Any, name: str, exclude_base_methods: bool = True, register_instance_itself: bool = False) -> List[str]:
        """Register an instance and its methods as tools in the catalog.
        
        This method registers an object instance and its methods as tools in the catalog.
        By default, it only registers methods defined in the instance's own class (not inherited methods)
        and does not register the instance itself as a tool.
        
        Args:
            instance: The object instance to register
            name: Base name for the instance and its methods
            exclude_base_methods: Whether to exclude methods inherited from base classes (default: True)
            register_instance_itself: Whether to register the instance itself as a tool (default: False)
            
        Returns:
            List of registered tool names
        """
        print(f"Registering instance {name}")
        registered_names = []
        
        # Get the class of the instance
        instance_class = instance.__class__
        
        # Get only methods defined in the instance's own class
        own_method_names = set()
        if exclude_base_methods:
            # Find methods defined in this class, not in base classes
            for cls in instance_class.__mro__:
                if cls == instance_class:
                    # Include methods from this class
                    own_method_names.update(cls.__dict__.keys())
                elif cls != object:  # Don't process the base 'object' class
                    # Exclude methods from base classes
                    own_method_names.difference_update(cls.__dict__.keys())
        
        # Register the base instance if requested
        if register_instance_itself:
            metadata = self._create_instance_metadata(instance, name)
            self._tools[name] = metadata
            self._tool_instances[name] = instance
            registered_names.append(name)
        
        # Register all public methods (filtering base methods if requested)
        for method_name, method in inspect.getmembers(instance, predicate=inspect.ismethod):
            if not method_name.startswith('_') and (not exclude_base_methods or method_name in own_method_names):
                full_name = f"{name}.{method_name}"
                method_metadata = self._create_method_metadata(method, method_name)
                method_metadata.class_name = name
                method_metadata.method_name = method_name
                self._tools[full_name] = method_metadata
                self._tool_instances[full_name] = method
                registered_names.append(full_name)
                print(f"  Registered method: {full_name}")
        
        return registered_names

    def register_tool(self, tool_name: str, metadata: Union[ToolMetadata, Dict, Any]) -> None:
        """Register a tool with the catalog.

        Args:
            tool_name: Name of the tool
            metadata: Either a ToolMetadata instance, a metadata dictionary, or an object to create metadata from
        """
        self._logger.info(f"Registering tool: {metadata}")
        self._logger.debug(f"Tool type: {type(metadata)}")

        try:
            if isinstance(metadata, ToolMetadata):
                self._tools[tool_name] = metadata
            elif isinstance(metadata, dict):
                # Convert dictionary format to ToolMetadata
                parameters = []
                for param in metadata.get('parameters', []):
                    parameters.append(ParameterInfo(
                        name=param['name'],
                        type_hint=param['type'],
                        required=param.get('required', True),
                        description=param.get('description', f"Parameter {param['name']}"),
                        default=param.get('default')
                    ))
                
                self._tools[tool_name] = ToolMetadata(
                    name=tool_name,
                    tool_type=metadata.get('tool_type', ToolType.PYTHON_FUNCTION),
                    description=metadata.get('description', ''),
                    parameters=parameters,
                    original_obj=metadata.get('original_obj'),
                    returns=ReturnInfo(
                        type_hint=metadata.get('return_type', 'Any'),
                        description=metadata.get('return_description', 'Return value')
                    ),
                    async_tool=metadata.get('async_tool', False)
                )
            else:
                base_metadata = self._create_instance_metadata(metadata, tool_name)
                self._tools[tool_name] = base_metadata
                self._tool_instances[tool_name] = metadata
        except Exception as e:
            self._logger.error(f"Failed to register tool {metadata}: {e}")
            raise

    def _create_method_metadata(self, method: Callable, method_name: str) -> ToolMetadata:
        """Create metadata for a method."""
        # Get docstring info for better description
        docstring = inspect.getdoc(method) or f"Method {method_name}"
        parsed_docstring = docstring_parser.parse(docstring)
        description = parsed_docstring.short_description or ""
        if parsed_docstring.long_description:
            description = description + "\n\n" + parsed_docstring.long_description
        
        # Extract parameters from method signature
        sig = inspect.signature(method)
        parameters = []
        param_descriptions = {param.arg_name: param.description for param in parsed_docstring.params}
        for param_name, param in sig.parameters.items():
            if param_name == 'self':
                continue
            type_hint = param.annotation if param.annotation != inspect.Parameter.empty else Any
            # Convert type hint to string format
            type_str = str(type_hint)
            if type_str.startswith("<class '") and type_str.endswith("'>"):
                type_str = type_str[8:-2]  # Remove "<class '" and "'>"
            parameters.append(ParameterInfo(
                name=param_name,
                type_hint=type_str,
                required=param.default == inspect.Parameter.empty,
                description=param_descriptions.get(param_name, f"Parameter {param_name}"),
                default=None if param.default == inspect.Parameter.empty else param.default
            ))
        
        # Get return type and description
        return_type = "Any"
        return_description = "Method return value"
        if sig.return_annotation != inspect.Parameter.empty:
            return_type = self._type_to_string(sig.return_annotation)
        if parsed_docstring.returns:
            return_description = parsed_docstring.returns.description
        
        return ToolMetadata(
            name=method_name,
            description=description or docstring,
            tool_type=ToolType.CLASS_METHOD,
            parameters=parameters,
            returns=ReturnInfo(type_hint=return_type, description=return_description),
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

    def register_class(self, cls: Type, name: Optional[str] = None, exclude_base_methods: bool = True, register_class_itself: bool = False) -> List[str]:
        """Register a Python class as a tool, including its methods.
        
        This method registers a class and its methods as tools in the catalog.
        By default, it only registers methods defined in the class itself (not inherited methods)
        and does not register the class itself as a tool.
        
        Args:
            cls: The class to register
            name: Base name for the class and its methods (defaults to class name)
            exclude_base_methods: Whether to exclude methods inherited from base classes (default: True)
            register_class_itself: Whether to register the class itself as a tool (default: False)
            
        Returns:
            List of registered tool names
        """
        class_name = name or cls.__name__
        registered_names = []
        
        # Register the class itself if requested
        if register_class_itself:
            metadata = self._create_class_metadata(cls, class_name)
            self._tools[class_name] = metadata
            self._classes[class_name] = cls
            registered_names.append(class_name)
        
        # Get only methods defined in the class itself
        own_method_names = set()
        if exclude_base_methods:
            # Find methods defined in this class, not in base classes
            for base_cls in cls.__mro__:
                if base_cls == cls:
                    # Include methods from this class
                    own_method_names.update(base_cls.__dict__.keys())
                elif base_cls != object:  # Don't process the base 'object' class
                    # Exclude methods from base classes
                    own_method_names.difference_update(base_cls.__dict__.keys())
        
        # Register class methods
        for method_name, method in inspect.getmembers(cls, predicate=inspect.isfunction):
            if not method_name.startswith('_') and (not exclude_base_methods or method_name in own_method_names):
                full_name = f"{class_name}.{method_name}"
                metadata = self._extract_docstring_info(method, full_name, ToolType.CLASS_METHOD)
                metadata.class_name = class_name
                metadata.method_name = method_name
                metadata.async_tool = inspect.iscoroutinefunction(method)
                
                self._tools[full_name] = metadata
                registered_names.append(full_name)
        
        return registered_names

    def get_tool_instance(self, name: str) -> Any:
        """Get a tool instance by name.

        Args:
            name: Name of the tool to get

        Returns:
            The tool instance

        Raises:
            KeyError: If the tool is not found
        """
        # First try direct lookup
        if name in self._tool_instances:
            return self._tool_instances[name]

        # If not found and this might be a method name
        if '.' in name:
            # Split on first dot to get base name
            parts = name.split('.')
            base_name = parts[0]
            method_path = '.'.join(parts[1:])

            # Try to find the base tool
            base_tool = self._tool_instances.get(base_name)
            if base_tool:
                # Navigate through the object hierarchy
                current = base_tool
                for part in method_path.split('.'):
                    if hasattr(current, part):
                        current = getattr(current, part)
                    else:
                        raise KeyError(f"Tool method {name} not found")
                return current

        raise KeyError(f"Tool {name} not found")

    def get_tool(self, name: str) -> Optional[ToolMetadata]:
        """Get metadata for a registered tool.
        
        This method handles both direct tool lookups and method lookups.
        For methods, it will:
        1. Try to find metadata for the full method name (e.g. 'tool.method')
        2. If not found, try to find metadata for the base tool name
        3. If base tool found, look for the method in its metadata
        """
        # First try direct lookup
        metadata = self._tools.get(name)
        if metadata:
            return metadata
            
        # If not found and this might be a method name
        if '.' in name:
            base_name, method_name = name.split('.')
            
            # Try to get the base tool's metadata
            base_metadata = self._tools.get(base_name)
            if base_metadata:
                # Look for the method in the base tool's metadata
                if base_metadata.tool_type == ToolType.CLASS_METHOD:
                    # Get the tool instance and method
                    tool_instance = self._tool_instances.get(base_name)
                    if tool_instance and hasattr(tool_instance, method_name):
                        method = getattr(tool_instance, method_name)
                        if callable(method):
                            # Create method metadata
                            method_metadata = self._create_method_metadata(method, name)
                            method_metadata.class_name = base_name
                            method_metadata.method_name = method_name
                            
                            # Get docstring info for better description
                            docstring = inspect.getdoc(method) or f"Method {method_name}"
                            parsed_docstring = docstring_parser.parse(docstring)
                            description = parsed_docstring.short_description or ""
                            if parsed_docstring.long_description:
                                description = description + "\n\n" + parsed_docstring.long_description
                            method_metadata.description = description or docstring
                            
                            # Extract parameters from method signature
                            sig = inspect.signature(method)
                            parameters = []
                            param_descriptions = {param.arg_name: param.description for param in parsed_docstring.params}
                            for param_name, param in sig.parameters.items():
                                if param_name == 'self':
                                    continue
                                parameters.append(ParameterInfo(
                                    name=param_name,
                                    type_hint=str(param.annotation) if param.annotation != inspect.Parameter.empty else 'Any',
                                    description=param_descriptions.get(param_name, f"Parameter {param_name}"),
                                    required=param.default == inspect.Parameter.empty,
                                    default=None if param.default == inspect.Parameter.empty else param.default
                                ))
                            method_metadata.parameters = parameters
                            
                            # Cache the metadata for future use
                            self._tools[name] = method_metadata
                            return method_metadata
                            
        return None

    def list_tools(self) -> List[str]:
        """List all registered tool names."""
        return list(self._tools.keys())

    def reset(self) -> None:
        """Reset the catalog to its initial state."""
        self._tools = {}
        self._tool_instances = {}
        self._functions = {}
        self._classes = {}
        self._openapi_tools = {}
        self._ai_tools = {}
        self._initialize_default_tools()

    def _initialize_default_tools(self):
        """Initialize default tools."""
        print("\n🔧 Initializing default tools...")
        try:
            # Initialize default tools only if they haven't been initialized
            if not self.DEFAULT_TOOLS:
                registered_tools = []
                
                # Register internal tools
                print("\n📦 Registering internal tools...")
                try:
                    internal_file_tools = InternalFileTools()
                    names = self.register_instance(internal_file_tools, "internal_file_tools", exclude_base_methods=True, register_instance_itself=True)
                    print(f"✅ Registered InternalFileTools with {len(names)} methods")
                    registered_tools.extend(names)
                except Exception as e:
                    print(f"❌ Failed to register InternalFileTools: {str(e)}")
                
                # Register general datetime tools
                print("\n⏰ Registering datetime tools...")
                try:
                    # Create tool instance
                    datetime_tools = DateTimeTools()
                    
                    # Register the instance methods
                    names = self.register_instance(
                        datetime_tools,
                        "datetime_tools",
                        exclude_base_methods=True,
                        register_instance_itself=True
                    )
                    
                    # Also register the standalone functions
                    self.register_tool("datetime_tools.get_current_datetime", get_current_datetime)
                    self.register_tool("datetime_tools.is_future_date", is_future_date)
                    
                    names.append("datetime_tools.get_current_datetime")
                    names.append("datetime_tools.is_future_date")
                    
                    print(f"✅ Registered DateTimeTools with {len(names)} methods")
                    registered_tools.extend(names)
                except Exception as e:
                    print(f"❌ Failed to register DateTimeTools: {str(e)}")
                    logger.error(f"Failed to register DateTimeTools: {str(e)}")
                
                # Register system monitoring tools
                print("\n🖥️ Registering system monitoring tools...")
                try:
                    # Create tool instance
                    system_monitor = SystemMonitorTools()
                    
                    # Register tool and its methods
                    names = self.register_instance(
                        system_monitor, 
                        "system_monitor", 
                        exclude_base_methods=True, 
                        register_instance_itself=True
                    )
                    
                    print(f"✅ Registered SystemMonitorTools with {len(names)} methods")
                    registered_tools.extend(names)
                except Exception as e:
                    print(f"❌ Failed to register SystemMonitorTools: {str(e)}")
                    logger.error(f"Failed to register SystemMonitorTools: {str(e)}")
                
                # Register network tools
                print("\n🌐 Registering network tools...")
                try:
                    # Create tool instance
                    network_tools = NetworkTools()
                    
                    # Register tool and its methods
                    names = self.register_instance(
                        network_tools, 
                        "network_tools", 
                        exclude_base_methods=True, 
                        register_instance_itself=True
                    )
                    
                    print(f"✅ Registered NetworkTools with {len(names)} methods")
                    registered_tools.extend(names)
                except Exception as e:
                    print(f"❌ Failed to register NetworkTools: {str(e)}")
                    logger.error(f"Failed to register NetworkTools: {str(e)}")
                
                # Register database tools
                print("\n🗃️ Registering database tools...")
                try:
                    from src.server.tools.database_tools.database_tools import DatabaseTools
                    # Create tool instance
                    database_tools = DatabaseTools()
                    
                    # Register tool and its methods
                    names = self.register_instance(
                        database_tools, 
                        "database_tools", 
                        exclude_base_methods=True, 
                        register_instance_itself=True
                    )
                    
                    print(f"✅ Registered DatabaseTools with {len(names)} methods")
                    registered_tools.extend(names)
                except Exception as e:
                    print(f"❌ Failed to register DatabaseTools: {str(e)}")
                    logger.error(f"Failed to register DatabaseTools: {str(e)}")
                
                # Register weather tools
                print("\n☁️ Registering weather tools...")
                try:
                    from src.server.tools.weather_tool import register_weather_tool
                    names = register_weather_tool(self)
                    print(f"✅ Registered WeatherTool with {len(names)} methods")
                    registered_tools.extend(names)
                except Exception as e:
                    print(f"❌ Failed to register WeatherTool: {str(e)}")
                    logger.error(f"Failed to register WeatherTool: {str(e)}")
                
                # Register Python execution tool
                print("\n🐍 Registering Python execution tool...")
                try:
                    # Create tool instance
                    py_exec = PyExec()
                    
                    # Register tool and its methods
                    names = self.register_instance(
                        py_exec, 
                        "PyExec", 
                        exclude_base_methods=True, 
                        register_instance_itself=True
                    )
                    
                    print(f"✅ Registered PyExec with {len(names)} methods")
                    registered_tools.extend(names)
                except Exception as e:
                    print(f"❌ Failed to register PyExec: {str(e)}")
                    logger.error(f"Failed to register PyExec: {str(e)}")
                
                try:
                    internal_credentials_tools = InternalCredentialsTools()
                    names = self.register_instance(internal_credentials_tools, "internal_credentials_tools", exclude_base_methods=True, register_instance_itself=True)
                    print(f"✅ Registered InternalCredentialsTools with {len(names)} methods")
                    registered_tools.extend(names)
                except Exception as e:
                    print(f"❌ Failed to register InternalCredentialsTools: {str(e)}")
                
                try:
                    internal_testing_tools = InternalTestingTools()
                    names = self.register_instance(internal_testing_tools, "internal_testing_tools", exclude_base_methods=True, register_instance_itself=True)
                    print(f"✅ Registered InternalTestingTools with {len(names)} methods")
                    registered_tools.extend(names)
                except Exception as e:
                    print(f"❌ Failed to register InternalTestingTools: {str(e)}")
                
                try:
                    internal_proxy_tools = InternalProxyTools()
                    names = self.register_instance(internal_proxy_tools, "internal_proxy_tools", exclude_base_methods=True, register_instance_itself=True)
                    print(f"✅ Registered InternalProxyTools with {len(names)} methods")
                    registered_tools.extend(names)
                except Exception as e:
                    print(f"❌ Failed to register InternalProxyTools: {str(e)}")
                
                # Try to register InternalPersistenceTools with lazy import to avoid circular imports
                print("\n📦 Registering persistence tools...")
                try:
                    # Import here to avoid circular import
                    from src.server.tools.internal_persistence_tools import InternalPersistenceTools
                    internal_persistence_tools = InternalPersistenceTools()
                    names = self.register_instance(internal_persistence_tools, "internal_persistence_tools", exclude_base_methods=True, register_instance_itself=True)
                    print(f"✅ Registered InternalPersistenceTools with {len(names)} methods")
                    registered_tools.extend(names)
                except Exception as e:
                    print(f"❌ Failed to register InternalPersistenceTools: {str(e)}")
                    logger.error(f"Failed to register InternalPersistenceTools: {str(e)}")
                
                # Register CrewAI tools
                print("\n📦 Registering CrewAI tools...")
                try:
                    website_tool = WebsiteSearchTool()
                    name = self.register_ai_tool(website_tool, "WebsiteSearchTool")
                    print(f"✅ Registered WebsiteSearchTool")
                    registered_tools.append(name)
                except Exception as e:
                    print(f"❌ Failed to register WebsiteSearchTool: {str(e)}")
                
                try:
                    serper_tool = SerperDevTool()
                    name = self.register_ai_tool(serper_tool, "SerperDevTool")
                    print(f"✅ Registered SerperDevTool")
                    registered_tools.append(name)
                except Exception as e:
                    print(f"❌ Failed to register SerperDevTool: {str(e)}")
                
                try:
                    file_read_tool = FileReadTool()
                    name = self.register_ai_tool(file_read_tool, "FileReadTool")
                    print(f"✅ Registered FileReadTool")
                    registered_tools.append(name)
                except Exception as e:
                    print(f"❌ Failed to register FileReadTool: {str(e)}")
                
                try:
                    # Register WebScraperTool
                    web_scraper = WebScraperTool()
                    names = self.register_instance(web_scraper, "WebScraperTool", exclude_base_methods=True, register_instance_itself=True)
                    print(f"✅ Registered WebScraperTool with {len(names)} methods")
                    registered_tools.extend(names)
                except Exception as e:
                    print(f"❌ Failed to register WebScraperTool: {str(e)}")
                
                try:
                    # Register FileTool
                    file_tool = FileTool()
                    names = self.register_instance(file_tool, "FileTool", exclude_base_methods=True, register_instance_itself=True)
                    print(f"✅ Registered FileTool with {len(names)} methods")
                    registered_tools.extend(names)
                except Exception as e:
                    print(f"❌ Failed to register FileTool: {str(e)}")
                
                try:
                    # Register MicroservicesTool
                    microservices_tool = MicroservicesTool()
                    names = self.register_instance(microservices_tool, "MicroservicesTool", exclude_base_methods=True, register_instance_itself=True)
                    print(f"✅ Registered MicroservicesTool with {len(names)} methods")
                    registered_tools.extend(names)
                except Exception as e:
                    print(f"❌ Failed to register MicroservicesTool: {str(e)}")
                
                try:
                    # Register SMSTool
                    sms_tool = SMSTool()
                    names = self.register_instance(sms_tool, "SMSTool", exclude_base_methods=True, register_instance_itself=True)
                    print(f"✅ Registered SMSTool with {len(names)} methods")
                    registered_tools.extend(names)
                except Exception as e:
                    print(f"❌ Failed to register SMSTool: {str(e)}")
                
                # Register GitHub tool if credentials are available
                print("\n📦 Checking GitHub credentials...")
                github_token = getenv("GITHUB_TOKEN")
                repo_name = getenv("GITHUB_REPO")
                
                if github_token and repo_name:
                    try:
                        print(f"  Found credentials for repo: {repo_name}")
                        github_tool = GitHubTool(github_token, repo_name)
                        names = self.register_instance(github_tool, "GitHubTool", exclude_base_methods=True, register_instance_itself=True)
                        print(f"✅ Registered GitHubTool with {len(names)} methods")
                        registered_tools.extend(names)
                    except Exception as e:
                        print(f"❌ Failed to register GitHubTool: {str(e)}")
                else:
                    print("❓ No GitHub credentials found, skipping tool registration")
                
                # Register URL tools
                print("\n📦 Registering URL tools...")
                try:
                    url_tools = URLTools()
                    names = self.register_instance(url_tools, "URLTools", exclude_base_methods=True, register_instance_itself=True)
                    print(f"✅ Registered URLTools with {len(names)} methods")
                    registered_tools.extend(names)
                except Exception as e:
                    print(f"❌ Failed to register URLTools: {str(e)}")
                
                # Store current tools as defaults
                print("\n📦 Storing default tools...")
                self.DEFAULT_TOOLS = {
                    'tools': self._tools.copy(),
                    'instances': self._tool_instances.copy(),
                    'functions': self._functions.copy(),
                    'classes': self._classes.copy(),
                    'openapi': self._openapi_tools.copy(),
                    'ai_tools': self._ai_tools.copy()
                }
                
                print(f"\n✅ Successfully registered {len(registered_tools)} tools:")
                for tool in registered_tools:
                    print(f"  - {tool}")
                
        except Exception as e:
            logger.error(f"Failed to initialize default tools: {str(e)}")
            traceback.print_exc()
            # Initialize with empty list on failure
            self.DEFAULT_TOOLS = []

    def _type_to_string(self, type_hint: Any) -> str:
        """Convert a type hint to a string representation."""
        if hasattr(type_hint, "__name__"):
            return type_hint.__name__
        return str(type_hint)

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
                        request_body = params['requestBody']
                        # Add the full request body parameter
                        parameters.append(ParameterInfo(
                            name="requestBody",
                            type_hint="object",
                            description=request_body.description or "Request body schema",
                            required=request_body.required
                        ))
                        # Also add individual properties for granular access
                        if request_body.param_schema and request_body.param_schema.properties:
                            for prop_name, prop_schema in request_body.param_schema.properties.items():
                                type_hint = prop_schema.type or "object"
                                parameters.append(ParameterInfo(
                                    name=prop_name,
                                    type_hint=type_hint,
                                    description=prop_schema.description or f"Property {prop_name}",
                                    required=prop_schema.required is not None and prop_name in prop_schema.required
                                ))
                else:
                    # Handle other parameter locations (query, path, etc.)
                    for param_name, param in params.items():
                        type_hint = param.param_schema.type or "object"
                        parameters.append(ParameterInfo(
                            name=param_name,
                            type_hint=type_hint,
                            description=param.description or f"Parameter {param_name}",
                            required=param.required
                        ))

        # Create metadata
        metadata = ToolMetadata(
            name=tool_name,
            description=function.description or f"OpenAPI tool {tool_name}",
            parameters=parameters,
            schema=tool.model_dump(),
            tool_type=ToolType.OPENAPI_TOOL,
            returns=ReturnInfo(
                type_hint="Dict[str, Any]",
                description=function.responses['200'].description if function.responses and '200' in function.responses else "Successful response"
            ),
            original_obj=tool,
            async_tool=True
        )

        # Register the tool
        self._tools[tool_name] = metadata
        self._tool_instances[tool_name] = tool
        self._openapi_tools[tool_name] = tool

        return tool_name

    def get_tool_metadata(self, name: str) -> Optional[ToolMetadata]:
        """Get metadata for a tool from the catalog."""
        logger.debug(f"Getting metadata for tool: {name}")
        logger.debug(f"Available tools: {list(self._tools.keys())}")
        
        # First try getting the tool directly
        if name in self._tools:
            logger.debug(f"Found metadata directly for {name}")
            return self._tools[name]
        
        # If not found and contains a dot, try getting the base tool's metadata
        if '.' in name:
            base_name, method_name = name.split('.')
            logger.debug(f"Trying base tool {base_name} for method {method_name}")
            
            # First check if we have metadata for the full method name
            if name in self._tools:
                logger.debug(f"Found metadata for full method name {name}")
                return self._tools[name]
            
            # Then check if we have the base tool instance
            base_instance = self._tool_instances.get(base_name)
            if base_instance and hasattr(base_instance, method_name):
                method = getattr(base_instance, method_name)
                if callable(method):
                    logger.debug(f"Creating metadata for method {method_name}")
                    # Create method metadata
                    method_metadata = self._create_method_metadata(method, name)
                    method_metadata.class_name = base_name
                    method_metadata.method_name = method_name
                    
                    # Cache the metadata for future use
                    self._tools[name] = method_metadata
                    return method_metadata
                
        logger.debug(f"No metadata found for {name}")
        return None

    def _create_tool_metadata(self, name: str, tool: Any) -> ToolMetadata:
        """Create metadata for a tool."""
        # Extract tool information
        if inspect.isclass(tool):
            return self._create_class_metadata(name, tool)
        elif inspect.isfunction(tool) or inspect.ismethod(tool):
            return self._create_function_metadata(name, tool)
        else:
            return self._create_instance_metadata(tool, name)

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

    def _load_tools(self):
        """Load all tools from the catalog."""
        # Load default tools
        for tool_type, tools in self.DEFAULT_TOOLS.items():
            for tool in tools:
                self.register_tool(tool)

tools_catalog = ToolsCatalog()
print("🔧 Tools catalog initialized with tools:", tools_catalog.list_tools()) 