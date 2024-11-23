from typing import Dict, Any, List, Union, Optional
import asyncio
import inspect
import httpx
from uuid import UUID, uuid4
from pydantic import BaseModel, Field
from crewai_tools import BaseTool as CrewAITool
from crewai_tools.tools.rag.rag_tool import RagTool
from langchain.tools import BaseTool as LangChainTool
from ..tools.tools_catalog import ToolsCatalog, tools_catalog, ParameterInfo
from ..models.tools_descriptors import ToolMetadata, ToolType
from ..models.toolset import Tool
from ..models.function import ResolvedSchema
class CurriedProxy(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    tool_names: List[str] = Field(default_factory=list)
    catalog: ToolsCatalog = Field(default_factory=lambda: tools_catalog)
    
    class Config:
        arbitrary_types_allowed = True

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

    def add_tool(self, name: str, tool: Union[callable, object, CrewAITool, LangChainTool, Tool]) -> None:
        """Add a tool to the proxy using the catalog.
        
        Args:
            name: Name for the tool
            tool: The tool to add - can be a Tool instance from OpenAPI, callable,
                CrewAI tool, LangChain tool, or class instance
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
        class CustomTool(CrewAITool):
            def _run(self, **kwargs: Any) -> Any:
                proxy_func = self.proxy.curried_proxy(self.tool_name)
                try:
                    loop = asyncio.get_running_loop()
                except RuntimeError:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                return loop.run_until_complete(proxy_func(kwargs))

        tool = CustomTool(
            name=name,
            description=metadata.description,
            proxy=self,
            tool_name=name
        )
        return tool

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
        