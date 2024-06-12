import autogen
from crewai import Agent, Task, Crew
from crewai_tools import WebsiteSearchTool, FileReadTool, SerperDevTool

from ..persistence.persistence_model_factory import PersistenceModelFactory
from ..models.agent import CreateCrewRequest, AgentModel, TaskModel, AutogenConfig
from ..tools.github_tool import GithubTool

persistence_model = PersistenceModelFactory.persistence_model("inmemory")

# To add your own tools please refer to the following link:
# https://docs.crewai.com/core-concepts/Tools/#creating-your-own-tools


config_list = autogen.config_list_from_json(env_or_file="OAI_CONFIG_LIST")
llm_config = {"config_list": config_list}


# Define available tools
TOOLS = {
    "WebsiteSearchTool": WebsiteSearchTool(),
    "SerperDevTool": SerperDevTool(),
    "FileReadTool": FileReadTool(
        file_path='job_description_example.md',
        description='A tool to read the job description example file.'
    ),
    "WebsiteSearchTool": WebsiteSearchTool(),
    "SerperDevTool": SerperDevTool(),
    "FileReadTool": FileReadTool(
        file_path='job_description_example.md',
        description='A tool to read the job description example file.'
    ),
    "GithubTool": GithubTool(
        access_token=os.getenv("GITHUB_ACCESS_TOKEN"),
        repo_name=os.getenv("GITHUB_REPO_NAME", "GenBrainAI/cerebrum")
    )
}

async def create_crew(request: CreateCrewRequest):
    # Create agents based on the request
    agents = []
    for agent_data in request.agents:
        tools = [TOOLS[tool.name] for tool in agent_data.tools if tool.name in TOOLS]
        agent = Agent(
            role=agent_data.role,
            goal=agent_data.goal,
            backstory=agent_data.backstory,
            tools=tools,
            verbose=True
        )
        agents.append(agent)

    # Create tasks based on the request
    tasks = []
    for task_data in request.tasks:
        # Find the agent with the matching role
        agent = next((a for a in agents if a.role == task_data.agent_role), None)
        if not agent:
            raise HTTPException(status_code=400, detail=f"Agent role '{task_data.agent_role}' not found.")
        task = Task(
            description=task_data.description,
            expected_output=task_data.expected_output,
            agent=agent
        )
        tasks.append(task)

    # Instantiate the crew
    crew = Crew(
        agents=agents,
        tasks=tasks
    )

    return crew


async def run_crewai(task_id: str):
    task = persistence_model.tasks.read(task_id)
    crewai_config = persistence_model.crewai_config.read(task.crewai_info_id)
    crew = create_crew(crewai_config.create_crew)
    # Instantiate the crew
    result = crew.kickoff()
    return result



async def create_autogen(config: AutogenConfig):
    try:
        agents = [create_agent(agent.dict()) for agent in config.agents]
        tasks = [ChatTask(**task.dict()) for task in config.tasks]
        chat_config = ChatConfig(agents=agents, tasks=tasks)
        return JSONResponse(content={"agents": [agent.__dict__ for agent in agents], "tasks": [task.dict() for task in tasks]}, status_code=200)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


async def run_autogen_agent(task_id: str):
    task = persistence_model.tasks.read(task_id)
    autogen_config = persistence_model.autogen_config.read(task.autogen_config_id)
    autogen = create_autogen(autogen_config)
    result = autogen.run()
    return result

