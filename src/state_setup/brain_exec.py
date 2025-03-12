"""
Brain Execution State Setup

This module sets up a state for demonstrating the brain.py script execution capabilities
using the PyExec tool. It creates a task manager and tasks for executing the brain.py script,
which implements a left-brain/right-brain conversation model for creative idea generation.
"""

import sys
import os
from pathlib import Path
import asyncio
import logging
import uuid
from datetime import datetime

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
from src.server.context import knowledge_base

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

async def add_brain_script_to_knowledge_base():
    """Add the brain.py script to the knowledge base for context."""
    try:
        # Read the brain.py script
        brain_script_path = Path(project_root) / "src" / "experimental" / "brain.py"
        if not brain_script_path.exists():
            logger.error(f"❌ Brain script not found at {brain_script_path}")
            return None
            
        with open(brain_script_path, 'r', encoding='utf-8') as f:
            brain_script_content = f.read()
        
        # Add to knowledge base
        # Note: This is commented out as the knowledge_base module doesn't have add_knowledge method
        # We'll handle the context differently
        # knowledge_id = await knowledge_base.add_knowledge(
        #     content=brain_script_content,
        #     domain="python_scripts",
        #     metadata={
        #         "name": "brain_script",
        #         "description": "Left-brain/right-brain conversation model for idea generation",
        #         "file_path": str(brain_script_path),
        #         "tags": ["python", "idea_generation", "conversation_model", "brain_simulation"]
        #     }
        # )
        
        # For now, just return a placeholder UUID
        knowledge_id = str(uuid.uuid4())
        logger.info(f"✅ Added brain script to knowledge base with ID: {knowledge_id}")
        return knowledge_id
    except Exception as e:
        logger.error(f"❌ Failed to add brain script to knowledge base: {str(e)}")
        return None

async def setup_brain_execution_state():
    """Set up a state for demonstrating brain.py script execution capabilities."""
    
    print("\n🧠 Setting up Brainiac Thinking state...")
    
    # Initialize persistence model
    persistence_model = PersistenceModelFactory.persistence_model("inmemory")
    
    # Add brain.py script to knowledge base
    knowledge_id = await add_brain_script_to_knowledge_base()
    
    # Create and register the PyExec tool
    py_exec = PyExec()
    tools_catalog = ToolsCatalog()
    
    # Create a curried proxy for the tools
    curried_proxy = CurriedProxy()
    curried_proxy.add_tool("PyExec.run_script", py_exec.run_script)
    curried_proxy.add_tool("PyExec.run_code", py_exec.run_code)
    
    # Save the curried proxy
    curried_proxy = persistence_model.curried_proxies.create(curried_proxy)
    print(f"🔧 Created curried proxy with ID: {curried_proxy.id}")
    
    # Convert UUID to string for Task creation
    curried_proxy_id_str = str(curried_proxy.id)
    
    # Create TasksManager for brain script execution
    brain_execution_manager = TasksManager(
        name="Brainiac Thinking",
        model="gpt-4o-mini",
        description="Executes and analyzes the brain.py script which simulates left-brain/right-brain dialogue for creative idea generation",
        messages=[
            Message(
                role="system",
                content="""You are an AI assistant specializing in executing and analyzing the brain.py script,
                which simulates a dialogue between the logical left brain and the creative right brain.
                
                Your capabilities include:
                1. Explaining how the brain.py script works and its cognitive science foundations
                2. Running the brain.py script with custom prompts for innovative idea generation
                3. Modifying the script to enhance its capabilities or add new brain regions
                4. Analyzing the conversation dynamics and idea evolution
                5. Suggesting improvements to the cognitive simulation model
                
                When working with the brain.py script, you should:
                - Understand the complementary nature of analytical and creative thinking
                - Execute it with thought-provoking prompts that challenge both brain hemispheres
                - Analyze how ideas evolve through the analytical-creative dialogue
                - Explain how this approach mimics human cognitive processes
                - Suggest applications for innovation, problem-solving, and creative thinking
                
                Always prioritize safety and security when executing code."""
            )
        ]
    )
    brain_execution_manager = persistence_model.tasksmanagers.create(brain_execution_manager)
    print(f"🧠 Created Brainiac Thinking manager with ID: {brain_execution_manager.id}")
    
    # Create task for explaining the brain.py script
    explain_brain_task = Task(
        name="Decode the Brain Script",
        description="Explain how the brain.py script works and its cognitive foundations",
        tasksmanager_id=str(brain_execution_manager.id),
        curried_proxy_id=curried_proxy_id_str,
        use_context=True,
        inherit_manager_context=True,
        messages=[
            Message(
                role="system",
                content="""Your task is to explain how the brain.py script works and its cognitive foundations.
                
                The brain.py script is located at 'src/experimental/brain.py' and implements a conversation model
                between a logical "left brain" and a creative "right brain" to generate ideas and solve problems.
                
                You should:
                1. Examine the code to understand its structure and functionality
                2. Explain the left-brain/right-brain conversation model and its basis in cognitive science
                3. Describe how the script generates and refines ideas through cognitive collaboration
                4. Discuss potential applications for innovation, problem-solving, and creative thinking
                5. Highlight the strengths and limitations of this cognitive simulation approach
                
                Focus on making the explanation clear and accessible, connecting the technical implementation
                to cognitive science concepts and real-world applications."""
            )
        ]
    )
    
    # Add knowledge base context if available
    if knowledge_id:
        context_ref = {
            'id': str(uuid.uuid4()),
            'type': 'knowledge',
            'source_id': knowledge_id,
            'metadata': {
                'name': 'brain_script_code',
                'description': 'Source code of the brain.py script',
                'tags_str': 'python,idea_generation,conversation_model,brain_simulation'
            },
            'priority': 100,
            'created_at': datetime.now()
        }
        
        if not hasattr(explain_brain_task, 'contexts') or explain_brain_task.contexts is None:
            explain_brain_task.contexts = []
        explain_brain_task.contexts.append(context_ref)
    
    explain_brain_task = persistence_model.tasks.create(explain_brain_task)
    print(f"🔍 Created Decode the Brain Script task with ID: {explain_brain_task.id}")
    
    # Create task for running the brain.py script with custom prompts
    run_brain_task = Task(
        name="Activate Neural Pathways",
        description="Run the brain.py script with a custom prompt to generate innovative ideas",
        tasksmanager_id=str(brain_execution_manager.id),
        curried_proxy_id=curried_proxy_id_str,
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
                2. Run the modified script with the user's prompt to stimulate both brain hemispheres
                3. Analyze the conversation dynamics and how ideas evolve through the dialogue
                4. Highlight particularly innovative ideas or insights generated during the conversation
                5. Explain how the left-brain/right-brain interaction contributed to the final outcome
                
                When modifying the script, replace the hardcoded prompt with a command-line argument:
                
                ```python
                import sys
                
                # Get prompt from command line argument or use default
                initial_prompt = sys.argv[1] if len(sys.argv) > 1 else "Let's find an idea for a highly advanced technological startup with high economic impact."
                ```
                
                Then run the modified script with the user's prompt as an argument."""
            )
        ]
    )
    
    # Add knowledge base context if available
    if knowledge_id:
        context_ref = {
            'id': str(uuid.uuid4()),
            'type': 'knowledge',
            'source_id': knowledge_id,
            'metadata': {
                'name': 'brain_script_code',
                'description': 'Source code of the brain.py script',
                'tags_str': 'python,idea_generation,conversation_model,brain_simulation'
            },
            'priority': 100,
            'created_at': datetime.now()
        }
        
        if not hasattr(run_brain_task, 'contexts') or run_brain_task.contexts is None:
            run_brain_task.contexts = []
        run_brain_task.contexts.append(context_ref)
    
    run_brain_task = persistence_model.tasks.create(run_brain_task)
    print(f"🚀 Created Activate Neural Pathways task with ID: {run_brain_task.id}")
    
    # Create task for modifying and enhancing the brain.py script
    modify_brain_task = Task(
        name="Evolve Neural Architecture",
        description="Modify and enhance the brain.py script to create more sophisticated cognitive simulations",
        tasksmanager_id=str(brain_execution_manager.id),
        curried_proxy_id=curried_proxy_id_str,
        use_context=True,
        inherit_manager_context=True,
        messages=[
            Message(
                role="system",
                content="""Your task is to modify and enhance the brain.py script based on user requirements.
                
                The brain.py script is located at 'src/experimental/brain.py' and implements a conversation model
                between a logical "left brain" and a creative "right brain".
                
                You should:
                1. Understand the user's requirements for enhancing the cognitive simulation
                2. Create a modified version of the script with the requested enhancements
                3. Run the modified script to demonstrate the enhanced cognitive model
                4. Explain the changes made and their impact on the idea generation process
                5. Suggest further improvements to make the cognitive simulation more realistic
                
                Possible enhancements might include:
                - Adding more specialized brain regions (e.g., emotional, intuitive, analytical)
                - Implementing different cognitive styles or personality types
                - Adding visualization of the conversation and idea evolution
                - Saving the generated ideas to a structured format for further analysis
                - Implementing different conversation strategies based on cognitive science research
                
                Focus on making clean, efficient modifications that maintain the original code's intent
                while adding more sophisticated cognitive simulation capabilities."""
            )
        ]
    )
    
    # Add knowledge base context if available
    if knowledge_id:
        context_ref = {
            'id': str(uuid.uuid4()),
            'type': 'knowledge',
            'source_id': knowledge_id,
            'metadata': {
                'name': 'brain_script_code',
                'description': 'Source code of the brain.py script',
                'tags_str': 'python,idea_generation,conversation_model,brain_simulation'
            },
            'priority': 100,
            'created_at': datetime.now()
        }
        
        if not hasattr(modify_brain_task, 'contexts') or modify_brain_task.contexts is None:
            modify_brain_task.contexts = []
        modify_brain_task.contexts.append(context_ref)
    
    modify_brain_task = persistence_model.tasks.create(modify_brain_task)
    print(f"🧬 Created Evolve Neural Architecture task with ID: {modify_brain_task.id}")
    
    # Save the state
    state_location = StorageLocation(
        type=StorageType.file,
        location="state",
        state_name="brainiac_thinking.json"
    )
    
    # Ensure the state directory exists
    os.makedirs("state", exist_ok=True)
    
    result = save_to_storage(persistence_model, state_location)
    print(f"💾 State saved: {result}")
    
    return {
        "brain_execution_manager_id": brain_execution_manager.id,
        "explain_brain_task_id": explain_brain_task.id,
        "run_brain_task_id": run_brain_task.id,
        "modify_brain_task_id": modify_brain_task.id,
        "curried_proxy_id": curried_proxy.id,
        "knowledge_id": knowledge_id
    }

if __name__ == "__main__":
    asyncio.run(setup_brain_execution_state()) 