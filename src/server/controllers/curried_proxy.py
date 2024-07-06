# # Example usage
# from src.server.persistence.persistence_model_factory import PersistenceModelFactory

# persistence_model = PersistenceModelFactory.persistence_model("inmemory")

# # Create a CurriedProxy instance
# curried_proxy = CurriedProxy()
# persistence_model.curried_proxies.create(curried_proxy)

# # Add a Tool
# api_tool = Tool(...)  # Create a Tool instance
# curried_proxy.add_tool("api_tool", api_tool)

# # Add a function
# def fibonacci(n: int) -> List[int]:
#     if n <= 0:
#         return []
#     elif n == 1:
#         return [0]
#     elif n == 2:
#         return [0, 1]
    
#     fib_sequence = [0, 1]
#     for i in range(2, n):
#         next_fib = fib_sequence[-1] + fib_sequence[-2]
#         fib_sequence.append(next_fib)
    
#     return fib_sequence

# curried_proxy.add_tool("fibonacci", fibonacci)

# # Add a class
# github_tool = GithubTool("your_access_token", "your_repo_name")
# curried_proxy.add_tool("github", github_tool)

# # Use the tools
# api_result = await curried_proxy.curried_proxy("api_tool")({"some": "arguments"})
# fib_result = await curried_proxy.curried_proxy("fibonacci")({"n": 10})
# readme = await curried_proxy.curried_proxy("github.get_readme")({})

# # Update the stored proxy
# persistence_model.curried_proxies.update(str(curried_proxy.id), curried_proxy)

from functools import partial
import httpx
from typing import Dict, Any, List, Callable, Union
from crewai_tools import BaseTool
from pydantic import BaseModel, Field
from src.server.models.toolset import Tool
from src.server.models.function import Function, ServerInfo
from src.server.models.toolset_credentials import ToolsetCredentials
from uuid import UUID, uuid4
import inspect

class PythonFunctionTool(BaseModel):
    name: str
    function: Callable
    description: str = ""

class CurriedProxy(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    tools_dict: Dict[str, Union[Tool, PythonFunctionTool]] = Field(default_factory=dict)

    class Config:
        arbitrary_types_allowed = True

    async def multiset_proxy(self, name: str, arguments: Dict[str, Any]) -> Any:
        tool = self.tools_dict[name]
        
        if isinstance(tool, PythonFunctionTool):
            return await self._call_python_function(tool.function, arguments)
        elif isinstance(tool, Tool):
            return await self._call_api_function(tool, arguments)
        else:
            raise ValueError(f"Unknown tool type for {name}")

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
            headers["Authorization"] = f"{credentials.auth_type} {credentials.auth_key}"

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
        if isinstance(tool, Tool):
            self.tools_dict[name] = tool
        elif callable(tool):
            self.tools_dict[name] = PythonFunctionTool(name=name, function=tool, description=tool.__doc__ or "")
        elif isinstance(tool, object):
            for method_name, method in inspect.getmembers(tool, predicate=inspect.ismethod):
                if not method_name.startswith('_'):
                    full_name = f"{name}.{method_name}"
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

    def export_to_crewai(self) -> List[BaseTool]:
        crewai_tools = []
        for name, tool in self.tools_dict.items():
            crewai_tool = self.create_crewai_tool(name, tool)
            crewai_tools.append(crewai_tool)
        return crewai_tools

    def create_crewai_tool(self, name: str, tool: Union[Tool, PythonFunctionTool]) -> BaseTool:
        class CustomTool(BaseTool):
            name: str = name
            description: str = tool.function.description if isinstance(tool, Tool) else tool.description

            def _run(self, **kwargs: Any) -> Any:
                return self.proxy.curried_proxy(self.name)(kwargs)

        crewai_tool = CustomTool()
        crewai_tool.proxy = self
        return crewai_tool