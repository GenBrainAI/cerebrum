from os import getenv
from dotenv import load_dotenv
from fastapi import HTTPException
from crewai import Agent, Task, Crew
from crewai_tools import WebsiteSearchTool, FileReadTool, SerperDevTool, BaseTool
from langchain.tools import BaseTool as LangChainBaseTool
from langchain_community.llms import Ollama
from langchain_openai import ChatOpenAI
from langchain_openai import AzureChatOpenAI

from ..persistence.persistence_model_factory import PersistenceModelFactory
from ..models.agent import CreateCrewRequest, AgentModel, TaskModel
from ..tools.file_tool import FileTool
from ..tools.github_tool import GitHubTool
from ..tools.jira_tool import JiraTool
from ..tools.microservices_tool import MicroservicesTool
from ..tools.sms_tool import SMSTool
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
        access_token=getenv("GITHUB_ACCESS_TOKEN"),
        repo_name=getenv("GITHUB_REPO_NAME", "GenBrainAI/cerebrum")
    ),
    "save_file": FileTool(),
    "microservices_tool": MicroservicesTool(),
    "SMSTool": SMSTool(),
}

class CrewLLM:
    def __init__(self):
        self.OpenAIGPT35 = ChatOpenAI(model_name="gpt-3.5-turbo", temperature=0.7)
        self.OpenAIGPT4 = ChatOpenAI(model_name="gpt-4", temperature=0.7)
        self.Ollama = Ollama(model="llama3.2:latest")

async def create_crew(request: CreateCrewRequest, curried_proxy: CurriedProxy) -> Crew:
    """Create a CrewAI crew from the given configuration."""
    llm = CrewLLM()
    try:
        agents = []
        for agent_data in request.agents:
            agent_tools = []
            
            # Get all tools from curried proxy using export_to_crewai
            if curried_proxy:
                crewai_tools = curried_proxy.export_to_crewai()
                agent_tools.extend(crewai_tools)

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
            tasks=tasks,
            verbose=True
        )

        return crew
    except HTTPException:
        raise
    except Exception as e:
        print(e)
        raise HTTPException(status_code=500, detail=str(e))
