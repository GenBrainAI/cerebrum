from functools import partial
import httpx

class CurriedProxy:
    def __init__(self, functions_dict):
        self.functions_dict = functions_dict

    async def multiset_proxy(self, name, arguments):
        function = self.functions_dict[name]
        # Prepare URL
        base_url = function['servers'][0]['url']
        url = base_url + function['url']
        headers = {}
        credentials = function['credentials']
        # Prepare headers with Authentication token
        if 'auth_type' in credentials and 'auth_key' in credentials and \
                credentials['auth_type'] is not None and credentials['auth_key'] is not None:
            headers = {
                "Authorization": f"{credentials['auth_type']}: {credentials['auth_key']}"
            }

        # Organize parameters by type
        query_params = {}
        header_params = {}
        path_params = {}
        body_params = {}

        # Check for additional global and/or security keys in toolset and add them to path_params
        path_keys = credentials.get('path_credentials', {})
        for key_set in path_keys:
            path_params[key_set['key']] = key_set['value']

        for param_type, params in function['parameters'].items():
            if param_type == 'query':
                query_params = {k: arguments[k] for k in params if k in arguments}
            elif param_type == 'header':
                header_params = {k: arguments[k] for k in params if k in arguments}
            elif param_type == 'path':
                path_params = {k: arguments[k] for k in params if k in arguments}
            elif param_type == 'requestBody':
                body_params = arguments.get('requestBody', {})

        # Update headers and URL with path and header parameters
        headers.update(header_params)
        url = url.format(**path_params)  # Assuming path parameters are used as {param} in the URL

        # Choose the appropriate content type
        if body_params:
            headers["Content-Type"] = "application/json"

        headers["Accept"] = "*/*"

        async with httpx.AsyncClient() as client:
            # Send request based on method
            if function['method'] == 'get':
                response = await client.get(url, params=query_params, headers=headers)
            elif function['method'] == 'post':
                response = await client.post(url, json=body_params, params=query_params, headers=headers)
            elif function['method'] == 'put':
                response = await client.put(url, json=body_params, params=query_params, headers=headers)
            elif function['method'] == 'delete':
                response = await client.delete(url, params=query_params, headers=headers)

        # Return the response content as JSON
        return response.json()

    def curried_proxy(self, name):
        return partial(self.multiset_proxy, name)


# Example usage
functions_dict = {
    'example': {
        'servers': [{'url': 'https://api.example.com'}],
        'url': '/resource/{id}',
        'method': 'get',
        'credentials': {
            'auth_type': 'Bearer',
            'auth_key': 'your_token_here',
            'path_credentials': [{'key': 'id', 'value': '123'}]
        },
        'parameters': {
            'query': ['filter', 'sort'],
            'header': ['Custom-Header'],
            'path': ['id'],
            'requestBody': {}
        }
    }
}

proxy = Proxy(functions_dict)

# Create a curried function for 'example'
curried_example = proxy.curried_proxy('example')

# Use the curried function with arguments
arguments = {
    'filter': 'active',
    'sort': 'desc',
    'Custom-Header': 'value',
    'requestBody': {}
}

# Since this is an async function, you need to run it within an event loop
import asyncio

result = asyncio.run(curried_example(arguments))
print(result)
