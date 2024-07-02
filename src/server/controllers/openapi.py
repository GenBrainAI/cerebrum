import asyncio
from datetime import datetime
from threading import Lock

import logging
import json
from prance import ResolvingParser
from deepdiff import DeepDiff
from fastapi.exceptions import HTTPException


def generate_function_name(method, path, method_content):
    """
    Generate a function name based on the HTTP method and path in method_content.
    Checks for 'operationId' or 'name' first, and if neither is present, generates a name.
    """
    # Check for 'operationId' or 'name'
    if 'name' in method_content:
        return method_content['name']

    if 'operationId' in method_content:
        return method_content['operationId']

    #print(f'return method: {method} path: {path}')

    # Split the path and remove empty strings
    path_parts = [p for p in path.split('/') if p]
    # Replace path parameters with general terms (e.g., {id} -> ById)
    name_parts = [p.replace('{', '').replace('}', '') if '{' in p else p.capitalize() for p in path_parts]
    # Join the parts with CamelCase or snake_case format
    function_name = ''.join(name_parts)
    name = method.lower() + function_name.capitalize()
    return name


def resolve_schema(schema, parser):
    if '$ref' in schema:
        ref_path = schema['$ref'].split('/')
        ref = parser.specification
        for path in ref_path[1:]:
            ref = ref[path]
        return resolve_schema(ref, parser)
    
    resolved_schema = {}
    jdump = json.dumps(schema)
    if 'type' in schema:
        resolved_schema['type'] = schema['type']
    if 'properties' in schema:
        resolved_schema['properties'] = {}
        for prop_name, prop_attrs in schema['properties'].items():
            resolved_schema['properties'][prop_name] = resolve_schema(prop_attrs, parser)
    if 'items' in schema:
        resolved_schema['items'] = resolve_schema(schema['items'], parser)
    
    return resolved_schema

def parse_openapi(swagger_yaml):
    tools = []
    try:
        parser = ResolvingParser(spec_string=swagger_yaml)
        info = parser.specification['info']
        servers = parser.specification['servers']
        
        for path, path_content in parser.specification['paths'].items():
            for method, method_content in path_content.items():
                if method in ['get', 'put', 'post', 'delete', 'options', 'head', 'patch', 'trace']:
                    name = generate_function_name(method, path, method_content)
                    tool = {
                        "type": "function",
                        "function": {
                            'name': name,
                            'url': path,
                            'method': method,
                            'description': method_content.get('summary', method_content.get('description', '')),
                            'parameters': {},
                            'responses': {},
                            'info': info,
                            'servers': servers
                        }
                    }
                    
                    request_body = method_content.get('requestBody', {})
                    if request_body:
                        content = request_body.get('content', {})
                        for content_type, content_value in content.items():
                            schema = content_value.get('schema', {})
                            resolved_schema = resolve_schema(schema, parser)
                            tool['function']['parameters']['requestBody'] = resolved_schema
                    
                    for param in method_content.get('parameters', []):
                        if 'name' in param and 'schema' in param:
                            param_type = param['in']
                            if param_type not in tool['function']['parameters']:
                                tool['function']['parameters'][param_type] = {}
                            param_info = resolve_schema(param['schema'], parser)
                            param_info['description'] = param.get('description', '')
                            param_info['required'] = param.get('required', False)
                            tool['function']['parameters'][param_type][param['name']] = param_info
                    
                    responses = method_content.get('responses', {})
                    for status_code, response_content in responses.items():
                        if 'content' in response_content:
                            for content_type, content_value in response_content['content'].items():
                                schema = content_value.get('schema', {})
                                resolved_schema = resolve_schema(schema, parser)
                                tool['function']['responses'][status_code] = {
                                    'description': response_content.get('description', ''),
                                    'content': {
                                        content_type: resolved_schema
                                    }
                                }
                    tool_json = json.dumps(tool)
                    # print(f'tool_json: {tool_json}')
                    tools.append(tool)
    except Exception as e:
        print(str(e))
        raise HTTPException(status_code=404, detail=str(e))

    return tools

# ----------- Tools ---------------
def process_toolset(toolset, id):
    parsed_tools = parse_openapi(toolset.swagger)
    print(f'number of tools proccesed: {len(parsed_tools)}')
    for tool in parsed_tools:
        tool['function']['credentials'] = toolset.credentials.dict()
        tool['function']['toolsetId'] = id
        tool_json = json.dumps(tool, indent=2)
        print(f'tool_json: {tool_json}')

    # print(f'parsed_tools: {parsed_tools}')
    toolset_data = {
        'name': toolset.name,
        'toolsetId': id,
        'description': toolset.description,
        'created_at': toolset.created_at,
        'swagger': toolset.swagger,
        'tools': parsed_tools,
    }
    
    return toolset_data
