# src/server/controllers/operator.py
import asyncio
import json
import logging
import os
from typing import List, Dict, Any
from openai import AsyncOpenAI
from anthropic import AsyncAnthropic
from fastapi import HTTPException

from ..persistence.persistence_model_factory import PersistenceModelFactory
from ..models.function import Function, ResolvedSchema
from ..models.toolset import Tool
from ..controllers.curried_proxy import CurriedProxy

persistence_model = PersistenceModelFactory.persistence_model("inmemory")

class ToolsOperator:
    def __init__(self, api_provider: str = "openai"):
        self.set_api_provider(api_provider)

    def set_api_provider(self, api_provider: str):
        self.api_provider = api_provider.lower()
        if self.api_provider == "openai":
            openai_api_key = os.environ.get("OPENAI_API_KEY")
            if not openai_api_key:
                raise ValueError("OPENAI_API_KEY not found in environment variables")
            self.client = AsyncOpenAI(api_key=openai_api_key)
        elif self.api_provider == "anthropic":
            anthropic_api_key = os.environ.get("ANTHROPIC_API_KEY")
            if not anthropic_api_key:
                raise ValueError("ANTHROPIC_API_KEY not found in environment variables")
            self.client = AsyncAnthropic(api_key=anthropic_api_key)
        else:
            raise ValueError(f"Unsupported API provider: {self.api_provider}")

    async def completion(self, tasksmanager_id, task_id, messages, model, curried_proxy: CurriedProxy) -> str:
        try:
            if self.api_provider == "openai":
                return await self._openai_completion(model, messages, curried_proxy)
            elif self.api_provider == "anthropic":
                return await self._anthropic_completion(model, messages, curried_proxy)
            else:
                raise ValueError(f"Unsupported API provider: {self.api_provider}")
        except Exception as e:
            logging.error(f"Error in completion: {e}")
            raise HTTPException(status_code=500, detail="Error in completion")

    async def _openai_completion(self, model, messages, curried_proxy: CurriedProxy):
        tools = curried_proxy.export_to_openai()
        messages = self._messages_to_openai(messages)

        while True:
            response = await self.client.chat.completions.create(
                model=model,
                messages=messages,
                tools=tools,
                tool_choice="auto"
            ) if tools else await self.client.chat.create(
                model=model,
                messages=messages
            )
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
            elif choice.finish_reason == "tool_calls":
                tool_calls = choice.message.tool_calls
                messages.append({'role': response.choices[0].message.role, 'tool_calls': tool_calls})
                # Prepare coroutines for all function calls
                coroutine_list = []
                tool_calls = choice.message.tool_calls
                for tool_call in tool_calls:
                    function_name = tool_call.function.name
                    function_args = json.loads(tool_call.function.arguments)
                    coroutine = curried_proxy.curried_proxy(function_name)(function_args)
                    coroutine_list.append(coroutine)

                # Run all coroutines concurrently and wait for all responses
                responses = await asyncio.gather(*coroutine_list)
                # Process each response and add it to messages
                for tool_call, function_response in zip(tool_calls, responses):
                    if isinstance(function_response, dict) or isinstance(function_response, list):
                        response_str = json.dumps(function_response)
                    else:
                        response_str = str(function_response)

                    messages.append({
                        "role": "tool",
                        "name": tool_call.function.name,
                        "tool_call_id": tool_call.id,
                        "content": response_str
                    })
            else:
                raise ValueError(f"Unexpected finish reason: {choice.finish_reason}")

    async def _anthropic_completion(self, model, messages, curried_proxy: CurriedProxy):
        tools = curried_proxy.export_to_anthropic()
        
        while True:
            response = await self.client.messages.create(
                model=model,
                messages=messages,
                tools=tools
            )
            
            choice = response.content[0]
            if choice.type == "text":
                return choice.text
            elif choice.type == "tool_calls":
                for tool_call in choice.tool_calls:
                    function_name = tool_call.name
                    function_args = tool_call.parameters
                    result = await curried_proxy.curried_proxy(function_name)(function_args)
                    messages.append({
                        "role": "tool",
                        "content": json.dumps(result),
                        "name": function_name
                    })
            else:
                raise ValueError(f"Unexpected content type: {choice.type}")

    def _messages_to_openai(self, messages):
        openai_messages = []
        for message in messages:
            openai_messages.append(
                {
                    "role": message.role,
                    "content": message.content,
                }
            )

        return openai_messages
