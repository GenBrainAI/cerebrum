import asyncio
import logging
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Import necessary modules
from src.server.persistence.persistence_model_factory import PersistenceModelFactory
from src.server.controllers.task_runner import TaskRunner
from src.server.controllers.curried_proxy import CurriedProxy

async def test_delegation_tool():
    """Test the delegation tool fix."""
    try:
        logger.info("Initializing persistence model...")
        persistence_model = PersistenceModelFactory.persistence_model()
        
        logger.info("Creating CurriedProxy...")
        curried_proxy = CurriedProxy()
        
        logger.info("Exporting tools to CrewAI...")
        crewai_tools = curried_proxy.export_to_crewai()
        
        # Find the delegation tool
        delegation_tool = None
        for tool in crewai_tools:
            if "delegate" in tool.name.lower() or "coworker" in tool.name.lower():
                delegation_tool = tool
                break
        
        if delegation_tool:
            logger.info(f"Found delegation tool: {delegation_tool.name}")
            logger.info(f"Description: {delegation_tool.description}")
            logger.info(f"Schema: {delegation_tool.args_schema.model_json_schema() if delegation_tool.args_schema else 'None'}")
            
            # Test the tool with dictionary inputs (simulating the error case)
            logger.info("\nTesting delegation tool with dictionary inputs...")
            try:
                result = await delegation_tool._arun(
                    task={"description": "Research concerts in New York", "type": "str"},
                    context={"description": "The user wants to find concerts in New York", "type": "str"},
                    coworker="Concert Researcher"
                )
                logger.info(f"Result: {result}")
                logger.info("✅ Delegation tool handled dictionary inputs correctly!")
            except Exception as e:
                logger.error(f"❌ Delegation tool failed with dictionary inputs: {str(e)}")
                logger.exception(e)
            
            # Test the tool with string inputs (correct case)
            logger.info("\nTesting delegation tool with string inputs...")
            try:
                result = await delegation_tool._arun(
                    task="Research concerts in New York",
                    context="The user wants to find concerts in New York",
                    coworker="Concert Researcher"
                )
                logger.info(f"Result: {result}")
                logger.info("✅ Delegation tool handled string inputs correctly!")
            except Exception as e:
                logger.error(f"❌ Delegation tool failed with string inputs: {str(e)}")
                logger.exception(e)
        else:
            logger.error("❌ Delegation tool not found in exported tools!")
        
        logger.info("\nTest completed!")
    except Exception as e:
        logger.error(f"Test failed with error: {str(e)}")
        logger.exception(e)

if __name__ == "__main__":
    asyncio.run(test_delegation_tool()) 