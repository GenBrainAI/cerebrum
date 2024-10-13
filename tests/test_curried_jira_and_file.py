import pytest
import os

from src.server.controllers.curried_proxy import CurriedProxy
from src.server.tools.file_tool import save_file
from src.server.tools.jira_tool import fetch_jira_tickets

pytestmark = pytest.mark.asyncio


@pytest.fixture
def curried_proxy():
    cp = CurriedProxy()
    yield cp
    for tool_name in cp.list_tools():
        cp.remove_tool(tool_name)


@pytest.fixture(autouse=True)
def cleanup_curried_proxy(curried_proxy):
    yield
    # Clean up all tools after each test
    for tool_name in curried_proxy.list_tools():
        curried_proxy.remove_tool(tool_name)

async def test_add_and_use_file_tool(curried_proxy):
    curried_proxy.add_tool("file_tool", save_file)
    try:
        result = await curried_proxy.curried_proxy("file_tool")({"file_path": "text", "file_content": "text"})
        assert "File written:" in result
        
        # Extract the filename from the result
        filename = result.split(":")[1].strip()
        
        # Verify the file exists and contains the correct content
        assert os.path.exists(filename)
        with open(filename, 'r') as file:
            assert file.read() == "text"
    finally:
        # Clean up the created file
        filename = result.split(":")[1].strip()
        if os.path.exists(filename):
            os.remove(filename)


async def test_add_and_use_jira_fetch_ticket(curried_proxy):
    curried_proxy.add_tool("jira_tool", fetch_jira_tickets)
    result = await curried_proxy.curried_proxy("jira_tool")({"project_key": "cer"})
    assert result


async def test_fetch_and_write_file(curried_proxy):
    curried_proxy.add_tool("file_tool", save_file)
    curried_proxy.add_tool("jira_tool", fetch_jira_tickets)

    tickets = await curried_proxy.curried_proxy("jira_tool")({"project_key": "cer"})
    
    created_files = []
    try:
        for ticket in tickets:
            # Check if ticket is a string (summary) or a dict with 'fields' key
            if isinstance(ticket, dict) and 'fields' in ticket:
                summary = ticket['fields'].get('summary', '')
            else:
                summary = str(ticket)  # Convert to string if it's not a dict
            
            result = await curried_proxy.curried_proxy("file_tool")({"file_path": "/tmp/test.txt", "file_content": summary})
            assert "File written:" in result
            filename = result.split(":")[1].strip()
            created_files.append(filename)
            with open(filename, 'r') as file:
                assert summary in file.read()
    finally:
        # Clean up created files
        for file in created_files:
            if os.path.exists(file):
                os.remove(file)
