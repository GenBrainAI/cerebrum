import pytest
import asyncio
from uuid import UUID
from src.server.controllers.curried_proxy import CurriedProxy
from src.server.models.curried_proxy_info import CurriedProxyInfo
from src.server.tools.sms_tool import SMSTool

@pytest.mark.asyncio
async def test_curried_proxy_serialization():
    # Create original proxy with tools
    original_proxy = CurriedProxy()
    sms_tool = SMSTool()
    original_proxy.add_tool("SMSTool", sms_tool)
    
    # Wait a moment to let tools register
    await asyncio.sleep(0.1)  # Give time for tool registration
    
    # Convert to info
    proxy_info = original_proxy.to_info()
    assert isinstance(proxy_info, CurriedProxyInfo)
    assert isinstance(proxy_info.id, UUID)
    assert len(proxy_info.tools) > 0
    
    # Reconstruct from info
    reconstructed_proxy = CurriedProxy.from_info(proxy_info)
    assert isinstance(reconstructed_proxy, CurriedProxy)
    assert reconstructed_proxy.id == original_proxy.id
    assert len(reconstructed_proxy.tool_names) == len(original_proxy.tool_names)
    
    # Test tool functionality
    tool_metadata = reconstructed_proxy.catalog.get_tool("SMSTool.send_sms")
    assert tool_metadata is not None
    assert tool_metadata.description is not None
    
    # Test tool execution
    args = {"phone_number": "1234567890", "message": "Test message"}
    result = await reconstructed_proxy.multiset_proxy("SMSTool.send_sms", args)
    assert isinstance(result, str)
    assert "SMS message logged" in result

@pytest.mark.asyncio
async def test_state_setup_compatibility():
    """Test compatibility with state_setup.py functionality"""
    from src.server.models.agent import CreateCrewRequest, AgentModel, TaskModel
    from src.server.controllers.agents_controller import create_crew
    
    # Create test crew request
    crew_request = CreateCrewRequest(
        description="Test Handler",
        agents=[
            AgentModel(
                role="Test Agent",
                goal="Test Goal",
                backstory="Test Backstory",
                tools=[{"name": "SMSTool.send_sms", "description": "Test tool"}]
            )
        ],
        tasks=[
            TaskModel(
                description="Test task",
                expected_output="Test output",
                agent_role="Test Agent"
            )
        ]
    )
    
    # Create proxy and add tools
    curried_proxy = CurriedProxy()
    sms_tool = SMSTool()
    curried_proxy.add_tool("SMSTool", sms_tool)
    
    # Create crew
    crew = await create_crew(crew_request, curried_proxy)
    assert crew is not None
    
    # Test serialization
    proxy_info = curried_proxy.to_info()
    reconstructed_proxy = CurriedProxy.from_info(proxy_info)
    
    # Test reconstructed proxy with crew
    new_crew = await create_crew(crew_request, reconstructed_proxy)
    assert new_crew is not None