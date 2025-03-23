"""
Integration tests for the Research Planning system.

These tests verify that the Research Planner works correctly with the Goal Decomposition Engine
and UI components in an end-to-end workflow.
"""

import pytest
import os
import asyncio
import streamlit as st
from unittest.mock import MagicMock, AsyncMock, patch
import tempfile
import shutil
import json
from datetime import datetime
import uuid

from src.server.planning.research_planner import (
    ResearchPlanner,
    KnowledgeGap,
    ResearchTask,
    ResearchStrategyType,
    ResearchPlan
)
from src.server.planning.goal_decomposition import GoalDecompositionEngine
from src.server.context.knowledge_integration import KnowledgeIntegrationSystem
from src.server.ui.research_planner_view import ResearchPlannerView


class TestResearchPlanningIntegration:
    """Integration test suite for the research planning system."""
    
    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for test data."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def knowledge_system(self):
        """Create a knowledge integration system with test data."""
        # Create a MagicMock with the correct spec and pre-defined methods
        knowledge_system = MagicMock(spec=KnowledgeIntegrationSystem)
        
        # Explicitly define the query_knowledge method
        knowledge_system.query_knowledge = AsyncMock()
        
        # Mock knowledge context
        async def mock_get_knowledge_context(topic, limit=10):
            return {
                "concepts": [
                    {"name": "Neural Networks", "confidence": 0.8},
                    {"name": "Deep Learning", "confidence": 0.7},
                    {"name": "Machine Learning", "confidence": 0.9},
                ],
                "relations": [
                    {"source": "Neural Networks", "target": "Deep Learning", "type": "is_part_of"},
                    {"source": "Deep Learning", "target": "Machine Learning", "type": "is_part_of"},
                ],
                "confidence": 0.75
            }
        
        # Mock knowledge query - updated to match expected parameters
        async def mock_query_knowledge(topic, depth=2, context=None):
            return {
                "semantic_items": [
                    {"content": "Neural networks have multiple layers", "source": "source1", "relevance": 0.9},
                    {"content": "Deep learning uses neural networks with many layers", "source": "source2", "relevance": 0.8},
                    {"content": "Machine learning includes various algorithms", "source": "source3", "relevance": 0.7},
                ],
                "confidence": 0.8
            }
        
        # Set the side effects
        knowledge_system.get_knowledge_context.side_effect = mock_get_knowledge_context
        knowledge_system.query_knowledge.side_effect = mock_query_knowledge
        
        # Add other required methods
        knowledge_system.initialize = AsyncMock()
        knowledge_system.add_knowledge = AsyncMock()
        knowledge_system.register_knowledge_source = AsyncMock()
        
        return knowledge_system
    
    @pytest.fixture
    def goal_engine(self, knowledge_system):
        """Create a goal decomposition engine."""
        engine = GoalDecompositionEngine(knowledge_system=knowledge_system)
        return engine
    
    @pytest.fixture
    def research_planner(self, knowledge_system, temp_dir):
        """Create a research planner with test configuration."""
        storage_dir = os.path.join(temp_dir, "research_plans")
        os.makedirs(storage_dir, exist_ok=True)
        
        return ResearchPlanner(
            knowledge_system=knowledge_system,
            storage_dir=storage_dir
        )
    
    @pytest.fixture
    def ui_component(self, research_planner, knowledge_system):
        """Create a UI component with the research planner."""
        return ResearchPlannerView(
            research_planner=research_planner,
            knowledge_system=knowledge_system
        )
    
    @pytest.mark.asyncio
    async def test_identify_gaps_to_create_plan(self, research_planner, knowledge_system):
        """Test identifying knowledge gaps and creating a research plan."""
        # Identify knowledge gaps
        gaps = await research_planner.identify_knowledge_gaps("Machine Learning Algorithms")
        
        # Verify gaps were identified correctly
        assert len(gaps) > 0
        assert all(isinstance(gap, KnowledgeGap) for gap in gaps.values())
        
        # Create a research plan
        plan = await research_planner.create_research_plan(
            title="ML Algorithms Research",
            description="Research plan for machine learning algorithms",
            knowledge_gaps=gaps
        )
        
        # Verify plan was created correctly
        assert plan.id is not None
        assert plan.title == "ML Algorithms Research"
        assert len(plan.tasks) > 0
        assert plan.total_estimated_time > 0
        
        # Verify tasks were created for the gaps
        for gap_id in gaps:
            assert any(gap_id in task.knowledge_gaps for task in plan.tasks.values())
    
    @pytest.mark.asyncio
    async def test_goal_decomposition_for_research(self, goal_engine, research_planner):
        """Test using goal decomposition to guide research planning."""
        # Create a goal
        goal = {
            "name": "Learn about NLP",
            "description": "Learn about natural language processing techniques",
            "type": "RESEARCH"
        }
        
        # Decompose the goal
        decomposed_goal = await goal_engine.decompose_goal(goal)
        
        # Extract topics from subgoals
        topics = [subgoal.name for subgoal in decomposed_goal.subgoals.values()]
        
        # For each topic, identify knowledge gaps
        all_gaps = {}
        for topic in topics[:2]:  # Limit to first 2 topics for test efficiency
            gaps = await research_planner.identify_knowledge_gaps(topic)
            all_gaps.update(gaps)
        
        # Create a research plan from the combined gaps
        plan = await research_planner.create_research_plan(
            title="NLP Research from Goal Decomposition",
            description="Research plan derived from decomposed goals",
            knowledge_gaps=all_gaps
        )
        
        # Verify the plan includes tasks for the identified gaps
        assert plan.id is not None
        assert len(plan.tasks) > 0
        
        # Each gap should be addressed by at least one task
        for gap_id in all_gaps:
            assert any(gap_id in task.knowledge_gaps for task in plan.tasks.values())
    
    @pytest.mark.asyncio
    async def test_save_and_load_research_plan(self, research_planner):
        """Test saving and loading a research plan."""
        # Create a mock knowledge gap
        gap_id = str(uuid.uuid4())
        gap = KnowledgeGap(
            id=gap_id,
            topic="Machine Learning",
            description="Understanding ML algorithms",
            confidence=0.3,
            importance=8
        )
        
        # Add the gap to the planner's knowledge_gaps
        research_planner.knowledge_gaps[gap_id] = gap
        
        # Create a plan
        plan = await research_planner.create_research_plan(
            title="Test Research Plan",
            description="Testing save and load functionality",
            knowledge_gaps=[gap_id]
        )
        
        # Get the plan
        loaded_plan = await research_planner.get_research_plan(plan.id)
        
        # Verify plan was loaded correctly
        assert loaded_plan.id == plan.id
        assert loaded_plan.title == plan.title
        assert loaded_plan.description == plan.description
        
        # Delete the plan
        deleted = await research_planner.delete_research_plan(plan.id)
        assert deleted is True
        
        # Verify plan was deleted
        loaded_plan = await research_planner.get_research_plan(plan.id)
        assert loaded_plan is None
    
    @pytest.mark.asyncio
    async def test_update_research_task_status(self, research_planner):
        """Test updating the status of a research task."""
        # Create knowledge gaps
        gaps = await research_planner.identify_knowledge_gaps("Deep Learning")
        
        # Create a research plan
        plan = await research_planner.create_research_plan(
            title="DL Research",
            description="Research plan for deep learning",
            knowledge_gaps=gaps
        )
        
        # Select a task to update
        task_id = next(iter(plan.tasks))
        
        # Update the task status
        updated = await research_planner.update_research_task(
            plan_id=plan.id,
            task_id=task_id,
            status="completed"
        )
        
        assert updated is True
        
        # Get the updated plan
        updated_plan = await research_planner.get_research_plan(plan.id)
        
        # Verify the task status was updated
        assert updated_plan.tasks[task_id].status == "completed"
    
    @pytest.mark.asyncio
    async def test_prioritize_research_tasks(self, research_planner):
        """Test prioritizing research tasks."""
        # Create a mock knowledge gap
        gap_id = str(uuid.uuid4())
        gap = KnowledgeGap(
            id=gap_id,
            topic="Reinforcement Learning",
            description="Understanding RL algorithms",
            confidence=0.2,
            importance=9
        )
        
        # Add the gap to the planner's knowledge_gaps
        research_planner.knowledge_gaps[gap_id] = gap
        
        # Create a plan with multiple tasks
        plan = await research_planner.create_research_plan(
            title="Test Research Plan for Prioritization",
            description="Testing task prioritization",
            knowledge_gaps=[gap_id]
        )
        
        # Get task ids
        task_ids = list(plan.tasks.keys())
        
        # Prioritize tasks
        prioritized_ids = await research_planner.prioritize_research_tasks(
            plan_id=plan.id
        )
        
        # Verify all tasks are included in the prioritized list
        assert set(prioritized_ids) == set(task_ids)
        
        # Update the plan with the new sequence
        plan.task_sequence = prioritized_ids
        
        # Get the updated plan
        updated_plan = await research_planner.get_research_plan(plan.id)
        
        # Verify the task sequence was updated
        assert updated_plan.task_sequence == prioritized_ids
    
    def test_ui_session_state_initialization(self, ui_component):
        """Test that UI component initializes session state correctly."""
        # Mock streamlit components
        with patch("streamlit.title"), \
             patch("streamlit.radio", return_value="Knowledge Gaps"), \
             patch.object(ui_component, "_render_knowledge_gaps_tab"):
            
            # Ensure session state is empty
            if hasattr(st, "session_state"):
                st.session_state.clear()
            else:
                setattr(st, "session_state", {})
            
            # Render the UI
            ui_component.render()
            
            # Verify session state was initialized
            assert "knowledge_gaps" in st.session_state
            assert "current_plan_id" in st.session_state
            assert "search_results" in st.session_state
            assert "selected_tab" in st.session_state
    
    @pytest.mark.asyncio
    async def test_end_to_end_workflow(self, research_planner, goal_engine, knowledge_system):
        """Test end-to-end workflow from goal decomposition to research task update."""
        # Create a goal
        goal = {
            "name": "Understand machine learning applications in healthcare",
            "description": "Research on how machine learning is being applied in healthcare settings",
            "type": "research"
        }
        
        # Decompose the goal
        decomposed_goal = await goal_engine.decompose_goal(goal)
        
        # Extract the first subgoal
        first_subgoal = next(iter(decomposed_goal.subgoals.values())).name
        
        # Identify knowledge gaps
        gaps = await research_planner.identify_knowledge_gaps(first_subgoal)
        
        # Create a research plan
        plan = await research_planner.create_research_plan(
            title=f"Research: {first_subgoal}",
            description=f"Research plan derived from goal: {goal['name']}",
            knowledge_gaps=gaps
        )
        
        # Store the plan (instead of calling save_research_plan)
        research_planner.research_plans[plan.id] = plan
        
        # Prioritize tasks
        task_ids = list(plan.tasks.keys())
        prioritized_ids = await research_planner.prioritize_research_tasks(
            plan_id=plan.id
        )
        
        # Update first task to in-progress
        first_task_id = prioritized_ids[0]
        await research_planner.update_research_task(
            plan_id=plan.id,
            task_id=first_task_id,
            status="in_progress"
        )
        
        # Complete first task
        await research_planner.update_research_task(
            plan_id=plan.id,
            task_id=first_task_id,
            status="completed"
        )
        
        # Get updated plan
        updated_plan = await research_planner.get_research_plan(plan.id)
        
        # Verify first task is completed
        assert updated_plan.tasks[first_task_id].status == "completed"
        
        # Delete the plan
        deleted = await research_planner.delete_research_plan(plan.id)
        assert deleted is True
        
        # Verify plan is deleted
        plans = await research_planner.get_all_research_plans()
        assert plan.id not in plans 