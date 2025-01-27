# test_agent.py

from fastapi.testclient import TestClient
import pytest
from src.server.main import app
import pytest_asyncio
from src.server.tools.tools_catalog import tools_catalog
from crewai_tools import WebsiteSearchTool, SerperDevTool, FileReadTool

client = TestClient(app)

@pytest.fixture(autouse=True)
def cleanup_tools():
    """Cleanup fixture that runs automatically before and after each test."""
    tools_catalog.reset()
    yield
    tools_catalog.reset()

@pytest.fixture(autouse=True)
def register_crewai_tools():
    """Register CrewAI tools before running tests."""
    website_tool = WebsiteSearchTool()
    serper_tool = SerperDevTool()
    file_read_tool = FileReadTool()
    tools_catalog.register_ai_tool(website_tool, "WebsiteSearchTool")
    tools_catalog.register_ai_tool(serper_tool, "SerperDevTool")
    tools_catalog.register_ai_tool(file_read_tool, "FileReadTool")
    yield

@pytest.mark.unit
def test_create_agents_and_tasks():
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

    response = client.post("/agent/crewai", json=request_data)
    assert response.status_code == 201
    data = response.json()
    assert data["message"] == "Crew created"