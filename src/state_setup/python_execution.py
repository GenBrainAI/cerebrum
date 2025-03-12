"""
Python Execution State Setup

This module sets up a state for demonstrating Python code execution capabilities
using the PyExec tool. It creates a task manager and tasks for executing Python code,
particularly focusing on the brain.py script which implements a left-brain/right-brain
conversation model.
"""

import sys
import os
from pathlib import Path
import asyncio
import logging

# Add the project root to the Python path
project_root = str(Path(__file__).parents[2])
sys.path.append(project_root)

from src.server.persistence.persistence_model_factory import PersistenceModelFactory
from src.server.models.tasks_manager import TasksManager
from src.server.models.task import Task
from src.server.models.message import Message
from src.server.models.persistence_models import StorageLocation, StorageType
from src.server.controllers.persistence_controller import save_to_storage
from src.server.tools.py_exec import PyExec
from src.server.controllers.curried_proxy import CurriedProxy
from src.server.models.tools_catalog import ToolsCatalog

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

async def setup_python_execution_state():
    """Set up a state for demonstrating Python code execution capabilities."""
    
    print("\n🔄 Setting up Python Execution state...")
    
    # Initialize persistence model
    persistence_model = PersistenceModelFactory.persistence_model("inmemory")
    
    # Create and register the PyExec tool
    py_exec = PyExec()
    tools_catalog = ToolsCatalog()
    
    # Create a curried proxy for the tools
    curried_proxy = CurriedProxy()
    curried_proxy.add_tool("PyExec.run_script", py_exec.run_script)
    curried_proxy.add_tool("PyExec.run_code", py_exec.run_code)
    
    # Save the curried proxy
    curried_proxy = persistence_model.curried_proxies.create(curried_proxy)
    print(f"✅ Created curried proxy with ID: {curried_proxy.id}")
    
    # Create TasksManager for Python execution
    python_execution_manager = TasksManager(
        name="Brain Script Execution",
        model="gpt-4o-mini",
        description="Executes and analyzes the brain.py script which implements a left-brain/right-brain conversation model",
        messages=[
            Message(
                role="system",
                content="""You are an AI assistant specializing in executing and analyzing Python code,
                particularly the brain.py script which implements a left-brain/right-brain conversation model.
                
                Your capabilities include:
                1. Explaining how the brain.py script works
                2. Running the brain.py script with custom prompts
                3. Modifying the script to enhance its capabilities
                4. Analyzing the conversation results
                5. Suggesting improvements to the code
                
                When working with the brain.py script, you should:
                - Understand the left-brain/right-brain conversation model
                - Execute it with appropriate prompts
                - Analyze the conversation dynamics between the analytical left brain and creative right brain
                - Explain how the script could be used for generating ideas and solving problems
                
                Always prioritize safety and security when executing code."""
            ).dict()
        ]
    )
    python_execution_manager = persistence_model.tasksmanagers.create(python_execution_manager)
    print(f"✅ Created Brain Script Execution manager with ID: {python_execution_manager.id}")
    
    # Create task for explaining the brain.py script
    explain_brain_task = Task(
        name="Explain Brain Script",
        description="Explain how the brain.py script works and its potential applications",
        tasksmanager_id=python_execution_manager.id,
        curried_proxy_id=curried_proxy.id,
        use_context=True,
        inherit_manager_context=True,
        messages=[
            Message(
                role="system",
                content="""Your task is to explain how the brain.py script works and its potential applications.
                
                The brain.py script is located at 'src/experimental/brain.py' and implements a conversation model
                between a logical "left brain" and a creative "right brain" to generate ideas and solve problems.
                
                You should:
                1. Examine the code to understand its structure and functionality
                2. Explain the left-brain/right-brain conversation model
                3. Describe how the script generates and refines ideas
                4. Discuss potential applications for idea generation and problem-solving
                5. Highlight the strengths and limitations of the approach
                
                Focus on making the explanation clear and accessible, even for users without a technical background."""
            ).dict()
        ]
    )
    explain_brain_task = persistence_model.tasks.create(explain_brain_task)
    print(f"✅ Created explain brain task with ID: {explain_brain_task.id}")
    
    # Create task for running the brain.py script with custom prompts
    run_brain_task = Task(
        name="Run Brain Script",
        description="Run the brain.py script with a custom prompt to generate ideas",
        tasksmanager_id=python_execution_manager.id,
        curried_proxy_id=curried_proxy.id,
        use_context=True,
        inherit_manager_context=True,
        messages=[
            Message(
                role="system",
                content="""Your task is to run the brain.py script with custom prompts provided by the user.
                
                The brain.py script is located at 'src/experimental/brain.py' and needs to be modified
                to accept the user's prompt instead of using the hardcoded prompt.
                
                You should:
                1. Create a modified version of the script that accepts a command-line argument for the prompt
                2. Run the modified script with the user's prompt
                3. Analyze and explain the conversation between the left and right brain
                4. Highlight interesting ideas or insights generated during the conversation
                5. Suggest how the ideas could be further developed or refined
                
                When modifying the script, replace the hardcoded prompt with a command-line argument:
                
                ```python
                import sys
                
                # Get prompt from command line argument or use default
                initial_prompt = sys.argv[1] if len(sys.argv) > 1 else "Let's find an idea for a highly advanced technological startup with high economic impact."
                ```
                
                Then run the modified script with the user's prompt as an argument."""
            ).dict()
        ]
    )
    run_brain_task = persistence_model.tasks.create(run_brain_task)
    print(f"✅ Created run brain task with ID: {run_brain_task.id}")
    
    # Create task for modifying and enhancing the brain.py script
    modify_brain_task = Task(
        name="Modify Brain Script",
        description="Modify and enhance the brain.py script based on user requirements",
        tasksmanager_id=python_execution_manager.id,
        curried_proxy_id=curried_proxy.id,
        use_context=True,
        inherit_manager_context=True,
        messages=[
            Message(
                role="system",
                content="""Your task is to modify and enhance the brain.py script based on user requirements.
                
                The brain.py script is located at 'src/experimental/brain.py' and implements a conversation model
                between a logical "left brain" and a creative "right brain".
                
                You should:
                1. Understand the user's requirements for enhancing the script
                2. Create a modified version of the script with the requested enhancements
                3. Run the modified script to demonstrate the enhancements
                4. Explain the changes made and their impact on the script's functionality
                5. Suggest further improvements based on the results
                
                Possible enhancements might include:
                - Adding more specialized brain regions (e.g., emotional, intuitive, analytical)
                - Improving the conversation flow and termination conditions
                - Adding visualization of the conversation
                - Saving the generated ideas to a file
                - Implementing different conversation strategies
                
                Focus on making clean, efficient modifications that maintain the original code's intent
                while adding the requested functionality."""
            ).dict()
        ]
    )
    modify_brain_task = persistence_model.tasks.create(modify_brain_task)
    print(f"✅ Created modify brain task with ID: {modify_brain_task.id}")
    
    # Save the state
    state_location = StorageLocation(
        type=StorageType.file,
        location="state",
        state_name="brain_execution_state.json"
    )
    
    # Ensure the state directory exists
    os.makedirs("state", exist_ok=True)
    
    result = save_to_storage(persistence_model, state_location)
    print(f"✅ State saved: {result}")
    
    return {
        "python_execution_manager_id": python_execution_manager.id,
        "explain_brain_task_id": explain_brain_task.id,
        "run_brain_task_id": run_brain_task.id,
        "modify_brain_task_id": modify_brain_task.id,
        "curried_proxy_id": curried_proxy.id
    }

if __name__ == "__main__":
    asyncio.run(setup_python_execution_state()) 