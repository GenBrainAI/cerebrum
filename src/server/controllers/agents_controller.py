from os import getenv
from dotenv import load_dotenv
from fastapi import HTTPException
from crewai import Agent, Task, Crew
from crewai_tools import WebsiteSearchTool, FileReadTool, SerperDevTool, BaseTool
from langchain.tools import BaseTool as LangChainBaseTool
from langchain_ollama.llms import OllamaLLM as Ollama
from langchain_openai import ChatOpenAI
from langchain_openai import AzureChatOpenAI
from typing import Optional
from ..persistence.persistence_model_factory import PersistenceModelFactory
from ..models.agent import CreateCrewRequest, AgentModel, TaskModel
from ..tools.file_tool import FileTool
from ..tools.github_tool import GitHubTool
from ..tools.jira_tool import JiraTool
from ..tools.microservices_tool import MicroservicesTool
from ..tools.sms_tool import SMSTool
from ..controllers.curried_proxy import CurriedProxy
from ..context.context_provider import ContextProvider
from ..context.crew_context_enhancer import CrewContextEnhancer, CrewContextConfig

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
    """LLM configuration for CrewAI agents."""
    def __init__(self):
        self.OpenAIGPT35 = ChatOpenAI(model_name="gpt-3.5-turbo", temperature=0.7)
        self.OpenAIGPT4 = ChatOpenAI(model_name="gpt-4", temperature=0.7)
        self.Ollama = Ollama(model="llama3.2:latest")

async def create_crew(
    request: CreateCrewRequest,
    curried_proxy: Optional[CurriedProxy] = None
) -> Crew:
    """
    Create a CrewAI crew. Maintains original crew creation logic
    without context dependencies.
    """
    llm = CrewLLM()
    try:
        # Create agents with tools from proxy
        agents = []
        agent_tools = []
        
        if curried_proxy:
            agent_tools = curried_proxy.export_to_crewai()
            
        for agent_data in request.agents:
            # Get LLM from agent data or default to GPT-4
            agent_llm = getattr(llm, agent_data.llm_model) if hasattr(agent_data, 'llm_model') else llm.OpenAIGPT4
            
            agent = Agent(
                role=agent_data.role,
                goal=agent_data.goal,
                backstory=agent_data.backstory,
                tools=agent_tools,
                verbose=True,
                llm=agent_llm
            )
            agents.append(agent)

        # Create tasks
        tasks = []
        for task_data in request.tasks:
            agent = next(
                (a for a in agents if a.role == task_data.agent_role),
                None
            )
            if not agent:
                raise HTTPException(status_code=400, detail=f"Agent role '{task_data.agent_role}' not found.")
                
            task = Task(
                description=task_data.description,
                expected_output=str(task_data.expected_output),
                agent=agent
            )
            tasks.append(task)

        # Create the crew
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

async def enhance_crew_with_context(
    crew: Crew,
    task_id: str
) -> Crew:
    """
    Optional enhancement of an existing crew with context capabilities.
    This maintains separation of concerns.
    """
    if not task_id:
        return crew
        
    try:
        # Initialize context components
        context_provider = ContextProvider()
        context_enhancer = CrewContextEnhancer(context_provider)
        
        # Configure context enhancement
        config = CrewContextConfig(
            task_id=task_id,
            include_code_context=True,
            include_domain_context=True
        )
        
        # Enhance the crew
        enhanced_crew = await context_enhancer.enhance_crew(crew, config)
        return enhanced_crew
        
    except Exception as e:
        print(f"Error enhancing crew with context: {e}")
        # Don't raise an exception - if context enhancement fails,
        # return the original crew
        return crew

