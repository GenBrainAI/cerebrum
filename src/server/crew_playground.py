import sys
import os

from crewai import Agent, Task, Crew
from crewai_tools import WebsiteSearchTool, FileReadTool, SerperDevTool
from fastapi import HTTPException

from src.server.persistence.persistence_model_factory import PersistenceModelFactory
from src.server.models.agent import CreateCrewRequest, AgentModel, TaskModel
from src.server.models.agent import CrewAIConfig

persistence_model = PersistenceModelFactory.persistence_model("inmemory")

def save_crew():
    TOOLS = {
        "WebsiteSearchTool": WebsiteSearchTool(),
        "SerperDevTool": SerperDevTool(),
        "FileReadTool": FileReadTool(
            file_path='job_description_example.md',
            description='A tool to read the job description example file.'
        )
    }
    request_data = {
        "description": "A tech company specializing in AI solutions.",
        "agents": [
            {
                "role": "Research Analyst",
                "goal": "Analyze the company website and provided description to extract insights on culture, values, and specific needs.",
                "backstory": "Expert in analyzing company cultures and identifying key values and needs from various sources, including websites and brief descriptions.",
                "tools": [
                    {"name": "WebsiteSearchTool", "description": "Tool for searching websites"},
                    {"name": "SerperDevTool", "description": "Development tool for data separation"}
                ]
            },
            {
                "role": "Job Description Writer",
                "goal": "Use insights from the Research Analyst to create a detailed, engaging, and enticing job posting.",
                "backstory": "Skilled in crafting compelling job descriptions that resonate with the company's values and attract the right candidates.",
                "tools": [
                    {"name": "WebsiteSearchTool", "description": "Tool for searching websites"},
                    {"name": "SerperDevTool", "description": "Development tool for data separation"},
                    {"name": "FileReadTool", "description": "Tool for reading files"}
                ]
            },
            {
                "role": "Review and Editing Specialist",
                "goal": "Review the job posting for clarity, engagement, grammatical accuracy, and alignment with company values and refine it to ensure perfection.",
                "backstory": "A meticulous editor with an eye for detail, ensuring every piece of content is clear, engaging, and grammatically perfect.",
                "tools": [
                    {"name": "WebsiteSearchTool", "description": "Tool for searching websites"},
                    {"name": "SerperDevTool", "description": "Development tool for data separation"},
                    {"name": "FileReadTool", "description": "Tool for reading files"}
                ]
            }
        ],
        "tasks": [
            {
                "description": "Analyze the provided company website and the hiring manager's company's domain ai-tech.com, description: \"A tech company specializing in AI solutions.\". Focus on understanding the company's culture, values, and mission. Identify unique selling points and specific projects or achievements highlighted on the site. Compile a report summarizing these insights, specifically how they can be leveraged in a job posting to attract the right candidates.",
                "expected_output": "A comprehensive report detailing the company's culture, values, and mission, along with specific selling points relevant to the job role. Suggestions on incorporating these insights into the job posting should be included.",
                "agent_role": "Research Analyst"
            },
            {
                "description": "Draft a job posting for the role described by the hiring manager: \"Senior AI Engineer\". Use the insights on \"A tech company specializing in AI solutions.\" to start with a compelling introduction, followed by a detailed role description, responsibilities, and required skills and qualifications. Ensure the tone aligns with the company's culture and incorporate any unique benefits or opportunities offered by the company. Specific benefits: \"Remote work, flexible hours, stock options\"",
                "expected_output": "A detailed, engaging job posting that includes an introduction, role description, responsibilities, requirements, and unique company benefits. The tone should resonate with the company's culture and values, aimed at attracting the right candidates.",
                "agent_role": "Job Description Writer"
            },
            {
                "description": "Review the draft job posting for the role: \"Senior AI Engineer\". Check for clarity, engagement, grammatical accuracy, and alignment with the company's culture and values. Edit and refine the content, ensuring it speaks directly to the desired candidates and accurately reflects the role's unique benefits and opportunities. Provide feedback for any necessary revisions.",
                "expected_output": "A polished, error-free job posting that is clear, engaging, and perfectly aligned with the company's culture and values. Feedback on potential improvements and final approval for publishing. Formatted in markdown.",
                "agent_role": "Review and Editing Specialist"
            }
        ]
    }
    try:
        request = CreateCrewRequest(**request_data)
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
        crewai_config = CrewAIConfig(
            crewai_config = request,
        )
        persistence_model.crewai_config.create(crewai_config)
        crewai_config_id = crewai_config.id
        json = persistence_model.to_json()
        persistence_model.from_json(json)
        crewai_config_restored = persistence_model.crewai_config.read(crewai_config_id)
        assert crewai_config_restored.id == crewai_config_id
    except Exception as e:
        print(str(e))

def some_test():
    def apply_params_to_string(string, params):
        for key, value in params.items():
            placeholder = "{" + key + "}"
            if isinstance(value, list):
                value = ", ".join(str(item) for item in value)
            string = string.replace(placeholder, str(value))
        return string

    template = """
        Hello, {name}!

        Your trip details are as follows:
        - Destination: {destination}
        - Dates: {start_date} to {end_date}
        - Activities: {activities}

        Enjoy your trip!
    """

    params = {
        "name": "John",
        "destination": "Paris",
        "start_date": "2023-07-01",
        "end_date": "2023-07-10",
        "activities": ["sightseeing", "museum visits", "food tasting"]
    }

    result = apply_params_to_string(template, params)
    print(result)


if __name__ == "__main__":
    #save_crew()
    some_test()