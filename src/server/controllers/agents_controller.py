import os
from dotenv import load_dotenv
from fastapi import HTTPException
from crewai import Agent, Task, Crew
from crewai_tools import WebsiteSearchTool, FileReadTool, SerperDevTool
from langchain.tools import BaseTool as LangChainBaseTool
from crewai_tools import BaseTool
from langchain_community.llms import Ollama
from langchain_openai import ChatOpenAI
from langchain_openai import AzureChatOpenAI

from ..persistence.persistence_model_factory import PersistenceModelFactory
from ..models.agent import CreateCrewRequest, AgentModel, TaskModel
from ..tools.file_tool import FileTool
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


class CrewLLM:
    def __init__(self):
        self.OpenAIGPT35 = ChatOpenAI(model_name="gpt-3.5-turbo", temperature=0.7)
        self.OpenAIGPT4 = ChatOpenAI(model_name="gpt-4", temperature=0.7)
        self.Ollama = Ollama(model="llama3.2:latest")
        # self.AzureChatOpenAI35 = AzureChatOpenAI(
        #     openai_api_version=os.environ.get("AZURE_OPENAI_VERSION", "api-version=2024-10-21"),
        #     azure_deployment=os.environ.get("AZURE_OPENAI_DEPLOYMENT", "o1-mini"))


async def create_crew(request: CreateCrewRequest, curried_proxy) -> Crew:
    llm = CrewLLM()
    """Create a CrewAI crew from the given configuration."""
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
                verbose=True,
                llm=llm.OpenAIGPT4
            )
            agents.append(agent)

        tasks = []
        for task_data in request.tasks:
            agent = next((a for a in agents if a.role == task_data.agent_role), None)
            if not agent:
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
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

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
