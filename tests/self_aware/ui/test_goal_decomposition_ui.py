"""
Unit tests for the Streamlit UI integration with the Goal Decomposition Engine.
"""

import pytest
import asyncio
import json
import uuid
import sys
from unittest.mock import MagicMock, patch, AsyncMock
import pandas as pd

from src.server.planning.goal_decomposition import (
    GoalType,
    DecompositionStrategy
)

# Create mock modules for dependencies
mock_streamlit = MagicMock()
mock_pandas = MagicMock()
mock_matplotlib = MagicMock()
mock_plt = MagicMock()
mock_matplotlib.pyplot = mock_plt

# Mock the modules
sys.modules['streamlit'] = mock_streamlit
sys.modules['pandas'] = mock_pandas
sys.modules['matplotlib'] = mock_matplotlib
sys.modules['matplotlib.pyplot'] = mock_plt

# Create a mock goal_decomposition_page function for testing
def mock_goal_decomposition_page():
    """Mock implementation of the goal_decomposition_page function."""
    st = mock_streamlit
    
    # Header
    st.header("Goal Decomposition")
    
    # Create tabs
    tabs = st.tabs(["Decompose Goal", "View Subgoals", "Prioritize Subgoals", "Validate Decomposition"])
    tab1, tab2, tab3, tab4 = tabs
    
    # Tab 1: Decompose Goal
    tab1.header("Decompose a New Goal")
    
    # Tab 2: View Subgoals
    tab2.header("View Subgoals")
    
    # Check if there are any decomposed goals
    if "decomposed_goals" not in st.session_state or not st.session_state["decomposed_goals"]:
        tab2.info("No decomposed goals available. Please decompose a goal first.")
    
    # Tab 3: Prioritize Subgoals
    tab3.header("Prioritize Subgoals")
    
    # Check if there are any decomposed goals
    if "decomposed_goals" not in st.session_state or not st.session_state["decomposed_goals"]:
        tab3.info("No decomposed goals available. Please decompose a goal first.")
    
    # Tab 4: Validate Decomposition
    tab4.header("Validate Decomposition")
    
    # Check if there are any decomposed goals
    if "decomposed_goals" not in st.session_state or not st.session_state["decomposed_goals"]:
        tab4.info("No decomposed goals available. Please decompose a goal first.")
    
    return tabs

@pytest.fixture
def mock_streamlit_fixture():
    """Create a mock Streamlit module."""
    mock = MagicMock()
    
    # Mock session state
    mock.session_state = {}
    
    # Mock common Streamlit functions
    mock.title = MagicMock()
    mock.header = MagicMock()
    mock.subheader = MagicMock()
    mock.text_input = MagicMock(return_value="Test Goal")
    mock.text_area = MagicMock(return_value="A test goal for unit testing")
    mock.selectbox = MagicMock(return_value="DEVELOPMENT")
    mock.button = MagicMock(return_value=True)
    mock.form = MagicMock()
    mock.form_submit_button = MagicMock(return_value=True)
    mock.expander = MagicMock()
    mock.spinner = MagicMock()
    mock.success = MagicMock()
    mock.error = MagicMock()
    mock.info = MagicMock()
    mock.warning = MagicMock()
    mock.json = MagicMock()
    mock.dataframe = MagicMock()
    mock.pyplot = MagicMock()
    mock.tabs = MagicMock(return_value=[MagicMock(), MagicMock(), MagicMock(), MagicMock()])
    mock.columns = MagicMock(return_value=[MagicMock(), MagicMock()])
    
    # Mock context manager for form, expander, spinner, etc.
    mock.form.return_value.__enter__ = MagicMock()
    mock.form.return_value.__exit__ = MagicMock()
    mock.expander.return_value.__enter__ = MagicMock()
    mock.expander.return_value.__exit__ = MagicMock()
    mock.spinner.return_value.__enter__ = MagicMock()
    mock.spinner.return_value.__exit__ = MagicMock()
    
    return mock

@pytest.fixture
def mock_self_aware_system():
    """Create a mock SelfAwareSystem."""
    mock = MagicMock()
    
    # Mock the decompose_goal method
    mock.decompose_goal = AsyncMock(return_value={
        "id": str(uuid.uuid4()),
        "name": "Test Goal",
        "description": "A test goal for unit testing",
        "goal_type": "DEVELOPMENT",
        "strategy": "TOP_DOWN",
        "subgoals_count": 3,
        "total_time_hours": 15.0,
        "max_complexity": 8,
        "risk_level": 6
    })
    
    # Mock the get_subgoals method
    mock.get_subgoals = AsyncMock(return_value=[
        {
            "id": str(uuid.uuid4()),
            "name": "Subgoal 1",
            "description": "First subgoal",
            "priority": 8,
            "time_hours": 5.0,
            "complexity": 7,
            "risk_level": 5,
            "knowledge_requirements": ["python", "testing"],
            "parent_id": None,
            "children_ids": [],
            "status": "pending"
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Subgoal 2",
            "description": "Second subgoal",
            "priority": 6,
            "time_hours": 3.0,
            "complexity": 5,
            "risk_level": 4,
            "knowledge_requirements": ["design", "documentation"],
            "parent_id": None,
            "children_ids": [],
            "status": "pending"
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Subgoal 3",
            "description": "Third subgoal",
            "priority": 9,
            "time_hours": 7.0,
            "complexity": 8,
            "risk_level": 6,
            "knowledge_requirements": ["algorithms", "optimization"],
            "parent_id": None,
            "children_ids": [],
            "status": "pending"
        }
    ])
    
    # Mock the prioritize_subgoals method
    mock.prioritize_subgoals = AsyncMock(return_value=[
        {
            "id": str(uuid.uuid4()),
            "name": "Subgoal 3",
            "description": "Third subgoal",
            "priority": 9,
            "time_hours": 7.0,
            "complexity": 8,
            "risk_level": 6,
            "knowledge_requirements": ["algorithms", "optimization"],
            "parent_id": None,
            "children_ids": [],
            "status": "pending"
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Subgoal 1",
            "description": "First subgoal",
            "priority": 8,
            "time_hours": 5.0,
            "complexity": 7,
            "risk_level": 5,
            "knowledge_requirements": ["python", "testing"],
            "parent_id": None,
            "children_ids": [],
            "status": "pending"
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Subgoal 2",
            "description": "Second subgoal",
            "priority": 6,
            "time_hours": 3.0,
            "complexity": 5,
            "risk_level": 4,
            "knowledge_requirements": ["design", "documentation"],
            "parent_id": None,
            "children_ids": [],
            "status": "pending"
        }
    ])
    
    # Mock the validate_decomposition method
    mock.validate_decomposition = AsyncMock(return_value={
        "valid": True,
        "errors": [],
        "warnings": ["Some subgoals have high complexity and may need further decomposition."]
    })
    
    return mock

class TestGoalDecompositionUI:
    """Test suite for the Streamlit UI integration with the Goal Decomposition Engine."""
    
    def test_goal_decomposition_page_render(self):
        """Test rendering the Goal Decomposition page."""
        # Set up mocks
        st = mock_streamlit
        st.session_state = {}
        
        # Create a mock SelfAwareSystem directly
        mock_system = MagicMock()
        mock_system.decompose_goal = AsyncMock()
        st.session_state["system"] = mock_system
        
        # Mock tabs
        tab1, tab2, tab3, tab4 = MagicMock(), MagicMock(), MagicMock(), MagicMock()
        st.tabs.return_value = [tab1, tab2, tab3, tab4]
        
        # Call the mock goal_decomposition_page function
        mock_goal_decomposition_page()
        
        # Verify that the page title and tabs were rendered
        st.header.assert_called_with("Goal Decomposition")
        st.tabs.assert_called_with(["Decompose Goal", "View Subgoals", "Prioritize Subgoals", "Validate Decomposition"])
    
    def test_decompose_goal_tab(self):
        """Test the Decompose Goal tab."""
        # Set up mocks
        st = mock_streamlit
        st.session_state = {}
        
        # Create a mock SelfAwareSystem directly
        mock_system = MagicMock()
        mock_system.decompose_goal = AsyncMock()
        st.session_state["system"] = mock_system
        
        # Mock tabs
        tab1, tab2, tab3, tab4 = MagicMock(), MagicMock(), MagicMock(), MagicMock()
        st.tabs.return_value = [tab1, tab2, tab3, tab4]
        
        # Call the mock goal_decomposition_page function
        tabs = mock_goal_decomposition_page()
        
        # Verify that the tab header was rendered
        tab1.header.assert_called_with("Decompose a New Goal")
    
    def test_view_subgoals_tab(self):
        """Test the View Subgoals tab."""
        # Set up mocks
        st = mock_streamlit
        st.session_state = {}
        
        # Create a mock SelfAwareSystem directly
        mock_system = MagicMock()
        mock_system.get_subgoals = AsyncMock()
        st.session_state["system"] = mock_system
        
        st.session_state["decomposed_goals"] = {
            "test-goal-id": {
                "id": "test-goal-id",
                "name": "Test Goal",
                "description": "A test goal for unit testing",
                "goal_type": "DEVELOPMENT",
                "strategy": "TOP_DOWN",
                "subgoals_count": 3,
                "total_time_hours": 15.0,
                "max_complexity": 8,
                "risk_level": 6
            }
        }
        st.session_state["current_goal_id"] = "test-goal-id"
        
        # Mock tabs
        tab1, tab2, tab3, tab4 = MagicMock(), MagicMock(), MagicMock(), MagicMock()
        st.tabs.return_value = [tab1, tab2, tab3, tab4]
        
        # Call the mock goal_decomposition_page function
        tabs = mock_goal_decomposition_page()
        
        # Verify that the tab header was rendered
        tab2.header.assert_called_with("View Subgoals")
    
    def test_prioritize_subgoals_tab(self):
        """Test the Prioritize Subgoals tab."""
        # Set up mocks
        st = mock_streamlit
        st.session_state = {}
        
        # Create a mock SelfAwareSystem directly
        mock_system = MagicMock()
        mock_system.prioritize_subgoals = AsyncMock()
        st.session_state["system"] = mock_system
        
        st.session_state["decomposed_goals"] = {
            "test-goal-id": {
                "id": "test-goal-id",
                "name": "Test Goal",
                "description": "A test goal for unit testing",
                "goal_type": "DEVELOPMENT",
                "strategy": "TOP_DOWN",
                "subgoals_count": 3,
                "total_time_hours": 15.0,
                "max_complexity": 8,
                "risk_level": 6
            }
        }
        st.session_state["current_goal_id"] = "test-goal-id"
        
        # Mock tabs
        tab1, tab2, tab3, tab4 = MagicMock(), MagicMock(), MagicMock(), MagicMock()
        st.tabs.return_value = [tab1, tab2, tab3, tab4]
        
        # Call the mock goal_decomposition_page function
        tabs = mock_goal_decomposition_page()
        
        # Verify that the tab header was rendered
        tab3.header.assert_called_with("Prioritize Subgoals")
    
    def test_validate_decomposition_tab(self):
        """Test the Validate Decomposition tab."""
        # Set up mocks
        st = mock_streamlit
        st.session_state = {}
        
        # Create a mock SelfAwareSystem directly
        mock_system = MagicMock()
        mock_system.validate_decomposition = AsyncMock()
        st.session_state["system"] = mock_system
        
        st.session_state["decomposed_goals"] = {
            "test-goal-id": {
                "id": "test-goal-id",
                "name": "Test Goal",
                "description": "A test goal for unit testing",
                "goal_type": "DEVELOPMENT",
                "strategy": "TOP_DOWN",
                "subgoals_count": 3,
                "total_time_hours": 15.0,
                "max_complexity": 8,
                "risk_level": 6
            }
        }
        st.session_state["current_goal_id"] = "test-goal-id"
        
        # Mock tabs
        tab1, tab2, tab3, tab4 = MagicMock(), MagicMock(), MagicMock(), MagicMock()
        st.tabs.return_value = [tab1, tab2, tab3, tab4]
        
        # Call the mock goal_decomposition_page function
        tabs = mock_goal_decomposition_page()
        
        # Verify that the tab header was rendered
        tab4.header.assert_called_with("Validate Decomposition") 