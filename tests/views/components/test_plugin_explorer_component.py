import pytest
from unittest.mock import MagicMock, patch, AsyncMock
import asyncio
import streamlit as st
from src.server.views.components.plugin_explorer_component import PluginExplorerComponent

class TestPluginExplorerComponent:
    """Tests for the PluginExplorerComponent."""
    
    @pytest.fixture
    def mock_plugin_manager(self):
        """Create a mock plugin manager."""
        mock_manager = MagicMock()
        mock_manager.list_plugins = MagicMock(return_value=[
            {
                "name": "crewai",
                "version": "1.0.0",
                "description": "CrewAI Plugin for orchestrating multi-agent workflows",
                "capabilities": ["agent_creation", "task_execution", "multi-agent_collaboration"],
                "is_initialized": True,
                "settings": {"model": "gpt-4o-mini"}
            },
            {
                "name": "autogen",
                "version": "1.0.0",
                "description": "Microsoft AutoGen Plugin for conversational agents",
                "capabilities": ["function_calling", "agent_handoff", "context_variables"],
                "is_initialized": True,
                "settings": {"model": "gpt-4o-mini"}
            }
        ])
        mock_manager.load_plugin = AsyncMock(return_value=True)
        return mock_manager
    
    @pytest.mark.asyncio
    async def test_render_with_plugins(self, mock_plugin_manager):
        """Test rendering the component with available plugins."""
        # Create component
        component = PluginExplorerComponent(mock_plugin_manager)
        
        # Mock streamlit functions
        with patch("streamlit.write") as mock_write, \
             patch("streamlit.warning") as mock_warning, \
             patch("streamlit.tabs") as mock_tabs, \
             patch("streamlit.subheader") as mock_subheader, \
             patch("streamlit.code") as mock_code, \
             patch("streamlit.markdown") as mock_markdown, \
             patch("streamlit.json") as mock_json, \
             patch("streamlit.columns", return_value=[MagicMock(), MagicMock()]) as mock_columns, \
             patch("src.server.views.components.plugin_explorer_component.PluginExplorerComponent._render_plugin_stats") as mock_stats, \
             patch("src.server.views.components.plugin_explorer_component.PluginExplorerComponent.render_capabilities_comparison") as mock_capabilities, \
             patch("src.server.views.components.plugin_explorer_component.PluginExplorerComponent._render_plugin_details") as mock_details:
            
            # Mock tabs to return a list of context managers
            mock_tab1 = MagicMock()
            mock_tab2 = MagicMock()
            mock_tabs.return_value = [mock_tab1, mock_tab2]
            
            # Call render
            component.render()
            
            # Assertions
            mock_plugin_manager.list_plugins.assert_called_once()
            mock_tabs.assert_called_once()  # Just check it was called, not the args
            mock_warning.assert_not_called()  # Should not show warning when plugins exist
            mock_capabilities.assert_called_once()  # Should call capabilities comparison
            mock_details.assert_called()  # Should call render details for each plugin
    
    @pytest.mark.asyncio
    async def test_render_no_plugins(self, mock_plugin_manager):
        """Test rendering when no plugins are available."""
        # Override mock to return empty list
        mock_plugin_manager.list_plugins.return_value = []
        
        # Create component
        component = PluginExplorerComponent(mock_plugin_manager)
        
        # Mock streamlit functions
        with patch("streamlit.write") as mock_write, \
             patch("streamlit.info") as mock_info, \
             patch("streamlit.warning") as mock_warning, \
             patch("streamlit.button") as mock_button, \
             patch("streamlit.tabs") as mock_tabs:
            
            mock_button.return_value = False
            
            # Call render
            component.render()
            
            # Assertions
            mock_plugin_manager.list_plugins.assert_called_once()
            mock_warning.assert_called_once()  # Should show warning when no plugins
            mock_tabs.assert_not_called()  # Should not create tabs
            mock_button.assert_called_once()  # Should show load demo button
    
    @pytest.mark.asyncio
    async def test_load_demo_plugins(self, mock_plugin_manager):
        """Test loading demo plugins."""
        # Create component
        component = PluginExplorerComponent(mock_plugin_manager)
        
        # Call _load_demo_plugins
        result = await component._load_demo_plugins()
        
        # Assertions
        assert result is True
        assert mock_plugin_manager.load_plugin.call_count == 3  # Should load 3 plugins
    
    @pytest.mark.asyncio
    async def test_render_capabilities_comparison(self, mock_plugin_manager):
        """Test rendering the capabilities comparison chart."""
        # Create component
        component = PluginExplorerComponent(mock_plugin_manager)
        
        # Mock pandas and altair
        with patch("pandas.DataFrame") as mock_df, \
             patch("altair.Chart") as mock_chart, \
             patch("streamlit.write") as mock_write, \
             patch("streamlit.altair_chart") as mock_altair_chart, \
             patch("streamlit.markdown") as mock_markdown, \
             patch("streamlit.columns") as mock_columns, \
             patch("streamlit.button") as mock_button:
            
            # Set up the mock to handle multiple write calls
            # We don't need to check the exact calls, just that it works
            
            # Mock chart methods to return self for method chaining
            mock_chart.return_value.mark_rect.return_value.encode.return_value.properties.return_value = "chart"
            mock_columns.return_value = [MagicMock(), MagicMock()]
            mock_button.return_value = False
            
            # Call render_capabilities_comparison
            component.render_capabilities_comparison()
            
            # Assertions - we don't need to check specific write calls
            mock_plugin_manager.list_plugins.assert_called_once()
            mock_df.assert_called_once()
            mock_chart.assert_called_once()
            mock_altair_chart.assert_called_once_with("chart", use_container_width=True) 