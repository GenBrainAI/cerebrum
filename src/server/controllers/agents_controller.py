from os import getenv
from dotenv import load_dotenv
from fastapi import HTTPException
from crewai import Agent, Task, Crew
from crewai.tools import BaseTool
from crewai_tools import WebsiteSearchTool, FileReadTool, SerperDevTool
from langchain.tools import BaseTool as LangChainBaseTool
from langchain_ollama.llms import OllamaLLM as Ollama
from langchain_openai import ChatOpenAI
from langchain_openai import AzureChatOpenAI
from typing import Optional, Dict, Any
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
        self.OpenAIGPT4 = ChatOpenAI(model_name="gpt-4o", temperature=0.7)
        self.Ollama = Ollama(model="llama3.2:latest")

async def create_crew(
    request: CreateCrewRequest,
    curried_proxy: Optional[CurriedProxy] = None
) -> Crew:
    """
    Create a CrewAI crew. Maintains original crew creation logic
    without context dependencies.
    """
    print("\n🔄 Creating CrewAI crew...")
    llm = CrewLLM()
    try:
        # Create agents with tools from proxy
        agents = []
        agent_tools = []
        
        if curried_proxy:
            print("🛠️ Curried proxy provided, exporting tools...")
            agent_tools = curried_proxy.export_to_crewai()
            print(f"🔧 Exported {len(agent_tools)} tools from proxy")
        else:
            print("⚠️ No curried proxy provided, agents will have no tools")
            
        for agent_data in request.agents:
            print(f"\n👤 Creating agent: {agent_data.role}")
            # Get LLM from agent data or default to gpt-4o-mini
            agent_llm = getattr(llm, agent_data.llm_model) if hasattr(agent_data, 'llm_model') else llm.OpenAIGPT4
            
            agent = Agent(
                role=agent_data.role,
                goal=agent_data.goal,
                backstory=agent_data.backstory,
                tools=agent_tools,
                verbose=True,
                llm=agent_llm
            )
            print(f"  ✅ Agent created with {len(agent_tools)} tools")
            agents.append(agent)

        # Create tasks
        tasks = []
        for task_data in request.tasks:
            print(f"\n📋 Creating task: {task_data.description[:50]}...")
            agent = next(
                (a for a in agents if a.role == task_data.agent_role),
                None
            )
            if not agent:
                error_msg = f"Agent role '{task_data.agent_role}' not found."
                print(f"  ❌ {error_msg}")
                raise HTTPException(status_code=400, detail=error_msg)
                
            task = Task(
                description=task_data.description,
                expected_output=str(task_data.expected_output),
                agent=agent
            )
            print(f"  ✅ Task created and assigned to agent: {task_data.agent_role}")
            tasks.append(task)

        # Create the crew
        crew = Crew(
            agents=agents,
            tasks=tasks,
            verbose=True
        )
        print("\n✨ Crew created successfully!")
        print(f"  - {len(agents)} agents")
        print(f"  - {len(tasks)} tasks")
        print(f"  - {len(agent_tools)} tools per agent\n")

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

async def execute_task(task_id: str, persistence_model) -> Dict[str, Any]:
    """Execute a task using CrewAI.
    
    Args:
        task_id: ID of the task to execute
        persistence_model: Persistence model instance
        
    Returns:
        Dictionary containing execution results
        
    Raises:
        HTTPException: If task execution fails
    """
    try:
        # Get task
        task = persistence_model.tasks.read(task_id)
        if not task:
            raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
            
        # Get required configurations
        crewai_config = persistence_model.crewai_config.read(task.crewai_config_id)
        if not crewai_config:
            raise HTTPException(status_code=404, detail="CrewAI configuration not found")
            
        curried_proxy = None
        if task.curried_proxy_id:
            curried_proxy = persistence_model.curried_proxies.read(task.curried_proxy_id)
            if not curried_proxy:
                raise HTTPException(status_code=404, detail="CurriedProxy not found")
        
        # Create crew
        crew = await create_crew(crewai_config.create_crew, curried_proxy)
        
        # Enhance with context if needed
        if task.use_context:
            crew = await enhance_crew_with_context(crew, task_id)
            
        # Execute crew tasks
        result = crew.kickoff()
        
        # Update task with execution logs
        task.execution_logs = crew.process_outputs()
        persistence_model.tasks.update(task)
        
        return {
            "task_id": task_id,
            "status": "completed",
            "result": result,
            "execution_logs": task.execution_logs
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error executing task: {e}")
        raise HTTPException(status_code=500, detail=str(e))

