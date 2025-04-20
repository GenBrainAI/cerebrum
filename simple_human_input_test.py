#!/usr/bin/env python3
"""
Minimal test script for demonstrating human input functionality with CrewAI directly.
This script bypasses the Cerebrum framework's CurriedProxy and tools_catalog.
"""

import os
import sys
import logging
from typing import Any, Dict

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)

logger = logging.getLogger(__name__)

# Ensure src is in the path so imports work correctly
parent_dir = os.path.dirname(os.path.abspath(__file__))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

# Direct imports from CrewAI
from crewai import Agent, Task, Crew, Process
from crewai.tools import BaseTool
from pydantic import BaseModel, Field

# Define the schema for the human input tool
class HumanInputSchema(BaseModel):
    """Schema for the human input tool."""
    query: str = Field(description="The question to ask the human user")

# Create a custom human input tool that extends BaseTool from crewai.tools
class HumanInputTool(BaseTool):
    """Tool for getting input from a human user."""
    
    name: str = "human_input"
    description: str = "Ask the human user for input during task execution"
    args_schema: type[BaseModel] = HumanInputSchema
    
    def _run(self, query: str) -> str:
        """Run the tool with the provided query."""
        print("\n" + "-" * 80)
        print(f"🔔 HUMAN INPUT REQUESTED: {query}")
        print("-" * 80)
        user_input = input("Your response: ")
        print("-" * 80 + "\n")
        return user_input
    
    async def _arun(self, query: str) -> str:
        """Run the tool asynchronously."""
        return self._run(query)

def create_human_input_crew():
    """Create a crew with a simple human input tool."""
    logger.info("Creating a crew with direct human input capability")
    
    # Create the human input tool
    human_input_tool = HumanInputTool()
    
    # Create a simple agent with the human input tool
    assistant = Agent(
        role="Assistant",
        goal="Help the user by gathering needed information",
        backstory="You are a helpful assistant that can ask the user questions when you need more information.",
        verbose=True,
        allow_delegation=False,
        tools=[human_input_tool]
    )
    
    # Create a task that requires human input
    information_gathering_task = Task(
        description="""
        You need to create a short summary of a topic of interest to the user.
        First, ask the user what topic they're interested in using the human_input tool.
        Then, ask 1-2 follow-up questions to gather specific information about what aspects of the topic
        they want to know about.
        Finally, create a 3-5 sentence summary based on their responses.
        
        IMPORTANT: When using the human_input tool, you must provide a simple string for the query parameter.
        Example: human_input(query="What topic would you like me to summarize?")
        Do NOT use a dictionary or any other complex type for the query parameter.
        """,
        agent=assistant,
        expected_output="A short summary of the user's topic of interest"
    )
    
    # Create the crew
    crew = Crew(
        agents=[assistant],
        tasks=[information_gathering_task],
        verbose=True,
        process=Process.sequential
    )
    
    logger.info("Crew creation complete")
    return crew

def main():
    """Main entry point for the script."""
    print("=== Simple Human Input Test for CrewAI ===")
    print("This script demonstrates a minimal implementation of human-in-the-loop functionality.")
    
    try:
        # Create the crew
        crew = create_human_input_crew()
        
        # Run the task
        logger.info("Starting crew execution...")
        result = crew.kickoff()
        print("\n==== SUMMARY ====")
        print(result)
        print("================")
            
    except Exception as e:
        logger.error(f"Error in main: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main() 