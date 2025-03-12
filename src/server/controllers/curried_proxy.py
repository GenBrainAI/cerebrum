from __future__ import annotations
from typing import Any, Dict, List, Optional, Union, Type, Tuple, Annotated
from uuid import UUID, uuid4
import inspect
import logging
import httpx
import asyncio
import docstring_parser

from crewai.tools import BaseTool
from langchain.tools import BaseTool as LangChainTool
from crewai_tools.tools.rag.rag_tool import RagTool
from pydantic import BaseModel, Field, create_model, ConfigDict

# Move these imports to be lazy imports inside methods
# from ..tools.tools_catalog import ToolsCatalog, ParameterInfo, tools_catalog
from ..models.curried_proxy_info import CurriedProxyInfo, ToolInfo
from ..models.toolset import Tool
from ..models.tools_descriptors import ToolMetadata, ToolContext, ToolType
from ..models.function import ResolvedSchema, ParameterSchema
from ..models.tools_descriptors import ParameterInfo  # Keep this import since it's used in multiple methods

logger = logging.getLogger(__name__)

class CurriedProxy(BaseModel):
    """A proxy that wraps a tool and provides a curried interface for calling it."""

    id: UUID = Field(default_factory=uuid4)
    tool_names: List[str] = Field(default_factory=list)
    catalog: Optional[Any] = None  # Changed from ToolsCatalog to Any to avoid import
    name_counter: Dict[str, int] = {}
    name: Optional[str] = Field(default="Unnamed Proxy")
    
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    def __init__(self, **data):
        """Initialize the CurriedProxy with optional catalog."""
        # Use lazy import for ToolsCatalog and tools_catalog
        if 'catalog' not in data or data['catalog'] is None:
            from ..tools.tools_catalog import tools_catalog
            data['catalog'] = tools_catalog
        super().__init__(**data)

    @staticmethod
    def remove_from_task(persistence_model, task_id: str, logger=None) -> bool:
        """Remove a CurriedProxy association from a task.
        
        Args:
            persistence_model: The persistence model to use
            task_id: The ID of the task to remove the proxy from
            logger: Optional logger for logging messages
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Get the task
            task = persistence_model.tasks.read(task_id)
            if not task:
                if logger:
                    logger.error(f"Task not found: {task_id}")
                return False
                
            # Check if the task has a CurriedProxy
            if not task.curried_proxy_id:
                if logger:
                    logger.warning(f"Task {task_id} has no associated CurriedProxy")
                return False
                
            # Remove the CurriedProxy association
            old_proxy_id = task.curried_proxy_id
            task.curried_proxy_id = None
            
            # Update the task
            try:
                persistence_model.tasks.update(task_id, task)
                if logger:
                    logger.info(f"Removed CurriedProxy {old_proxy_id} from task {task_id}")
                return True
            except AttributeError:
                # If update doesn't exist, try other methods
                try:
                    persistence_model.tasks.create(task)
                    if logger:
                        logger.info(f"Updated task {task_id} to remove CurriedProxy")
                    return True
                except Exception as e:
                    if logger:
                        logger.error(f"Failed to update task: {str(e)}")
                    return False
        except Exception as e:
            if logger:
                logger.error(f"Error removing proxy from task: {str(e)}")
                import traceback
                logger.error(traceback.format_exc())
            return False

    def to_info(self) -> CurriedProxyInfo:
        """Convert CurriedProxy to CurriedProxyInfo for serialization."""
        tools = []
        for tool_name in self.tool_names:
            tool_metadata = self.catalog.get_tool(tool_name)
            if not tool_metadata:
                continue

            if tool_metadata.tool_type == ToolType.OPENAPI_TOOL:
                # Handle OpenAPI tools
                tool = self.catalog.get_tool_instance(tool_name)
                if not tool:
                    continue
                tools.append(ToolInfo(
                    name=tool_name,
                    type="tool",
                    tool_data=tool.model_dump()
                ))
            elif tool_metadata.tool_type == ToolType.CREWAI_TOOL:
                # Handle CrewAI tools
                tools.append(ToolInfo(
                    name=tool_name,
                    type="crewai",
                    tool_data={"name": tool_name}
                ))
            else:
                # Handle Python functions/methods
                if tool_metadata.tool_type == ToolType.CLASS_METHOD:
                    # For class methods, check if there's a dot in the name
                    if "." in tool_name:
                        class_name, method_name = tool_name.split(".")
                        tools.append(ToolInfo(
                            name=tool_name,
                            type="function",
                            tool_data={
                                "function_module": tool_metadata.original_obj.__module__,
                                "class_name": class_name,
                                "method_name": method_name,
                                "is_method": True
                            }
                        ))
                    else:
                        # Handle class methods without dots
                        tools.append(ToolInfo(
                            name=tool_name,
                            type="function",
                            tool_data={
                                "function_module": tool_metadata.original_obj.__module__,
                                "class_name": tool_name,
                                "method_name": None,
                                "is_method": True
                            }
                        ))
                else:
                    # For regular functions
                    if "." in tool_name:
                        # Handle module.function_name format
                        module_name, func_name = tool_name.split(".")
                        tools.append(ToolInfo(
                            name=tool_name,
                            type="function",
                            tool_data={
                                "function_module": tool_metadata.original_obj.__module__,
                                "module_name": module_name,
                                "function_name": func_name,
                                "is_method": False
                            }
                        ))
                    else:
                        tools.append(ToolInfo(
                            name=tool_name,
                            type="function",
                            tool_data={
                                "function_module": tool_metadata.original_obj.__module__,
                                "function_name": tool_name,
                                "is_method": False
                            }
                        ))

        # Create a name based on the tools if available
        proxy_name = "New CurriedProxy"
        if hasattr(self, 'name') and self.name:
            # Use the proxy's existing name
            proxy_name = self.name
        elif tools and len(tools) > 0:
            # Only generate a name based on tools if no name is set
            # Use the first tool name as part of the proxy name
            first_tool = tools[0].name.split('.')[-1]
            proxy_name = f"Proxy for {first_tool}" + (f" +{len(tools)-1}" if len(tools) > 1 else "")

        return CurriedProxyInfo(
            id=self.id,
            tools=tools,
            name_counter=self.name_counter,
            name=proxy_name  # Include the name field
        )

    @classmethod
    def from_info(cls, info: CurriedProxyInfo) -> 'CurriedProxy':
        """Construct CurriedProxy from CurriedProxyInfo.
        
        Since tools are loaded in the tools_catalog at startup, we only need to:
        1. Restore the proxy's ID
        2. Restore the tool names list for lookup
        3. Restore the name counter
        4. Use the existing tools_catalog instance
        """
        proxy = cls(id=info.id)
        
        # Restore tool names from the serialized info
        for tool_info in info.tools:
            proxy.tool_names.append(tool_info.name)
            
        # Restore name counter
        proxy.name_counter = info.name_counter
        
        # Store the name as an attribute if available
        if hasattr(info, 'name') and info.name:
            proxy.name = info.name
        
        return proxy

    async def multiset_proxy(self, name: str, arguments: Dict[str, Any]) -> Any:
        """Execute a tool by name with given arguments."""
        try:
            # First try direct metadata lookup
            tool_metadata = self.catalog.get_tool(name)
            if tool_metadata is None:
                # If not found, try with class prefix if this might be a method
                if '.' in name and not name.startswith('.'):
                    class_name = name.split('.')[0]
                    if class_name in self.tool_names:
                        tool_metadata = self.catalog.get_tool(name)
            
            if tool_metadata is None:
                return {"error": f"Tool {name} not found"}

            # Get tool instance
            tool_instance = self.catalog.get_tool_instance(name)
            if tool_instance is None:
                return {"error": f"Tool instance {name} not found"}

            # Execute based on tool type
            if tool_metadata.tool_type == ToolType.OPENAPI_TOOL:
                return await self._call_openapi_tool(tool_instance, arguments)
            elif tool_metadata.tool_type == ToolType.PYTHON_FUNCTION:
                if inspect.iscoroutinefunction(tool_instance):
                    return await tool_instance(**arguments)
                return tool_instance(**arguments)
            elif tool_metadata.tool_type == ToolType.CLASS_METHOD:
                if inspect.iscoroutinefunction(tool_instance):
                    return await tool_instance(**arguments)
                return tool_instance(**arguments)
            else:
                return {"error": f"Unsupported tool type: {tool_metadata.tool_type}"}
                
        except Exception as e:
            return {"error": str(e)}

    async def execute(self, tool_name: str, args: Dict[str, Any]) -> Any:
        """Execute a tool by name with given arguments.
        
        Args:
            tool_name: The name of the tool to execute
            args: The arguments to pass to the tool
            
        Returns:
            The result of the tool execution
        """
        try:
            # Get tool metadata
            metadata = self.catalog.get_tool(tool_name)
            if not metadata:
                raise ValueError(f"Tool {tool_name} not found")
                
            # Get tool instance
            tool_instance = self.catalog.get_tool_instance(tool_name)
            if not tool_instance:
                raise ValueError(f"Tool instance {tool_name} not found")
                
            # Execute the tool based on its type
            if metadata.tool_type == ToolType.OPENAPI_TOOL:
                return await self._call_openapi_tool(tool_instance, args)
            elif metadata.tool_type == ToolType.PYTHON_FUNCTION:
                if inspect.iscoroutinefunction(tool_instance):
                    return await tool_instance(**args)
                return tool_instance(**args)
            elif metadata.tool_type == ToolType.CLASS_METHOD:
                if inspect.iscoroutinefunction(tool_instance):
                    return await tool_instance(**args)
                return tool_instance(**args)
            else:
                raise ValueError(f"Unsupported tool type: {metadata.tool_type}")
                
        except Exception as e:
            raise ValueError(f"Error executing tool {tool_name}: {str(e)}")

    def curried_proxy(self, name: str):
        """Create a curried function for the named tool."""
        return lambda args: self.multiset_proxy(name, args)

    def add_tool(self, name: str, tool: Union[callable, object, BaseTool, LangChainTool, RagTool, Tool]) -> None:
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
            elif isinstance(tool, (BaseTool, LangChainTool, RagTool)):
                tool_name = self.catalog.register_ai_tool(tool, name)
                tool_names = [tool_name]
            elif callable(tool) and not inspect.isclass(tool):
                tool_name = self.catalog.register_function(tool, name)
                tool_names = [tool_name]
            elif inspect.isclass(tool):
                tool_names = self.catalog.register_class(tool, name)
            else:
                # For class instances or objects
                tool_names = self.catalog.register_instance(tool, name)
                # Remove the base name if it's also in the list of method names
                if name in tool_names and len(tool_names) > 1:
                    tool_names.remove(name)
                
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

    def export_to_crewai(self) -> List[BaseTool]:
        """Export tools to CrewAI format."""
        print("\n🔍 DEBUG: Exporting tools to CrewAI")
        print(f"📋 Tool names in proxy: {', '.join(sorted(self.tool_names))}")
        
        crewai_tools = []
        for tool_name in self.tool_names:
            print(f"  ⚙️ Processing tool: {tool_name}")
            try:
                # Get tool metadata
                metadata = self.catalog.get_tool_metadata(tool_name)
                if metadata:
                    print(f"    Type: {metadata.tool_type}")
                    description = metadata.description.split('\n')[0] if metadata.description else ''
                    print(f"    Description: {description}")
                    if metadata.parameters:
                        print(f"    Parameters: {[p.name for p in metadata.parameters]}")
                    
                    # Create CrewAI tool
                    crewai_tool = CerebrumCrewAITool(
                        name=tool_name,
                        description=metadata.description or "No description available",
                        proxy=self
                    )
                    crewai_tools.append(crewai_tool)
                    print(f"    ✅ Created CrewAI tool: {tool_name}")
                else:
                    print(f"    ❌ No metadata found for {tool_name}")
                    
            except Exception as e:
                print(f"    ❌ Error processing tool {tool_name}: {str(e)}")
                continue
        
        print(f"📦 Total tools exported: {len(crewai_tools)}")
        return crewai_tools

    def export_to_openai(self) -> List[Dict[str, Any]]:
        """Export tools to OpenAI format."""
        openai_tools = []
        for tool_name in self.tool_names:
            metadata = self.catalog.get_tool(tool_name)
            if metadata is None:
                continue

            # Get tool instance to check for required_args
            tool_instance = metadata.original_obj
            parameters = {}
            required = []

            # Add parameters from required_args if available
            if hasattr(tool_instance, 'required_args'):
                for param_name, type_hint in tool_instance.required_args.items():
                    description = "Description of the content" if param_name == "description" else "Path to the file to read" if param_name == "file_path" else f"Parameter {param_name}"
                    parameters[param_name] = {
                        "type": "object" if "Dict" in type_hint or "object" in type_hint else "string",
                        "description": description
                    }
                    required.append(param_name)

            # Extract schema from metadata
            if metadata.schema and 'function' in metadata.schema:
                function_params = metadata.schema['function'].get('parameters', {})
                if 'requestBody' in function_params:
                    request_body = function_params['requestBody'].get('requestBody', {})
                    if request_body and 'param_schema' in request_body:
                        param_schema = request_body['param_schema']
                        if param_schema.get('properties'):
                            # Convert the schema properties directly
                            for prop_name, prop_schema in param_schema['properties'].items():
                                parameters[prop_name] = self._convert_schema(prop_schema)
                                if request_body.get('required'):
                                    required.append(prop_name)

            # Add any remaining parameters from metadata
            for param in metadata.parameters:
                if param.name not in parameters:
                    description = param.description or f"Parameter {param.name}"
                    parameters[param.name] = {
                        "type": "object" if "Dict" in param.type_hint or "object" in param.type_hint else "string",
                        "description": description
                    }
                    if param.required:
                        required.append(param.name)

            openai_tools.append({
                "type": "function",
                "function": {
                    "name": tool_name,
                    "description": metadata.description,
                    "parameters": {
                        "type": "object",
                        "properties": parameters,
                        "required": required
                    }
                }
            })
        return openai_tools

    def export_to_anthropic(self) -> List[Dict[str, Any]]:
        """Export tools to Anthropic format."""
        anthropic_tools = []
        for tool_name in self.tool_names:
            metadata = self.catalog.get_tool(tool_name)
            if metadata is None:
                continue

            # Get tool instance to check for required_args
            tool_instance = metadata.original_obj
            parameters = {}
            required = []

            # Add parameters from required_args if available
            if hasattr(tool_instance, 'required_args'):
                for param_name, type_hint in tool_instance.required_args.items():
                    description = "Description of the content" if param_name == "description" else "Path to the file to read" if param_name == "file_path" else f"Parameter {param_name}"
                    parameters[param_name] = {
                        "type": "string",
                        "description": description
                    }
                    required.append(param_name)

            # Add parameters from metadata
            for param in metadata.parameters:
                if param.name not in parameters:
                    description = "Description of the content" if param.name == "description" else "Path to the file to read" if param.name == "file_path" else param.description or f"Parameter {param.name}"
                    parameters[param.name] = {
                        "type": "string",
                        "description": description
                    }
                    if param.required:
                        required.append(param.name)

            anthropic_tools.append({
                "name": tool_name,
                "description": metadata.description,
                "type": "function",
                "parameters": {
                    "type": "object",
                    "properties": parameters,
                    "required": required
                }
            })
        return anthropic_tools

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
                # For requestBody, extract the schema from the nested structure
                if isinstance(params, dict) and 'requestBody' in params:
                    request_body = params['requestBody']
                    if isinstance(request_body, ParameterSchema) and request_body.schema:
                        converted = self._convert_schema(request_body.schema)
                        schema["properties"] = converted.get("properties", {})
                        if request_body.required:
                            schema["required"].extend(converted.get("required", []))
                elif isinstance(params, ResolvedSchema):
                    converted = self._convert_schema(params)
                    schema["properties"] = converted.get("properties", {})
                    if params.required:
                        schema["required"].extend(params.required)
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
        """Convert schema to OpenAI function schema format."""
        if isinstance(schema, ResolvedSchema):
            converted = {
                "type": schema.type or "string"  # Default to string if type is None
            }
            
            # Only add description if it has a value
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
                "type": schema.get("type", "string")  # Default to string if type is missing
            }
            
            # Only add description if it exists and has a value
            if schema.get("description"):
                converted["description"] = schema["description"]
                
            if "properties" in schema and schema["properties"]:
                converted["properties"] = {}
                for prop_name, prop_schema in schema["properties"].items():
                    prop_converted = self._convert_schema(prop_schema)
                    # Only add property if conversion returned a valid schema
                    if prop_converted and isinstance(prop_converted, dict):
                        converted["properties"][prop_name] = prop_converted
                    
                # Only add required if it exists and has values
                if schema.get("required"):
                    converted["required"] = schema["required"]
                    
            if "items" in schema and schema["items"]:
                items_converted = self._convert_schema(schema["items"])
                if items_converted:
                    converted["items"] = items_converted
                
            return converted
        
        # Default fallback for unknown schema types
        return {"type": "string", "description": "Generic parameter"}

    def _create_crewai_tool(self, name: str, metadata: ToolMetadata) -> BaseTool:
        """Create a CrewAI tool from tool metadata."""
        return CerebrumCrewAITool(
            name=name,
            description=metadata.description,
            proxy=self
        )

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
        """Create a CurriedProxy from a dictionary."""
        proxy = cls(
            id=UUID(data["id"]),
            tool_names=data["tool_names"],
            name=data.get("name", "Unnamed Proxy")
        )
        
        # Use lazy import for ToolsCatalog
        if "catalog" in data:
            from ..tools.tools_catalog import ToolsCatalog
            proxy.catalog = ToolsCatalog.from_dict(data["catalog"])
        
        return proxy
    
    async def _call_openapi_tool(self, tool: Tool, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute an OpenAPI tool with the given arguments."""
        try:
            # Get the base URL from the first server
            if not tool.function.servers or not tool.function.servers[0].url:
                return {"error": "No server URL provided"}
            
            base_url = tool.function.servers[0].url.rstrip('/')
            path = tool.function.url.lstrip('/')
            url = f"{base_url}/{path}"

            # Prepare headers with authentication if credentials are present
            headers = {}
            if tool.function.credentials:
                auth_type = tool.function.credentials.get('auth_type', '')
                auth_key = tool.function.credentials.get('auth_key', '')
                if auth_type and auth_key:
                    headers["Authorization"] = f"{auth_type} {auth_key}"

            # Add Accept header
            headers["Accept"] = "*/*"

            # Organize parameters by type
            query_params = {}
            header_params = {}
            path_params = {}
            body_params = {}

            for param_location, params in tool.function.parameters.items():
                for param_name, param in params.items():
                    if param_name in arguments:
                        if param.in_ == 'query':
                            query_params[param_name] = arguments[param_name]
                        elif param.in_ == 'header':
                            header_params[param_name] = arguments[param_name]
                        elif param.in_ == 'path':
                            path_params[param_name] = arguments[param_name]
                        elif param.in_ == 'body':
                            body_params[param_name] = arguments[param_name]

            # Update headers with any header parameters
            headers.update(header_params)

            # Add Content-Type header if there are body parameters
            if body_params:
                headers["Content-Type"] = "application/json"

            # Replace path parameters in URL
            for name, value in path_params.items():
                url = url.replace(f"{{{name}}}", str(value))

            async with httpx.AsyncClient() as client:
                if tool.function.method.lower() == 'get':
                    response = await client.get(url=url, params=query_params, headers=headers)
                elif tool.function.method.lower() == 'post':
                    response = await client.post(url=url, params=query_params, json=body_params, headers=headers)
                else:
                    return {"error": f"Unsupported HTTP method: {tool.function.method}"}

                if response.status_code >= 400:
                    return {"error": f"Request failed with status {response.status_code}: {response.text}"}

                # Try to return JSON if the response is JSON, otherwise return text
                content_type = response.headers.get('content-type', '')
                if 'application/json' in content_type:
                    return await response.json()
                return {"result": response.text}

        except Exception as e:
            return {"error": str(e)}

    def register_tool(self, name: str, tool: Any) -> None:
        """Register a tool with this proxy.
        
        Args:
            name: The name of the tool
            tool: The tool instance
        """
        # Add tool to catalog
        self.add_tool(name, tool)
        
        # Store original description if available
        if hasattr(tool, 'description'):
            self.catalog.update_tool_metadata(name, {'description': tool.description})

    def _create_args_schema(self, tool_name: str, parameters: Dict[str, str]) -> Type[BaseModel]:
        """Create a Pydantic model for tool arguments."""
        fields = {}
        if parameters:
            for param_name, type_hint in parameters.items():
                python_type = self._convert_type_hint(type_hint)
                fields[param_name] = (python_type, Field(..., description=f"Parameter {param_name}"))
        else:
            # Create a default schema if no parameters are provided
            fields = {"input": (str, Field(..., description="Input for the tool"))}

        schema = create_model(f"{tool_name}_args", **fields)
        return schema

    def _convert_type_hint_to_annotation(self, type_hint: Optional[str]) -> Any:
        """Convert type hint string to pydantic annotation."""
        python_type = self._convert_type_hint(type_hint)
        return Annotated[python_type, Field(description=f"Parameter of type {python_type.__name__}")]

    def _convert_type_hint(self, type_hint: Optional[Union[str, Tuple]]) -> Type:
        """Convert a type hint string or tuple to a Python type."""
        if type_hint is None:
            return str

        # If type_hint is a tuple, extract the first element (the type)
        if isinstance(type_hint, tuple):
            type_hint = type_hint[0]
            # If it's already a type, return it
            if isinstance(type_hint, type):
                return type_hint

        # If it's already a type, return it
        if isinstance(type_hint, type):
            return type_hint

        # Convert string type hints
        type_map = {
            'str': str,
            'int': int,
            'float': float,
            'bool': bool,
            'list': list,
            'dict': dict,
            'any': Any
        }

        if isinstance(type_hint, str):
            return type_map.get(type_hint.lower(), str)  # Default to str if type not found
        
        return str  # Default to str for unknown types

    async def _arun(self, **kwargs: Any) -> Any:
        """Execute the tool asynchronously."""
        try:
            # Validate arguments using the schema
            if self.args_schema:
                validated_args = self.args_schema(**kwargs)
                kwargs = validated_args.model_dump()

            # Execute the tool through the proxy
            return await self._proxy.execute(self.name, kwargs)
        except Exception as e:
            raise ValueError(f"Error executing tool {self.name}: {str(e)}")

    def _run(self, **kwargs) -> str:
        """Run the tool synchronously - not supported."""
        raise NotImplementedError("This tool only supports async execution")

class CerebrumToolSchema(BaseModel):
    """Base schema for all Cerebrum tools."""
    model_config = ConfigDict(extra='forbid')  # Prevent extra fields like kwargs

class ArgsSchema(BaseModel):
    """Base schema for tool arguments that forbids extra fields."""
    model_config = ConfigDict(extra='forbid')

    @classmethod
    def model_json_schema(cls, *args, **kwargs):
        """Remove kwargs from required fields if present."""
        schema = super().model_json_schema(*args, **kwargs)
        if 'required' in schema and 'kwargs' in schema['required']:
            schema['required'].remove('kwargs')
        return schema

class CerebrumCrewAITool(BaseTool):
    """A CrewAI tool that wraps a Cerebrum tool."""

    model_config = {"arbitrary_types_allowed": True}

    def __init__(self, name: str, description: str, proxy: Any):
        """Initialize the tool with name, description and proxy."""
        # Get tool metadata to ensure we have all parameters
        metadata = proxy.catalog.get_tool(name)
        if metadata is None and '.' in name:
            # Try getting metadata for the method directly
            base_name, method_name = name.split('.')
            base_metadata = proxy.catalog.get_tool(base_name)
            if base_metadata:
                # Get the tool instance and method
                tool_instance = proxy.catalog._tool_instances.get(base_name)
                if tool_instance and hasattr(tool_instance, method_name):
                    method = getattr(tool_instance, method_name)
                    if callable(method):
                        # Create method metadata and store it in the catalog
                        metadata = proxy.catalog._create_method_metadata(method, name)
                        metadata.class_name = base_name
                        metadata.method_name = method_name
                        # Get docstring info for better description
                        docstring = inspect.getdoc(method) or f"Method {method_name}"
                        parsed_docstring = docstring_parser.parse(docstring)
                        method_description = parsed_docstring.short_description or ""
                        if parsed_docstring.long_description:
                            method_description = method_description + "\n\n" + parsed_docstring.long_description
                        metadata.description = method_description or docstring
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
                        metadata.parameters = parameters
                        # Store the method metadata in the catalog
                        proxy.catalog._tools[name] = metadata
                        proxy.catalog._tools[method_name] = metadata  # Also store with just the method name

        if metadata is None:
            raise ValueError(f"Tool {name} not found in catalog")

        # Create field definitions from metadata parameters and required_args
        field_definitions = {}
        
        # Add parameters from required_args if available
        if hasattr(metadata, 'original_obj') and hasattr(metadata.original_obj, 'required_args'):
            for param_name, type_hint in metadata.original_obj.required_args.items():
                python_type = eval(type_hint)
                description = "Description of the content" if param_name == "description" else "Path to the file to read" if param_name == "file_path" else f"Parameter {param_name}"
                field_definitions[param_name] = (python_type, Field(..., description=description))

        # Add parameters from metadata
        if hasattr(metadata, 'parameters'):
            for param in metadata.parameters:
                if param.name not in field_definitions:
                    python_type = eval(param.type_hint) if param.type_hint else str
                    description = "Description of the content" if param.name == "description" else "Path to the file to read" if param.name == "file_path" else param.description or f"Parameter {param.name}"
                    field_definitions[param.name] = (python_type, Field(..., description=description))

        # Create schema class
        schema = create_model(
            f"{name}Schema",
            **field_definitions,
            __config__=ConfigDict(extra='forbid', arbitrary_types_allowed=True)
        )

        # Initialize parent with schema
        super().__init__(name=name, description=description, args_schema=schema)
        
        # Store proxy for later use
        self._proxy = proxy

    def _run(self, **kwargs: Any) -> Any:
        """Execute the tool synchronously."""
        return asyncio.run(self._arun(**kwargs))

    async def _arun(self, **kwargs: Any) -> Any:
        """Execute the tool asynchronously."""
        try:
            # Validate arguments using the schema
            if self.args_schema:
                validated_args = self.args_schema(**kwargs)
                kwargs = validated_args.model_dump()

            # Execute the tool through the proxy
            return await self._proxy.execute(self.name, kwargs)
        except Exception as e:
            raise ValueError(f"Error executing tool {self.name}: {str(e)}")

def create_crewai_tool(name: str, metadata: ToolMetadata, proxy: Any) -> BaseTool:
    """Create a CrewAI tool from tool metadata and proxy.
    
    Args:
        name: The name of the tool
        metadata: The tool's metadata containing description and parameters
        proxy: The CurriedProxy instance for executing the tool
    """
    return CerebrumCrewAITool(
        name=name,
        description=metadata.description,
        proxy=proxy
    )
