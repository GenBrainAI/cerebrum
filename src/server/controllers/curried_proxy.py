from functools import partial
import httpx
from typing import Dict, Any, List
from crewai import Agent, Task, Crew
from crewai_tools import BaseTool

class CurriedProxy:
    def __init__(self, functions_dict: Dict[str, Any]):
        self.functions_dict = functions_dict

    async def multiset_proxy(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        function = self.functions_dict[name]
        base_url = function['servers'][0]['url']
        url = base_url + function['url']
        headers = {}
        credentials = function['credentials']

        if 'auth_type' in credentials and 'auth_key' in credentials:
            headers["Authorization"] = f"{credentials['auth_type']} {credentials['auth_key']}"

        query_params = {}
        header_params = {}
        path_params = {}
        body_params = {}

        path_keys = credentials.get('path_credentials', {})
        for key_set in path_keys:
            path_params[key_set['key']] = key_set['value']

        for param_type, params in function['parameters'].items():
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
            method = function['method'].lower()
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

    def export_to_crewai(self) -> List[BaseTool]:
        crewai_tools = []
        for name, function in self.functions_dict.items():
            tool = self.create_crewai_tool(name, function)
            crewai_tools.append(tool)
        return crewai_tools

    def create_crewai_tool(self, name: str, function: Dict[str, Any]) -> BaseTool:
        class CustomTool(BaseTool):
            name: str = name
            description: str = function.get('description', f"Tool for {name}")

            def _run(self, **kwargs: Any) -> Any:
                return self.proxy.curried_proxy(self.name)(kwargs)

        tool = CustomTool()
        tool.proxy = self
        return tool

# Example usage
functions_dict = {
    'example_get': {
        'servers': [{'url': 'https://api.example.com'}],
        'url': '/resource/{id}',
        'method': 'get',
        'description': 'Fetch a resource by ID',
        'credentials': {
            'auth_type': 'Bearer',
            'auth_key': 'your_token_here',
            'path_credentials': [{'key': 'id', 'value': '123'}]
        },
        'parameters': {
            'query': ['filter', 'sort'],
            'header': ['Custom-Header'],
            'path': ['id'],
        }
    },
    'example_post': {
        'servers': [{'url': 'https://api.example.com'}],
        'url': '/resource',
        'method': 'post',
        'description': 'Create a new resource',
        'credentials': {
            'auth_type': 'Bearer',
            'auth_key': 'your_token_here',
        },
        'parameters': {
            'requestBody': {'name': 'string', 'description': 'string'}
        }
    }
}

proxy = CurriedProxy(functions_dict)

# Export tools to CrewAI
crewai_tools = proxy.export_to_crewai()

# Create a CrewAI agent with the exported tools
agent = Agent(
    role='API Interactor',
    goal='Interact with external APIs',
    backstory='An agent specialized in making API calls',
    tools=crewai_tools,
    verbose=True
)

# Create a task for the agent
task = Task(
    description='Fetch a resource and then create a new one',
    agent=agent
)

# Create a crew with the agent and task
crew = Crew(
    agents=[agent],
    tasks=[task],
    verbose=2
)

# Execute the task
result = crew.kickoff()
print(result)