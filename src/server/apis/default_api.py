import json
from typing import Optional

from fastapi import (
    APIRouter,
    Form,
    Path,
    status,
    UploadFile, File
)
from fastapi.exceptions import HTTPException
from starlette.responses import Response

from src.server.controllers import openapi
from src.server.models.toolset_credentials import ToolsetCredentials
from ..controllers.persistence_controller import load_from_storage, save_to_storage
from ..models.error import Error
from ..models.function import Function, ResolvedSchema, ParameterSchema, ResponseContent, ServerInfo, Info
from ..models.persistence_models import StorageLocation
from ..models.toolset import Toolset, Tool
from ..persistence.persistence_model_factory import PersistenceModelFactory
from ..utils.task_utils import generate_tools_by_ids
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


def create_toolset_X(credentials, name, description, swagger_content):
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
    toolset = openapi.process_toolset(persisted_toolset, persisted_toolset.id)

    persisted_toolset.tool_ids = []
    for tool in toolset['tools']:
        try:
            new_tool = persistence_model.tools.create(Tool(**tool))
            print(f"new_tool: {new_tool}")
            persisted_toolset.tool_ids.append(new_tool.id)
        except Exception as e:
            print("Error" + str(e))

    return persisted_toolset


def create_toolset(credentials, name, description, swagger_content):
    credentials_dict = json.loads(credentials)
    toolset_credentials = ToolsetCredentials(**credentials_dict)

    toolset_data = {
        "name": name,
        "description": description,
        "credentials": toolset_credentials,
        "swagger": swagger_content
    }

    toolset = Toolset(**toolset_data)
    persisted_toolset = persistence_model.toolsets.create(toolset)
    parsed_tools = openapi.parse_openapi(persisted_toolset.swagger)

    persisted_toolset.tool_ids = []
    for parsed_tool in parsed_tools:
        try:
            function_data = parsed_tool['function']

            # Convert parameters
            parameters = {}
            for param_type, param_value in function_data['parameters'].items():
                if param_type == 'requestBody':
                    parameters[param_type] = ResolvedSchema.parse_obj(param_value)
                else:
                    parameters[param_type] = {
                        name: ParameterSchema(name=name, in_=param_type, **param_info)
                        for name, param_info in param_value.items()
                    }

            # Convert responses
            responses = {
                status: ResponseContent(
                    description=resp_data['description'],
                    content={
                        content_type: {
                            'schema': ResolvedSchema.parse_obj(content_schema)
                        }
                        for content_type, content_schema in resp_data['content'].items()
                    }
                )
                for status, resp_data in function_data['responses'].items()
            }

            function = Function(
                name=function_data['name'],
                url=function_data['url'],
                method=function_data['method'],
                description=function_data['description'],
                parameters=parameters,
                responses=responses,
                info=Info(**function_data['info']),
                servers=[ServerInfo(**s) for s in function_data['servers']],
                credentials=toolset_credentials,
                toolsetId=persisted_toolset.id
            )

            new_tool = persistence_model.tools.create(Tool(function=function, type="function"))
            persisted_toolset.tool_ids.append(new_tool.id)
        except Exception as e:
            print(f"Error creating tool: {str(e)}")

    return persisted_toolset


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
) -> Response:
    if swagger_file:
        content = await swagger_file.read()
        swagger_content = content.decode("utf-8")
    elif swagger_str:
        swagger_content = swagger_str
    else:
        raise HTTPException(status_code=400, detail="Swagger definition is required.")

    try:
        persisted_toolset = create_toolset(credentials, name, description, swagger_content)
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


@router.get("/toolsets", status_code=status.HTTP_200_OK)
async def get_toolsets(
) -> Toolset:
    try:
        return persistence_model.toolsets.list()
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
