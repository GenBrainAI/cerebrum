import pytest
from fastapi.testclient import TestClient
from src.server.main import app
from src.server.utils.task_utils import find_file
from src.server.controllers.curried_proxy import CurriedProxy

client = TestClient(app)

@pytest.mark.asyncio
async def test_curried_proxy(client: TestClient):
    # Read the content of the swagger YAML file
    with open(find_file("tests/calculator/calculator.yaml"), "r") as file:
        swagger_yaml_content = file.read()
    
    # Prepare toolset data for form submission
    toolset_data = {
        "name": ("", "Complex Numbers Calculator API"),
        "description": ("", "API for complex number calculations"),
        "credentials": ("", '{"auth_type":"Bearer","auth_key":"test_token"}'),
        "swagger_str": ("", swagger_yaml_content)
    }
    
    # Create toolset
    toolset_response = client.post("/toolsets", files=toolset_data)
    assert toolset_response.status_code == 201
    toolset_id = toolset_response.json()["id"]

    # Fetch the created toolset
    toolset_response = client.get(f"/toolsets/{toolset_id}")
    assert toolset_response.status_code == 200
    toolset = toolset_response.json()

    # Create CurriedProxy instance
    tools_dict = {toolset['name']: Tool(**toolset)}
    proxy = CurriedProxy(tools_dict)

    # Test curried_proxy
    with patch('httpx.AsyncClient.post', new_callable=AsyncMock) as mock_post:
        mock_post.return_value.json.return_value = {"result": {"real": 4, "imag": 6}}
        result = await proxy.curried_proxy('Complex Numbers Calculator API')({"requestBody": {"num1": {"real": 1, "imag": 2}, "num2": {"real": 3, "imag": 4}}})
        assert result == {"result": {"real": 4, "imag": 6}}
        mock_post.assert_called_once_with(
            url='http://localhost:10101/add',
            json={"num1": {"real": 1, "imag": 2}, "num2": {"real": 3, "imag": 4}},
            params={},
            headers={
                'Authorization': 'Bearer test_token',
                'Content-Type': 'application/json',
                'Accept': '*/*'
            }
        )

    # Test export_to_crewai
    crewai_tools = proxy.export_to_crewai()
    assert len(crewai_tools) == 1
    assert isinstance(crewai_tools[0], BaseTool)
    assert crewai_tools[0].name == 'Complex Numbers Calculator API'
    assert crewai_tools[0].description == toolset['description']
