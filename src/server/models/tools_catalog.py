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
import time

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
            self._execution_metrics: Dict[str, Dict[str, Any]] = {}
            self._logger = logging.getLogger(__name__)
            ToolsCatalog._initialized = True

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

    def list_tools(self) -> List[str]:
        """Get a list of all registered tool names.
        
        Returns:
            List of tool names
        """
        return list(self._tools.keys())

    def get_tool(self, name: str) -> ToolMetadata:
        """Get metadata for a tool.
        
        Args:
            name: Name of the tool to retrieve
            
        Returns:
            Tool metadata
            
        Raises:
            KeyError: If tool not found
        """
        if name not in self._tools:
            raise KeyError(f"Tool '{name}' not found in catalog")
        return self._tools[name]

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

    def register_tool(self, tool: Any, name: Optional[str] = None) -> str:
        """Register a tool with enhanced logging and validation."""
        tool_name = name or getattr(tool, '__name__', str(tool))
        
        try:
            self._logger.info(f"Registering tool: {tool_name}")
            self._logger.debug(f"Tool type: {type(tool)}")
            
            # Validate tool has docstring
            if inspect.isfunction(tool) or inspect.isclass(tool):
                if not tool.__doc__:
                    raise ValueError(f"Tool {tool_name} failed validation: missing docstring")
            elif not getattr(tool, '__doc__', None):
                raise ValueError(f"Tool {tool_name} failed validation: missing docstring")
            
            # Handle class instances
            if not inspect.isclass(tool) and not inspect.isfunction(tool):
                metadata = self._create_class_instance_metadata(tool, tool_name)
                self._tools[tool_name] = metadata
                self._instances[tool_name] = tool
                
                # Register methods
                for method_name in dir(tool):
                    if not method_name.startswith('_'):
                        method = getattr(tool, method_name)
                        if callable(method):
                            method_tool_name = f"{tool_name}.{method_name}"
                            method_metadata = self._create_method_metadata(method, method_tool_name, tool.__class__.__name__)
                            self._tools[method_tool_name] = method_metadata
                
                return tool_name
            
            # Handle classes
            if inspect.isclass(tool):
                # Validate class has at least one method
                if not [m for m in dir(tool) if not m.startswith('_')]:
                    raise ValueError(f"Tool {tool_name} failed validation: class has no public methods")
                metadata = self._create_class_metadata(tool, tool_name)
                self._tools[tool_name] = metadata
                self._instances[tool_name] = tool()
                
                # Register methods
                instance = self._instances[tool_name]
                for method_name in dir(instance):
                    if not method_name.startswith('_'):
                        method = getattr(instance, method_name)
                        if callable(method):
                            method_tool_name = f"{tool_name}.{method_name}"
                            method_metadata = self._create_method_metadata(method, method_tool_name, tool.__name__)
                            self._tools[method_tool_name] = method_metadata
                
                return tool_name
            
            # Handle functions
            metadata = self._create_function_metadata(tool, tool_name)
            self._tools[tool_name] = metadata
            self._instances[tool_name] = tool
            return tool_name
            
        except Exception as e:
            self._logger.error(f"Failed to register tool {tool_name}: {str(e)}")
            raise

    def _create_method_metadata(self, method: Callable, method_name: str, class_name: str) -> ToolMetadata:
        """Create metadata for a class method."""
        docstring = method.__doc__ or ""
        parsed_docstring = docstring_parser.parse(docstring)
        
        # Get type hints from the method's signature
        try:
            type_hints = get_type_hints(method)
        except Exception:
            type_hints = {}
        
        # Extract parameters from docstring
        parameters = []
        for param in parsed_docstring.params:
            param_info = ParameterInfo(
                name=param.arg_name,
                description=param.description or "",
                type_hint=str(type_hints.get(param.arg_name, "Any")),
                required=True  # Default to required
            )
            parameters.append(param_info)
        
        # Extract return info from docstring
        return_info = None
        if parsed_docstring.returns:
            return_info = ReturnInfo(
                description=parsed_docstring.returns.description or "",
                type_hint=str(type_hints.get('return', "Any"))
            )
        else:
            return_info = ReturnInfo(
                description="",
                type_hint=str(type_hints.get('return', "Any"))
            )
        
        # Create metadata
        metadata = ToolMetadata(
            name=method_name,
            description=parsed_docstring.short_description or docstring,
            tool_type=ToolType.CLASS_METHOD,
            parameters=parameters,
            returns=return_info,
            class_name=class_name,
            method_name=method_name.split('.')[-1],
            original_obj=method
        )
        
        return metadata

    def _create_class_instance_metadata(self, tool: Any, tool_name: str) -> ToolMetadata:
        """Create metadata for a class instance and its methods."""
        # Get class docstring info
        docstring_info = self._extract_docstring_info(tool.__class__)
        
        # Get all public methods
        method_metadatas = []
        for method_name in dir(tool):
            if not method_name.startswith('_'):
                method = getattr(tool, method_name)
                if callable(method):
                    # Create metadata for method
                    method_docstring = self._extract_docstring_info(method)
                    method_metadata = ToolMetadata(
                        name=f"{tool_name}.{method_name}",
                        description=method_docstring.description,
                        tool_type=ToolType.CLASS_METHOD,
                        parameters=method_docstring.parameters,
                        returns=method_docstring.returns,
                        original_obj=method,
                        class_name=tool_name,
                        method_name=method_name,
                        async_tool=inspect.iscoroutinefunction(method)
                    )
                    # Store method metadata
                    self._tools[f"{tool_name}.{method_name}"] = method_metadata
                    method_metadatas.append(method_metadata)
        
        # Create base tool metadata that includes all method descriptions and parameters
        base_description = docstring_info.description + "\n\nAvailable methods:\n"
        for method_metadata in method_metadatas:
            base_description += f"\n- {method_metadata.method_name}: {method_metadata.description}"
        
        # Combine parameters from all methods
        all_parameters = []
        for method_metadata in method_metadatas:
            all_parameters.extend(method_metadata.parameters)
        
        # Create base tool metadata
        base_metadata = ToolMetadata(
            name=tool_name,
            description=base_description,
            tool_type=ToolType.CLASS_METHOD,
            parameters=all_parameters,
            returns=docstring_info.returns,
            original_obj=tool,
            class_name=tool.__class__.__name__,
            async_tool=any(m.async_tool for m in method_metadatas)
        )
        
        return base_metadata

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

    def _extract_docstring_info(self, obj: Any) -> DocstringInfo:
        """Extract docstring information from a function or class."""
        # Get docstring
        docstring = inspect.getdoc(obj) or ""
        
        # Parse docstring
        parsed = docstring_parser.parse(docstring)
        
        # Extract parameters
        parameters = []
        for param in parsed.params:
            parameters.append(ParameterInfo(
                name=param.arg_name,
                type_hint=param.type_name,
                description=param.description or "",
                required=True  # Default to required
            ))
        
        # Extract return info
        return_info = ReturnInfo(
            type_hint=parsed.returns.type_name if parsed.returns else None,
            description=parsed.returns.description if parsed.returns else ""
        )
        
        # Create docstring info
        return DocstringInfo(
            description=parsed.short_description or "",
            parameters=parameters,
            returns=return_info
        )

    def unregister_tool(self, name: str) -> None:
        """Unregister a tool from the catalog.
        
        Args:
            name: Name of the tool to unregister
        """
        if name in self._tools:
            del self._tools[name]
        if name in self._instances:
            del self._instances[name]
        if name in self._functions:
            del self._functions[name]
        if name in self._classes:
            del self._classes[name]
        if name in self._execution_metrics:
            del self._execution_metrics[name]
            
    def reset(self) -> None:
        """Reset the catalog to its initial state."""
        self._tools = {}
        self._instances = {}
        self._functions = {}
        self._classes = {}
        self._execution_metrics = {}

    @classmethod
    def reset(cls):
        """Reset the catalog state. Should only be used in tests."""
        if cls._instance is not None:
            # Clear instance state
            cls._instance._tools.clear()
            cls._instance._instances.clear()
            cls._instance._functions.clear()
            cls._instance._classes.clear()
            cls._instance._execution_metrics.clear()
            
            # Re-initialize
            cls._initialized = False
            cls._instance = None 

    def register_instance(self, instance: Any, name: str) -> List[str]:
        """Register an instance and all its methods.
        
        Args:
            instance: The object instance to register
            name: Base name for the instance
            
        Returns:
            List of registered tool names
        """
        print(f"Registering instance {name}")
        registered_names = []
        
        # Register the base instance
        metadata = self._create_class_instance_metadata(instance, name)
        self._tools[name] = metadata
        self._instances[name] = instance
        registered_names.append(name)
        
        # Register all public methods
        for method_name in dir(instance):
            if not method_name.startswith('_'):
                method = getattr(instance, method_name)
                if callable(method):
                    full_name = f"{name}.{method_name}"
                    method_metadata = self._create_method_metadata(method, full_name, instance.__class__.__name__)
                    self._tools[full_name] = method_metadata
                    registered_names.append(full_name)
                    print(f"  Registered method: {full_name}")
        
        return registered_names 

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

        # Register the tool with extracted metadata
        self.register_tool(
            tool_name,
            ToolMetadata(
                name=tool_name,
                description=function.description or f"OpenAPI tool {tool_name}",
                parameters=parameters,
                schema=tool.model_dump(),
                type=ToolType.OPENAPI
            )
        )

        return tool_name 