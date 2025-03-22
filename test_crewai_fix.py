import asyncio
import logging
import os
import sys
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

async def test_crewai_task():
    """Test the CrewAI task execution with the fixed implementation."""
    try:
        logger.info("Initializing persistence model...")
        persistence_model = PersistenceModelFactory.persistence_model()
        
        logger.info("Creating TaskRunner...")
        task_runner = TaskRunner(persistence_model)
        
        logger.info("Initializing TaskRunner...")
        await task_runner.initialize()
        
        logger.info("TaskRunner initialized successfully!")
        
        # You would need a valid task ID and tasksmanager ID to test further
        # For now, we'll just verify that the initialization works
        
        logger.info("Test completed successfully!")
    except Exception as e:
        logger.error(f"Test failed with error: {str(e)}")
        logger.exception(e)

if __name__ == "__main__":
    asyncio.run(test_crewai_task()) 