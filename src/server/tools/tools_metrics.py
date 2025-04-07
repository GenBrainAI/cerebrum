"""Tool execution metrics tracking."""
from __future__ import annotations
from typing import Dict, Any, Optional, Type, List, Union, Callable
from datetime import datetime
import logging
import asyncio
from crewai.tools import BaseTool
import time
import functools
from pydantic import PrivateAttr, BaseModel, Field, ConfigDict, create_model

logger = logging.getLogger(__name__)

def measure_execution_time(func: Callable) -> Callable:
    """Decorator to measure the execution time of a function."""
    @functools.wraps(func)
    async def async_wrapper(*args, **kwargs):
        """Async wrapper for measuring execution time."""
        start_time = time.time()
        try:
            result = await func(*args, **kwargs)
            end_time = time.time()
            logger.info(f"Function {func.__name__} executed in {end_time - start_time:.4f} seconds")
            return result
        except Exception as e:
            end_time = time.time()
            logger.error(f"Function {func.__name__} failed after {end_time - start_time:.4f} seconds: {str(e)}")
            raise
    
    @functools.wraps(func)
    def sync_wrapper(*args, **kwargs):
        """Sync wrapper for measuring execution time."""
        start_time = time.time()
        try:
            result = func(*args, **kwargs)
            end_time = time.time()
            logger.info(f"Function {func.__name__} executed in {end_time - start_time:.4f} seconds")
            return result
        except Exception as e:
            end_time = time.time()
            logger.error(f"Function {func.__name__} failed after {end_time - start_time:.4f} seconds: {str(e)}")
            raise
    
    # Choose the appropriate wrapper based on whether the function is async or not
    if asyncio.iscoroutinefunction(func):
        return async_wrapper
    else:
        return sync_wrapper

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

class CerebrumCrewAITool(BaseTool):
    """A tool that can be used with CrewAI, wrapping a tool from the catalog."""
    
    _proxy: Any = PrivateAttr()
    _execution_metrics: Dict = PrivateAttr(default={})
    
    def __init__(self, name: str, description: str, proxy: Any):
        """Initialize the tool.
        
        Args:
            name: The name of the tool
            description: A description of what the tool does
            proxy: The proxy object that will execute the tool
        """
        super().__init__(name=name, description=description)
        self._proxy = proxy
        self._execution_metrics = {}

        # Get tool metadata from catalog
        tool_metadata = proxy.catalog.get_tool_metadata(name)
        if not tool_metadata:
            raise ValueError(f"Tool metadata not found for {name}")

        # Create field definitions for parameters
        field_definitions = {}
        for param in tool_metadata.parameters:
            # Convert type hint to Python type
            type_hint = self._convert_type_hint(param.type_hint)
            
            # Create field with proper type and metadata
            field_definitions[param.name] = (
                type_hint,
                Field(
                    description=param.description,
                    required=param.required,
                    default=... if param.required else None
                )
            )

        # Create a dynamic Pydantic model for the parameters
        self.args_schema = create_model(
            f"{name}_Parameters",
            **field_definitions,
            __config__=ConfigDict(extra='forbid')
        )
    
    def _convert_type_hint(self, type_hint: str) -> Type:
        """Convert a type hint string to a Python type.
        
        Args:
            type_hint: The type hint as a string
            
        Returns:
            The corresponding Python type
        """
        type_map = {
            'str': str,
            'string': str,
            'int': int,
            'integer': int,
            'float': float,
            'number': float,
            'bool': bool,
            'boolean': bool,
            'dict': Dict[str, Any],
            'Dict[str, Any]': Dict[str, Any],
            'list': List[str],
            'List[str]': List[str],
            'object': Dict[str, Any],
            'array': List[str],
            'Any': Any,
            'any': Any
        }
        
        # Clean up type hint
        clean_type = type_hint.strip().lower()
        if clean_type.startswith('<') and clean_type.endswith('>'):
            clean_type = clean_type[8:-2]  # Remove "<class '" and "'>"
            
        return type_map.get(clean_type, str)
    
    async def _arun(self, **kwargs) -> Any:
        """Run the tool asynchronously.
        
        Args:
            **kwargs: The parameters for the tool
            
        Returns:
            The result of the tool execution
        """
        start_time = time.time()
        try:
            # Execute through proxy with parameters
            result = await self._proxy.execute(self.name, **kwargs)
            end_time = time.time()
            self._execution_metrics = {
                'start_time': start_time,
                'end_time': end_time,
                'duration': end_time - start_time,
                'success': True,
                'error': None,
                'input': kwargs,
                'output': result
            }
            return result
        except Exception as e:
            end_time = time.time()
            self._execution_metrics = {
                'start_time': start_time,
                'end_time': end_time,
                'duration': end_time - start_time,
                'success': False,
                'error': str(e),
                'input': kwargs,
                'output': None
            }
            raise e
    
    def _run(self, **kwargs) -> Any:
        """Run the tool synchronously.
        
        Args:
            **kwargs: The parameters for the tool
            
        Returns:
            The result of the tool execution
        """
        return asyncio.run(self._arun(**kwargs))
    
    @property
    def description(self) -> str:
        """Get the tool description including arguments.
        
        Returns:
            A formatted string with the tool description and argument details
        """
        # Get schema from args_schema
        schema = self.args_schema.model_json_schema()
        properties = schema.get('properties', {})
        required = schema.get('required', [])
        
        # Build argument descriptions
        args_desc = []
        for name, prop in properties.items():
            is_required = name in required
            type_str = prop.get('type', 'any')
            arg_desc = f"- {name} ({type_str}): {prop.get('description', '')} ({'required' if is_required else 'optional'})"
            args_desc.append(arg_desc)
            
        # Format the complete description
        tool_desc = [
            f"Tool Name: {self.name}",
            "Tool Description:",
            super().description,
            "Tool Arguments:",
            *args_desc
        ]
        
        return "\n".join(tool_desc)