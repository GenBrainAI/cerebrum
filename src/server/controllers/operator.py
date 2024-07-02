import asyncio
import json
import logging
import os
import re
from typing import List, Dict, Any, Callable
from typing import Optional, AsyncIterable
from dotenv import load_dotenv

import httpx
from openai import OpenAI
from fastapi import HTTPException

from typing import Dict
from pydantic import BaseModel

from src.server.controllers.rest_proxy_controller import RestProxyController
from ..persistence.persistence_model_factory import PersistenceModelFactory
from ..models.function import Function, ResolvedSchema
from ..models.toolset import Tool

load_dotenv()

persistence_model = PersistenceModelFactory.persistence_model("inmemory")

def transform_schema_pydantic(schema: ResolvedSchema) -> Dict:
    if schema.type == 'object' and schema.properties:
        transformed_properties = {
            prop_name: transform_schema_pydantic(prop_schema)
            for prop_name, prop_schema in schema.properties.items()
        }
        return {
            'type': 'object',
            'properties': transformed_properties,
            'required': schema.required or []
        }
    elif schema.type == 'array' and schema.items:
        return {
            'type': 'array',
            'items': transform_schema_pydantic(schema.items)
        }
    else:
        return {
            'type': schema.type or 'string',
            'description': schema.description or ''
        }
 
def transform_functions_for_openai(functions_dict: Dict[str, Tool]) -> List[Dict]:
    transformed_functions = []
    for fname, tool in functions_dict.items():
        function: Function = tool.function
        simplified_params = {
            'type': 'object',
            'properties': {},
            'required': []
        }

        if 'requestBody' in function.parameters:
            request_body = function.parameters['requestBody']
            simplified_params['properties']['requestBody'] = transform_schema_pydantic(request_body)

        for param_type in ['query', 'header', 'path']:
            if param_type in function.parameters:
                for param_name, param_info in function.parameters[param_type].items():
                    simplified_params['properties'][param_name] = transform_schema_pydantic(param_info.schema)
                    if param_info.required:
                        simplified_params['required'].append(param_name)

        transformed_functions.append({
            "type": "function",
            "function": {
                'name': fname,
                'description': function.description,
                'parameters': simplified_params,
            }
        })

    return transformed_functions


def get_task_tools(tasksmanager_id: str, task_id: str):
    functions_dict = {}
    toolsets_ids = set()
    task = persistence_model.tasks.read(task_id)
    toolsets_ids.update(task.toolsets)

    tasksmanager = persistence_model.tasksmanagers.read(tasksmanager_id)
    tasksmanager_tools = tasksmanager.toolsets
    toolsets_ids.update(tasksmanager_tools)

    for index, toolset_id in enumerate(toolsets_ids):
        toolset = persistence_model.toolsets.read(toolset_id)
        for tid in toolset.tool_ids:
            tool = persistence_model.tools.read(tid)
            if tool.type != 'function':
                continue
            fname = f"fn{index}_{tool.function.name}"
            functions_dict[fname] = tool
    
    tools = transform_functions_for_openai(functions_dict)
    return tools, functions_dict


def messages_to_openai(messages):
    openai_messages = []
    for message in messages:
      openai_messages.append(
          {
              "role": message.role,
              "content": message.content,
          }
      )

    return openai_messages


class ToolsOperator:
    client: OpenAI

    def __init__(self):
        self.client = OpenAI(
            api_key = os.environ.get("OPENAI_API_KEY"),
        )
        self.proxy = RestProxyController()


    async def multiset_proxy(self, name, arguments, functions_dict):
        return await self.proxy.multiset_proxy(name, arguments, functions_dict)

    async def completion(self, tasksmanager_id, task_id, session_messages, model = None) -> str:

      tasksmanager = persistence_model.tasksmanagers.read(tasksmanager_id)
      model = model or tasksmanager.model
      task = persistence_model.tasks.read(task_id)

      # Todo merge tools and settings
      tools, functions_dict = get_task_tools(tasksmanager_id, task_id)

      messages = tasksmanager.messages
      messages += task.messages
      messages += session_messages
      messages = messages_to_openai(messages)

      # Initial API call
      try:
        response = self.client.chat.completions.create(
            model=model,
            messages=messages,
            tools=tools,
            tool_choice="auto",
        )

        # Loop to handle the responses
        while True:
            choice = response.choices[0]
            chat_completion_message = choice.message.content

            if choice.finish_reason in ["stop", "length"]:
                # Add the final message to the history and return it
                messages.append({'role': 'assistant', 'content': chat_completion_message})
                return chat_completion_message
            elif choice.finish_reason == "content_filter":
                # Handle content filter cases
                filtered_message = "Content filtered by model: " + chat_completion_message
                messages.append({'role': 'assistant', 'content': chat_completion_message})
                return filtered_message
            elif choice.finish_reason == "function_call":
                # Handle deprecated function calls
                raise Exception("Function call is deprecated and not supported")
            elif choice.finish_reason == "tool_calls":
                tool_calls = choice.message.tool_calls
                messages.append({'role': response.choices[0].message.role, 'tool_calls': tool_calls})
                # Prepare coroutines for all function calls
                coroutine_list = []
                for tool_call in tool_calls:
                    function_name = tool_call.function.name
                    function_args = json.loads(tool_call.function.arguments)
                    coroutine = self.multiset_proxy(function_name, function_args, functions_dict)
                    coroutine_list.append(coroutine)

                # Run all coroutines concurrently and wait for all responses
                responses = await asyncio.gather(*coroutine_list)
                # Process each response and add it to messages
                for tool_call, function_response in zip(tool_calls, responses):
                    if isinstance(function_response, dict) or isinstance(function_response, list):
                        response_str = json.dumps(function_response)
                    else:
                        response_str = str(function_response)

                    messages.append(
                        {
                            "role": "tool",
                            "name": tool_call.function.name,
                            "tool_call_id": tool_call.id,
                            "content": response_str,
                        }
                    )

                # Make the next API call with the updated messages
                response = self.client.chat.completions.create(
                    model=model,
                    messages=messages,
                    tools=tools,
                    tool_choice="auto",
                )
      except Exception as e:
        logging.error(f"Error in completion: {e}")
        raise HTTPException(status_code=500, detail="Error in completion")

