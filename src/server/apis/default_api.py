import json
from datetime import datetime

from typing import Dict, List, Optional, Any

import importlib
import pkgutil
from fastapi.exceptions import HTTPException


from fastapi import (
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
    UploadFile, File
)
from pydantic import ValidationError
from starlette.responses import Response

from ..utils.serialization import CustomEncoder

from src.server.controllers import openapi
from src.server.models.toolset_credentials import ToolsetCredentials

from ..models.extra_models import TokenModel
from ..models.tasks_manager import TasksManager
from ..models.error import Error
from ..models.list_tasks_managers import ListTasksManagers
from ..models.task import Task
from ..models.toolset import Toolset
from ..models.persistence_models import StorageLocation
from ..controllers.persistence_controller import load_from_storage, save_to_storage
from ..persistence.persistence_model_factory import PersistenceModelFactory

router = APIRouter()

persistence_model = PersistenceModelFactory.persistence_model("inmemory")

@router.get(
    "/health_check",
    responses={
        200: {"description": "All OK"},
        500: {"model": Error, "description": "Huston we have a problem"},
    },
    tags=["default"],
    summary="Check service if it&#39;s all good",
    response_model_by_alias=True,
)
async def health_check(
) -> None:
  return "All OK"


@router.post(
    "/toolsets",
    responses={
        201: {"model": Toolset, "description": "Global toolset created successfully."},
        400: {"model": Error, "description": "Invalid request data or validation error."},
        401: {"model": Error, "description": "Unauthorized - authentication is required to access this endpoint."},
        500: {"model": Error, "description": "Internal server error."},
    },
    tags=["default"],
    summary="Create a new global toolset.",
    response_model_by_alias=True,
)
async def create_global_toolset(
    name: str = Form(...),
    description: str = Form(...),
    credentials: str = Form(...),
    swagger_file: Optional[UploadFile] = File(None),
    swagger_str: Optional[str] = Form(None)
) -> Toolset:
    if swagger_file:
        content = await swagger_file.read()
        swagger_content = content.decode("utf-8")
    elif swagger_str:
        swagger_content = swagger_str
    else:
        raise HTTPException(status_code=400, detail="Swagger definition is required.")
    
    try:
        # Parse the credentials JSON string into a Python dict
        credentials_dict = json.loads(credentials)
        # Create a ToolsetCredentials object from the dict
        toolset_credentials = ToolsetCredentials(**credentials_dict)

        toolset_data = {
            "name": name,
            "description": description,
            "credentials": toolset_credentials,
            "swagger": swagger_content
        }

        toolset = Toolset(**toolset_data)
        persisted_toolset = persistence_model.toolsets.create(toolset)
        fn_toolset = openapi.process_toolset(persisted_toolset, persisted_toolset.id)
        
        persisted_toolset.tool_ids = []
        for fn_tool in fn_toolset['tools']:
            try:
                pfn = persistence_model.tools.create(fn_tool)
                persisted_toolset.tool_ids.append(pfn['id'])

            except Exception as e:
                print(str(e))
        return Response(
            content=persisted_toolset.json(),
            status_code=status.HTTP_201_CREATED,
            media_type="application/json",
        )
    except Exception as e:
        print(str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/toolsets/{id}",
    responses={
        200: {"model": Toolset, "description": "Toolset requsted by id"},
        400: {"model": Error, "description": "Bad request"},
        401: {"model": Error, "description": "Unauthorized"},
        404: {"model": Error, "description": "TasksManager not found"},
    },
    tags=["default"],
    summary="get toolset details",
    response_model_by_alias=True,
)
async def get_toolsets(
    id: str = Path(..., description="ID of the tasksmanager to retrieve"),
) -> Toolset:
    try:
        return persistence_model.toolsets.read(id)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@router.post(
    "/generate_tools/{toolset_id}",
    responses={
        200: {"model": Toolset, "description": "generate tools by id"},
        400: {"model": Error, "description": "Bad request"},
        401: {"model": Error, "description": "Unauthorized"},
        404: {"model": Error, "description": "Toolset not found"},
    },
    tags=["default"],
    summary="generates tools",
    response_model_by_alias=True,
)

async def generate_tools(
    toolset_id: str = Path(..., description="ID of the toolsets"),
) -> Response:
    try:
        tools, funcs = generate_tools_by_ids(persistence_model, toolsets_ids={toolset_id})
        return tools
    except Exception as e:
        print(f"From /generate_tools: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@router.post("/state/save", status_code=status.HTTP_201_CREATED)
async def save_state(storage: StorageLocation):
    message = save_to_storage(storage)
    return Response(
        content=message,
        status_code=status.HTTP_201_CREATED,
        media_type="application/json",
    )

@router.post("/state/load", status_code=status.HTTP_200_OK)
async def load_state(storage: StorageLocation, return_as_json: Optional[bool] = True):
    message = load_from_storage(storage)
    if return_as_json:
        return Response(
            content=message,
            status_code=status.HTTP_201_CREATED,
            media_type="application/json",
        )
    else:
        return Response(
            content={"message": "State saved elsewhere as per config"},
            status_code=status.HTTP_201_CREATED,
            media_type="application/json",
    )
