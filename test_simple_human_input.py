#!/usr/bin/env python3
"""
Simple test script for human input functionality with CrewAI.
This script demonstrates human-in-the-loop functionality with a console interface.
"""

import os
import sys
import logging
import uuid

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

# Import necessary components
from crewai import Agent, Task, Crew, Process
from src.server.tools.human_tools import HumanInputTool, human_input_tool
from src.server.controllers.curried_proxy import CurriedProxy
from src.server.tools.tools_catalog import ToolsCatalog

# Override the HumanInputTool's _run method for console input
def console_run(self, query: str = "") -> str:
    """
    Console-based implementation of the human input tool's _run method.
    This allows the tool to work in a console environment instead of the UI.
    """
    print("\n" + "-" * 80)
    print(f"🔔 HUMAN INPUT REQUESTED: {query}")
    print("-" * 80)
    user_input = input("Your response: ")
    print("-" * 80 + "\n")
    return user_input

def create_simple_crew():
    """
    Create a simple crew with an agent and a task requiring human input.
    """
    logger.info("Creating a simple crew with human input capability")
    
    # Initialize tools catalog
    tools_catalog = ToolsCatalog()
    
    # Create a human input tool
    human_input = HumanInputTool()
    
    # Save the original run method so we can restore it later
    original_run = human_input._run
    
    # Override the run method with our console implementation
    human_input._run = console_run.__get__(human_input, HumanInputTool)
    
    # Register the human input tool with the catalog
    tools_catalog.register_tool("human_input", human_input)
    
    # Create a CurriedProxy with a valid UUID
    proxy_id = str(uuid.uuid4())
    curried_proxy = CurriedProxy(id=proxy_id)
    
    # Add the human input tool to the proxy
    curried_proxy.register_tool("human_input", human_input)
    
    # Create a list of CrewAI tools
    crewai_tools = []
    
    # Create a CerebrumCrewAITool for human input
    from src.server.controllers.curried_proxy import CerebrumCrewAITool
    human_tool = CerebrumCrewAITool(
        name="human_input",
        description="Ask the human user for input during task execution",
        proxy=curried_proxy
    )
    crewai_tools.append(human_tool)
    
    # Create a simple agent
    assistant = Agent(
        role="Assistant",
        goal="Help the user by gathering needed information",
        backstory="You are a helpful assistant that can ask the user questions when you need more information.",
        verbose=True,
        allow_delegation=False,
        tools=crewai_tools
    )
    
    # Create a task that requires human input
    information_gathering_task = Task(
        description="""
        You need to create a short summary of a topic of interest to the user.
        First, ask the user what topic they're interested in using the human_input tool.
        Then, ask 1-2 follow-up questions to gather specific information about what aspects of the topic
        they want to know about.
        Finally, create a 3-5 sentence summary based on their responses.
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
    return crew, original_run

def main():
    """Main entry point for the script."""
    print("=== Simple Human Input Test for CrewAI ===")
    print("This script demonstrates human-in-the-loop functionality with a console interface.")
    
    try:
        # Create the crew and get the original run method
        crew, original_run = create_simple_crew()
        
        # Run the task
        try:
            logger.info("Starting crew execution...")
            result = crew.kickoff()
            print("\n==== SUMMARY ====")
            print(result)
            print("================")
        except Exception as e:
            logger.error(f"Error during task execution: {e}")
            import traceback
            traceback.print_exc()
        finally:
            # Restore the original run method to avoid side effects
            human_tool = HumanInputTool()
            human_tool._run = original_run
            
    except Exception as e:
        logger.error(f"Error in main: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main() 