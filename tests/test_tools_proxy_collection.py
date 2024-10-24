import pytest
from src.server.models.agent import ToolsProxyCollection, ToolsetSpec, ToolSpec, ObjectToolSpec, CreateCrewRequest, AgentModel, TaskModel, ToolModel

def test_tools_proxy_collection():
    tools_proxy_collection = ToolsProxyCollection(
        toolsets=[
            ToolsetSpec(id="toolset1", name="DevOpsTools"),
            ToolsetSpec(id="toolset2", name="SecurityTools")
        ],
        functions=[
            ToolSpec(name="custom_function1", type="function"),
            ToolSpec(name="custom_function2", type="function")
        ],
        objects=[
            ObjectToolSpec(name="github_tool", object_type="github_tool"),
            ObjectToolSpec(name="jira_tool", object_type="jira_tool")
        ]
    )

    assert len(tools_proxy_collection.toolsets) == 2
    assert len(tools_proxy_collection.functions) == 2
    assert len(tools_proxy_collection.objects) == 2

    assert tools_proxy_collection.toolsets[0].id == "toolset1"
    assert tools_proxy_collection.toolsets[1].name == "SecurityTools"

    assert tools_proxy_collection.functions[0].name == "custom_function1"
    assert tools_proxy_collection.functions[1].type == "function"

    assert tools_proxy_collection.objects[0].name == "github_tool"
    assert tools_proxy_collection.objects[1].object_type == "jira_tool"

def test_create_crew_request_with_tools_proxy_collection():
    tools_proxy_collection = ToolsProxyCollection(
        toolsets=[ToolsetSpec(id="toolset1", name="DevOpsTools")],
        functions=[ToolSpec(name="custom_function1", type="function")],
        objects=[ObjectToolSpec(name="github_tool", object_type="github_tool")]
    )

    create_crew_request = CreateCrewRequest(
        description="A crew for DevOps tasks",
        agents=[
            AgentModel(
                role="Developer",
                goal="Develop software",
                backstory="Experienced developer",
                tools=[ToolModel(name="IDE", description="Integrated Development Environment")]
            )
        ],
        tasks=[
            TaskModel(
                description="Implement a new feature",
                expected_output="Working code",
                agent_role="Developer"
            )
        ],
        tools_proxy_collection=tools_proxy_collection
    )

    assert create_crew_request.tools_proxy_collection is not None
    assert len(create_crew_request.tools_proxy_collection.toolsets) == 1
    assert len(create_crew_request.tools_proxy_collection.functions) == 1
    assert len(create_crew_request.tools_proxy_collection.objects) == 1

def test_create_crew_request_without_tools_proxy_collection():
    create_crew_request = CreateCrewRequest(
        description="A crew for DevOps tasks",
        agents=[
            AgentModel(
                role="Developer",
                goal="Develop software",
                backstory="Experienced developer",
                tools=[ToolModel(name="IDE", description="Integrated Development Environment")]
            )
        ],
        tasks=[
            TaskModel(
                description="Implement a new feature",
                expected_output="Working code",
                agent_role="Developer"
            )
        ]
    )

    assert create_crew_request.tools_proxy_collection is None