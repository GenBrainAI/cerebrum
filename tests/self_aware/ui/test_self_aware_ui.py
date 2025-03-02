"""
Unit tests for the Self-Aware UI component.
"""

import os
import json
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
import streamlit as st
from typing import Dict, List, Any, Optional

from src.server.ui.self_aware_ui import CerebrumSystemUI, run_async
from src.server.self_aware_core import CerebrumSystemCore

@pytest.fixture
def mock_self_aware_core():
    """Create a mock CerebrumSystemCore."""
    mock = MagicMock(spec=CerebrumSystemCore)
    
    # Mock async methods
    mock.index_codebase = AsyncMock(return_value={
        "indexed_files": 10,
        "total_files": 10,
        "skipped_files": 0
    })
    
    mock.execute_command = AsyncMock(return_value=MagicMock(
        command="ls -la",
        exit_code=0,
        stdout="file1.txt\nfile2.txt",
        stderr="",
        success=True
    ))
    
    mock.search_code = AsyncMock(return_value=[
        MagicMock(
            file_path="test.py",
            content="def test_function():\n    pass",
            start_line=1,
            end_line=2,
            language="python",
            relevance_score=0.95
        )
    ])
    
    mock.get_file_content = AsyncMock(return_value="file content")
    
    mock.get_context = AsyncMock(return_value="context content")
    
    mock.add_to_context = AsyncMock(return_value="item1")
    
    mock.get_pending_approvals = AsyncMock(return_value=[])
    
    mock.execute_approved_command = AsyncMock(return_value=MagicMock(
        command="cat file.txt",
        exit_code=0,
        stdout="file content",
        stderr="",
        success=True
    ))
    
    mock.reject_command = AsyncMock(return_value=True)
    
    mock.get_codebase_stats = AsyncMock(return_value={
        "total_files": 10,
        "total_lines": 1000,
        "languages": {
            "python": 5,
            "javascript": 3,
            "markdown": 2
        },
        "last_updated": "2023-01-01T00:00:00"
    })
    
    mock.refresh_codebase = AsyncMock(return_value={
        "indexed_files": 2,
        "total_files": 10,
        "skipped_files": 8
    })
    
    return mock

@pytest.fixture
def mock_streamlit():
    """Mock Streamlit components."""
    with patch("src.server.ui.self_aware_ui.st") as mock_st:
        # Mock session_state
        mock_st.session_state = MagicMock()
        mock_st.session_state.core = None
        mock_st.session_state.command_history = []
        mock_st.session_state.search_history = []
        mock_st.session_state.pending_approvals = []
        mock_st.session_state.codebase_stats = {}
        mock_st.session_state.context = ""
        mock_st.session_state.persistence_model = None
        
        # Mock sidebar
        mock_st.sidebar = MagicMock()
        mock_st.sidebar.title = MagicMock()
        mock_st.sidebar.header = MagicMock()
        mock_st.sidebar.success = MagicMock()
        mock_st.sidebar.info = MagicMock()
        mock_st.sidebar.warning = MagicMock()
        mock_st.sidebar.button = MagicMock(return_value=False)
        mock_st.sidebar.metric = MagicMock()
        mock_st.sidebar.text = MagicMock()
        
        # Mock main components
        mock_st.title = MagicMock()
        mock_st.header = MagicMock()
        mock_st.subheader = MagicMock()
        mock_st.markdown = MagicMock()
        mock_st.text = MagicMock()
        mock_st.text_input = MagicMock(return_value="")
        mock_st.text_area = MagicMock()
        mock_st.number_input = MagicMock(return_value=30)
        mock_st.slider = MagicMock(return_value=5)
        mock_st.checkbox = MagicMock(return_value=True)
        mock_st.button = MagicMock(return_value=False)
        mock_st.code = MagicMock()
        mock_st.json = MagicMock()
        mock_st.success = MagicMock()
        mock_st.error = MagicMock()
        mock_st.info = MagicMock()
        mock_st.spinner = MagicMock()
        mock_st.expander = MagicMock()
        mock_st.columns = MagicMock(return_value=[MagicMock(), MagicMock()])
        mock_st.tabs = MagicMock(return_value=[MagicMock(), MagicMock(), MagicMock(), MagicMock(), MagicMock()])
        mock_st.set_page_config = MagicMock()
        
        yield mock_st

@pytest.fixture
def cerebrum_system_ui(mock_self_aware_core, mock_streamlit):
    """Create a CerebrumSystemUI instance with mocked dependencies."""
    with patch("src.server.ui.self_aware_ui.CerebrumSystemCore", return_value=mock_self_aware_core):
        # Mock os.path.exists to return False to avoid loading config file
        with patch("os.path.exists", return_value=False):
            ui = CerebrumSystemUI()
            mock_streamlit.session_state.core = mock_self_aware_core
            yield ui

def test_initialize_session_state(cerebrum_system_ui, mock_streamlit):
    """Test initializing session state."""
    # Reset session state
    mock_streamlit.session_state.core = None
    mock_streamlit.session_state.command_history = None
    mock_streamlit.session_state.search_history = None
    mock_streamlit.session_state.pending_approvals = None
    mock_streamlit.session_state.codebase_stats = None
    mock_streamlit.session_state.context = None
    mock_streamlit.session_state.persistence_model = None
    
    # Call the method
    cerebrum_system_ui._initialize_session_state()
    
    # Verify session state was initialized
    assert mock_streamlit.session_state.core is None
    assert mock_streamlit.session_state.command_history == []
    assert mock_streamlit.session_state.search_history == []
    assert mock_streamlit.session_state.pending_approvals == []
    assert mock_streamlit.session_state.codebase_stats == {}
    assert mock_streamlit.session_state.context == ""
    assert mock_streamlit.session_state.persistence_model is None

def test_initialize_core(cerebrum_system_ui, mock_streamlit, mock_self_aware_core):
    """Test initializing the core."""
    # Reset core
    mock_streamlit.session_state.core = None
    
    # Mock os.path.exists and open
    with patch("os.path.exists", return_value=False):
        with patch("src.server.ui.self_aware_ui.run_async", return_value={}):
            # Call the method
            cerebrum_system_ui._initialize_core()
    
    # Verify core was initialized
    assert mock_streamlit.session_state.core is not None

def test_render_sidebar(cerebrum_system_ui, mock_streamlit):
    """Test rendering the sidebar."""
    # Call the method
    cerebrum_system_ui.render_sidebar()
    
    # Verify sidebar components were rendered
    mock_streamlit.sidebar.title.assert_called_once_with("Cerebrum System Core")
    mock_streamlit.sidebar.header.assert_any_call("Component Status")
    mock_streamlit.sidebar.success.assert_any_call("✅ Context Manager: Active")
    mock_streamlit.sidebar.success.assert_any_call("✅ Vector Store: Active")
    mock_streamlit.sidebar.success.assert_any_call("✅ Terminal Executor: Active")
    mock_streamlit.sidebar.header.assert_any_call("Codebase Statistics")
    mock_streamlit.sidebar.button.assert_any_call("Refresh Stats")
    mock_streamlit.sidebar.header.assert_any_call("Pending Approvals")
    mock_streamlit.sidebar.button.assert_any_call("Check Approvals")
    mock_streamlit.sidebar.info.assert_called_once_with("No pending approvals")

def test_render_terminal_section(cerebrum_system_ui, mock_streamlit):
    """Test rendering the terminal section."""
    # Call the method
    cerebrum_system_ui.render_terminal_section()
    
    # Verify terminal components were rendered
    mock_streamlit.header.assert_called_once_with("Terminal Command Execution")
    mock_streamlit.text_input.assert_any_call("Enter command:")
    mock_streamlit.text_input.assert_any_call("Working directory:", value=".")
    mock_streamlit.number_input.assert_called_once_with("Timeout (seconds):", value=30, min_value=1, max_value=300)
    mock_streamlit.checkbox.assert_called_once_with("Requires approval", value=True)
    mock_streamlit.button.assert_called_once_with("Execute")

def test_render_search_section(cerebrum_system_ui, mock_streamlit):
    """Test rendering the search section."""
    # Call the method
    cerebrum_system_ui.render_search_section()
    
    # Verify search components were rendered
    mock_streamlit.header.assert_called_once_with("Code Search")
    mock_streamlit.text_input.assert_called_once_with("Search query:")
    mock_streamlit.slider.assert_called_once_with("Number of results:", min_value=1, max_value=20, value=5)
    mock_streamlit.button.assert_called_once_with("Search")

def test_render_context_section(cerebrum_system_ui, mock_streamlit):
    """Test rendering the context section."""
    # Call the method
    cerebrum_system_ui.render_context_section()
    
    # Verify context components were rendered
    mock_streamlit.header.assert_called_once_with("System Context")
    mock_streamlit.number_input.assert_called_once_with("Max tokens:", value=1000, min_value=100, max_value=8192)
    mock_streamlit.checkbox.assert_called_once_with("Include metadata", value=False)
    mock_streamlit.button.assert_called_once_with("Refresh Context")

def test_render_indexing_section(cerebrum_system_ui, mock_streamlit):
    """Test rendering the indexing section."""
    # Call the method
    cerebrum_system_ui.render_indexing_section()
    
    # Verify indexing components were rendered
    mock_streamlit.header.assert_called_once_with("Codebase Indexing")
    mock_streamlit.checkbox.assert_called_once_with("Incremental indexing", value=True)
    mock_streamlit.button.assert_called_once_with("Index Codebase")

def test_render_tasks_section(cerebrum_system_ui, mock_streamlit):
    """Test rendering the tasks section."""
    # This test is no longer needed as the method doesn't exist
    pass

def test_render(cerebrum_system_ui, mock_streamlit):
    """Test rendering the complete UI."""
    # Mock render methods
    cerebrum_system_ui.render_sidebar = MagicMock()
    cerebrum_system_ui.render_terminal_section = MagicMock()
    cerebrum_system_ui.render_search_section = MagicMock()
    cerebrum_system_ui.render_context_section = MagicMock()
    cerebrum_system_ui.render_indexing_section = MagicMock()
    
    # Mock st.tabs to return the correct number of tabs
    mock_streamlit.tabs.return_value = [MagicMock(), MagicMock(), MagicMock(), MagicMock()]
    
    # Call the method
    cerebrum_system_ui.render()
    
    # Verify page config was set
    mock_streamlit.set_page_config.assert_called_once_with(
        page_title="Cerebrum System Core",
        page_icon="🧠",
        layout="wide"
    )
    
    # Verify render methods were called
    cerebrum_system_ui.render_sidebar.assert_called_once()
    cerebrum_system_ui.render_terminal_section.assert_called_once()
    cerebrum_system_ui.render_search_section.assert_called_once()
    cerebrum_system_ui.render_context_section.assert_called_once()
    cerebrum_system_ui.render_indexing_section.assert_called_once()

def test_run_async():
    """Test the run_async helper function."""
    async def async_func(x, y):
        return x + y
    
    result = run_async(async_func, 1, 2)
    assert result == 3 