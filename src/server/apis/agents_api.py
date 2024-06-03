import os
from fastapi import FastAPI, HTTPException, APIRouter
from dotenv import load_dotenv
from ..models.agent import CreateCrewRequest, AgentModel, TaskModel, AutogenConfig
from crewai import Agent, Task, Crew
from crewai_tools import WebsiteSearchTool, FileReadTool, SerperDevTool
from ..tools.github_tool import GithubTool

router = APIRouter()

# To add your own tools please refer to the following link:
# https://docs.crewai.com/core-concepts/Tools/#creating-your-own-tools

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

@router.post("/agent")
async def create_agents(request: CreateCrewRequest):
    try:
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

        # Kick off the process
        #result = crew.kickoff()

        return {"message": "Job Posting Creation Process Completed", "result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/agent/{agent_id}/run")
async def run_agent_process(agent_id: str):
    try:
        # # Find the agent with the matching role
        # agent = next((a for a in agents if a.role == agent_id), None)
        # if not agent:
        #     raise HTTPException(status_code=400, detail=f"Agent role '{agent_id}' not found.")

        # # Instantiate the crew
        # crew = Crew(
        #     agents=[agent],
        #     tasks=[]
        # )

        # # Kick off the process
        # result = crew.kickoff()

        return {"message": "Agent process started successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/agent/autogen")
async def autogen_agent(config: AutogenConfig):
    try:
        agents = [create_agent(agent.dict()) for agent in config.agents]
        tasks = [ChatTask(**task.dict()) for task in config.tasks]
        chat_config = ChatConfig(agents=agents, tasks=tasks)
        return JSONResponse(content={"agents": [agent.__dict__ for agent in agents], "tasks": [task.dict() for task in tasks]}, status_code=200)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
