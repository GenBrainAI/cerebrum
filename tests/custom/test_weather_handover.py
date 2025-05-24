import asyncio
import uuid
import logging

# Configure basic logging for the test
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Model and Controller Imports ---
from src.server.models.task import Task
from src.server.models.tasks_manager import TasksManager
from src.server.models.message import Message
from src.server.models.curried_proxy_info import ToolInfo # For CurriedProxy tool addition
from src.server.persistence.persistence_model_factory import PersistenceModelFactory
from src.server.controllers.task_runner import TaskRunner
# TaskSequenceController is usually part of TaskRunner, so direct import might not be needed if using runner's instance
# from src.server.controllers.task_sequence_controller import TaskSequenceController
from src.server.controllers.curried_proxy import CurriedProxy

# --- Tool Imports ---
from src.server.tools.weather_tool import WeatherTool # Assuming this is the correct path

async def main():
    logger.info("Starting Weather Handover Test Script")

    # 1. Setup: Persistence Model and TaskRunner
    logger.info("Initializing InMemoryPersistenceModel and TaskRunner...")
    persistence_model_factory = PersistenceModelFactory()
    # Reset factory state and ensure in-memory is used for this test
    PersistenceModelFactory.reset() 
    persistence_model = persistence_model_factory.persistence_model(type="inmemory")
    
    task_runner = TaskRunner(persistence_model=persistence_model)
    await task_runner.initialize() # Initialize plugins, etc.

    # TaskSequenceController is initialized within TaskRunner
    sequence_controller = task_runner.sequence_controller
    if not sequence_controller:
        logger.error("TaskSequenceController not initialized in TaskRunner!")
        return
    logger.info("TaskRunner and TaskSequenceController initialized.")

    # 2. Tool and Proxy Setup
    logger.info("Setting up WeatherTool and CurriedProxy...")
    weather_tool_instance = WeatherTool()
    
    proxy = CurriedProxy(name="WeatherProxyTest")
    
    # Adding tool methods to the proxy.
    # The CurriedProxy's add_tool method takes the name and the callable.
    # Description is auto-derived from docstrings.
    proxy.add_tool("weather.get_weather", weather_tool_instance.get_weather)
    proxy.add_tool("weather.get_forecast", weather_tool_instance.get_forecast)
    
    # Persist the proxy
    created_proxy = persistence_model.curried_proxies.create(proxy)
    if not created_proxy:
        logger.error(f"Failed to create proxy: {proxy.id}")
        # Fallback if create doesn't return the object with ID (depends on persistence implementation)
        proxy_id = proxy.id 
        if not persistence_model.curried_proxies.read(proxy_id): # Check if it was persisted
             logger.error(f"Proxy {proxy_id} was not found after attempting creation.")
             return
    else:
        proxy_id = created_proxy.id

    logger.info(f"WeatherTool and CurriedProxy (ID: {proxy_id}) setup complete.")

    # 3. TasksManager Setup
    logger.info("Setting up TasksManager...")
    tasks_manager = TasksManager(
        id=str(uuid.uuid4()), # Ensure ID is set if create doesn't auto-generate
        name="WeatherHandoverTestManager", 
        model="gpt-4o-mini", # Specify a model, important for TaskRunner
        description="Manager for testing weather and clothing recommendation sequence."
    )
    created_manager = persistence_model.tasksmanagers.create(tasks_manager)
    if not created_manager:
        logger.error(f"Failed to create TasksManager: {tasks_manager.id}")
        # Fallback if create doesn't return the object with ID
        manager_id = tasks_manager.id
        if not persistence_model.tasksmanagers.read(manager_id):
            logger.error(f"TasksManager {manager_id} was not found after attempting creation.")
            return
    else:
        manager_id = created_manager.id
    logger.info(f"TasksManager (ID: {manager_id}) setup complete.")

    # 4. Task Definitions
    logger.info("Defining Tasks...")
    # Task 1: GetWeatherForParis
    task1_id = str(uuid.uuid4())
    task1_messages = [Message(role="user", content="What is the weather in Paris?")]
    task1 = Task(
        id=task1_id,
        name="GetWeatherForParis",
        description="Fetches the current weather for Paris. Uses the weather.get_weather tool.",
        tasksmanager_id=str(manager_id), # Ensure string
        curried_proxy_id=str(proxy_id), # Ensure string
        messages=task1_messages,
        framework=None # Ensure not CrewAI
    )
    created_task1 = persistence_model.tasks.create(task1)
    if not created_task1: # Check based on your persistence model's behavior
        logger.error(f"Failed to create Task 1: {task1_id}")
        # Fallback if create doesn't return the object with ID
        if not persistence_model.tasks.read(task1_id):
            logger.error(f"Task 1 {task1_id} was not found after attempting creation.")
            return
    logger.info(f"Task 1 'GetWeatherForParis' (ID: {task1.id}) created.")

    # Task 2: RecommendClothingForParis
    task2_id = str(uuid.uuid4())
    task2_system_message = Message(role="system", content="You are a helpful clothing recommendation assistant. Based on the weather information provided in the context from the previous step (current weather in Paris), suggest appropriate attire. If no specific weather details are available, say so.")
    task2_user_message = Message(role="user", content="Based on the weather information for Paris, what should I wear?")
    task2_messages = [task2_system_message, task2_user_message]
    
    task2 = Task(
        id=task2_id,
        name="RecommendClothingForParis",
        description="Recommends clothing based on the weather in Paris, using context from the GetWeatherForParis task.",
        tasksmanager_id=str(manager_id), # Ensure string
        curried_proxy_id=str(proxy_id), # Ensure string
        messages=task2_messages,
        framework=None, # Ensure not CrewAI
        # No explicit input_from_tasks field, relying on sequence controller context passing
    )
    created_task2 = persistence_model.tasks.create(task2)
    if not created_task2:
        logger.error(f"Failed to create Task 2: {task2_id}")
        if not persistence_model.tasks.read(task2_id):
            logger.error(f"Task 2 {task2_id} was not found after attempting creation.")
            return
    logger.info(f"Task 2 'RecommendClothingForParis' (ID: {task2.id}) created.")

    # 5. Sequence Execution
    logger.info("Executing task sequence...")
    task_ids_list = [task1.id, task2.id]
    initial_context = {
        "user_query_for_sequence": "What's the weather in Paris and what should I wear?" 
        # This context can be used by the sequence controller if needed, 
        # but tasks have their own messages.
    }

    try:
        sequence_result = await sequence_controller.execute_sequence(
            tasksmanager_id=manager_id,
            task_ids=task_ids_list,
            initial_context=initial_context
        )
    except Exception as e:
        logger.error(f"Error during sequence execution: {e}", exc_info=True)
        return

    logger.info(f"Sequence execution completed. Result: {sequence_result}")

    # 6. Assertions
    assert sequence_result is not None, "Sequence result should not be None"
    assert sequence_result.get("status") == "completed", \
        f"Sequence status should be 'completed', but was '{sequence_result.get('status')}' with error: {sequence_result.get('error')}"
    
    results_dict = sequence_result.get("results", {})
    assert len(results_dict) == 2, f"Expected 2 results in results_dict, got {len(results_dict)}"

    task1_result = results_dict.get(task1.id)
    task2_result = results_dict.get(task2.id)

    assert task1_result is not None, f"Task 1 result not found for ID {task1.id}"
    assert task2_result is not None, f"Task 2 result not found for ID {task2.id}"

    # Note: With a dummy API key, tasks making LLM calls will fail.
    # The assertions below will likely fail on 'status == "completed"'.
    # For this test execution, we are primarily checking if the sequence runs and attempts the tasks.
    # A more robust test for context handover would mock LLM/tool responses.

    assert task1_result.get("status") == "completed", \
        f"Task 1 status should be 'completed', got '{task1_result.get('status')}', error: {task1_result.get('error')}"
    
    assert task2_result.get("status") == "completed", \
        f"Task 2 status should be 'completed', got '{task2_result.get('status')}', error: {task2_result.get('error')}"

    logger.info(f"Task 1 ('{task1.name}') response: {task1_result.get('response')}") # Will log the error response
    logger.info(f"Task 2 ('{task2.name}') response: {task2_result.get('response')}") # Will log the error response

    # Crucial Assertion: Verify Task 2 used Task 1's output.
    # This is an indirect check. We expect Task 1 to output weather for Paris.
    # Task 2 should then recommend clothing based on plausible Paris weather.
    # For example, if Paris is often cool and rainy, recommendations might include jackets/umbrellas.
    # If it were sunny and hot, it'd be different.
    # The key is that the recommendation is specific enough to imply weather knowledge.
    
    task2_response_text = task2_result.get("response", "").lower() if task2_result else ""
    
    # Check for general weather-related clothing terms
    # These assertions will likely fail if the task itself failed due to API key error,
    # as the response will be an error message.
    if task2_result and task2_result.get("status") == "completed":
        weather_clothing_keywords = ["wear", "clothing", "attire", "dress", "jacket", "coat", "sweater", "shirt", 
                                     "pants", "trousers", "shorts", "umbrella", "boots", "shoes", "scarf", 
                                     "hat", "gloves", "layers", "sunglasses"]
        
        # Check for terms that might indicate weather conditions were considered
        weather_condition_hints = ["weather", "temperature", "rain", "sunny", "cloudy", "windy", "cold", "warm", "cool", "hot", "forecast"]

        found_clothing_keyword = any(keyword in task2_response_text for keyword in weather_clothing_keywords)
        found_condition_hint = any(keyword in task2_response_text for keyword in weather_condition_hints)
        
        assert found_clothing_keyword, \
            f"Task 2 response does not seem to contain clothing recommendations. Response: {task2_response_text}"

        assert found_condition_hint or "paris" in task2_response_text, \
            f"Task 2 response does not seem to acknowledge weather conditions or the location (Paris). Response: {task2_response_text}"
        logger.info("Content assertions for Task 2 passed (task was completed).")
    else:
        logger.warning(f"Skipping content assertions for Task 2 as its status was not 'completed'. Status: {task2_result.get('status') if task2_result else 'N/A'}")


    logger.info("All structural assertions passed!") # This might be reached even if tasks failed.
    logger.info("Weather Handover Test Script completed successfully.")

if __name__ == "__main__":
    asyncio.run(main())
