import pytest
import os
from pathlib import Path
from dotenv import load_dotenv
from src.server.controllers.operator import ToolsOperator
from src.server.models.message import Message
from src.server.controllers.curried_proxy import CurriedProxy
from unittest.mock import AsyncMock, MagicMock, patch

# Load environment variables from .env file
load_dotenv()

@pytest.fixture(scope="module")
def event_loop():
    import asyncio
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(autouse=True)
def setup_env():
    # Function to get environment variable with a default value
    def get_env_var(var_name, default=None):
        return os.environ.get(var_name) or default

    # Set environment variables, with fallback to None if not set
    os.environ['OPENAI_API_KEY'] = get_env_var('OPENAI_API_KEY')
    os.environ['ANTHROPIC_API_KEY'] = get_env_var('ANTHROPIC_API_KEY')
    os.environ['GROQ_API_KEY'] = get_env_var('GROQ_API_KEY')

    # Special handling for Google Application Credentials
    google_creds = get_env_var('GOOGLE_APPLICATION_CREDENTIALS')
    if not google_creds:
        # Check in user's home directory
        home_dir = str(Path.home())
        potential_path = os.path.join(home_dir, 'gemini-key.json')
        if os.path.exists(potential_path):
            os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = potential_path
        else:
            print(f"Warning: Google Application Credentials not found at {potential_path}")

    # Check if required variables are set
    missing_vars = []
    for var in ['OPENAI_API_KEY', 'ANTHROPIC_API_KEY', 'GOOGLE_APPLICATION_CREDENTIALS', 'GROQ_API_KEY']:
        if not os.environ.get(var):
            missing_vars.append(var)

    if missing_vars:
        pytest.skip(f"Skipping tests due to missing environment variables: {', '.join(missing_vars)}")

@pytest.mark.asyncio
async def test_openai_completion():
    if not os.environ.get('OPENAI_API_KEY'):
        pytest.skip("Skipping OpenAI test due to missing API key")
    operator = ToolsOperator(api_provider="openai")
    messages = [Message(role="user", content="Say 'Hello, World!'")]
    curried_proxy = CurriedProxy()
    response = await operator.completion(
        tasksmanager_id="test_id",
        task_id="test_task",
        messages=messages,
        model="gpt-4o-mini",
        curried_proxy=curried_proxy
    )
    assert "Hello, World!" in response

@pytest.mark.asyncio
async def test_anthropic_completion():
    # Mock the Anthropic client
    mock_client = AsyncMock()
    mock_response = AsyncMock()
    mock_content = MagicMock()
    mock_content.text = "Hello, World!"
    mock_response.content = [mock_content]
    mock_client.messages.create.return_value = mock_response

    # Create a ToolsOperator instance with the mocked client
    with patch('anthropic.AsyncAnthropic', return_value=mock_client):
        # We need to patch the client initialization in the operator
        operator = ToolsOperator(api_provider="anthropic")
        # Directly set the mocked client
        operator.client = mock_client
        
        messages = [Message(role="user", content="Say 'Hello, World!'")]
        curried_proxy = CurriedProxy()
        
        response = await operator.completion(
            tasksmanager_id="test_id",
            task_id="test_task",
            messages=messages,
            model="claude-3-5-sonnet-20240620",
            curried_proxy=curried_proxy
        )
        
        # Verify the mock was called with the expected parameters
        mock_client.messages.create.assert_called_once()
        call_args = mock_client.messages.create.call_args[1]
        assert call_args["model"] == "claude-3-5-sonnet-20240620"
        assert call_args["messages"][0]["content"] == "Say 'Hello, World!'"
        
        # Verify the response
        assert response == "Hello, World!"

@pytest.mark.asyncio
async def test_gemini_completion():
    if not os.environ.get('GOOGLE_APPLICATION_CREDENTIALS'):
        pytest.skip("Skipping Gemini test due to missing credentials")
    operator = ToolsOperator(api_provider="gemini")
    messages = [Message(role="user", content="Say 'Hello, World!'")]
    curried_proxy = CurriedProxy()
    response = await operator.completion(
        tasksmanager_id="test_id",
        task_id="test_task",
        messages=messages,
        model="gemini-pro",
        curried_proxy=curried_proxy
    )
    assert "Hello, World!" in response

@pytest.mark.asyncio
async def test_groq_completion():
    if not os.environ.get('GROQ_API_KEY'):
        pytest.skip("Skipping Groq test due to missing API key")
    operator = ToolsOperator(api_provider="groq")
    messages = [Message(role="user", content="Say 'Hello, World!'")]
    curried_proxy = CurriedProxy()
    response = await operator.completion(
        tasksmanager_id="test_id",
        task_id="test_task",
        messages=messages,
        model="llama3-8b-8192",
        curried_proxy=curried_proxy
    )
    assert "Hello" in response and "World" in response

@pytest.mark.asyncio
async def test_langchain_completion():
    if not os.environ.get('OPENAI_API_KEY'):  # LangChain test uses OpenAI
        pytest.skip("Skipping LangChain test due to missing OpenAI API key")
    operator = ToolsOperator(api_provider="langchain")
    messages = [Message(role="user", content="Say 'Hello, World!'")]
    curried_proxy = CurriedProxy()
    response = await operator.completion(
        tasksmanager_id="test_id",
        task_id="test_task",
        messages=messages,
        model="gpt-4o-mini",  # LangChain will use OpenAI's model
        curried_proxy=curried_proxy
    )
    assert "Hello, World!" in response
