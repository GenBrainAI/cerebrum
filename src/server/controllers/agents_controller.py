import os
from dotenv import load_dotenv
from fastapi import HTTPException
from crewai import Agent, Task, Crew
from crewai_tools import WebsiteSearchTool, FileReadTool, SerperDevTool
from langchain.tools import BaseTool as LangChainBaseTool
from crewai_tools import BaseTool
from ..models.toolset import Tool

# from llama_index.tools import BaseTool as LlamaIndexBaseTool

from ..persistence.persistence_model_factory import PersistenceModelFactory
from ..models.agent import CreateCrewRequest, AgentModel, TaskModel
from ..tools.file_tool import FileTool
from ..tools.github_tool import GitHubTool
from ..controllers.curried_proxy import CurriedProxy
from ..tools.github_tool import GitHubTool
from ..tools.jira_tool import JiraTool
from ..tools.microservices_tool import MicroservicesTool

persistence_model = PersistenceModelFactory.persistence_model("inmemory")
load_dotenv()
# Define available tools
TOOLS = {
    "WebsiteSearchTool": WebsiteSearchTool(),
    "SerperDevTool": SerperDevTool(),
    "FileReadTool": FileReadTool(
        file_path='job_description_example.md',
        description='A tool to read the job description example file.'
    ),
    "GitHubTool": GitHubTool(
        access_token=os.getenv("GITHUB_ACCESS_TOKEN"),
        repo_name=os.getenv("GITHUB_REPO_NAME", "GenBrainAI/cerebrum")
    ),
    "save_file": FileTool(),
    "microservices_tool": MicroservicesTool()
}


def create_crewai_tool(tool):
    if isinstance(tool, (LangChainBaseTool)):  #, LlamaIndexBaseTool)):
        # Wrap LangChain or LlamaIndex tools
        return tool
    elif callable(tool):
        # Wrap simple functions
        return Tool.from_function(tool)
    else:
        # Assume it's already a CrewAI compatible tool
        return tool

async def create_crew(request: CreateCrewRequest, curried_proxy: CurriedProxy):
    try:
        agents = []
        for agent_data in request.agents:
            agent_tools = []
            for tool_model in agent_data.tools:
                tool = curried_proxy.get_tool(tool_model.name)
                if tool:
                    if isinstance(tool, BaseTool):
                        agent_tools.append(tool)
                    else:
                        agent_tools.append(curried_proxy.create_crewai_tool(tool_model.name, tool))

            agent = Agent(
                role=agent_data.role,
                goal=agent_data.goal,
                backstory=agent_data.backstory,
                tools=agent_tools,
                verbose=True
            )
            agents.append(agent)

        tasks = []
        for task_data in request.tasks:
            agent = next((a for a in agents if a.role == task_data.agent_role), None)
            if not agent:
                # Raise the HTTPException directly
                raise HTTPException(
                    status_code=400,
                    detail=f"Agent role '{task_data.agent_role}' not found."
                )
            task = Task(
                description=task_data.description,
                expected_output=task_data.expected_output,
                agent=agent
            )
            tasks.append(task)

        crew = Crew(
            agents=agents,
            tasks=tasks
        )

        return crew
    except HTTPException:
        # Re-raise HTTPExceptions directly
        raise
    except Exception as e:
        # Wrap other exceptions in a 500 status code
        raise HTTPException(status_code=500, detail=str(e))
    
async def run_crewai(task_id: str):
    task = persistence_model.tasks.read(task_id)
    crewai_config = persistence_model.crewai_config.read(task.crewai_info_id)
    create_crew_request = crewai_config.create_crew

    # Create CurriedProxy instance
    curried_proxy = CurriedProxy()

    if create_crew_request.tools_proxy_collection:
        tpc = create_crew_request.tools_proxy_collection

        # Add toolsets
        for toolset_spec in tpc.toolsets:
            toolset = persistence_model.toolsets.read(toolset_spec.id)
            for tool_id in toolset.tool_ids:
                tool = persistence_model.tools.read(tool_id)
                curried_proxy.add_tool(f"{toolset_spec.name}_{tool.function.name}", tool)

        # Add functions
        for function_spec in tpc.functions:
            function_tool = persistence_model.tools.read(function_spec.name)
            curried_proxy.add_tool(function_spec.name, function_tool)

        # Add objects
        for object_spec in tpc.objects:
            if object_spec.object_type == "github_tool":
                github_tool = GitHubTool(
                    access_token=os.getenv("GITHUB_ACCESS_TOKEN"),
                    repo_name=os.getenv("GITHUB_REPO_NAME")
                )
                curried_proxy.add_tool(object_spec.name, github_tool)
            elif object_spec.object_type == "jira_tool":
                # Assuming you have a JiraTool class
                jira_tool = JiraTool(
                    jira_url=os.getenv("JIRA_URL"),
                    jira_username=os.getenv("JIRA_USERNAME"),
                    jira_api_token=os.getenv("JIRA_API_TOKEN")
                )
                curried_proxy.add_tool(object_spec.name, jira_tool)
            # Add other object types as needed

    # Create and run the crew
    crew = await create_crew(create_crew_request, curried_proxy)
    result = crew.kickoff()
    return result# async def create_autogen(config: AutogenConfig):
#     try:
#         agents = [create_agent(agent.dict()) for agent in config.agents]
#         tasks = [ChatTask(**task.dict()) for task in config.tasks]
#         chat_config = ChatConfig(agents=agents, tasks=tasks)
#         return JSONResponse(content={"agents": [agent.__dict__ for agent in agents], "tasks": [task.dict() for task in tasks]}, status_code=200)
#     except Exception as e:
#         raise HTTPException(status_code=400, detail=str(e))


# async def run_autogen_agent(task_id: str):
#     task = persistence_model.tasks.read(task_id)
#     autogen_config = persistence_model.autogen_config.read(task.autogen_config_id)
#     autogen = create_autogen(autogen_config)
#     result = autogen.run()
#     return result
