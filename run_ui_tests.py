#!/usr/bin/env python
"""
Simple test runner for Research Planner UI tests
"""

import sys
import os
import unittest
from unittest.mock import MagicMock, patch, AsyncMock
import tempfile
import shutil
import uuid
from datetime import datetime

# Add the project root to the path so we can import modules
sys.path.insert(0, os.path.abspath("."))

# Import the modules we need to test
from src.server.planning.research_planner import (
    ResearchPlanner,
    KnowledgeGap,
    ResearchTask,
    ResearchPlan,
    ResearchStrategyType
)
from src.server.ui.research_planner_view import ResearchPlannerView

# Custom session state class that acts like an object but also like a dict
class SessionState(dict):
    """Custom session state that behaves like both a dict and an object with attributes."""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        for key, value in kwargs.items():
            setattr(self, key, value)
    
    def __getattr__(self, name):
        if name in self:
            return self[name]
        return None
    
    def __setattr__(self, name, value):
        self[name] = value
    
    def get(self, key, default=None):
        return self[key] if key in self else default


# Mock asyncio.run to return values directly
def mock_asyncio_run(coro):
    if isinstance(coro, AsyncMock):
        return coro.return_value
    return coro

# Mock Plotly modules to bypass visualization errors
class MockPlotly:
    def __init__(self):
        self.express = MagicMock()
        self.graph_objects = MagicMock()
        
        # Mock scatter
        self.graph_objects.Scatter = MagicMock()
        self.graph_objects.scatter = MagicMock()
        self.graph_objects.scatter.Marker = MagicMock()
        
        # Mock layout
        self.graph_objects.Layout = MagicMock()
        
        # Mock Figure
        self.graph_objects.Figure = MagicMock()

# Mock Streamlit
class MockStreamlit:
    """Mock Streamlit module for testing."""
    
    def __init__(self):
        self.sidebar = MagicMock()
        self.tabs = []
        self.columns_result = []
        self.form_submit_button_value = False
        self.session_state = SessionState(
            selected_tab="Knowledge Gaps",
            knowledge_gaps={},
            current_plan_id=None,
            search_results={}
        )
        self.experimental_rerun_called = False
        self.radio_result = "Knowledge Gaps"
        self.button_result = False
        self.text_input_result = ""
    
    def title(self, *args, **kwargs):
        return MagicMock()
    
    def header(self, *args, **kwargs):
        return MagicMock()
    
    def subheader(self, *args, **kwargs):
        return MagicMock()
    
    def markdown(self, *args, **kwargs):
        return MagicMock()
    
    def text(self, *args, **kwargs):
        return MagicMock()
    
    def write(self, *args, **kwargs):
        return MagicMock()
    
    def button(self, label, *args, **kwargs):
        return self.button_result
    
    def form(self, key):
        class FormContext:
            def __enter__(self):
                return MagicMock()
            def __exit__(self, exc_type, exc_val, exc_tb):
                pass
        return FormContext()
    
    def form_submit_button(self, label, *args, **kwargs):
        return self.form_submit_button_value
    
    def text_input(self, label, *args, **kwargs):
        return self.text_input_result
    
    def text_area(self, label, *args, **kwargs):
        return ""
    
    def number_input(self, label, *args, **kwargs):
        return kwargs.get("value", 0)
    
    def selectbox(self, label, options, *args, **kwargs):
        if options:
            return options[0]
        return None
    
    def multiselect(self, label, options, *args, **kwargs):
        return []
    
    def checkbox(self, label, *args, **kwargs):
        return False
    
    def radio(self, label, options, index=0, *args, **kwargs):
        return self.radio_result
    
    def slider(self, label, *args, **kwargs):
        return kwargs.get("value", 0)
    
    def tab(self, label):
        tab = MagicMock()
        self.tabs.append(tab)
        return tab
    
    def columns(self, spec):
        cols = [MagicMock() for _ in range(len(spec) if isinstance(spec, list) else spec)]
        self.columns_result = cols
        return cols
    
    def container(self):
        return MagicMock()
    
    def expander(self, label, *args, **kwargs):
        class ExpanderContext:
            def __enter__(self):
                return MagicMock()
            def __exit__(self, exc_type, exc_val, exc_tb):
                pass
        return ExpanderContext()
    
    def empty(self):
        return MagicMock()
    
    def dataframe(self, *args, **kwargs):
        return MagicMock()
    
    def info(self, *args, **kwargs):
        return MagicMock()
    
    def success(self, *args, **kwargs):
        return MagicMock()
    
    def warning(self, *args, **kwargs):
        return MagicMock()
    
    def error(self, *args, **kwargs):
        return MagicMock()
    
    def plotly_chart(self, *args, **kwargs):
        return MagicMock()
    
    def spinner(self, text):
        class SpinnerContext:
            def __enter__(self):
                return MagicMock()
            def __exit__(self, exc_type, exc_val, exc_tb):
                pass
        return SpinnerContext()
    
    def experimental_rerun(self):
        self.experimental_rerun_called = True
    
    def metric(self, label, value, delta=None):
        return MagicMock()
    
    def progress(self, value):
        return MagicMock()
    
    def download_button(self, *args, **kwargs):
        return False
    
    def json(self, *args, **kwargs):
        return MagicMock()
    
    def line_chart(self, *args, **kwargs):
        return MagicMock()
    
    def bar_chart(self, *args, **kwargs):
        return MagicMock()
    
    def altair_chart(self, *args, **kwargs):
        return MagicMock()
    
    def table(self, *args, **kwargs):
        return MagicMock()
    
    def tabs(self, *args, **kwargs):
        return [MagicMock() for _ in args[0]]


class TestResearchPlannerView(unittest.TestCase):
    """Test suite for the Research Planner UI."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create a mock research planner
        self.mock_research_planner = MagicMock()
        
        # Create sample data
        self.sample_gaps = {
            "gap1": KnowledgeGap(
                id="gap1",
                topic="AI Ethics",
                description="Understanding ethical implications of AI",
                confidence=0.3,
                importance=9,
                sources=["paper1", "book1"],
                related_gaps=[]
            ),
            "gap2": KnowledgeGap(
                id="gap2",
                topic="Neural Networks",
                description="Understanding deep learning architectures",
                confidence=0.5,
                importance=7,
                sources=["paper2"],
                related_gaps=["gap1"]
            )
        }
        
        self.sample_plan = ResearchPlan(
            id="plan1",
            title="AI Research Plan",
            description="A plan to research AI topics",
            knowledge_gaps={
                "gap1": self.sample_gaps["gap1"],
                "gap2": self.sample_gaps["gap2"]
            },
            tasks={
                "task1": ResearchTask(
                    id="task1",
                    title="Research Ethics in AI",
                    description="Explore ethical considerations in AI development",
                    strategy=ResearchStrategyType.SYSTEMATIC,
                    estimated_time_hours=2.0,
                    knowledge_gaps=["gap1"],
                    priority=8,
                    sources=[{"type": "paper", "title": "Ethics in AI"}],
                    dependencies=[],
                    status="pending"
                ),
                "task2": ResearchTask(
                    id="task2",
                    title="Study Neural Networks",
                    description="Learn about deep learning architectures",
                    strategy=ResearchStrategyType.EXPLORATORY,
                    estimated_time_hours=3.0,
                    knowledge_gaps=["gap2"],
                    priority=7,
                    dependencies=["task1"],
                    status="in_progress"
                )
            },
            total_estimated_time=5.0,
            creation_time=datetime.now().isoformat(),
            task_sequence=["task1", "task2"],
            status="pending"
        )
        
        # Set up the mock for streamlit
        self.mock_st = MockStreamlit()
        
        # Mock Plotly
        self.mock_plotly = MockPlotly()
        
        # Create the UI component
        with patch('src.server.ui.research_planner_view.st', self.mock_st):
            with patch('src.server.ui.research_planner_view.asyncio.run', mock_asyncio_run):
                with patch('src.server.ui.research_planner_view.go', self.mock_plotly.graph_objects):
                    with patch('src.server.ui.research_planner_view.px', self.mock_plotly.express):
                        self.ui = ResearchPlannerView(research_planner=self.mock_research_planner)
    
    def test_initialization(self):
        """Test initialization of ResearchPlannerView."""
        self.assertEqual(self.ui.research_planner, self.mock_research_planner)
    
    def test_render(self):
        """Test rendering the UI."""
        with patch('src.server.ui.research_planner_view.st', self.mock_st):
            with patch('src.server.ui.research_planner_view.asyncio.run', mock_asyncio_run):
                with patch('src.server.ui.research_planner_view.go', self.mock_plotly.graph_objects):
                    with patch('src.server.ui.research_planner_view.px', self.mock_plotly.express):
                        # Set mock expectations
                        self.mock_st.radio_result = "Knowledge Gaps"
                        
                        # Call render
                        self.ui.render()
    
    def test_render_knowledge_gaps_tab(self):
        """Test rendering the Knowledge Gaps tab."""
        with patch('src.server.ui.research_planner_view.st', self.mock_st):
            with patch('src.server.ui.research_planner_view.asyncio.run', mock_asyncio_run):
                with patch('src.server.ui.research_planner_view.go', self.mock_plotly.graph_objects):
                    with patch('src.server.ui.research_planner_view.px', self.mock_plotly.express):
                        # Set up mock data
                        self.mock_st.session_state.search_results = {
                            "topic": "Artificial Intelligence",
                            "gaps": self.sample_gaps
                        }
                        
                        # Call the tab render method directly - this should use existing search results
                        self.ui._render_knowledge_gaps_tab()
                        
                        # Now test search button functionality
                        self.mock_st.button_result = True
                        self.mock_st.text_input_result = "Machine Learning"
                        
                        # Mock the identify_knowledge_gaps method
                        self.mock_research_planner.identify_knowledge_gaps = MagicMock(return_value=self.sample_gaps)
                        
                        # Call the tab render method again with button clicked
                        self.ui._render_knowledge_gaps_tab()
                        
                        # Verify that the research planner method was called
                        self.mock_research_planner.identify_knowledge_gaps.assert_called_with("Machine Learning")
    
    def test_render_research_plans_tab(self):
        """Test rendering the Research Plans tab."""
        with patch('src.server.ui.research_planner_view.st', self.mock_st):
            with patch('src.server.ui.research_planner_view.asyncio.run', mock_asyncio_run):
                with patch('src.server.ui.research_planner_view.go', self.mock_plotly.graph_objects):
                    with patch('src.server.ui.research_planner_view.px', self.mock_plotly.express):
                        # Set up mock data
                        self.mock_research_planner.get_all_research_plans = MagicMock(return_value={
                            "plan1": self.sample_plan
                        })
                        
                        # Call the tab render method directly
                        self.ui._render_research_plans_tab()
                        
                        # Verify that the research planner method was called
                        self.mock_research_planner.get_all_research_plans.assert_called()


if __name__ == "__main__":
    unittest.main() 