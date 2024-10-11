import os
from dotenv import load_dotenv
from fastapi import HTTPException
from crewai import Agent, Task, Crew
from crewai_tools import WebsiteSearchTool, FileReadTool, SerperDevTool
from langchain.tools import BaseTool as LangChainBaseTool

# from llama_index.tools import BaseTool as LlamaIndexBaseTool

from ..persistence.persistence_model_factory import PersistenceModelFactory
from ..models.agent import CreateCrewRequest, AgentModel, TaskModel
from ..tools.file_tool import FileTool
from ..tools.github_tool import GitHubTool
from ..controllers.curried_proxy import CurriedProxy

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
    "save_file": FileTool()
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
    agents = []
    for agent_data in request.agents:
        tools = [create_crewai_tool(TOOLS[tool.name]) for tool in agent_data.tools if tool.name in TOOLS]

        # Get class tools
        for tool in tools:
            if isinstance(tool, GitHubTool):
                tools.remove(tool)
                for attr_name in dir(tool):
                    attr = getattr(tool, attr_name)
                    if callable(attr) and not attr_name.startswith("__"):
                        curried_proxy.add_tool(attr_name, attr)

        tools.extend(curried_proxy.export_to_crewai())

        agent = Agent(
            role=agent_data.role,
            goal=agent_data.goal,
            backstory=agent_data.backstory,
            tools=tools,
            verbose=True
        )
        agents.append(agent)

    tasks = []
    for task_data in request.tasks:
        agent = next((a for a in agents if a.role == task_data.agent_role), None)
        if not agent:
            raise HTTPException(status_code=400, detail=f"Agent role '{task_data.agent_role}' not found.")
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


async def run_crewai(task_id: str):
    task = persistence_model.tasks.read(task_id)
    crewai_config = persistence_model.crewai_config.read(task.crewai_info_id)
    # Create CurriedProxy instance
    curried_proxy = persistence_model.curried_proxies.read(task.curried_proxy_id)

    # Add tools from task and tasksmanager
    tasksmanager = persistence_model.tasksmanagers.read(task.tasksmanager_id)
    if task.toolsets:
        toolset_ids = task.toolsets + tasksmanager.toolsets
    else:
        toolset_ids = tasksmanager.toolsets

    for toolset_id in toolset_ids:
        toolset = persistence_model.toolsets.read(toolset_id)
        for tool_id in toolset.tool_ids:
            tool = persistence_model.tools.read(tool_id)
            curried_proxy.add_tool(f"{toolset.name}_{tool.function.name}", tool)

    crew = await create_crew(crewai_config.create_crew, curried_proxy)
    result = crew.kickoff()
    return result

# async def create_autogen(config: AutogenConfig):
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
