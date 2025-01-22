import csv
import importlib
import io
import json
import os

import yaml
from ..models.custom_exceptions import UnsupportedTaskTypeError, ExtractModeError



def get_openai_tools(persistence_model, task, autobot):
    """
    Gathers and prepares the OpenAI toolsets for the given task and autobot.

    :param persistence_model: The persistence model handling data access.
    :param task: The task object.
    :param autobot: The autobot object.
    :return: A tuple containing tools and a dictionary of functions.
    """

    toolsets_ids = set()
    if task.toolsets is not None:
        toolsets_ids.update(task.toolsets)

    if autobot.toolsets is not None:
        toolsets_ids.update(autobot.toolsets)

    return generate_tools_by_ids(persistence_model, toolsets_ids)


def generate_tools_by_ids(persistence_model, toolsets_ids):
    functions_dict = {}
    for index, toolset_id in enumerate(toolsets_ids):
        toolset = persistence_model.toolsets.read(toolset_id)
        if toolset is None:
            print("Couldn't fine toolset for ID# " + str(toolset_id))
            continue
        for tid in toolset.tool_ids:
            tool = persistence_model.tools.read(tid)
            if tool.type != 'function':
                continue
            function = tool.function
            fname = f"fn{index}_{function.name}"
            functions_dict[fname] = function.model_dump()
            functions_dict[fname]["tool_id"] = tid
    if len(functions_dict) > 0:
        tools = transform_functions_for_openai(functions_dict)
        return tools, functions_dict
    else:
        return [], {}


def transform_functions_for_openai(functions_dict):
    """
    Transforms function definitions into a schema suitable for OpenAI tools.

    :param functions_dict: A dictionary of functions to transform.
    :return: A list of transformed function definitions.
    """
    transformed_functions = []
    for fname, function in functions_dict.items():
        simplified_params = {
            'type': 'object',
            'properties': {},
            'required': []}

        if 'requestBody' in function['parameters']:
            request_body = function['parameters']['requestBody']
            request_body_json = json.dumps(request_body)
            print(f'request_body_json: {request_body_json}')
            simplified_params['properties']['requestBody'] = transform_schema(request_body)
            simplified_params_json = json.dumps(simplified_params)
            print(f'simplified_params_json: {simplified_params_json}')

        for param_type in ['query', 'header', 'path']:
            for param_name, param_info in function['parameters'].get(param_type, {}).items():
                simplified_params['properties'][param_name] = transform_schema(param_info)
                if param_info.get('required', False):
                    simplified_params['required'].append(param_name)

        transformed_functions.append({
            "type": "function",
            "function": {
                'name': fname,
                'description': function.get('description', ''),
                'parameters': simplified_params,
            }
        })

    return transformed_functions


def transform_schema(schema):
    """
    Recursively transforms a schema into a simpler, OpenAI-compatible format.

    :param schema: The schema to transform.
    :return: The transformed schema.
    """
    if schema.get('type') == 'object' and 'properties' in schema:
        transformed_properties = {}
        for prop_name, prop_info in schema['properties'].items():
            transformed_properties[prop_name] = transform_schema(prop_info)
        return {
            'type': 'object',
            'properties': transformed_properties,
            'required': schema.get('required', [])
        }
    elif schema.get('type') == 'array' and 'items' in schema:
        return {
            'type': 'array',
            'items': transform_schema(schema['items'])
        }
    else:
        return {
            'type': schema.get('type', 'string'),
            'description': schema.get('description', '')
        }



def extract_code_segment(text, mode):
    """
    Extracts code data from a string based on specified code type within markers like ```code_type ... ```.

    Parameters:
    - text (str): A string containing code data encapsulated within ```code_type ... ``` markers.
    - code_type (str): The type of code to extract ('yaml', 'json', 'python', 'xml', 'csv', 'markdown').

    Returns:
    - Depending on code_type:
        - dict, list, or str if YAML, JSON, Python, XML, or Markdown.
        - list of dicts if CSV.
    - None: If extraction or decoding fails, or if the code type is not recognized.
    """
    try:
        start_marker = f"```{mode}"
        end_marker = "```"
        start_index = text.find(start_marker) + len(start_marker)
        if start_index == -1 + len(start_marker):
            return None  # Start marker not found

        end_index = text.find(end_marker, start_index)
        if end_index == -1:
            return None  # End marker not found

        code_str = text[start_index:end_index].strip()

        if mode == 'yaml':
            try:
                return yaml.safe_load(code_str)
            except yaml.YAMLError:
                return None
        elif mode == 'json':
            try:
                return json.loads(code_str)
            except json.JSONDecodeError:
                try:
                    return json.loads("{" + code_str + "}")
                except json.JSONDecodeError:
                    return None
        elif mode == 'python':
            return code_str  # Returning Python code as string; execution or further processing is not handled here.
        elif mode == 'xml':
            # TOFDO: Fix this
            # try:
            #     return ET.fromstring(code_str)  # Returns an ElementTree element
            # except ET.ParseError:
            return None
        elif mode == 'csv':
            try:
                reader = csv.DictReader(io.StringIO(code_str))
                return list(reader)  # Returns list of dictionaries
            except csv.Error:
                return None
        elif mode == 'markdown':
            return code_str  # Markdown is returned as a string; rendering is not handled here.
        else:
            return None  # Code type not supported
    except Exception as e:
        ExtractModeError(mode=mode, response=text)


def find_file(file_base_loc: str, limit: int = 2):
    output_path = file_base_loc
    for i in range(0, limit):
        if os.path.isfile(output_path):
            return output_path
        else:
            output_path = os.path.join("..", output_path)
    raise Exception(f"{file_base_loc} not found")
