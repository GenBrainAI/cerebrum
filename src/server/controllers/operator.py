# src/server/controllers/operator.py
import asyncio
import json
import logging
import os
import google.generativeai as genai
from google.oauth2 import service_account
from google.auth.transport.requests import Request
from typing import List, Dict, Any
from openai import AsyncOpenAI
from anthropic import AsyncAnthropic
from groq import AsyncGroq
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from groq import AsyncGroq
import google.generativeai as genai
from google.generativeai.types import FunctionDeclaration
import re

from fastapi import HTTPException
from langchain.schema import (
    SystemMessage,
    HumanMessage,
    AIMessage,
    FunctionMessage,
)

from ..persistence.persistence_model_factory import PersistenceModelFactory
from ..models.function import Function, ResolvedSchema
from ..models.toolset import Tool
from ..controllers.curried_proxy import CurriedProxy

persistence_model = PersistenceModelFactory.persistence_model("inmemory")

class ToolsOperator:
    def __init__(self, api_provider: str = "openai"):
        self.set_api_provider(api_provider)
        # Dictionary to map between original function names and OpenAI-compatible names
        self.function_name_map = {}
        self.reverse_function_name_map = {}

    def set_api_provider(self, api_provider: str):
        self.api_provider = api_provider.lower()
        if self.api_provider == "openai":
            self.client = AsyncOpenAI(
                api_key=os.environ.get("OPENAI_API_KEY"),
                timeout=120.0  # Set 120 second timeout
            )
        elif self.api_provider == "anthropic":
            self.client = AsyncAnthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
        elif self.api_provider == "gemini":
            genai.configure(api_key=os.environ.get("GOOGLE_API_KEY"))
            self.client = genai.GenerativeModel('gemini-1.5-pro')
        elif self.api_provider == "groq":
            from groq import AsyncGroq
            self.client = AsyncGroq(api_key=os.environ.get("GROQ_API_KEY"))
        elif self.api_provider == "langchain":
            # No client initialization needed for LangChain
            self.client = None
        else:
            raise ValueError(f"Unsupported API provider: {self.api_provider}")


    async def completion(self, tasksmanager_id, task_id, messages, model, curried_proxy: CurriedProxy) -> str:
        try:
            # Add debug logging to see messages being sent to the model
            logging.info(f"===== OPERATOR COMPLETION CALLED =====")
            logging.info(f"Model: {model}")
            logging.info(f"Task ID: {task_id}")
            logging.info(f"Message count: {len(messages)}")
            for i, msg in enumerate(messages):
                if hasattr(msg, 'role') and hasattr(msg, 'content'):
                    logging.info(f"Message [{i}] - {msg.role}: {msg.content[:150]}...")
                elif isinstance(msg, dict):
                    logging.info(f"Message [{i}] - {msg.get('role')}: {msg.get('content', '')[:150]}...")
            
            if self.api_provider == "openai":
                return await self._openai_completion(model, messages, curried_proxy)
            elif self.api_provider == "anthropic":
                return await self._anthropic_completion(model, messages, curried_proxy)
            elif self.api_provider == "langchain":
                return await self._langchain_completion(model, messages, curried_proxy)
            elif self.api_provider == "groq":
                return await self._groq_completion(model, messages, curried_proxy)
            elif self.api_provider == "gemini":
                return await self._gemini_completion(model, messages, curried_proxy)
            else:
                raise ValueError(f"Unsupported API provider: {self.api_provider}")
        except Exception as e:
            detail = f"Error in completion: {e}"
            logging.error(detail)
            raise HTTPException(status_code=500, detail=detail)

    async def _openai_completion(self, model, messages, curried_proxy: CurriedProxy):
        # Get tools from curried proxy
        tools = curried_proxy.export_to_openai()
        
        # Clear previous mappings
        self.function_name_map = {}
        self.reverse_function_name_map = {}
        
        # Create OpenAI-compatible function names
        if tools:
            logging.info(f"===== REGISTERED TOOLS =====")
            logging.info(f"Available tools count: {len(tools)}")
            for i, tool in enumerate(tools):
                original_name = tool['function']['name']
                
                # Log available tools for debugging
                params_summary = {}
                if 'parameters' in tool['function']:
                    if 'properties' in tool['function']['parameters']:
                        params_summary = {k: v.get('type', 'unknown') for k, v in tool['function']['parameters'].get('properties', {}).items()}
                    
                logging.info(f"Tool [{i}]: {original_name} - {tool['function'].get('description', '')[:100]}...")
                logging.info(f"      Parameters: {params_summary}")
                
                if '.' in original_name:
                    # Replace periods with hyphens for OpenAI compatibility
                    openai_name = original_name.replace('.', '-')
                    self.function_name_map[original_name] = openai_name
                    self.reverse_function_name_map[openai_name] = original_name
                    # Update the name in the tool
                    tool['function']['name'] = openai_name
                    logging.info(f"      Renamed for OpenAI: {original_name} -> {openai_name}")
        
        messages = self._messages_to_openai(messages)

        while True:
            logging.info(f"===== SENDING REQUEST TO OPENAI =====")
            logging.info(f"Model: {model}")
            logging.info(f"Tool count: {len(tools) if tools else 0}")
            logging.info(f"Message count: {len(messages)}")
            
            response = await self.client.chat.completions.create(
                model=model,
                messages=messages,
                tools=tools if tools else None,
                tool_choice="auto" if tools else None,
                timeout=120.0  # Todo: re concider this shit, Set 120 second timeout for completion request
            )

            choice = response.choices[0]
            chat_completion_message = choice.message.content

            if choice.finish_reason in ["stop", "length"]:
                # Add the final message to the history and return it
                messages.append({'role': 'assistant', 'content': chat_completion_message})
                logging.info(f"===== COMPLETION FINISHED: {choice.finish_reason} =====")
                logging.info(f"Final response: {chat_completion_message[:150]}...")
                return chat_completion_message
            elif choice.finish_reason == "content_filter":
                # Handle content filter cases
                filtered_message = "Content filtered by model: " + chat_completion_message
                messages.append({'role': 'assistant', 'content': chat_completion_message})
                logging.info(f"===== CONTENT FILTERED =====")
                logging.info(f"Filtered message: {filtered_message[:150]}...")
                return filtered_message
            elif choice.finish_reason == "tool_calls":
                tool_calls = choice.message.tool_calls
                messages.append({'role': response.choices[0].message.role, 'tool_calls': tool_calls})
                
                # Log tool calls for debugging
                logging.info(f"===== TOOL CALLS DETECTED =====")
                logging.info(f"Number of tool calls: {len(tool_calls)}")
                
                # Prepare coroutines for all function calls
                coroutine_list = []
                for idx, tool_call in enumerate(tool_calls):
                    # Get the OpenAI-compatible function name
                    openai_function_name = tool_call.function.name
                    # Convert back to original function name if it exists in the mapping
                    original_function_name = self.reverse_function_name_map.get(openai_function_name, openai_function_name)
                    
                    try:
                        function_args = json.loads(tool_call.function.arguments)
                        # Log tool call details
                        logging.info(f"Tool Call [{idx+1}]: {original_function_name}")
                        logging.info(f"  OpenAI name: {openai_function_name}")
                        logging.info(f"  Parameters: {json.dumps(function_args, indent=2)}")
                        
                        coroutine = curried_proxy.curried_proxy(original_function_name)(function_args)
                        coroutine_list.append((tool_call, original_function_name, coroutine))
                    except json.JSONDecodeError:
                        logging.error(f"Error parsing function arguments: {tool_call.function.arguments}")
                        coroutine_list.append((tool_call, original_function_name, asyncio.sleep(0)))  # Dummy coroutine

                # Run all coroutines concurrently and wait for all responses
                responses = []
                for tool_call, original_name, coroutine in coroutine_list:
                    try:
                        logging.info(f"===== EXECUTING TOOL: {original_name} =====")
                        start_time = asyncio.get_event_loop().time()
                        result = await coroutine
                        execution_time = asyncio.get_event_loop().time() - start_time
                        
                        # Log tool execution result
                        result_preview = str(result)[:500] + "..." if len(str(result)) > 500 else str(result)
                        logging.info(f"Tool execution successful: {original_name}")
                        logging.info(f"Execution time: {execution_time:.2f} seconds")
                        logging.info(f"Result: {result_preview}")
                        
                        responses.append((tool_call, original_name, result))
                    except Exception as e:
                        logging.error(f"Error executing function {original_name}: {str(e)}")
                        import traceback
                        logging.error(traceback.format_exc())
                        error_response = {"error": str(e)}
                        logging.info(f"Returning error to model: {error_response}")
                        responses.append((tool_call, original_name, error_response))
                
                # Process each response and add it to messages
                logging.info(f"===== TOOL RESPONSES =====")
                for idx, (tool_call, original_name, function_response) in enumerate(responses):
                    if isinstance(function_response, dict) or isinstance(function_response, list):
                        response_str = json.dumps(function_response)
                    else:
                        response_str = str(function_response)

                    logging.info(f"Tool Response [{idx+1}]: {original_name}")
                    response_preview = response_str[:500] + "..." if len(response_str) > 500 else response_str
                    logging.info(f"  Response: {response_preview}")
                    
                    messages.append({
                        "role": "tool",
                        "name": tool_call.function.name,  # Keep the OpenAI-compatible name in messages
                        "tool_call_id": tool_call.id,
                        "content": response_str
                    })
                
                logging.info(f"===== TOOL EXECUTION COMPLETE =====")
                logging.info(f"Continuing conversation with {len(messages)} messages")
            else:
                raise ValueError(f"Unexpected finish reason: {choice.finish_reason}")

    async def _anthropic_completion(self, model, messages, curried_proxy: CurriedProxy):
        try:
            tools = curried_proxy.export_to_anthropic()
            anthropic_messages = self._messages_to_anthropic(messages)

            # Prepare the API call parameters
            api_params = {
                "model": model,
                "max_tokens": 1000,  # You can adjust this value as needed
                "messages": anthropic_messages,
            }

            # Only add the tools parameter if there are tools
            if tools:
                api_params["tools"] = tools

            response = await self.client.messages.create(**api_params)

            if response.content:
                return response.content[0].text
            else:
                raise ValueError("No content in Anthropic response")
        except Exception as e:
            logging.error(f"Error in Anthropic completion: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    def _messages_to_anthropic(self, messages):
        return [{"role": "user" if msg.role == "user" else "assistant", "content": msg.content} for msg in messages]

    def _messages_to_openai(self, messages):
        try:
            openai_messages = []
            for message in messages:
                openai_messages.append(
                {
                    "role": message.role,
                    "content": message.content,
                }
            )

            return openai_messages
        except Exception as e:
            logging.error(f"Error in OpenAI messages conversion: {e}")
            #print the message dictionary
            print(messages)
            raise HTTPException(status_code=500, detail=str(e))

    async def _langchain_completion(self, model: str, messages: List[Dict[str, Any]], curried_proxy: CurriedProxy) -> str:
        try:
            tools = curried_proxy.export_to_openai()  # We'll use OpenAI function format for compatibility
            
            # Clear previous mappings
            self.function_name_map = {}
            self.reverse_function_name_map = {}
            
            # Create OpenAI-compatible function names
            if tools:
                for tool in tools:
                    original_name = tool['function']['name']
                    if '.' in original_name:
                        # Replace periods with hyphens for OpenAI compatibility
                        openai_name = original_name.replace('.', '-')
                        self.function_name_map[original_name] = openai_name
                        self.reverse_function_name_map[openai_name] = original_name
                        # Update the name in the tool
                        tool['function']['name'] = openai_name
                        
            langchain_messages = self._convert_messages_to_langchain(messages)

            # Create the appropriate LangChain chat model based on the model name
            if model.startswith("gpt-"):
                llm = ChatOpenAI(model_name=model, temperature=0)
            elif model.startswith("claude-"):
                llm = ChatAnthropic(model=model)
            else:
                raise ValueError(f"Unsupported model for LangChain: {model}")

            # Create a ChatPromptTemplate from the messages
            prompt = ChatPromptTemplate.from_messages(langchain_messages)

            # Create a chain
            chain = prompt | llm | StrOutputParser()

            full_response = ""
            async for chunk in chain.astream({"tools": tools}):
                full_response += chunk

                # Check if the response contains function calls
                if "function_call" in full_response:
                    function_call_match = re.search(r'{"name": "(.*?)", "arguments": (.*?)}', full_response)
                    if function_call_match:
                        openai_function_name = function_call_match.group(1)
                        # Convert back to original function name if it exists in the mapping
                        original_function_name = self.reverse_function_name_map.get(openai_function_name, openai_function_name)
                        function_args = json.loads(function_call_match.group(2))

                        # Execute the function with the original name
                        result = await curried_proxy.curried_proxy(original_function_name)(function_args)

                        # Add the function result to the messages
                        langchain_messages.append(FunctionMessage(content=json.dumps(result), name=openai_function_name))

                        # Continue the conversation with the function result
                        prompt = ChatPromptTemplate.from_messages(langchain_messages)
                        chain = prompt | llm | StrOutputParser()
                        full_response = ""
                        continue

            return full_response.strip()
        except Exception as e:
            logging.error(f"Error in LangChain completion: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    def _convert_messages_to_langchain(self, messages: List[Any]) -> List[Any]:
        langchain_messages = []
        for message in messages:
            if message.role == "system":
                langchain_messages.append(SystemMessage(content=message.content))
            elif message.role == "user":
                langchain_messages.append(HumanMessage(content=message.content))
            elif message.role == "assistant":
                langchain_messages.append(AIMessage(content=message.content))
            elif message.role == "function":
                langchain_messages.append(FunctionMessage(content=message.content, name=message.name))
        return langchain_messages

    async def _groq_completion(self, model: str, messages: List[Dict[str, Any]], curried_proxy: CurriedProxy) -> str:
        try:
            tools = curried_proxy.export_to_openai()  # We'll use OpenAI function format for compatibility
            
            # Clear previous mappings
            self.function_name_map = {}
            self.reverse_function_name_map = {}
            
            # Create OpenAI-compatible function names
            if tools:
                for tool in tools:
                    original_name = tool['function']['name']
                    if '.' in original_name:
                        # Replace periods with hyphens for OpenAI compatibility
                        openai_name = original_name.replace('.', '-')
                        self.function_name_map[original_name] = openai_name
                        self.reverse_function_name_map[openai_name] = original_name
                        # Update the name in the tool
                        tool['function']['name'] = openai_name
            
            groq_messages = self._messages_to_openai(messages)  # Reuse OpenAI format

            # Prepare the function descriptions for Groq
            functions = [tool['function'] for tool in tools] if tools else None

            response = await self.client.chat.completions.create(
                model=model or "llama3-8b-8192",  # Groq's Llama3-8b-8192 model
                messages=groq_messages,
                functions=functions
            )

            return await self._process_llm_response(response, curried_proxy, groq_messages)
        except Exception as e:
            logging.error(f"Error in Groq completion: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    async def _process_llm_response(self, response, curried_proxy, messages):
        choice = response.choices[0]
        message = choice.message

        if hasattr(message, 'function_call') and message.function_call:
            function_call = message.function_call
            openai_function_name = function_call.name
            # Convert back to original function name if it exists in the mapping
            original_function_name = self.reverse_function_name_map.get(openai_function_name, openai_function_name)
            function_args = json.loads(function_call.arguments)

            # Execute the function with the original name
            result = await curried_proxy.curried_proxy(original_function_name)(function_args)

            # Add the function result to the messages
            new_message = {"role": "function", "name": openai_function_name, "content": json.dumps(result)}

            # Continue the conversation with the function result
            return await self.completion(
                tasksmanager_id=None,  # We don't need these for recursive calls
                task_id=None,
                messages=messages + [new_message],
                model="llama3-8b-8192",
                curried_proxy=curried_proxy
            )
        else:
            return message.content

    async def _gemini_completion(self, model: str, messages: List[Dict[str, Any]], curried_proxy: CurriedProxy) -> str:
        try:
            tools = curried_proxy.export_to_openai()  # We'll use OpenAI function format for compatibility

            # Clear previous mappings
            self.function_name_map = {}
            self.reverse_function_name_map = {}
            
            # Create OpenAI-compatible function names
            if tools:
                for tool in tools:
                    original_name = tool['function']['name']
                    if '.' in original_name:
                        # Replace periods with hyphens for OpenAI compatibility
                        openai_name = original_name.replace('.', '-')
                        self.function_name_map[original_name] = openai_name
                        self.reverse_function_name_map[openai_name] = original_name
                        # Update the name in the tool
                        tool['function']['name'] = openai_name

            # Convert OpenAI tools format to Gemini's FunctionDeclaration
            gemini_tools = [
                FunctionDeclaration(
                    name=tool['function']['name'],
                    description=tool['function'].get('description', ''),
                    parameters=tool['function']['parameters']
                ) for tool in tools
            ]

            # Convert messages to Gemini format
            gemini_messages = []
            for message in messages:
                if message.role == 'system':
                    gemini_messages.append({"role": "user", "parts": [{"text": message.content}]})
                else:
                    gemini_messages.append({"role": message.role, "parts": [{"text": message.content}]})

            # Create a chat session
            chat = self.client.start_chat(history=gemini_messages)

            # Send the last message and get the response
            response = await asyncio.to_thread(
                chat.send_message,
                gemini_messages[-1]['parts'][0]['text'],
                tools=gemini_tools
            )
            return await self._process_gemini_response(response, curried_proxy, gemini_messages)
        except Exception as e:
            logging.error(f"Error in Gemini completion: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    async def _process_gemini_response(self, response, curried_proxy, gemini_messages):
        if response.candidates[0].content.parts[0].function_call:
            function_call = response.candidates[0].content.parts[0].function_call
            openai_function_name = function_call.name
            # Convert back to original function name if it exists in the mapping
            original_function_name = self.reverse_function_name_map.get(openai_function_name, openai_function_name)
            function_args = json.loads(function_call.args)

            # Execute the function with the original name
            result = await curried_proxy.curried_proxy(original_function_name)(function_args)

            # Add the function result to the messages
            gemini_messages.append({"role": "function", "parts": [{"text": json.dumps(result)}], "name": openai_function_name})

            # Continue the conversation with the function result
            chat = self.client.start_chat(history=gemini_messages)
            follow_up_response = await asyncio.to_thread(
                chat.send_message,
                "Please continue based on the function result."
            )
            return follow_up_response.text
        else:
            return response.text
