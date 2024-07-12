import httpx
from typing import Dict, Any
from src.server.models.toolset import Tool
from src.server.models.function import Function, ParameterSchema
from src.server.models.toolset_credentials import ToolsetCredentials

class RestProxyController:

    async def multiset_proxy(self, name: str, arguments: Dict[str, Any], tools_dict: Dict[str, Tool]):
        tool = tools_dict[name]
        function: Function = tool.function
        
        # Prepare URL
        base_url = function.servers[0].url
        url = base_url + function.url
        headers = {}
        credentials: ToolsetCredentials = function.credentials
        
        # Prepare headers with Authentication token
        if credentials.auth_type and credentials.auth_key:
            headers = {
                "Authorization": f"{credentials.auth_type}: {credentials.auth_key}"
            }

        # Organize parameters by type
        query_params = {}
        header_params = {}
        path_params = {}
        body_params = {}

        # Check for additional global and/or security keys in toolset and add them to path_params
        if credentials.path_credentials:
            for key_set in credentials.path_credentials:
                path_params[key_set.key] = key_set.value

        for param_type, params in function.parameters.items():
            if param_type == 'query':
                query_params = {k: arguments[k] for k, v in params.items() if k in arguments}
            elif param_type == 'header':
                header_params = {k: arguments[k] for k, v in params.items() if k in arguments}
            elif param_type == 'path':
                path_params.update({k: arguments[k] for k, v in params.items() if k in arguments})
            elif param_type == 'requestBody':
                body_params = arguments.get('requestBody', {})

        # Update headers and URL with path and header parameters
        headers.update(header_params)
        url = url.format(**path_params)  # Assuming path parameters are used as {param} in the URL

        # Choose the appropriate content type
        if body_params:
            headers["Content-Type"] = "application/json"

        headers["Accept"] = "*/*"

        return await self._send_request(function.method, url, query_params, body_params, headers)

    async def proxy(self, function_name: str, event: Dict[str, Any], tool: Tool):
        function: Function = tool.function
        
        # Prepare URL
        base_url = function.servers[0].url
        url = base_url + function.url

        # Organize parameters by type
        headers = event.get('headers', {})
        query_params = event.get('queryStringParameters', {})
        path_params = event.get('pathParameters', {})
        body_params = event.get('body', {})

        credentials: ToolsetCredentials = function.credentials
        # Prepare headers with Authentication token
        if credentials.auth_type and credentials.auth_key:
            headers["Authorization"] = f"{credentials.auth_type}: {credentials.auth_key}"

        # Check for additional global and/or security keys in toolset and add them to path_params
        if credentials.path_credentials:
            for key_set in credentials.path_credentials:
                path_params[key_set.key] = key_set.value

        # Update headers and URL with path and header parameters
        headers.update(event.get('headers', {}))
        url = url.format(**path_params)  # Assuming path parameters are used as {param} in the URL

        # Choose the appropriate content type
        if body_params:
            headers["Content-Type"] = "application/json"

        headers["Accept"] = "*/*"

        return await self._send_request(function.method, url, query_params, body_params, headers)

    async def _send_request(self, method: str, url: str, query_params: Dict[str, Any], body_params: Dict[str, Any], headers: Dict[str, str]):
        method = method.lower().strip()
        http_methods = [
            'get',
            'post',
            'put',
            'delete',
            'patch',
            'head',
            'options']
        
        if method not in http_methods:
            raise ValueError(f"Unsupported HTTP method: '{method}'")

        async with httpx.AsyncClient() as client:
            if method.lower() == 'get':
                response = await client.get(url, params=query_params, headers=headers)
            elif method.lower() == 'post':
                response = await client.post(url, json=body_params, params=query_params, headers=headers)
            elif method.lower() == 'put':
                response = await client.put(url, json=body_params, params=query_params, headers=headers)
            elif method.lower() == 'delete':
                response = await client.delete(url, params=query_params, headers=headers)
            elif method == 'patch':
                response = await client.patch(url, json=body_params, params=query_params, headers=headers)
            elif method == 'head':
                response = await client.head(url, params=query_params, headers=headers)
            elif method == 'options':
                response = await client.options(url, params=query_params, headers=headers)

        return response.json()
