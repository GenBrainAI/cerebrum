import sys
from pathlib import Path
import asyncio
import logging
from datetime import datetime
from typing import Optional, Dict, Any

# Add project root to Python path
project_root = str(Path(__file__).parents[2])  # Go up two levels to reach project root
sys.path.append(project_root)

from src.server.persistence.persistence_model_factory import PersistenceModelFactory
from src.server.models.persistence_models import StorageLocation, StorageType
from src.server.models.task import Task
from src.server.controllers.persistence_controller import load_from_storage
from src.server.controllers.task_runner import TaskRunner
from src.server.models.message import Message
from src.server.tools.tools_catalog import tools_catalog
from src.server.controllers.curried_proxy import CurriedProxy
from src.server.models.agent import Process
from src.server.context.unified_context_manager import UnifiedContextManager
from langchain_openai import ChatOpenAI

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

class DynamicToolRunner:
    """Manages the dynamic tool creation process with improved context and state management."""
    
    def __init__(self):
        self.persistence_model = PersistenceModelFactory.persistence_model("inmemory")
        self.tools_catalog = tools_catalog  # Use the global instance
        self.context_manager = UnifiedContextManager()
        self.task_runner: Optional[TaskRunner] = None
        self.manager_llm = ChatOpenAI(
            model_name="gpt-4",
            temperature=0.7,
            max_tokens=4000
        )
        
    async def initialize(self):
        """Initialize the runner and load necessary components."""
        await self.load_state()
        await self.initialize_task_runner()
        await self.context_manager.initialize()
        
    async def load_state(self):
        """Load state from storage."""
        state_location = StorageLocation(
            type=StorageType.file,
            location="state/specialized",
            state_name="dynamic_tools_state.json"
        )
        
        if not Path(f"{state_location.location}/{state_location.state_name}").exists():
            raise FileNotFoundError("❌ No state file found. Please run dynamic_tools.py first to set up the state.")
            
        logger.info("🔄 Loading persistence state...")
        state_data = load_from_storage(state_location)
        logger.info("✅ State loaded successfully")
        
        await self._validate_state()
        
    async def _validate_state(self):
        """Validate loaded state and configurations."""
        # Validate tools catalog
        catalog_tools = self.tools_catalog.list_tools()
        if not catalog_tools:
            raise ValueError("❌ No tools found in catalog")
        logger.info(f"📦 Found {len(catalog_tools)} tools in catalog")
            
        # Validate curried proxies
        curried_proxies = self.persistence_model.curried_proxies.list()
        if not curried_proxies:
            raise ValueError("❌ No CurriedProxy found in persistence model")
        logger.info(f"🔧 Found CurriedProxy: {curried_proxies[0].id}")
            
        # Validate tasks
        tasks = self.persistence_model.tasks.list()
        if not tasks:
            raise ValueError("❌ No tasks found in state")
        logger.info(f"📋 Found task: {tasks[0].id}")
            
        # Validate CrewAI config
        task = tasks[0]
        crewai_config = self.persistence_model.crewai_config.read(task.crewai_config_id)
        if not crewai_config:
            raise ValueError("❌ CrewAI config not found")
        logger.info(f"⚙️ Found CrewAI config: {crewai_config.id}")
            
    async def initialize_task_runner(self):
        """Initialize the task runner with proper configuration."""
        self.task_runner = TaskRunner(self.persistence_model)
        await self.task_runner.initialize()
        logger.info("✅ Task runner initialized")
        
    def _create_message_context(self, prompt: str) -> Message:
        """Create a message with context for task execution."""
        return Message(
            role="user",
            content=prompt,
            created_at=datetime.now().isoformat(),
            updated_at=datetime.now().isoformat()
        )
        
    async def run_tool_creation(self, prompt: str, process_type: Process = Process.hierarchical) -> str:
        """Run the dynamic tool creation process with the specified process type."""
        try:
            await self.initialize()
            
            # Get task and update process type if needed
            tasks = self.persistence_model.tasks.list()
            task = tasks[0]
            
            # Update CrewAI config with process type
            crewai_config = self.persistence_model.crewai_config.read(task.crewai_config_id)
            crewai_config.process = process_type
            self.persistence_model.crewai_config.update(task.crewai_config_id, crewai_config)
            
            # Create message with context
            message = self._create_message_context(prompt)
            
            # Prepare context for task execution
            context = await self.context_manager.prepare_context(task.id)
            
            # Run the task with context
            logger.info("🚀 Running task with prompt...")
            result = await self.task_runner.run_task(
                tasksmanager_id=task.tasksmanager_id,
                task_id=task.id,
                running_extra_params={
                    'messages': [message],
                    'context': context,
                    'process_type': process_type
                }
            )
            
            # Process and validate response
            response_text = self._process_result(result)
            
            # Update context with results
            await self.context_manager.update_context(task.id, {
                'last_result': response_text,
                'last_execution_time': datetime.now().isoformat()
            })
            
            logger.info("✅ Task execution completed")
            logger.info(f"📊 Result: {response_text}")
            
            return response_text
            
        except Exception as e:
            logger.error(f"❌ Error running dynamic tool creation: {str(e)}")
            raise
            
    def _process_result(self, result: Any) -> str:
        """Process and validate the task execution result."""
        if isinstance(result, dict) and 'response' in result:
            return result['response']
        return str(result)

async def run_dynamic_tool_creation(prompt: str) -> str:
    """Main entry point for dynamic tool creation."""
    runner = DynamicToolRunner()
    return await runner.run_tool_creation(prompt)

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