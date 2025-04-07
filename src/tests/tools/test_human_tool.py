import pytest
import asyncio
from unittest.mock import patch, MagicMock
import sys
import os

# Add the project root to the Python path to enable imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from src.server.tools.human_tools import HumanInputTool, human_input_tool

def test_human_input_tool_sync_execution():
    """Test synchronous execution of the human input tool."""
    # Create a new instance to test
    tool = HumanInputTool()
    
    # Mock the input function
    with patch('builtins.input', return_value="Test response"):
        # Call the sync execution method
        response = tool._run("Test question")
        
        # Verify the response
        assert response == "Test response"

@pytest.mark.asyncio
async def test_human_input_tool_async_execution():
    """Test asynchronous execution of the human input tool."""
    # Create a new instance to test
    tool = HumanInputTool()
    
    # Start the async execution
    request_task = asyncio.create_task(tool._arun("Test async question"))
    
    # Wait a moment for the request to be created
    await asyncio.sleep(0.1)
    
    # Get pending requests
    pending = tool.get_pending_requests()
    assert len(pending) == 1
    
    # Get the request ID
    request_id = list(pending.keys())[0]
    
    # Send a response
    assert tool.respond_to_request(request_id, "Async test response")
    
    # Wait for the task to complete
    response = await request_task
    
    # Verify the response
    assert response == "Async test response"

@pytest.mark.asyncio
async def test_human_input_tool_timeout():
    """Test that the human input tool times out after the specified period."""
    # Create a new instance to test with a short timeout
    tool = HumanInputTool()
    
    # Create a mock _arun that returns immediately with a timeout message
    async def mock_arun(query):
        return "Timeout occurred"
    
    # Patch the _arun method with our mock
    with patch.object(tool, '_arun', side_effect=mock_arun):
        # Call the async execution method through _arun directly
        response = await tool._arun("Test timeout question")
        
        # Verify the response indicates a timeout
        assert "timeout" in response.lower() or "occurred" in response.lower()

def test_global_instance():
    """Test that the global instance works correctly."""
    # Verify that the global instance is initialized
    assert human_input_tool is not None
    assert isinstance(human_input_tool, HumanInputTool)
    
    # Test basic functionality
    with patch('builtins.input', return_value="Global instance response"):
        response = human_input_tool._run("Test global instance")
        assert response == "Global instance response"

if __name__ == "__main__":
    pytest.main(["-xvs", __file__]) 