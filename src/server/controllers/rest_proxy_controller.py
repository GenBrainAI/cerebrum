

import httpx
import json

class RestProxyController:

  async def multiset_proxy(self, name, arguments, functions_dict):

    function = functions_dict[name]
    # Prepare URL
    base_url = function['servers'][0]['url']
    url = base_url + function['url']
    headers = {}
    credentials = function['credentials']
    # Prepare headers with Authentication token
    if 'auth_type' in credentials and 'auth_key' in credentials and  \
        credentials['auth_type'] is not None and credentials['auth_key'] is not None:
        headers = {
            "Authorization": f"{credentials.auth_type}: {credentials.auth_key}"
        }

    # Organize parameters by type
    query_params = {}
    header_params = {}
    path_params = {}
    body_params = {}

    # Check for additional global and/or security keys in toolset and add them to path_params
    path_keys = credentials['path_credentials'] or {}
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
            # body_properties = params.get('properties', {})
            # body_params = {k: arguments[k] for k in body_properties if k in arguments}
            body_params = arguments['requestBody']

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



  async def proxy(self, function_name, event, function):

    # Prepare URL
    base_url = function['servers'][0]['url']
    url = base_url + function['url']

    # Organize parameters by type
    headers = event['headers'] or {}
    query_params = event['queryStringParameters'] or {}
    header_params = event['headers'] or {}
    path_params = event['pathParameters'] or {}
    body_params = event['body'] or {}


    credentials = function['credentials']
    # Prepare headers with Authentication token
    if 'auth_type' in credentials and 'auth_key' in credentials and  \
        credentials['auth_type'] is not None and credentials['auth_key'] is not None:
        headers = {
            "Authorization": f"{credentials.auth_type}: {credentials.auth_key}"
        }

    # Check for additional global and/or security keys in toolset and add them to path_params
    path_keys = credentials['path_credentials'] or {}
    for key_set in path_keys:
        path_params[key_set['key']] = key_set['value']

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



#====


# import httpx
# import json

# class RestProxyController:

#   async def proxy_function_w_arguments(self, function, arguments):

#       base_url = function['servers'][0]['url']
#       url = base_url + function['url']
#       headers = {}
#       credentials = function['credentials']
#       # Prepare headers with Authentication token
#       if 'auth_type' in credentials and 'auth_key' in credentials and  \
#           credentials['auth_type'] is not None and credentials['auth_key'] is not None:
#           headers = {
#               "Authorization": f"{credentials.auth_type}: {credentials.auth_key}"
#           }
      
#       # Organize parameters by type
#       query_params = {}
#       header_params = {}
#       path_params = {}
#       body_params = {}
      
#       # Check for additional global and/or security keys in toolset and add them to path_params
#       path_keys = credentials['path_credentials'] or {}
#       for key_set in path_keys:
#           path_params[key_set['key']] = key_set['value']
      
#       for param_type, params in function['parameters'].items():
#           if param_type == 'query':
#               query_params = {k: arguments[k] for k in params if k in arguments}
#           elif param_type == 'header':
#               header_params = {k: arguments[k] for k in params if k in arguments}
#           elif param_type == 'path':
#               path_params = {k: arguments[k] for k in params if k in arguments}
#           elif param_type == 'requestBody':
#               # body_properties = params.get('properties', {})
#               # body_params = {k: arguments[k] for k in body_properties if k in arguments}
#               body_params = arguments['requestBody']
      
#       # Update headers and URL with path and header parameters
#       headers.update(header_params)
#       url = url.format(**path_params)  # Assuming path parameters are used as {param} in the URL
      
#       # Choose the appropriate content type
#       if body_params:
#           headers["Content-Type"] = "application/json"
      
#       headers["Accept"] = "*/*"
      
#       async with httpx.AsyncClient() as client:
#           # Send request based on method
#           if function['method'] == 'get':
#               response = await client.get(url, params=query_params, headers=headers)
#           elif function['method'] == 'post':
#               response = await client.post(url, json=body_params, params=query_params, headers=headers)
#           elif function['method'] == 'put':
#               response = await client.put(url, json=body_params, params=query_params, headers=headers)
#           elif function['method'] == 'delete':
#               response = await client.delete(url, params=query_params, headers=headers)
      
#       # Return the response content as JSON
#       return response.json()


#   async def multiset_proxy(self, name, arguments, functions_dict):

#     function = functions_dict[name]
#     return self.proxy_function_w_arguments(function, arguments)

#   async def proxy(self, function_name, event, function):

#     # Prepare URL
#     base_url = function['servers'][0]['url']
#     url = base_url + function['url']

#     # Organize parameters by type
#     headers = event['headers'] or {}
#     query_params = event['queryStringParameters'] or {}
#     header_params = event['headers'] or {}
#     path_params = event['pathParameters'] or {}
#     body_params = event['body'] or {}


#     credentials = function['credentials']
#     # Prepare headers with Authentication token
#     if 'auth_type' in credentials and 'auth_key' in credentials and  \
#         credentials['auth_type'] is not None and credentials['auth_key'] is not None:
#         headers = {
#             "Authorization": f"{credentials.auth_type}: {credentials.auth_key}"
#         }

#     # Check for additional global and/or security keys in toolset and add them to path_params
#     path_keys = credentials['path_credentials'] or {}
#     for key_set in path_keys:
#         path_params[key_set['key']] = key_set['value']

#     # Update headers and URL with path and header parameters
#     headers.update(header_params)
#     url = url.format(**path_params)  # Assuming path parameters are used as {param} in the URL

#     # Choose the appropriate content type
#     if body_params:
#         headers["Content-Type"] = "application/json"

#     headers["Accept"] = "*/*"

#     async with httpx.AsyncClient() as client:
#         # Send request based on method
#         if function['method'] == 'get':
#             response = await client.get(url, params=query_params, headers=headers)
#         elif function['method'] == 'post':
#             response = await client.post(url, json=body_params, params=query_params, headers=headers)
#         elif function['method'] == 'put':
#             response = await client.put(url, json=body_params, params=query_params, headers=headers)
#         elif function['method'] == 'delete':
#             response = await client.delete(url, params=query_params, headers=headers)

#     # Return the response content as JSON
#     return response.json()


# async def proxy_fn(self, function, arguments):
#     return self.proxy_function_w_arguments(function, arguments)

