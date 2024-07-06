import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime
from src.server.controllers.curried_proxy import CurriedProxy
from src.server.models.toolset import Tool
from src.server.models.function import Function, ServerInfo, Info, ResolvedSchema, ParameterSchema, ResponseContent
from src.server.models.toolset_credentials import ToolsetCredentials
from src.server.persistence.persistence_model_factory import PersistenceModelFactory

class MockGithubTool:
    async def ls(self, path: str = '') -> list:
        return ['file1.txt', 'file2.py']

    async def get_readme(self, path: str = '') -> str:
        return "# Mock README"

def fibonacci(n: int) -> list:
    if n <= 0:
        return []
    elif n == 1:
        return [0]
    elif n == 2:
        return [0, 1]
    
    fib_sequence = [0, 1]
    for i in range(2, n):
        next_fib = fib_sequence[-1] + fib_sequence[-2]
        fib_sequence.append(next_fib)
    
    return fib_sequence

@pytest.fixture
def curried_proxy():
    return CurriedProxy()

@pytest.fixture
def mock_tool():
    return Tool(
        function=Function(
            name="mock_function",
            url="/resource",
            method="get",
            description="Mock API Tool",
            info=Info(
                title="Mock API",
                version="1.0",
                description="A mock API for testing"
            ),
            servers=[ServerInfo(url='https://api.example.com')],
            parameters={
                "query": {
                    "param1": ParameterSchema(
                        name="param1",
                        in_="query",
                        description="A query parameter",
                        required=False,
                        schema=ResolvedSchema(type="string")
                    )
                }
            },
            responses={
                "200": ResponseContent(
                    description="Successful response",
                    content={
                        "application/json": {
                            "schema": ResolvedSchema(
                                type="object",
                                properties={
                                    "result": ResolvedSchema(type="string")
                                }
                            )
                        }
                    }
                )
            },
            credentials=ToolsetCredentials(
                auth_type='Bearer',
                auth_key='mock_token'
            )
        ),
        type="function"
    )

@pytest.mark.asyncio
async def test_add_and_use_api_tool(curried_proxy, mock_tool):
    curried_proxy.add_tool("mock_api", mock_tool)
    
    with patch('httpx.AsyncClient.get') as mock_get:
        mock_get.return_value.json.return_value = {"result": "success"}
        result = await curried_proxy.curried_proxy("mock_api")({})
        assert result == {"result": "success"}
        mock_get.assert_called_once()

@pytest.mark.asyncio
async def test_add_and_use_function_tool(curried_proxy):
    curried_proxy.add_tool("fibonacci", fibonacci)
    
    result = await curried_proxy.curried_proxy("fibonacci")({"n": 5})
    assert result == [0, 1, 1, 2, 3]

@pytest.mark.asyncio
async def test_add_and_use_class_methods(curried_proxy):
    github_tool = MockGithubTool()
    curried_proxy.add_tool("github", github_tool)
    
    ls_result = await curried_proxy.curried_proxy("github.ls")({})
    assert ls_result == ['file1.txt', 'file2.py']
    
    readme_result = await curried_proxy.curried_proxy("github.get_readme")({})
    assert readme_result == "# Mock README"

def test_list_tools(curried_proxy, mock_tool):
    curried_proxy.add_tool("mock_api", mock_tool)
    curried_proxy.add_tool("fibonacci", fibonacci)
    github_tool = MockGithubTool()
    curried_proxy.add_tool("github", github_tool)
    
    tool_list = curried_proxy.list_tools()
    assert set(tool_list) == {"mock_api", "fibonacci", "github.ls", "github.get_readme"}

def test_remove_tool(curried_proxy, mock_tool):
    curried_proxy.add_tool("mock_api", mock_tool)
    curried_proxy.add_tool("fibonacci", fibonacci)
    
    assert "mock_api" in curried_proxy.list_tools()
    curried_proxy.remove_tool("mock_api")
    assert "mock_api" not in curried_proxy.list_tools()
    assert "fibonacci" in curried_proxy.list_tools()

@pytest.mark.asyncio
async def test_persistence_integration():
    persistence_model = PersistenceModelFactory.persistence_model("inmemory")
    
    curried_proxy = CurriedProxy()
    created_proxy = persistence_model.curried_proxies.create(curried_proxy)
    
    created_proxy.add_tool("fibonacci", fibonacci)
    github_tool = MockGithubTool()
    created_proxy.add_tool("github", github_tool)
    
    persistence_model.curried_proxies.update(str(created_proxy.id), created_proxy)
    
    retrieved_proxy = persistence_model.curried_proxies.read(str(created_proxy.id))
    assert "fibonacci" in retrieved_proxy.list_tools()
    assert "github.ls" in retrieved_proxy.list_tools()
    
    fib_result = await retrieved_proxy.curried_proxy("fibonacci")({"n": 5})
    assert fib_result == [0, 1, 1, 2, 3]

@pytest.mark.asyncio
async def test_export_to_crewai(curried_proxy, mock_tool):
    curried_proxy.add_tool("mock_api", mock_tool)
    curried_proxy.add_tool("fibonacci", fibonacci)
    
    crewai_tools = curried_proxy.export_to_crewai()
    assert len(crewai_tools) == 2
    assert all(hasattr(tool, '_run') for tool in crewai_tools)
    
    # Test running a CrewAI tool
    fibonacci_tool = next(tool for tool in crewai_tools if tool.name == "fibonacci")
    result = await fibonacci_tool._run(n=5)
    assert result == [0, 1, 1, 2, 3]

