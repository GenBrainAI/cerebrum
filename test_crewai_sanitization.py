import asyncio
import logging
import datetime
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Import the sanitization functions
from src.server.controllers.crew_runner import sanitize_data
from src.server.controllers.task_runner import TaskRunner
from src.server.persistence.persistence_model_factory import PersistenceModelFactory

def test_sanitize_data():
    """Test the sanitize_data function with various data types."""
    # Create test data with datetime objects
    test_data = {
        "string": "test",
        "int": 123,
        "float": 123.45,
        "bool": True,
        "none": None,
        "datetime": datetime.datetime.now(),
        "date": datetime.date.today(),
        "list": [1, 2, datetime.datetime.now()],
        "nested_dict": {
            "key": "value",
            "datetime": datetime.datetime.now(),
            "list": [1, datetime.date.today()]
        },
        "complex_object": object()
    }
    
    # Sanitize the data
    sanitized = sanitize_data(test_data)
    
    # Check that all datetime objects are converted to strings
    logger.info("Original data:")
    logger.info(f"  datetime: {type(test_data['datetime'])}")
    logger.info(f"  date: {type(test_data['date'])}")
    logger.info(f"  list[2]: {type(test_data['list'][2])}")
    logger.info(f"  nested_dict.datetime: {type(test_data['nested_dict']['datetime'])}")
    logger.info(f"  nested_dict.list[1]: {type(test_data['nested_dict']['list'][1])}")
    logger.info(f"  complex_object: {type(test_data['complex_object'])}")
    
    logger.info("\nSanitized data:")
    logger.info(f"  datetime: {type(sanitized['datetime'])}")
    logger.info(f"  date: {type(sanitized['date'])}")
    logger.info(f"  list[2]: {type(sanitized['list'][2])}")
    logger.info(f"  nested_dict.datetime: {type(sanitized['nested_dict']['datetime'])}")
    logger.info(f"  nested_dict.list[1]: {type(sanitized['nested_dict']['list'][1])}")
    logger.info(f"  complex_object: {type(sanitized['complex_object'])}")
    
    # Verify all values are of supported types
    assert isinstance(sanitized['datetime'], str)
    assert isinstance(sanitized['date'], str)
    assert isinstance(sanitized['list'][2], str)
    assert isinstance(sanitized['nested_dict']['datetime'], str)
    assert isinstance(sanitized['nested_dict']['list'][1], str)
    assert isinstance(sanitized['complex_object'], str)
    
    logger.info("✅ All datetime objects successfully converted to strings")
    logger.info(f"Sanitized data: {sanitized}")

async def test_task_runner_sanitization():
    """Test the TaskRunner's sanitization method."""
    # Create a TaskRunner instance
    persistence_model = PersistenceModelFactory.persistence_model()
    task_runner = TaskRunner(persistence_model)
    
    # Create test data with datetime objects
    test_data = {
        "string": "test",
        "datetime": datetime.datetime.now(),
        "date": datetime.date.today(),
        "list": [1, 2, datetime.datetime.now()],
        "nested_dict": {
            "key": "value",
            "datetime": datetime.datetime.now()
        }
    }
    
    # Sanitize the data
    sanitized = task_runner._sanitize_for_crewai(test_data)
    
    # Verify all values are of supported types
    assert isinstance(sanitized['datetime'], str)
    assert isinstance(sanitized['date'], str)
    assert isinstance(sanitized['list'][2], str)
    assert isinstance(sanitized['nested_dict']['datetime'], str)
    
    logger.info("✅ TaskRunner sanitization works correctly")
    logger.info(f"Sanitized data: {sanitized}")

async def main():
    """Run all tests."""
    logger.info("Testing sanitize_data function...")
    test_sanitize_data()
    
    logger.info("\nTesting TaskRunner sanitization...")
    await test_task_runner_sanitization()
    
    logger.info("\n✅ All tests passed!")

if __name__ == "__main__":
    asyncio.run(main()) 