import asyncio
import inspect
import httpx
import asyncio
import logging
import json
import re
from datetime import datetime
from uuid import UUID, uuid4
from pydantic import BaseModel, Field, create_model
from typing import Dict, Any, List, Type, Union, Optional
from crewai_tools import BaseTool as CrewAITool
from crewai_tools.tools.rag.rag_tool import RagTool
from langchain.tools import BaseTool as LangChainTool
from ..tools.tools_catalog import ToolsCatalog, tools_catalog, ParameterInfo
from ..models.tools_descriptors import ToolMetadata, ToolType
from ..models.toolset import Tool
from ..models.function import ResolvedSchema
from ..models.curried_proxy_info import CurriedProxyInfo, ToolInfo
from crewai_tools import BaseTool as CrewAITool


logger = logging.getLogger(__name__)

class CurriedProxy(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    tool_names: List[str] = Field(default_factory=list)
    catalog: ToolsCatalog = Field(default_factory=lambda: tools_catalog)
    
    class Config:
        arbitrary_types_allowed = True

    def to_info(self) -> CurriedProxyInfo:
        """Convert current CurriedProxy to CurriedProxyInfo"""
        tools = []
        for name in self.tool_names:
            tool_metadata = self.catalog.get_tool(name)
            if not tool_metadata:
                continue
                
            if tool_metadata.tool_type == ToolType.OPENAPI_TOOL:
                tool_info = ToolInfo(
                    name=name,
                    type='tool',
                    tool_data=tool_metadata.original_obj.dict() if hasattr(tool_metadata.original_obj, 'dict') else {}
                )
            else:
                # Handle Python functions and methods
                if tool_metadata.class_name:
                    # This is a class method
                    tool_info = ToolInfo(
                        name=name,
                        type='function',
                        tool_data={
                            'name': name,
                            'description': tool_metadata.description,
                            'function_module': tool_metadata.original_obj.__module__,
                            'function_name': tool_metadata.method_name,
                            'class_name': tool_metadata.class_name,
                            'is_method': True
                        }
                    )
                else:
                    # Regular function
                    tool_info = ToolInfo(
                        name=name,
                        type='function',
                        tool_data={
                            'name': name,
                            'description': tool_metadata.description,
                            'function_module': tool_metadata.original_obj.__module__,
                            'function_name': tool_metadata.original_obj.__name__,
                            'is_method': False
                        }
                    )
            tools.append(tool_info)
        
        return CurriedProxyInfo(
            id=self.id,
            tools=tools,
            name_counter={}  # Maintain compatibility with old format
        )

    @classmethod
    def from_info(cls, info: CurriedProxyInfo) -> 'CurriedProxy':
        """Construct CurriedProxy from CurriedProxyInfo"""
        from importlib import import_module
        
        proxy = cls(id=info.id)
        
        for tool_info in info.tools:
            if tool_info.type == 'tool':
                # Reconstruct Tool instance
                tool = Tool(**tool_info.tool_data)
                proxy.catalog.register_openapi_tool(tool, tool_info.name)
                proxy.tool_names.append(tool_info.name)
            else:
                # Reconstruct function/method
                module = import_module(tool_info.tool_data['function_module'])
                
                # For SMSTool and similar class-based tools, always create an instance
                if 'class_name' in tool_info.tool_data:
                    class_ = getattr(module, tool_info.tool_data['class_name'])
                    instance = class_()
                    # Register the whole instance if this is the first method from this class
                    class_name = tool_info.tool_data['class_name']
                    if not any(name.startswith(f"{class_name}.") for name in proxy.tool_names):
                        proxy.catalog.register_class(instance.__class__, class_name)
                    proxy.tool_names.append(tool_info.name)
                elif 'function_name' in tool_info.tool_data:
                    # Regular function
                    function = getattr(module, tool_info.tool_data['function_name'])
                    proxy.catalog.register_function(function, tool_info.name)
                    proxy.tool_names.append(tool_info.name)              
                else:
                    raise ValueError(f"No function_name or class_name found in tool_data for {tool_info.name}")       
        return proxy

    async def multiset_proxy(self, name: str, arguments: Dict[str, Any]) -> Any:
        """Execute a tool by name with given arguments."""
        # First try direct metadata lookup
        tool_metadata = self.catalog.get_tool(name)
        if tool_metadata is None:
            # If not found, try with class prefix if this might be a method
            if '.' in name and not name.startswith('.'):
                class_name = name.split('.')[0]
                if class_name in self.tool_names:
                    tool_metadata = self.catalog.get_tool(name)
        
        if tool_metadata is None:
            raise ValueError(f"Tool not found: {name}")

        try:
            if tool_metadata.tool_type == ToolType.OPENAPI_TOOL:
                return await self._call_openapi_tool(tool_metadata.original_obj, arguments)
            else:
                tool_instance = self.catalog.get_tool_instance(name)
                if inspect.iscoroutinefunction(tool_instance):
                    return await tool_instance(**arguments)
                return tool_instance(**arguments)
        except Exception as e:
            return {"error": str(e)}

    def curried_proxy(self, name: str):
        """Create a curried function for the named tool."""
        return lambda args: self.multiset_proxy(name, args)

    def add_tool(self, name: str, tool: Union[callable, object, CrewAITool, LangChainTool, RagTool, Tool]) -> None:
        """Add a tool to the proxy using the catalog.
        
        Args:
            name: Name for the tool
            tool: The tool to add - can be a Tool instance from OpenAPI, callable,
                CrewAI tool, LangChain tool, RagTool, or class instance
        """
        try:
            if isinstance(tool, Tool):
                tool_name = self.catalog.register_openapi_tool(tool, name)
                tool_names = [tool_name]
            elif isinstance(tool, (CrewAITool, LangChainTool, RagTool)):
                tool_name = self.catalog.register_ai_tool(tool, name)
                tool_names = [tool_name]
            elif callable(tool) and not inspect.isclass(tool):
                tool_name = self.catalog.register_function(tool, name)
                tool_names = [tool_name]
            elif inspect.isclass(tool):
                tool_names = self.catalog.register_class(tool, name)
            else:
                # For class instances or objects
                tool_names = self.catalog.register_class(tool.__class__, name)
                
            for tool_name in tool_names:
                if tool_name not in self.tool_names:
                    self.tool_names.append(tool_name)
                    
        except Exception as e:
            raise ValueError(f"Failed to add tool {name}: {str(e)}")

    def remove_tool(self, name: str) -> None:
        """Remove a tool from the proxy."""
        if name in self.tool_names:
            self.tool_names.remove(name)

    def list_tools(self) -> List[str]:
        """List all registered tool names."""
        return self.tool_names

    def get_tool(self, name: str) -> Optional[ToolMetadata]:
        """Get tool metadata by name."""
        return self.catalog.get_tool(name)

    def export_to_crewai(self) -> List[CrewAITool]:
        """Export tools as CrewAI tools."""
        crewai_tools = []
        for name in self.tool_names:
            metadata = self.catalog.get_tool(name)
            if metadata:
                tool = self._create_crewai_tool(name, metadata)
                crewai_tools.append(tool)
        return crewai_tools

    def export_to_openai(self) -> List[Dict[str, Any]]:
        openai_tools = []
        for name in self.tool_names:
            metadata = self.catalog.get_tool(name)
            if metadata:
                openai_tool = {
                    "type": "function",
                    "function": {
                        "name": name,
                        "description": metadata.description,
                        "parameters": {
                            "type": "object",
                            "properties": {},
                            "required": []
                        }
                    }
                }
                
                # Handle schema conversion for OpenAPI tools
                if metadata.tool_type == ToolType.OPENAPI_TOOL:
                    if metadata.schema:
                        converted_params = self._convert_parameters_to_openai_schema(metadata.schema)
                        openai_tool["function"]["parameters"] = converted_params
                # Convert parameter list for other tools
                elif metadata.parameters:
                    param_schema = {
                        "type": "object",
                        "properties": {},
                        "required": []
                    }
                    for param in metadata.parameters:
                        param_schema["properties"][param.name] = {
                            "type": self._get_openai_type(param.type_hint),
                            "description": param.description
                        }
                        if param.required:
                            param_schema["required"].append(param.name)
                    openai_tool["function"]["parameters"] = param_schema
                
                openai_tools.append(openai_tool)
                
        return openai_tools

    def _get_openai_type(self, type_hint: Optional[str]) -> str:
        """Convert Python/custom type hints to OpenAI types."""
        if not type_hint:
            return "string"
            
        type_hint = str(type_hint).lower()
        if "int" in type_hint or "float" in type_hint:
            return "number"
        elif "bool" in type_hint:
            return "boolean"
        elif "list" in type_hint or "array" in type_hint:
            return "array"
        elif "dict" in type_hint or "object" in type_hint:
            return "object"
        return "string"

    def _convert_parameters_to_openai_schema(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        schema = {
            "type": "object",
            "properties": {},
            "required": []
        }

        for param_type, params in parameters.items():
            if param_type == 'requestBody':
                # For requestBody, directly use the schema properties
                if isinstance(params, ResolvedSchema):
                    converted = self._convert_schema(params)
                    schema["properties"] = converted.get("properties", {})  # Use the properties directly
                else:
                    schema["properties"] = self._convert_schema(params).get("properties", {})
            else:
                # Handle other parameter types
                for name, param in params.items():
                    if hasattr(param, 'schema'):
                        schema["properties"][name] = self._convert_schema(param.schema)
                        if getattr(param, 'required', False):
                            schema["required"].append(name)

        return schema

    def _convert_resolved_schema_to_properties(self, schema: ResolvedSchema) -> Dict[str, Any]:
        """Convert ResolvedSchema to OpenAI properties format."""
        properties = {}
        
        if schema.properties:
            for prop_name, prop_schema in schema.properties.items():
                if isinstance(prop_schema, ResolvedSchema):
                    if prop_schema.type == "object" and prop_schema.properties:
                        # Handle nested objects
                        properties[prop_name] = {
                            "type": "object",
                            "properties": self._convert_resolved_schema_to_properties(prop_schema)
                        }
                        if prop_schema.required:
                            properties[prop_name]["required"] = prop_schema.required
                    else:
                        # Handle primitive types
                        properties[prop_name] = {
                            "type": prop_schema.type or "string"
                        }
                        if prop_schema.description:
                            properties[prop_name]["description"] = prop_schema.description
                else:
                    properties[prop_name] = self._convert_schema(prop_schema)

        return properties

    def _convert_schema(self, schema: Union[ResolvedSchema, Dict[str, Any]]) -> Dict[str, Any]:
        """Convert schema to OpenAI-compatible format.
        
        Args:
            schema: Either a ResolvedSchema object or a dict representing the schema
            
        Returns:
            Dictionary in OpenAI function parameter format
        """
        if isinstance(schema, ResolvedSchema):
            converted = {
                "type": schema.type or "string"  # Default to string if type is None
            }
            
            if schema.description:
                converted["description"] = schema.description
                
            if schema.properties:
                converted["properties"] = {}
                for prop_name, prop_schema in schema.properties.items():
                    converted["properties"][prop_name] = self._convert_schema(prop_schema)
                    
                if schema.required:
                    converted["required"] = schema.required
                    
            if schema.items:
                converted["items"] = self._convert_schema(schema.items)
                
            return converted
            
        elif isinstance(schema, dict):
            converted = {
                "type": schema.get("type", "string")
            }
            
            if "description" in schema:
                converted["description"] = schema["description"]
                
            if "properties" in schema:
                converted["properties"] = {}
                for prop_name, prop_schema in schema["properties"].items():
                    converted["properties"][prop_name] = self._convert_schema(prop_schema)
                    
                if "required" in schema:
                    converted["required"] = schema["required"]
                    
            if "items" in schema:
                converted["items"] = self._convert_schema(schema["items"])
                
            return converted
        
        return {"type": "string"}  # Default fallback

    def export_to_anthropic(self) -> List[Dict[str, Any]]:
        """Export tools as Anthropic function definitions."""
        anthropic_tools = []
        for name in self.tool_names:
            metadata = self.catalog.get_tool(name)
            if metadata:
                anthropic_tool = {
                    "type": "function",
                    "name": name,
                    "description": metadata.description,
                    "parameters": self._parameters_to_anthropic_schema(metadata.parameters)
                }
                anthropic_tools.append(anthropic_tool)
        return anthropic_tools

    def _create_crewai_tool(self, name: str, metadata: ToolMetadata) -> CrewAITool:
        """Create a CrewAI tool from tool metadata."""
        return create_crewai_tool(name, metadata, self)


    def _parameters_to_schema(self, parameters: List[ParameterInfo]) -> Dict[str, Any]:
        """Convert parameter info to JSON schema."""
        schema = {
            "type": "object",
            "properties": {},
            "required": []
        }

        for param in parameters:
            param_type = "string"
            if param.type_hint:
                if param.type_hint in (int, float):
                    param_type = "number"
                elif param.type_hint == bool:
                    param_type = "boolean"

            schema["properties"][param.name] = {
                "type": param_type,
                "description": param.description
            }

            if param.required:
                schema["required"].append(param.name)

        return schema

    def _parameters_to_anthropic_schema(self, parameters: List[ParameterInfo]) -> Dict[str, Any]:
        """Convert parameters to Anthropic schema format."""
        return self._parameters_to_schema(parameters)

    def to_dict(self) -> Dict[str, Any]:
        """Convert proxy to dictionary for serialization."""
        return {
            "id": str(self.id),
            "tool_names": self.tool_names,
            "catalog": self.catalog.to_dict()
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CurriedProxy':
        """Create proxy from serialized dictionary."""
        proxy = cls(
            id=UUID(data["id"]),
            tool_names=data["tool_names"]
        )
        proxy.catalog = ToolsCatalog.from_dict(data["catalog"])
        return proxy
    
    async def _call_openapi_tool(self, tool: Tool, arguments: Dict[str, Any]) -> Any:
        """Execute an OpenAPI tool."""
        try:
            function = tool.function
            base_url = function.servers[0].url if function.servers else ""
            url = base_url + function.url
            headers = {}
            
            # Handle credentials from the tool's function
            if function.credentials:
                if function.credentials.auth_type and function.credentials.auth_key:
                    headers["Authorization"] = f"{function.credentials.auth_type}: {function.credentials.auth_key}"
                    
            # Initialize parameter containers
            query_params = {}
            header_params = {}
            path_params = {}
            body_params = None

            # Process parameters based on their location
            for param_type, params in function.parameters.items():
                if param_type == 'query':
                    query_params = {k: arguments.get(k) for k, v in params.items() if k in arguments}
                elif param_type == 'header':
                    header_params = {k: arguments.get(k) for k, v in params.items() if k in arguments}
                elif param_type == 'path':
                    path_params = {k: arguments.get(k) for k, v in params.items() if k in arguments}
                elif param_type == 'requestBody':
                    # Use the schema directly from the OpenAPI definition
                    body_params = arguments
                    
            # Update headers with custom header parameters
            headers.update(header_params)
                    
            # Set default headers
            headers["Content-Type"] = "application/json" if body_params is not None else "application/x-www-form-urlencoded"
            headers["Accept"] = "*/*"
            
            # Format URL with path parameters
            if path_params:
                url = url.format(**path_params)
                
            # Execute request
            async with httpx.AsyncClient() as client:
                request_kwargs = {
                    "url": url,
                    "params": query_params,
                    "headers": headers,
                }
                
                if body_params is not None:
                    request_kwargs["json"] = body_params
                    
                response = await getattr(client, function.method.lower())(**request_kwargs)
                if response.status_code >= 400:
                    response.raise_for_status()
                return response.json()      
        except Exception as e:
            return {"error": f"Request failed: {str(e)}"}


# CreaAI specific export functions

def convert_type_hint(type_hint: Optional[str]) -> Type:
    """
    Convert a type hint string to an actual Python type.
    
    Args:
        type_hint: String representation of the type
        
    Returns:
        Actual Python type or Any if type can't be determined
    """
    if not type_hint:
        return Any
        
    # Handle '<class 'type'>' format
    class_match = re.match(r"<class '(\w+)'>", type_hint)
    if class_match:
        type_hint = class_match.group(1)

    # Strip any quotes and spaces
    type_hint = type_hint.strip().strip("'").strip('"')
    
    # Basic type mapping
    type_map = {
        'str': str,
        'string': str,
        'int': int,
        'integer': int,
        'float': float,
        'bool': bool,
        'boolean': bool,
        'list': List,
        'dict': Dict,
        'any': Any,
        'none': type(None),
        'List': List,
        'Dict': Dict,
        'Any': Any,
        'Optional': Optional,
        'Union': Union
    }
    
    # Check if it's a basic type
    if type_hint.lower() in type_map:
        return type_map[type_hint.lower()]
    
    # Handle Optional[Type] pattern
    if type_hint.startswith('Optional['):
        inner_type = type_hint[9:-1]  # Remove Optional[ and ]
        return Optional[convert_type_hint(inner_type)]
    
    # Handle List[Type] pattern
    if type_hint.startswith('List['):
        inner_type = type_hint[5:-1]  # Remove List[ and ]
        return List[convert_type_hint(inner_type)]
    
    # Handle Dict[Key, Value] pattern
    if type_hint.startswith('Dict['):
        key_value = type_hint[5:-1].split(',')  # Remove Dict[ and ] and split
        if len(key_value) == 2:
            key_type = convert_type_hint(key_value[0].strip())
            value_type = convert_type_hint(key_value[1].strip())
            return Dict[key_type, value_type]
    
    # Handle Union[Type1, Type2] pattern
    if type_hint.startswith('Union['):
        types = type_hint[6:-1].split(',')  # Remove Union[ and ] and split
        converted_types = [convert_type_hint(t.strip()) for t in types]
        return Union[tuple(converted_types)]
        
    # Default to Any for unknown types
    logger.warning(f"Unknown type hint '{type_hint}', defaulting to Any")
    return Any

class ToolArgumentSchema(BaseModel):
    """Base schema for tool arguments."""
    class Config:
        extra = "forbid"  # Prevent additional arguments

def create_argument_schema(metadata: ToolMetadata) -> Type[ToolArgumentSchema]:
    """Create a Pydantic schema for tool arguments based on metadata."""
    fields: Dict[str, Any] = {}
    
    for param in metadata.parameters:
        try:
            # Convert type hint string to actual type
            field_type = convert_type_hint(param.type_hint)
            
            # Create field with proper validation
            field_info = Field(
                default=param.default if not param.required else ...,
                description=param.description or "",
                title=param.name.title()
            )
            
            # Add field to schema
            fields[param.name] = (field_type, field_info)
            
        except Exception as e:
            logger.error(f"Error processing parameter {param.name}: {str(e)}")
            # Fallback to Any type with warning
            fields[param.name] = (Any, field_info)
    
    model_name = f"{metadata.name.replace('.', '_')}_Args"
    try:
        return create_model(model_name, __base__=ToolArgumentSchema, **fields)
    except Exception as e:
        logger.error(f"Error creating argument schema for tool {metadata.name}: {str(e)}, fields: {fields}")
        raise

def parse_input_arguments(kwargs: Dict[str, Any], tool_name: str) -> Dict[str, Any]:
    """
    Parse and normalize input arguments for tool execution.
    
    Args:
        kwargs: Raw input arguments
        tool_name: Name of the tool being executed
        
    Returns:
        Normalized arguments dictionary
    """
    try:
        # Log initial state
        logger.debug(f"[{tool_name}] Initial arguments: {kwargs}")
        
        # Handle empty input
        if not kwargs:
            logger.warning(f"[{tool_name}] Received empty arguments")
            return {}

        # Handle string JSON input
        if len(kwargs) == 1 and "input" in kwargs and isinstance(kwargs["input"], str):
            try:
                parsed = json.loads(kwargs["input"])
                if isinstance(parsed, dict):
                    logger.debug(f"[{tool_name}] Parsed input JSON: {parsed}")
                    return parsed
            except json.JSONDecodeError as e:
                logger.debug(f"[{tool_name}] Failed to parse input as JSON: {e}")

        # Handle single string parameter that might be JSON
        if len(kwargs) == 1 and isinstance(list(kwargs.values())[0], str):
            try:
                parsed = json.loads(list(kwargs.values())[0])
                if isinstance(parsed, dict):
                    logger.debug(f"[{tool_name}] Parsed single parameter JSON: {parsed}")
                    return parsed
            except json.JSONDecodeError:
                logger.debug(f"[{tool_name}] Single parameter is not JSON")

        # If we get here, return the original arguments
        return kwargs
        
    except Exception as e:
        logger.error(f"[{tool_name}] Error parsing arguments: {str(e)}")
        return kwargs

class CerebrumToolWrapper:
    """Wrapper class to hold the tool's execution context."""
    def __init__(self, proxy: Any, metadata: ToolMetadata):
        self.proxy = proxy
        self.metadata = metadata
        self.args_schema = create_argument_schema(metadata)

class CerebrumCrewAITool(CrewAITool):
    """Enhanced CrewAI tool with improved argument handling and async support."""
    def __init__(self, name: str, description: str, proxy: Any, metadata: ToolMetadata, **kwargs):
        super().__init__(name=name, description=description, **kwargs)
        self._context = CerebrumToolWrapper(proxy, metadata)

        if metadata.returns and metadata.returns.description:
            self.description = f"{self.description}\nReturns: {metadata.returns.description}"

        # Add parameter information to description
        param_desc = self._build_parameter_description()
        if param_desc:
            self.description = f"{self.description}\n\nParameters:\n{param_desc}"

    def _build_parameter_description(self) -> str:
        """Build a description of required and optional parameters."""
        if not self._context.metadata.parameters:
            return ""
            
        required_params = []
        optional_params = []
        
        for param in self._context.metadata.parameters:
            param_desc = f"{param.name}"
            if param.description:
                param_desc += f": {param.description}"
            if param.type_hint:
                param_desc += f" (type: {param.type_hint})"
                
            if param.required:
                required_params.append(param_desc)
            else:
                optional_params.append(param_desc)

        desc_parts = []
        if required_params:
            desc_parts.append("Required:\n  " + "\n  ".join(required_params))
        if optional_params:
            desc_parts.append("Optional:\n  " + "\n  ".join(optional_params))
            
        return "\n".join(desc_parts)

    async def _arun(self, **kwargs: Any) -> Any:
        """Async execution of the tool."""
        try:
            # Parse and normalize input arguments
            parsed_args = parse_input_arguments(kwargs, self.name)
            logger.debug(f"[{self.name}] Using arguments: {parsed_args}")
            
            # Validate arguments using schema
            try:
                validated_args = self._context.args_schema(**parsed_args)
                logger.debug(f"[{self.name}] Arguments validated successfully")
            except Exception as e:
                logger.error(f"[{self.name}] Validation error: {str(e)}")
                raise

            # Execute tool
            start_time = datetime.now()
            try:
                result = await self._context.proxy.curried_proxy(self.name)(validated_args.dict())
                execution_time = (datetime.now() - start_time).total_seconds()
                logger.debug(f"[{self.name}] Execution completed in {execution_time:.2f}s")
                return result
            except Exception as e:
                logger.error(f"[{self.name}] Execution error: {str(e)}")
                raise
            
        except Exception as e:
            logger.error(f"[{self.name}] Tool execution failed: {str(e)}")
            raise

    def _run(self, **kwargs: Any) -> Any:
        """Synchronous wrapper for async execution."""
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        return loop.run_until_complete(self._arun(**kwargs))

def create_crewai_tool(name: str, metadata: ToolMetadata, proxy: Any) -> CrewAITool:
    """Factory function to create a CrewAI tool from metadata."""
    return CerebrumCrewAITool(
        name=name,
        description=metadata.description,
        proxy=proxy,
        metadata=metadata
    )
