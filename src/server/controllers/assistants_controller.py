
import asyncio
import json
import os
import httpx
from openai import AsyncOpenAI
from datetime import datetime
import logging

from src.server.models.tasks_manager import TasksManager
from ..persistence.persistence_model_factory import PersistenceModelFactory
from .rest_proxy_controller import RestProxyController

class AssistantsController:
    def __init__(self, openai_api_key):
        self.client = AsyncOpenAI(api_key=os.environ.get("OPENAI_API_KEY", openai_api_key))
        self.persistence = PersistenceModelFactory.persistence_model()
        self.proxy = RestProxyController()

    async def async_function_proxy(self, name, arguments, settings):
      return await self.proxy.multiset_proxy(name, arguments, settings)

    async def create_assistant(self, tasksmanager_id, model, name, deprecation, instructions, tools_id, file_ids, metadata=None):
        tools = await self.retrieve_tools(tools_id)
        assistant = await self.client.beta.assistants.create(
            model=model,
            name=name,
            description=deprecation,
            instructions=instructions,
            tools=tools['functions'],
            file_ids=file_ids,
            metadata=metadata
        )
        assistant_id = assistant.id
        await self.upsert_assistant(assistant_id, tasksmanager_id, tools_id, assistant)
        return assistant

    async def delete_assistant(self, assistant_id):
        self.client.beta.assistants.delete(assistant_id=assistant_id)
        self.persistence.collection("assistant").delete(assistant_id)

    async def upsert_assistant(self, assistant_id, tasksmanager_id, tools_id, assistant):
        tasksmanager = TasksManager(
            id=assistant_id,
            tasksmanager_id=tasksmanager_id,
            tools_id=tools_id,
            created_at=datetime.utcnow(),
            assistant=assistant
        )
        self.persistence.tasksmanagers.update(assistant_id, tasksmanager)
        logging.info(f"Stored tasksmanager_id: {tasksmanager_id} for assistant_id: {assistant_id}")

    async def retrieve_assistant(self, assistant_id):
        response = await self.client.beta.assistants.retrieve(assistant_id=assistant_id)
        return response

    async def add_file(self, tasksmanager_id, file, name):
        """
        Add a file to the assistant.
        """
        file_object = await self.client.files.create(
            file=file,
            purpose="assistants"
        )
        file_id = self.persistence.collection("files").create(file_object.id, file_object)
        return file_id

    # Updated to reflect the Assistant's API capabilities
    async def create_thread(self, tasksmanager_id, messages):
        # Create a new thread for the specified assistant
        thread = await self.client.beta.threads.create(messages=messages)
        """
        Store the data in Firestore for a given assistant.
        """
        thread_id = self.persistence.collection('threads').crate(thread.id, thread)
        return thread_id

    async def delete_thread(self, thread_id):
        self.client.beta.threads.delete(
            thread_id=thread_id
        )
        self.persistence.collection('threads').delete(thread_id)

    async def create_message(self, tasksmanager_id, thread_id, role, content, file_ids):
        """
        Send a prompt to the thread and update Firestore record.
        """
        message = await self.client.beta.threads.messages.create(
            thread_id=thread_id,
            role=role,
            content=content,
            file_ids=file_ids
        )

        self.persistence.collection('messages').document(message.id, message)
        return message

    async def create_thread_and_run(self, tasksmanager_id, assistant_id, instructions, model, tools_id=None):
        """
        Create a thread and run it. pay attention that the thread should contain messages.
        """
        tools = None
        if tools_id is None:
            tools = None
        else:
            tools = await self.retrieve_tools(tools_id)
            tools = tools['functions']

        run = await self.client.beta.threads.create_and_run(
            assistant_id=assistant_id,
            instructions=instructions,
            model=model,
            tools=tools
        )

        self.persistance.collection('runs').create(run.id, {
            'tasksmanager_id': tasksmanager_id,
            'tools_id': tools_id,
            'thred_id': run.thread_id,
            'run_id': run.id,
            'assistant_id': assistant_id,
            'created_at': datetime.utcnow().isoformat(),
            'running': True,
            'run': run
        })
        return await self.handle_tools_actions(run, tools, run.thread_id)

    async def create_run(self, tasksmanager_id, thread_id, assistant_id, instructions, model, tools_id):
        """
        Create a thread and run it. pay attention that the thread should contain messages.
        """
        tools = await self.retrieve_tools(tools_id)
        run = await self.client.beta.threads.runs.create(
            thread_id=thread_id,
            assistant_id=assistant_id,
            instructions=instructions,
            model=model,
            tools=tools['functions']
        )
        self.persistance.collection('runs').create(run.id, {
            'tasksmanager_id': tasksmanager_id,
            'assistant_id': assistant_id,
            'created_at': datetime.utcnow().isoformat(),
            'running': True,
            run: run
        })
        return await self.handle_tools_actions(run, tools, thread_id)

    async def create_message_and_run(self, tasksmanager_id, thread_id, role, content, file_ids, assistant_id, instructions,
                                    model, tools_id):
        await self.create_message(tasksmanager_id, thread_id, role, content, file_ids)
        return await self.create_thread_and_run(tasksmanager_id, assistant_id, instructions, model, tools_id)

    # Add observability to this
    async def handle_tools_actions(self, run, tools, thread_id):
        if run and tools and thread_id:
            ra = run.required_action
            while ra:
                if ra.type == 'submit_tool_outputs':
                    # All outputs must be submitted in a single request
                    tool_outputs = await self.run_tools(run.required_action.submit_tool_outputs, tools)
                    run = await self.submit_tool_outputs(thread_id, run.id, tool_outputs)
                    ra = run.required_action
                else:
                    # Print error message and break
                    print(f"Unsupported required action type: {ra.type}")
                    break
        return run

    async def submit_tool_outputs(self, thread_id, run_id, tool_outputs):
        """
        Submit the tool outputs to the thread.
        """
        run = await self.client.beta.threads.runs.submit_tool_outputs(
            thread_id=thread_id,
            run_id=run_id,
            tool_outputs=tool_outputs
        )
        return run

    async def run_tools(self, submit_tool, settings):
        """
        Run the tools required by the assistant.
        """
        coroutine_list = []
        tool_calls = submit_tool.tool_calls
        for tool in tool_calls:
            if tool.type == 'function':
                coroutine = self.async_function_proxy(tool.function, tool.arguments, settings)
                coroutine_list.append(coroutine)
            else:
                raise Exception(f"Unsupported tool type: {tool.type}")

        # Run all coroutines concurrently and wait for all responses
        responses = await asyncio.gather(*coroutine_list)
        ret_responses = []
        for tool_call, function_response in zip(tool_calls, responses):
            # Convert the response to a string, handling JSON and other types
            if isinstance(function_response, dict) or isinstance(function_response, list):
                response_str = json.dumps(function_response)
                ret_responses.append(response_str)
            else:
                response_str = str(function_response)
                ret_responses.append(response_str)

        return ret_responses

    async def retrieve_tools(self, tools_id):
        tools = self.persistence.tools.read(tools_id)
        return tools
