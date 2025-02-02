import sys
from pathlib import Path
import asyncio
import logging
from datetime import datetime

# Add project root to Python path
project_root = str(Path(__file__).parents[2])  # Go up two levels to reach project root
sys.path.append(project_root)

from src.server.persistence.persistence_model_factory import PersistenceModelFactory
from src.server.models.persistence_models import StorageLocation, StorageType
from src.server.models.task import Task
from src.server.controllers.persistence_controller import load_from_storage
from src.server.controllers.task_runner import TaskRunner
from src.server.models.message import Message
from src.server.models.tools_catalog import ToolsCatalog
from src.server.controllers.curried_proxy import CurriedProxy

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

async def run_dynamic_tool_creation(prompt: str):
    """Load state and run dynamic tool creation with the given prompt."""
    try:
        print("\n🔍 DEBUG: Initial Tools Status (Before State Load)")
        tools_catalog = ToolsCatalog()
        
        # Tools are now initialized in ToolsCatalog._initialize_default_tools
        print("\n📦 Initial Tools in Catalog:")
        catalog_tools = tools_catalog.list_tools()
        for tool in sorted(catalog_tools):
            metadata = tools_catalog.get_tool(tool)
            print(f"  - {tool}")
            if metadata:
                print(f"    Type: {metadata.tool_type}")
                description = metadata.description.split('\n')[0] if metadata.description else ''
                print(f"    Description: {description}")
                if metadata.parameters:
                    print(f"    Parameters: {[p.name for p in metadata.parameters]}")

        # Initialize persistence model
        persistence_model = PersistenceModelFactory.persistence_model("inmemory")
        
        # Load state
        state_location = StorageLocation(
            type=StorageType.file,
            location="persistent_state",
            state_name="dynamic_tools_state.json"
        )
        
        if not Path(f"{state_location.location}/{state_location.state_name}").exists():
            logger.error("❌ No state file found. Please run dynamic_tools.py first to set up the state.")
            return
        
        logger.info("🔄 Loading persistence state...")
        state_data = load_from_storage(state_location)
        logger.info("✅ State loaded successfully")

        print("\n🔍 DEBUG: Tools Status After State Load")
        # Debug prints for tools registration
        tools_catalog = ToolsCatalog()
        print("\n📦 Tools in Catalog:")
        catalog_tools = tools_catalog.list_tools()
        for tool in sorted(catalog_tools):
            metadata = tools_catalog.get_tool(tool)
            print(f"  - {tool}")
            if metadata:
                print(f"    Type: {metadata.tool_type}")
                description = metadata.description.split('\n')[0] if metadata.description else ''
                print(f"    Description: {description}")
                if metadata.parameters:
                    print(f"    Parameters: {[p.name for p in metadata.parameters]}")

        # Get curried proxy from persistence model
        curried_proxies = persistence_model.curried_proxies.list()
        if curried_proxies:
            curried_proxy = curried_proxies[0]
            print("\n🔧 Tools in CurriedProxy:")
            proxy_tools = curried_proxy.list_tools()
            for tool in sorted(proxy_tools):
                print(f"  - {tool}")
                tool_metadata = curried_proxy.get_tool(tool)
                if tool_metadata:
                    print(f"    Type: {tool_metadata.tool_type}")
                    description = tool_metadata.description.split('\n')[0] if tool_metadata.description else ''
                    print(f"    Description: {description}")
        else:
            print("\n❌ No CurriedProxy found in persistence model")
        
        # Get existing task
        tasks = persistence_model.tasks.list()
        if not tasks:
            logger.error("❌ No tasks found in state")
            return
            
        task = tasks[0]
        logger.info(f"📋 Found task: {task.id}")
        
        # Get CrewAI config
        crewai_config = persistence_model.crewai_config.read(task.crewai_config_id)
        if not crewai_config:
            logger.error("❌ CrewAI config not found")
            return
        logger.info(f"⚙️ Found CrewAI config: {crewai_config.id}")
        
        # Initialize task runner
        task_runner = TaskRunner(persistence_model)
        await task_runner.initialize()
        logger.info("✅ Task runner initialized")
        
        # Create message context
        message = Message(
            role="user",
            content=prompt,
            created_at=datetime.now().isoformat(),
            updated_at=datetime.now().isoformat()
        )
        
        # Run the task with the message
        logger.info("🚀 Running task with prompt...")
        result = await task_runner.run_task(
            tasksmanager_id=task.tasksmanager_id,
            task_id=task.id,
            running_extra_params={'messages': [message]}
        )
        
        # Process response
        if isinstance(result, dict) and 'response' in result:
            response_text = result['response']
        else:
            response_text = str(result)
            
        logger.info("✅ Task execution completed")
        logger.info(f"📊 Result: {response_text}")
        
        return response_text
        
    except Exception as e:
        logger.error(f"❌ Error running dynamic tool creation: {str(e)}")
        raise

if __name__ == "__main__":
    prompt = """Create a standalone Python tool that calculates the Fibonacci sequence for complex numbers.

Requirements:
1. The tool must be saved as 'complex_fibonacci_tool.py' in the dist directory
2. Initial values should be i+i and i+2i (where i is the imaginary unit)
3. The tool should calculate F(n) = F(n-1) + F(n-2) where the numbers are complex
4. Include these features:
   - Type hints for all functions
   - Proper error handling
   - Unit tests
   - Documentation with examples
   - A main function demonstrating usage

Example usage:
```python
fib = ComplexFibonacci()
result = fib.calculate(5)  # Calculate 5th number in sequence
```

DO NOT create a web service or API - just implement the pure Python calculation tool.
The implementation should focus on the actual complex number Fibonacci sequence calculation."""
    
    try:
        asyncio.run(run_dynamic_tool_creation(prompt))
    except Exception as e:
        logger.error(f"❌ Failed to run dynamic tool creation: {str(e)}")
        sys.exit(1) 