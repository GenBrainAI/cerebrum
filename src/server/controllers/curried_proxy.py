import re
from functools import partial
import inspect
import httpx
from uuid import UUID, uuid4
from typing import Dict, Any, List, Callable, Union
from crewai_tools import BaseTool
from pydantic import BaseModel, Field
from ..models.toolset import Tool
from ..models.function import Function, ServerInfo
from ..models.toolset_credentials import ToolsetCredentials
from ..models.function import ResolvedSchema
import inspect


class PythonFunctionTool(BaseTool):
    def _run(self, *args: Any, **kwargs: Any) -> Any:
        pass

    name: str
    function: Callable
    description: str = ""


class CurriedProxy(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    tools_dict: Dict[str, Union[Tool, PythonFunctionTool]] = Field(default_factory=dict)
    name_counter: Dict[str, int] = Field(default_factory=dict)

    class Config:
        arbitrary_types_allowed = True

    def generate_safe_name(self, original_name: str) -> str:
        # Remove non-alphanumeric characters and replace spaces with underscores
        safe_name = re.sub(r'[^\w\s-]', '', original_name).strip().replace(' ', '_')

        # Ensure the name starts with a letter or underscore
        if not safe_name[0].isalpha() and safe_name[0] != '_':
            safe_name = f"tool_{safe_name}"

        # If the name already exists, append a number
        base_name = safe_name
        if base_name in self.name_counter:
            self.name_counter[base_name] += 1
            safe_name = f"{base_name}_{self.name_counter[base_name]}"
        else:
            self.name_counter[base_name] = 0

        return safe_name

    async def multiset_proxy(self, name: str, arguments: Dict[str, Any]) -> Any:
        tool = self.tools_dict[name]
        try:
            if isinstance(tool, PythonFunctionTool):
                return await self._call_python_function(tool.function, arguments)
            elif isinstance(tool, Tool):
                return await self._call_api_function(tool, arguments)
            else:
                raise ValueError(f"Unknown tool type for {name}")
        except Exception as e:
            return {"error": str(e)}

    async def _call_python_function(self, func: Callable, arguments: Dict[str, Any]) -> Any:
        if inspect.iscoroutinefunction(func):
            return await func(**arguments)
        else:
            return func(**arguments)

    async def _call_api_function(self, tool: Tool, arguments: Dict[str, Any]) -> Dict[str, Any]:
        function: Function = tool.function
        base_url = function.servers[0].url
        url = base_url + function.url
        headers = {}
        credentials: ToolsetCredentials = function.credentials

        if credentials.auth_type and credentials.auth_key:
            headers["Authorization"] = f"{credentials.auth_type}: {credentials.auth_key}"

        query_params = {}
        header_params = {}
        path_params = {}
        body_params = {}

        if credentials.path_credentials:
            for key_set in credentials.path_credentials:
                path_params[key_set.key] = key_set.value

        for param_type, params in function.parameters.items():
            if param_type == 'query':
                query_params = {k: arguments.get(k) for k in params if k in arguments}
            elif param_type == 'header':
                header_params = {k: arguments.get(k) for k in params if k in arguments}
            elif param_type == 'path':
                path_params.update({k: arguments.get(k) for k in params if k in arguments})
            elif param_type == 'requestBody':
                body_params = arguments.get('requestBody', {})

        headers.update(header_params)
        url = url.format(**path_params)

        headers["Content-Type"] = "application/json" if body_params else "application/x-www-form-urlencoded"
        headers["Accept"] = "*/*"

        async with httpx.AsyncClient() as client:
            method = function.method.lower()
            request_kwargs = {
                "url": url,
                "params": query_params,
                "headers": headers,
            }
            if method in ['post', 'put', 'patch']:
                request_kwargs["json" if headers["Content-Type"] == "application/json" else "data"] = body_params

            response = await getattr(client, method)(**request_kwargs)

        return response.json()

    def curried_proxy(self, name: str):
        return partial(self.multiset_proxy, name)

    def add_tool(self, name: str, tool: Union[Tool, Callable, object]):
        safe_name = self.generate_safe_name(name)
        if isinstance(tool, Tool):
            self.tools_dict[safe_name] = tool
        elif callable(tool):
            self.tools_dict[safe_name] = PythonFunctionTool(name=safe_name, function=tool,
                                                            description=tool.__doc__ or "")
        elif isinstance(tool, object):
            for method_name, method in inspect.getmembers(tool, predicate=inspect.ismethod):
                if not method_name.startswith('_'):
                    full_name = self.generate_safe_name(f"{name}.{method_name}")
                    self.tools_dict[full_name] = PythonFunctionTool(
                        name=full_name,
                        function=method,
                        description=method.__doc__ or ""
                    )
        else:
            raise ValueError(f"Unsupported tool type: {type(tool)}")

    def remove_tool(self, name: str):
        self.tools_dict.pop(name, None)

    def get_tool(self, name: str) -> Union[Tool, PythonFunctionTool]:
        return self.tools_dict.get(name)

    def list_tools(self) -> List[str]:
        return list(self.tools_dict.keys())

    def create_crewai_tool(self, name: str, tool: Union[Tool, PythonFunctionTool]) -> BaseTool:
        tool_description = tool.function.description if isinstance(tool, Tool) else tool.description

        class CustomTool(BaseTool):
            name: str
            description: str
            proxy: CurriedProxy

            def _run(self, **kwargs: Any) -> Any:
                return self.proxy.curried_proxy(self.name)(kwargs)

        custom_tool = CustomTool(
            name=name,
            description=tool_description,
            proxy=self
        )
        return custom_tool

    def export_to_crewai(self) -> List[BaseTool]:
        crewai_tools = []
        for name, tool in self.tools_dict.items():
            crewai_tool = self.create_crewai_tool(name, tool)
            crewai_tools.append(crewai_tool)
        return crewai_tools

    def export_to_openai(self) -> List[Dict[str, Any]]:
        openai_tools = []
        for name, tool in self.tools_dict.items():
            if isinstance(tool, Tool):
                function = tool.function
                openai_tool = {
                    "type": "function",
                    "function": {
                        "name": name,
                        "description": function.description,
                        "parameters": self._convert_parameters_to_openai_schema(function.parameters)
                    }
                }
                openai_tools.append(openai_tool)
            elif isinstance(tool, PythonFunctionTool):
                openai_tool = {
                    "type": "function",
                    "function": {
                        "name": name,
                        "description": tool.description,
                        "parameters": self._get_function_parameters(tool.function)
                    }
                }
                openai_tools.append(openai_tool)
        return openai_tools

    def export_to_anthropic(self) -> List[Dict[str, Any]]:
        anthropic_tools = []
        for name, tool in self.tools_dict.items():
            if isinstance(tool, Tool):
                function = tool.function
                anthropic_tool = {
                    "type": "function",
                    "name": name,
                    "description": function.description,
                    "parameters": self._convert_parameters_to_anthropic_schema(function.parameters)
                }
                anthropic_tools.append(anthropic_tool)
            elif isinstance(tool, PythonFunctionTool):
                anthropic_tool = {
                    "type": "function",
                    "name": name,
                    "description": tool.description,
                    "parameters": self._get_function_parameters(tool.function)
                }
                anthropic_tools.append(anthropic_tool)
        return anthropic_tools

    def _convert_parameters_to_openai_schema(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        schema = {
            "type": "object",
            "properties": {},
            "required": []
        }

        for param_type, params in parameters.items():
            if param_type == 'requestBody':
                schema["properties"]["requestBody"] = self._convert_schema(params)
            else:
                for name, param in params.items():
                    schema["properties"][name] = self._convert_schema(param.schema)
                    if param.required:
                        schema["required"].append(name)
        return schema

    def _convert_parameters_to_anthropic_schema(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        # Anthropic's schema is similar to OpenAI's, so we can reuse the conversion
        return self._convert_parameters_to_openai_schema(parameters)

    def _convert_schema(self, schema: Union[Dict[str, Any], ResolvedSchema]) -> Dict[str, Any]:
        if isinstance(schema, dict):
            converted = {"type": schema.get("type", "string")}
            if "description" in schema:
                converted["description"] = schema["description"]
            if "properties" in schema:
                converted["properties"] = {
                    k: self._convert_schema(v) for k, v in schema["properties"].items()
                }
            if "items" in schema:
                converted["items"] = self._convert_schema(schema["items"])
        elif isinstance(schema, ResolvedSchema):
            converted = {"type": schema.type or "string"}
            if schema.description:
                converted["description"] = schema.description
            if schema.properties:
                converted["properties"] = {
                    k: self._convert_schema(v) for k, v in schema.properties.items()
                }
            if schema.items:
                converted["items"] = self._convert_schema(schema.items)
        else:
            # If it's neither a dict nor a ResolvedSchema, return a default schema
            converted = {"type": "string"}

        return converted

    def _get_function_parameters(self, func: Callable) -> Dict[str, Any]:
        sig = inspect.signature(func)
        parameters = {
            "type": "object",
            "properties": {},
            "required": []
        }
        for name, param in sig.parameters.items():
            if param.annotation != inspect.Parameter.empty:
                parameters["properties"][name] = {"type": str(param.annotation.__name__)}
            else:
                parameters["properties"][name] = {"type": "string"}
            if param.default == inspect.Parameter.empty:
                parameters["required"].append(name)
        return parameters
