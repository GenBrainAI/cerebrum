import json
import os

# Define the notebook content
notebook = {
    "cells": [
        {
            "cell_type": "markdown",
            "metadata": {},
            "source": [
                "# Cerebrum Weather Assistant Example\n",
                "\n",
                "This notebook demonstrates how to use the Cerebrum framework as a library to create a weather assistant that provides clothing recommendations based on weather conditions."
            ]
        },
        {
            "cell_type": "markdown",
            "metadata": {},
            "source": [
                "## Setup and Imports\n",
                "\n",
                "First, let's import the necessary modules from the Cerebrum framework."
            ]
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "source": [
                "import sys\n",
                "import os\n",
                "from pathlib import Path\n",
                "import uuid\n",
                "from datetime import datetime\n",
                "\n",
                "# Add the project root to the Python path\n",
                "project_root = str(Path().resolve().parents[0])\n",
                "sys.path.append(project_root)\n",
                "\n",
                "from src.server.persistence.persistence_model_factory import PersistenceModelFactory\n",
                "from src.server.models.tasks_manager import TasksManager\n",
                "from src.server.models.task import Task\n",
                "from src.server.models.message import Message\n",
                "from src.server.controllers.curried_proxy import CurriedProxy\n",
                "from src.server.tools.weather_tool import WeatherTool\n",
                "from src.server.controllers.task_runner import TaskRunner"
            ]
        },
        {
            "cell_type": "markdown",
            "metadata": {},
            "source": [
                "## Initialize Persistence Model\n",
                "\n",
                "Create an in-memory persistence model to store our tasks and tools."
            ]
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "source": [
                "# Initialize persistence model\n",
                "persistence_model = PersistenceModelFactory.persistence_model(\"inmemory\")\n",
                "print(\"✅ Initialized in-memory persistence model\")"
            ]
        },
        {
            "cell_type": "markdown",
            "metadata": {},
            "source": [
                "## Create and Register Weather Tools\n",
                "\n",
                "Set up the weather tools and register them with a curried proxy."
            ]
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "source": [
                "# Create weather tool\n",
                "weather_tool = WeatherTool()\n",
                "\n",
                "# Create a curried proxy for the tools\n",
                "curried_proxy = CurriedProxy()\n",
                "curried_proxy.add_tool(\"weather.get_weather\", weather_tool.get_weather)\n",
                "curried_proxy.add_tool(\"weather.get_forecast\", weather_tool.get_forecast)\n",
                "\n",
                "# Save the curried proxy\n",
                "curried_proxy = persistence_model.curried_proxies.create(curried_proxy)\n",
                "curried_proxy_id_str = str(curried_proxy.id)\n",
                "print(f\"✅ Created curried proxy with ID: {curried_proxy_id_str}\")"
            ]
        },
        {
            "cell_type": "markdown",
            "metadata": {},
            "source": [
                "## Create Weather Task Manager\n",
                "\n",
                "Create a task manager for weather-related tasks."
            ]
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "source": [
                "# Create TasksManager for weather\n",
                "weather_manager = TasksManager(\n",
                "    name=\"WeatherManager\",\n",
                "    model=\"gpt-4o-mini\",\n",
                "    description=\"Manages tasks for weather reporting and clothing recommendations.\",\n",
                "    messages=[\n",
                "        Message(\n",
                "            role=\"system\",\n",
                "            content=\"You are a helpful assistant.\"\n",
                "        )\n",
                "    ]\n",
                ")\n",
                "weather_manager = persistence_model.tasksmanagers.create(weather_manager)\n",
                "print(f\"✅ Created Weather Manager with ID: {weather_manager.id}\")"
            ]
        },
        {
            "cell_type": "markdown",
            "metadata": {},
            "source": [
                "## Create Clothing Recommendation Task\n",
                "\n",
                "Create a task that provides clothing recommendations based on weather conditions."
            ]
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "source": [
                "# Create task for clothing recommendations\n",
                "clothing_task = Task(\n",
                "    name=\"WhatToWear\",\n",
                "    description=\"Provides clothing recommendations based on weather conditions\",\n",
                "    tasksmanager_id=str(weather_manager.id),\n",
                "    curried_proxy_id=curried_proxy_id_str,\n",
                "    use_context=True,\n",
                "    inherit_manager_context=True,\n",
                "    messages=[\n",
                "        Message(\n",
                "            role=\"system\",\n",
                "            content=\"\"\"You are a clothing recommendation assistant specialized in weather-appropriate attire. Your role is to provide helpful, practical clothing suggestions based on weather conditions.\n",
                "\n",
                "When making recommendations, consider:\n",
                "\n",
                "1. Temperature ranges:\n",
                "   - Hot (>85°F/30°C): Lightweight, breathable fabrics\n",
                "   - Warm (70-85°F/21-30°C): Light layers, short sleeves\n",
                "   - Mild (55-70°F/13-21°C): Light jackets, long sleeves\n",
                "   - Cool (40-55°F/4-13°C): Sweaters, light coats\n",
                "   - Cold (25-40°F/-4-4°C): Heavy coats, layers, hats\n",
                "   - Very cold (<25°F/-4°C): Thermal layers, heavy insulation\n",
                "\n",
                "2. Precipitation:\n",
                "   - Rain: Waterproof jackets, umbrellas, water-resistant footwear\n",
                "   - Snow: Waterproof boots, insulated coats, gloves, hats\n",
                "   - Sleet/Ice: Non-slip footwear, waterproof outer layers\n",
                "\n",
                "3. Wind conditions:\n",
                "   - Windy: Wind-resistant layers, secured accessories\n",
                "   - Gusty: Avoid loose clothing, use windbreakers\n",
                "\n",
                "4. Humidity levels:\n",
                "   - High humidity: Moisture-wicking fabrics, breathable materials\n",
                "   - Low humidity: Hydrating fabrics, skin protection\n",
                "\n",
                "5. UV exposure:\n",
                "   - Sunny: Hats, sunglasses, UV-protective clothing\n",
                "   - Overcast: Still consider UV protection\n",
                "\n",
                "6. Activity level:\n",
                "   - Active: Moisture-wicking, flexible clothing\n",
                "   - Casual: Comfortable, appropriate layers\n",
                "   - Formal: Weather-appropriate professional attire\n",
                "\n",
                "Always ask for specific weather details if not provided. Tailor recommendations to the user's location, planned activities, and personal preferences. Provide practical, specific suggestions rather than general advice.\"\"\"\n",
                "        )\n",
                "    ]\n",
                ")\n",
                "clothing_task = persistence_model.tasks.create(clothing_task)\n",
                "print(f\"✅ Created Clothing Recommendation Task with ID: {clothing_task.id}\")"
            ]
        },
        {
            "cell_type": "markdown",
            "metadata": {},
            "source": [
                "## Create Task Runner\n",
                "\n",
                "Initialize the task runner to execute our tasks."
            ]
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "source": [
                "# Create task runner\n",
                "task_runner = TaskRunner(persistence_model)\n",
                "print(\"✅ Created Task Runner\")"
            ]
        },
        {
            "cell_type": "markdown",
            "metadata": {},
            "source": [
                "## Function to Get Weather and Clothing Recommendations\n",
                "\n",
                "Create a function that takes a location and returns weather information and clothing recommendations."
            ]
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "source": [
                "async def get_weather_and_clothing_recommendations(location: str):\n",
                "    \"\"\"Get weather information and clothing recommendations for a location.\"\"\"\n",
                "    # Create a new chat session\n",
                "    session_id = f\"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}\"\n",
                "    \n",
                "    # First message to get weather information\n",
                "    weather_query = f\"What is the weather in {location}?\"\n",
                "    weather_response = await task_runner.run_task(\n",
                "        task_id=str(clothing_task.id),\n",
                "        message=weather_query,\n",
                "        session_id=session_id\n",
                "    )\n",
                "    \n",
                "    # Second message to get clothing recommendations\n",
                "    clothing_query = f\"What should I wear for this weather in {location}?\"\n",
                "    clothing_response = await task_runner.run_task(\n",
                "        task_id=str(clothing_task.id),\n",
                "        message=clothing_query,\n",
                "        session_id=session_id\n",
                "    )\n",
                "    \n",
                "    return {\n",
                "        \"location\": location,\n",
                "        \"weather_info\": weather_response,\n",
                "        \"clothing_recommendations\": clothing_response\n",
                "    }"
            ]
        },
        {
            "cell_type": "markdown",
            "metadata": {},
            "source": [
                "## Try It Out\n",
                "\n",
                "Let's test our weather assistant with different locations."
            ]
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "source": [
                "import asyncio\n",
                "\n",
                "# Test with New York\n",
                "result_ny = await get_weather_and_clothing_recommendations(\"New York\")\n",
                "\n",
                "print(f\"\\n🌆 {result_ny['location']} Weather Information:\")\n",
                "print(f\"{'=' * 50}\")\n",
                "print(result_ny['weather_info'])\n",
                "print(f\"\\n👕 Clothing Recommendations:\")\n",
                "print(f\"{'=' * 50}\")\n",
                "print(result_ny['clothing_recommendations'])"
            ]
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "source": [
                "# Test with London\n",
                "result_london = await get_weather_and_clothing_recommendations(\"London\")\n",
                "\n",
                "print(f\"\\n🌆 {result_london['location']} Weather Information:\")\n",
                "print(f\"{'=' * 50}\")\n",
                "print(result_london['weather_info'])\n",
                "print(f\"\\n👕 Clothing Recommendations:\")\n",
                "print(f\"{'=' * 50}\")\n",
                "print(result_london['clothing_recommendations'])"
            ]
        },
        {
            "cell_type": "markdown",
            "metadata": {},
            "source": [
                "## Create a Function for Interactive Weather Assistant\n",
                "\n",
                "Let's create a function that allows users to interactively query the weather assistant."
            ]
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "source": [
                "from IPython.display import clear_output\n",
                "\n",
                "async def interactive_weather_assistant():\n",
                "    \"\"\"Interactive weather assistant that provides weather information and clothing recommendations.\"\"\"\n",
                "    print(\"🌤️ Welcome to the Cerebrum Weather Assistant! 👕\")\n",
                "    print(\"This assistant provides weather information and clothing recommendations.\")\n",
                "    print(\"Type 'exit' to quit.\\n\")\n",
                "    \n",
                "    session_id = f\"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}\"\n",
                "    conversation_history = []\n",
                "    \n",
                "    while True:\n",
                "        user_input = input(\"You: \")\n",
                "        if user_input.lower() == 'exit':\n",
                "            print(\"\\nThank you for using the Cerebrum Weather Assistant! Goodbye!\")\n",
                "            break\n",
                "        \n",
                "        # Add user message to history\n",
                "        conversation_history.append({\"role\": \"user\", \"content\": user_input})\n",
                "        \n",
                "        # Get response from the assistant\n",
                "        response = await task_runner.run_task(\n",
                "            task_id=str(clothing_task.id),\n",
                "            message=user_input,\n",
                "            session_id=session_id\n",
                "        )\n",
                "        \n",
                "        # Add assistant response to history\n",
                "        conversation_history.append({\"role\": \"assistant\", \"content\": response})\n",
                "        \n",
                "        # Display the response\n",
                "        print(f\"\\nAssistant: {response}\\n\")\n",
                "        \n",
                "    return conversation_history"
            ]
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "source": [
                "# Run the interactive assistant\n",
                "# conversation = await interactive_weather_assistant()\n",
                "# Uncomment the line above to run the interactive assistant"
            ]
        },
        {
            "cell_type": "markdown",
            "metadata": {},
            "source": [
                "## Loading an Existing Weather State\n",
                "\n",
                "Instead of creating a new state, we can also load an existing state from a file."
            ]
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "source": [
                "from src.server.models.persistence_models import StorageLocation, StorageType\n",
                "from src.server.controllers.persistence_controller import load_from_storage\n",
                "\n",
                "def load_weather_state():\n",
                "    \"\"\"Load the weather state from a file.\"\"\"\n",
                "    try:\n",
                "        # Define the storage location\n",
                "        state_location = StorageLocation(\n",
                "            type=StorageType.file,\n",
                "            location=\"state\",\n",
                "            state_name=\"weather.json\"\n",
                "        )\n",
                "        \n",
                "        # Load the state\n",
                "        state_data = load_from_storage(state_location)\n",
                "        \n",
                "        # Create a new persistence model\n",
                "        persistence_model = PersistenceModelFactory.persistence_model(\"inmemory\")\n",
                "        \n",
                "        # Load the state into the persistence model\n",
                "        persistence_model.from_json(state_data)\n",
                "        \n",
                "        print(f\"✅ Loaded weather state from {state_location.location}/{state_location.state_name}\")\n",
                "        \n",
                "        # Return the loaded persistence model\n",
                "        return persistence_model\n",
                "    except Exception as e:\n",
                "        print(f\"❌ Failed to load weather state: {str(e)}\")\n",
                "        return None"
            ]
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "source": [
                "# Load the weather state\n",
                "loaded_persistence_model = load_weather_state()\n",
                "\n",
                "if loaded_persistence_model:\n",
                "    # List available tasks\n",
                "    tasks = loaded_persistence_model.tasks.list()\n",
                "    print(f\"\\nAvailable tasks: {len(tasks)}\")\n",
                "    for task in tasks:\n",
                "        print(f\"- {task.name}: {task.description}\")\n",
                "        \n",
                "    # Create a task runner with the loaded persistence model\n",
                "    loaded_task_runner = TaskRunner(loaded_persistence_model)\n",
                "    print(\"\\n✅ Created Task Runner with loaded persistence model\")"
            ]
        },
        {
            "cell_type": "markdown",
            "metadata": {},
            "source": [
                "## Using the Loaded Weather State\n",
                "\n",
                "Now we can use the loaded weather state to get weather information and clothing recommendations."
            ]
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "source": [
                "async def use_loaded_weather_state(location: str):\n",
                "    \"\"\"Use the loaded weather state to get weather information and clothing recommendations.\"\"\"\n",
                "    if not loaded_persistence_model:\n",
                "        print(\"❌ No loaded persistence model available\")\n",
                "        return None\n",
                "    \n",
                "    # Get the first task (assuming it's the WhatToWear task)\n",
                "    tasks = loaded_persistence_model.tasks.list()\n",
                "    if not tasks:\n",
                "        print(\"❌ No tasks available in the loaded persistence model\")\n",
                "        return None\n",
                "    \n",
                "    task = tasks[0]\n",
                "    \n",
                "    # Create a new chat session\n",
                "    session_id = f\"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}\"\n",
                "    \n",
                "    # First message to get weather information\n",
                "    weather_query = f\"What is the weather in {location}?\"\n",
                "    weather_response = await loaded_task_runner.run_task(\n",
                "        task_id=str(task.id),\n",
                "        message=weather_query,\n",
                "        session_id=session_id\n",
                "    )\n",
                "    \n",
                "    # Second message to get clothing recommendations\n",
                "    clothing_query = f\"What should I wear for this weather in {location}?\"\n",
                "    clothing_response = await loaded_task_runner.run_task(\n",
                "        task_id=str(task.id),\n",
                "        message=clothing_query,\n",
                "        session_id=session_id\n",
                "    )\n",
                "    \n",
                "    return {\n",
                "        \"location\": location,\n",
                "        \"weather_info\": weather_response,\n",
                "        \"clothing_recommendations\": clothing_response\n",
                "    }"
            ]
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "source": [
                "# Test with Amsterdam using the loaded state\n",
                "if loaded_persistence_model:\n",
                "    result_amsterdam = await use_loaded_weather_state(\"Amsterdam\")\n",
                "    \n",
                "    if result_amsterdam:\n",
                "        print(f\"\\n🌆 {result_amsterdam['location']} Weather Information:\")\n",
                "        print(f\"{'=' * 50}\")\n",
                "        print(result_amsterdam['weather_info'])\n",
                "        print(f\"\\n👕 Clothing Recommendations:\")\n",
                "        print(f\"{'=' * 50}\")\n",
                "        print(result_amsterdam['clothing_recommendations'])"
            ]
        },
        {
            "cell_type": "markdown",
            "metadata": {},
            "source": [
                "## Conclusion\n",
                "\n",
                "This notebook demonstrates how to use the Cerebrum framework as a library to create a weather assistant that provides clothing recommendations based on weather conditions. We've shown two approaches:\n",
                "\n",
                "1. **Creating a new state from scratch**:\n",
                "   - Initialize a persistence model\n",
                "   - Create and register weather tools\n",
                "   - Create a task manager and tasks\n",
                "   - Use a task runner to execute tasks\n",
                "\n",
                "2. **Loading an existing state from a file**:\n",
                "   - Load a state from a JSON file\n",
                "   - Use the loaded state to execute tasks\n",
                "\n",
                "This example showcases the flexibility of the Cerebrum framework and how it can be integrated into Python notebooks for interactive applications. The framework provides a powerful way to create AI assistants with specialized capabilities, such as providing weather information and clothing recommendations."
            ]
        }
    ],
    "metadata": {
        "kernelspec": {
            "display_name": "Python 3",
            "language": "python",
            "name": "python3"
        },
        "language_info": {
            "codemirror_mode": {
                "name": "ipython",
                "version": 3
            },
            "file_extension": ".py",
            "mimetype": "text/x-python",
            "name": "python",
            "nbconvert_exporter": "python",
            "pygments_lexer": "ipython3",
            "version": "3.11.0"
        }
    },
    "nbformat": 4,
    "nbformat_minor": 2
}

# Write the notebook to a file
notebook_path = os.path.join("notebooks", "weather-example.ipynb")
with open(notebook_path, "w") as f:
    json.dump(notebook, f, indent=1)

print(f"Successfully created notebook at {notebook_path}") 