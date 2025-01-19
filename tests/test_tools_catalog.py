import pytest
from typing import List, Optional, Dict, Any
import os
import asyncio
from unittest.mock import patch, MagicMock
from crewai_tools import WebsiteSearchTool, FileReadTool, SerperDevTool
from github import Github, Repository, Auth
from src.server.tools.tools_catalog import (
    ToolsCatalog,
    ToolType,
    ParameterInfo,
    ReturnInfo,
    ToolMetadata
)
from src.server.tools.file_tool import FileTool
from src.server.tools.github_tool import GitHubTool
from src.server.tools.microservices_tool import MicroservicesTool
from src.server.tools.sms_tool import SMSTool
import base64

# Test fixtures and helper functions
_original_catalog = None

def create_mock_repo():
    """Create a mock GitHub repository."""
    mock_repo = MagicMock(spec=Repository.Repository)
    mock_repo.full_name = "GenBrainAI/cerebrum"
    mock_repo.get_contents.return_value = MagicMock(
        path="test/path",
        sha="test_sha",
        content="test_content"
    )
    mock_repo.create_git_ref.return_value = None
    mock_repo.get_branch.return_value = MagicMock(
        commit=MagicMock(sha="test_sha")
    )
    return mock_repo

def create_mock_env():
    """Create mock environment variables for testing."""
    return {
        "GITHUB_ACCESS_TOKEN": "mock-token",
        "GITHUB_REPO_NAME": "GenBrainAI/cerebrum",
    }

@pytest.fixture
def mock_github(monkeypatch):
    """Mock GitHub environment and API."""
    monkeypatch.setenv("GITHUB_TOKEN", "test_token")
    monkeypatch.setenv("GITHUB_REPO", "test_repo")

    # Create a mock repository that will have base64 encoded content
    mock_repo = MagicMock()
    mock_repo.full_name = "test_repo"
    mock_content = MagicMock()
    mock_content.content = base64.b64encode(b'mocked_content')
    mock_content.path = "test/path"
    mock_content.sha = "test_sha"
    mock_repo.get_contents.return_value = mock_content

    # Create a mock GitHub instance
    mock_github = MagicMock()
    mock_github.get_repo.return_value = mock_repo

    # Create a mock GitHub class that returns our mock instance
    mock_github_class = MagicMock(return_value=mock_github)

    # Patch both potential import paths
    patcher1 = patch('src.server.tools.github_tool.Github', mock_github_class)
    patcher2 = patch('github.Github', mock_github_class)
    patcher1.start()
    patcher2.start()

    yield mock_github

    patcher1.stop()
    patcher2.stop()

@pytest.fixture
def mock_environment(monkeypatch):
    """Mock environment variables for testing."""
    monkeypatch.setenv("GITHUB_TOKEN", "test_token")
    monkeypatch.setenv("GITHUB_REPO", "test_repo")
    yield

@pytest.fixture(autouse=True)
def reset_catalog():
    """Fixture to reset the ToolsCatalog singleton between tests."""
    global _original_catalog
    
    # Store reference to original catalog
    _original_catalog = ToolsCatalog._instance
    
    # Reset the singleton state
    ToolsCatalog._instance = None
    ToolsCatalog._initialized = False
    
    yield
    
    # After test, restore original state
    ToolsCatalog._instance = _original_catalog
    ToolsCatalog._initialized = _original_catalog is not None

@pytest.mark.asyncio
async def test_singleton_behavior(mock_github):
    """Test that ToolsCatalog behaves as a singleton."""
    catalog1 = ToolsCatalog()
    catalog2 = ToolsCatalog()
    
    assert catalog1 is catalog2
    assert id(catalog1) == id(catalog2)
    
    # Create another instance and verify it's the same
    catalog3 = ToolsCatalog()
    assert catalog1 is catalog3
    assert id(catalog1) == id(catalog3)

@pytest.mark.asyncio
async def test_default_tools_initialization(mock_github):
    """Test that default tools are properly initialized."""
    catalog = ToolsCatalog()
    
    # Verify all default tools are registered
    tools = catalog.list_tools()
    expected_tools = [
        "WebsiteSearchTool",
        "SerperDevTool",
        "FileReadTool",
        "GitHubTool",
        "FileTool",
        "MicroservicesTool",
        "SMSTool"
    ]
    
    # Check that all expected tools are present (noting that some might have multiple methods)
    for tool_name in expected_tools:
        matching_tools = [t for t in tools if tool_name in t]
        assert len(matching_tools) > 0, f"Tool {tool_name} not found in catalog"
        
        # Verify tool metadata exists
        tool_metadata = catalog.get_tool(matching_tools[0])
        assert tool_metadata is not None
        assert isinstance(tool_metadata, ToolMetadata)

@pytest.mark.asyncio
async def test_tool_instances(mock_github):
    """Test that tool instances are properly managed."""
    catalog = ToolsCatalog()
    
    # Test getting instances of different tool types
    website_tool = catalog.get_tool_instance("WebsiteSearchTool")
    assert isinstance(website_tool, WebsiteSearchTool)
    
    file_tool = catalog.get_tool_instance("FileTool")
    assert isinstance(file_tool, FileTool)
    
    github_tool = catalog.get_tool_instance("GitHubTool")
    assert isinstance(github_tool, GitHubTool)

@pytest.mark.asyncio
async def test_tool_metadata(mock_github):
    """Test that tool metadata is correctly captured."""
    catalog = ToolsCatalog()
    
    # Test CrewAI tool metadata
    websearch_metadata = catalog.get_tool("WebsiteSearchTool")
    assert websearch_metadata is not None
    assert str(websearch_metadata.tool_type) == str(ToolType.CREWAI_TOOL)
    assert websearch_metadata.description
    
    # Test Python class method metadata - using one of the actual registered methods
    github_method_metadata = catalog.get_tool("GitHubTool.create_branch")  # or any other GitHub tool method
    assert github_method_metadata is not None
    assert str(github_method_metadata.tool_type) == str(ToolType.CLASS_METHOD)
    assert github_method_metadata.description
    assert github_method_metadata.class_name == "GitHubTool"
    assert github_method_metadata.method_name == "create_branch"
    
    # List all GitHub tool methods to verify registration
    github_tools = [name for name in catalog.list_tools() if name.startswith("GitHubTool.")]
    assert len(github_tools) > 0, "No GitHub tool methods found in catalog"
    
    # Verify each GitHub tool method has correct metadata
    for tool_name in github_tools:
        metadata = catalog.get_tool(tool_name)
        assert metadata is not None
        assert metadata.tool_type.value == ToolType.CLASS_METHOD.value
        assert metadata.class_name == "GitHubTool"

@pytest.mark.asyncio
async def test_tool_execution(mock_github):
    """Test that tools can be executed through the catalog."""
    catalog = ToolsCatalog()
    
    # Test file tool
    file_tool = catalog.get_tool_instance("FileTool")
    test_content = "test content"
    test_file = "test.txt"
    
    try:
        if isinstance(file_tool, FileTool):
            result = file_tool._run(file_path=test_file, file_content=test_content)
        elif asyncio.iscoroutinefunction(file_tool):
            result = await file_tool(file_path=test_file, file_content=test_content)
        else:
            result = file_tool(file_path=test_file, file_content=test_content)
        
        assert f"File written: {test_file}" in result
        
        # Verify file was created
        assert os.path.exists(test_file)
        with open(test_file, 'r') as f:
            assert f.read() == test_content
        
        # Test GitHub tool
        github_tool = catalog.get_tool_instance("GitHubTool")
        
        # Check that the get_file_contents method returns the expected value
        content = github_tool.get_file_contents("test/path")
        assert content == {'content': 'mocked_content', 'path': 'test/path', 'sha': 'test_sha'}
    finally:
        # Cleanup
        if os.path.exists(test_file):
            os.remove(test_file)

@pytest.mark.asyncio
async def test_tool_serialization(mock_github):
    """Test that the catalog can be serialized and deserialized."""
    catalog = ToolsCatalog()
    
    # Serialize
    catalog_dict = catalog.to_dict()
    assert "tools" in catalog_dict
    assert len(catalog_dict["tools"]) > 0
    
    # Deserialize
    new_catalog = ToolsCatalog.from_dict(catalog_dict)
    assert len(new_catalog.list_tools()) == len(catalog.list_tools())
    
    # Verify tool metadata was preserved
    for tool_name in catalog.list_tools():
        original_metadata = catalog.get_tool(tool_name)
        new_metadata = new_catalog.get_tool(tool_name)
        
        assert new_metadata.name == original_metadata.name
        assert new_metadata.tool_type == original_metadata.tool_type
        assert len(new_metadata.parameters) == len(original_metadata.parameters)

@pytest.mark.asyncio
async def test_add_new_tool(mock_github):
    """Test adding a new tool to the catalog."""
    catalog = ToolsCatalog()
    initial_tool_count = len(catalog.list_tools())
    
    # Define a new tool function
    async def custom_tool(input_text: str, repeat: int = 1) -> str:
        """A custom test tool.
        
        Args:
            input_text: Text to process
            repeat: Number of times to repeat the text
            
        Returns:
            Processed text
        """
        return input_text * repeat
    
    # Register the new tool
    tool_name = catalog.register_function(custom_tool)
    
    # Verify tool was added
    assert len(catalog.list_tools()) == initial_tool_count + 1
    assert tool_name in catalog.list_tools()
    
    # Verify tool metadata
    metadata = catalog.get_tool(tool_name)
    assert metadata.async_tool
    assert len(metadata.parameters) == 2
    assert metadata.parameters[0].name == "input_text"
    assert metadata.parameters[1].name == "repeat"

@pytest.mark.asyncio
async def test_error_handling(mock_github):
    """Test error handling in the catalog."""
    catalog = ToolsCatalog()
    
    # Test getting non-existent tool
    with pytest.raises(KeyError):
        catalog.get_tool_instance("non_existent_tool")
    
    # Test getting metadata for non-existent tool
    assert catalog.get_tool("non_existent_tool") is None
    
    # Test registering invalid tool type
    with pytest.raises(Exception):
        catalog.register_ai_tool("not_a_tool")

if __name__ == "__main__":
    pytest.main(["-v", "--asyncio-mode=auto", __file__])