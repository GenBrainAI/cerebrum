import pytest
from src.server.tools.tools_catalog import ToolsCatalog
from src.server.models.function import Function, ResolvedSchema, Info, ServerInfo
from src.server.models.toolset import Tool
from src.server.models.toolset_credentials import ToolsetCredentials
from src.server.models.function import Function, ResolvedSchema, Info, ServerInfo, ResponseContent
from src.server.controllers.curried_proxy import CurriedProxy
from src.server.models.tools_descriptors import ToolType

@pytest.fixture
def catalog():
    return ToolsCatalog()

@pytest.fixture
def sample_resolved_schema():
    return ResolvedSchema(
        type="object",
        properties={
            "num1": ResolvedSchema(
                type="object",
                properties={
                    "real": ResolvedSchema(type="number"),
                    "imag": ResolvedSchema(type="number")
                }
            ),
            "num2": ResolvedSchema(
                type="object",
                properties={
                    "real": ResolvedSchema(type="number"),
                    "imag": ResolvedSchema(type="number")
                }
            )
        }
    )


@pytest.fixture
def sample_function(sample_resolved_schema):
    return Function(
        name="test_function",
        url="/test",
        method="post",
        description="Test function",
        parameters={
            "requestBody": sample_resolved_schema
        },
        info=Info(title="Test API", version="1.0"),
        servers=[ServerInfo(url="http://test.com")],
        credentials=ToolsetCredentials(auth_type="Bearer", auth_key="test"),
        responses={
            "200": ResponseContent(
                description="Successful response",
                content={
                    "application/json": {
                        "schema": ResolvedSchema(
                            type="object",
                            properties={
                                "result": ResolvedSchema(type="object")
                            }
                        )
                    }
                }
            )
        }
    )

def test_catalog_registration(catalog, sample_function):
    # Test registering a tool
    tool = Tool(function=sample_function, type="function")
    name = catalog.register_openapi_tool(tool, "test_tool")
    
    # Verify registration
    assert name in catalog.list_tools()
    assert catalog.get_tool(name) is not None
    
    # Print metadata for debugging
    metadata = catalog.get_tool(name)
    print(f"\nTool metadata:\n{metadata}")
    return metadata

def test_parameter_conversion(catalog, sample_function, sample_resolved_schema):
    # Create a curried proxy for testing the conversion
    curried_proxy = CurriedProxy()

    # Register the tool with our sample schema
    tool = Tool(
        function=sample_function,  # Now using the actual Function instance
        type="function"
    )
    name = catalog.register_openapi_tool(tool, "test_tool")
    
    # Get metadata from catalog to verify schema before conversion
    catalog_tool = catalog.get_tool(name)
    print(f"\nCatalog Tool Metadata:\n{catalog_tool}")
    
    # Add the tool to curried proxy from catalog
    curried_proxy.add_tool(name, tool)
    
    # Export to OpenAI format
    openai_tools = curried_proxy.export_to_openai()
    print(f"\nOpenAI Tools:\n{openai_tools}")
    
    # There should be one tool
    assert len(openai_tools) == 1
    openai_tool = openai_tools[0]
    
    # Verify the function parameters are properly converted
    assert openai_tool["type"] == "function"
    assert "parameters" in openai_tool["function"]
    parameters = openai_tool["function"]["parameters"]
    
    # Verify complex number schema structure
    assert parameters["type"] == "object"
    assert "properties" in parameters
    
    # Verify the properties directly (no requestBody wrapper)
    properties = parameters["properties"]
    assert "num1" in properties
    assert "num2" in properties

    # Verify nested complex number properties
    for num in ["num1", "num2"]:
        num_props = properties[num]
        assert num_props["type"] == "object"
        assert "properties" in num_props
        assert "real" in num_props["properties"]
        assert "imag" in num_props["properties"]
        assert num_props["properties"]["real"]["type"] == "number"
        assert num_props["properties"]["imag"]["type"] == "number"

    return openai_tool

def test_openai_export(catalog, sample_function):
    # Create a curried proxy
    curried_proxy = CurriedProxy()
    
    # Register the tool first
    tool = Tool(function=sample_function, type="function")
    name = catalog.register_openapi_tool(tool, "test_tool")
    
    # Add tool to curried proxy
    curried_proxy.add_tool(name, tool)
    
    # Export to OpenAI format using curried proxy
    openai_tools = curried_proxy.export_to_openai()
    print(f"\nOpenAI tools:\n{openai_tools}")
    
    # Verify structure
    assert len(openai_tools) > 0
    tool_def = openai_tools[0]
    assert tool_def["type"] == "function"
    assert "function" in tool_def
    assert "parameters" in tool_def["function"]
    
    # Verify parameters structure directly
    parameters = tool_def["function"]["parameters"]
    assert parameters["type"] == "object"
    assert "properties" in parameters
    
    properties = parameters["properties"]
    # Verify complex number structure
    assert "num1" in properties
    assert "num2" in properties
    
    # Verify nested number structure
    for num in ["num1", "num2"]:
        num_props = properties[num]
        assert num_props["type"] == "object"
        assert "properties" in num_props
        assert "real" in num_props["properties"]
        assert "imag" in num_props["properties"]
        assert num_props["properties"]["real"]["type"] == "number"
        assert num_props["properties"]["imag"]["type"] == "number"
    
    # Test that this would result in the correct API call structure
    expected_api_payload = {
        "num1": {"real": 1, "imag": 2},
        "num2": {"real": 3, "imag": 4}
    }
    # Verify our schema would allow this structure
    assert all(
        key in properties and
        "properties" in properties[key] and
        "real" in properties[key]["properties"] and
        "imag" in properties[key]["properties"]
        for key in expected_api_payload
    )

    return tool_def


def test_full_conversion_chain(catalog, sample_function, sample_resolved_schema):
    """Test the entire conversion chain from catalog registration to OpenAI format."""
    print("\nStep 1 - Register Tool in Catalog")
    # 1. Register tool in catalog
    tool = Tool(function=sample_function, type="function")
    name = catalog.register_openapi_tool(tool, "test_tool")
    metadata = catalog.get_tool(name)
    print(f"Registered Tool Metadata:\n{metadata}")

    # Verify metadata preserved the schema
    assert metadata is not None
    assert metadata.tool_type == ToolType.OPENAPI_TOOL
    assert metadata.parameters is not None
    assert len(metadata.parameters) > 0
    
    # Find parameter and verify schema structure
    request_body_param = next(
        (param for param in metadata.parameters if param.name == "requestBody"),
        None
    )
    assert request_body_param is not None
    print(f"\nRequest Body Parameter:\n{request_body_param}")

    print("\nStep 2 - Add Tool to CurriedProxy")
    # 2. Set up curried proxy with the tool
    curried_proxy = CurriedProxy()
    curried_proxy.add_tool(name, tool)
    print(f"Tool Names in Proxy: {curried_proxy.tool_names}")

    print("\nStep 3 - Export to OpenAI Format")
    # 3. Export to OpenAI format
    openai_tools = curried_proxy.export_to_openai()
    print(f"OpenAI Tools:\n{openai_tools}")

    # 4. Verify final OpenAI format
    assert len(openai_tools) == 1
    openai_tool = openai_tools[0]

    # Verify function structure
    assert openai_tool["type"] == "function"
    assert "function" in openai_tool
    assert openai_tool["function"]["name"] == name
    assert "parameters" in openai_tool["function"]

    # Verify parameters structure
    parameters = openai_tool["function"]["parameters"]
    assert parameters["type"] == "object"
    assert "properties" in parameters
    
    # Verify complex number schema structure directly in properties
    properties = parameters["properties"]
    assert "num1" in properties
    assert "num2" in properties

    # Verify nested number properties
    for num in ["num1", "num2"]:
        num_props = properties[num]
        assert num_props["type"] == "object"
        assert "properties" in num_props
        assert "real" in num_props["properties"]
        assert "imag" in num_props["properties"]
        assert num_props["properties"]["real"]["type"] == "number"
        assert num_props["properties"]["imag"]["type"] == "number"

    print("\nStep 4 - Final Structure Verification Complete")
    print(f"Final OpenAI Parameters Structure:\n{parameters}")

    # Test that this would result in the correct API call structure
    expected_api_payload = {
        "num1": {"real": 1, "imag": 2},
        "num2": {"real": 3, "imag": 4}
    }
    # Verify our schema would allow this structure
    assert all(
        key in properties and
        "properties" in properties[key] and
        "real" in properties[key]["properties"] and
        "imag" in properties[key]["properties"]
        for key in expected_api_payload
    )

    return {
        "catalog_metadata": metadata,
        "request_body_param": request_body_param,
        "openai_tool": openai_tool,
        "final_parameters": parameters
    }
