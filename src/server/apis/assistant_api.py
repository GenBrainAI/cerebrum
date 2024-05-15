# coding: utf-8

from typing import Dict, List  # noqa: F401
import importlib
import pkgutil


from fastapi import (  # noqa: F401
    APIRouter,
    Body,
    Cookie,
    Depends,
    Form,
    Header,
    Path,
    Query,
    Response,
    Security,
    status,
)

from src.server.models.assistant.extra_models import TokenModel  # noqa: F401
from src.server.models.assistant.add_file_request import AddFileRequest
from src.server.models.assistant.assistant_response import AssistantResponse
from src.server.models.assistant.create_assistant_request import CreateAssistantRequest
from src.server.models.assistant.create_message_and_run_request import CreateMessageAndRunRequest
from src.server.models.assistant.create_message_request import CreateMessageRequest
from src.server.models.assistant.create_run_request import CreateRunRequest
from src.server.models.assistant.create_thread_and_run_request import CreateThreadAndRunRequest
from src.server.models.assistant.create_thread_request import CreateThreadRequest
from src.server.models.assistant.file_response import FileResponse
from src.server.models.assistant.message_and_run_response import MessageAndRunResponse
from src.server.models.assistant.message_response import MessageResponse
from src.server.models.assistant.run_response import RunResponse
from src.server.models.assistant.thread_and_run_response import ThreadAndRunResponse
from src.server.models.assistant.thread_response import ThreadResponse
from src.server.models.assistant.upsert_assistant_request import UpsertAssistantRequest


router = APIRouter()


@router.post(
    "/assistant/{assistant_id}/delete",
    responses={
        204: {"description": "Assistant deleted successfully"},
    },
    tags=["default"],
    summary="Delete an assistant",
    response_model_by_alias=True,
)
async def assistant_assistant_id_delete_post(
    assistant_id: str = Path(..., description=""),
) -> None:
    ...


@router.get(
    "/assistant/{assistant_id}",
    responses={
        200: {"model": AssistantResponse, "description": "Assistant retrieved successfully"},
    },
    tags=["default"],
    summary="Retrieve an assistant",
    response_model_by_alias=True,
)
async def assistant_assistant_id_get(
    assistant_id: str = Path(..., description=""),
) -> AssistantResponse:
    ...


@router.post(
    "/assistant/{assistant_id}/upsert",
    responses={
        200: {"model": AssistantResponse, "description": "Assistant upserted successfully"},
    },
    tags=["default"],
    summary="Upsert an assistant",
    response_model_by_alias=True,
)
async def assistant_assistant_id_upsert_post(
    assistant_id: str = Path(..., description=""),
    upsert_assistant_request: UpsertAssistantRequest = Body(None, description=""),
) -> AssistantResponse:
    ...


@router.post(
    "/assistant/create",
    responses={
        200: {"model": AssistantResponse, "description": "Assistant created successfully"},
    },
    tags=["default"],
    summary="Create a new assistant",
    response_model_by_alias=True,
)
async def assistant_create_post(
    create_assistant_request: CreateAssistantRequest = Body(None, description=""),
) -> AssistantResponse:
    ...


@router.post(
    "/file/add",
    responses={
        200: {"model": FileResponse, "description": "File added successfully"},
    },
    tags=["default"],
    summary="Add a file to an assistant",
    response_model_by_alias=True,
)
async def file_add_post(
    add_file_request: AddFileRequest = Body(None, description=""),
) -> FileResponse:
    ...


@router.post(
    "/message-and-run/create",
    responses={
        200: {"model": MessageAndRunResponse, "description": "Message and thread run created successfully"},
    },
    tags=["default"],
    summary="Create a message and run a thread",
    response_model_by_alias=True,
)
async def message_and_run_create_post(
    create_message_and_run_request: CreateMessageAndRunRequest = Body(None, description=""),
) -> MessageAndRunResponse:
    ...


@router.post(
    "/message/create",
    responses={
        200: {"model": MessageResponse, "description": "Message created successfully"},
    },
    tags=["default"],
    summary="Create a message in a thread",
    response_model_by_alias=True,
)
async def message_create_post(
    create_message_request: CreateMessageRequest = Body(None, description=""),
) -> MessageResponse:
    ...


@router.post(
    "/run/create",
    responses={
        200: {"model": RunResponse, "description": "Run created successfully"},
    },
    tags=["default"],
    summary="Create a run for a thread",
    response_model_by_alias=True,
)
async def run_create_post(
    create_run_request: CreateRunRequest = Body(None, description=""),
) -> RunResponse:
    ...


@router.post(
    "/thread-and-run/create",
    responses={
        200: {"model": ThreadAndRunResponse, "description": "Thread and run created successfully"},
    },
    tags=["default"],
    summary="Create a thread and run it immediately",
    response_model_by_alias=True,
)
async def thread_and_run_create_post(
    create_thread_and_run_request: CreateThreadAndRunRequest = Body(None, description=""),
) -> ThreadAndRunResponse:
    ...


@router.post(
    "/thread/create",
    responses={
        200: {"model": ThreadResponse, "description": "Thread created successfully"},
    },
    tags=["default"],
    summary="Create a new thread for an assistant",
    response_model_by_alias=True,
)
async def thread_create_post(
    create_thread_request: CreateThreadRequest = Body(None, description=""),
) -> ThreadResponse:
    ...


@router.delete(
    "/thread/{thread_id}/delete",
    responses={
        204: {"description": "Thread deleted successfully"},
    },
    tags=["default"],
    summary="Delete a thread",
    response_model_by_alias=True,
)
async def thread_thread_id_delete_delete(
    thread_id: str = Path(..., description=""),
) -> None:
    ...
