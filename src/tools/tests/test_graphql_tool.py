import pytest
import pytest_asyncio
from typing import Dict, Any
from src.tools.graphql_tool import GraphQLTool

@pytest.fixture
def graphql_tool():
    """Create a GraphQL tool instance for testing."""
    return GraphQLTool()

@pytest.mark.asyncio
async def test_graphql_tool_sync(graphql_tool):
    """Test synchronous GraphQL query execution."""
    query = """
    query {
        test {
            status
        }
    }
    """
    result = graphql_tool._run(query)
    assert isinstance(result, dict)
    assert "data" in result
    assert result["data"]["status"] == "success"

@pytest.mark.asyncio
async def test_graphql_tool_async(graphql_tool):
    """Test asynchronous GraphQL query execution."""
    query = """
    query {
        test {
            status
        }
    }
    """
    result = await graphql_tool._arun(query)
    assert isinstance(result, dict)
    assert "data" in result
    assert result["data"]["status"] == "success"

@pytest.mark.asyncio
async def test_graphql_tool_with_variables(graphql_tool):
    """Test GraphQL query execution with variables."""
    query = """
    query($id: ID!) {
        test(id: $id) {
            status
        }
    }
    """
    variables = {"id": "123"}
    result = await graphql_tool._arun(query, variables)
    assert isinstance(result, dict)
    assert "data" in result
    assert result["data"]["status"] == "success"

@pytest.mark.asyncio
async def test_graphql_tool_error_handling(graphql_tool):
    """Test error handling in GraphQL tool."""
    # Invalid query to trigger error
    query = "invalid { query"
    result = await graphql_tool._arun(query)
    assert isinstance(result, dict)
    assert "error" in result 