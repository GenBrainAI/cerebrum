"""
Test the integration of the Goal Decomposition Engine with the Self-Aware System.
"""

import pytest
import asyncio
from unittest.mock import MagicMock, patch, AsyncMock
import os
import tempfile
import shutil

from src.server.self_aware_integration import SelfAwareSystem
from src.server.planning.goal_decomposition import (
    GoalDecompositionEngine,
    GoalType,
    DecompositionStrategy
)
from src.server.system.cognitive_loop import (
    CognitivePhase,
    WorkerType,
    TaskPriority
)

@pytest.fixture
async def self_aware_system():
    """Create a SelfAwareSystem instance with a temporary storage path."""
    # Create a temporary directory for storage
    temp_dir = tempfile.mkdtemp()
    
    # Create the system
    system = SelfAwareSystem(storage_path=temp_dir)
    
    # Initialize the system
    await system.initialize()
    
    yield system
    
    # Clean up
    shutil.rmtree(temp_dir)

@pytest.mark.asyncio
async def test_goal_decomposition_integration(self_aware_system):
    """Test the integration of the Goal Decomposition Engine with the Self-Aware System."""
    # Create a test goal
    test_goal = {
        "name": "Implement Feature X",
        "description": "Implement a new feature X for the system",
        "type": "DEVELOPMENT",
        "metadata": {
            "priority": "high",
            "owner": "test_user"
        }
    }
    
    # Decompose the goal
    decomposed_goal = await self_aware_system.decompose_goal(
        goal=test_goal,
        strategy="TOP_DOWN"
    )
    
    # Verify the decomposed goal
    assert decomposed_goal is not None
    assert decomposed_goal["name"] == test_goal["name"]
    assert decomposed_goal["goal_type"] == "DEVELOPMENT"
    assert len(decomposed_goal["subgoals"]) > 0
    assert len(decomposed_goal["root_subgoal_ids"]) > 0
    
    # Get the decomposed goal by ID
    retrieved_goal = await self_aware_system.get_decomposed_goal(decomposed_goal["id"])
    assert retrieved_goal is not None
    assert retrieved_goal["id"] == decomposed_goal["id"]
    
    # Prioritize subgoals
    prioritized_subgoals = await self_aware_system.prioritize_subgoals(decomposed_goal["id"])
    assert len(prioritized_subgoals) > 0
    
    # Estimate resources
    resource_estimate = await self_aware_system.estimate_goal_resources(decomposed_goal["id"])
    assert resource_estimate is not None
    assert resource_estimate["time_hours"] > 0
    
    # Validate decomposition
    validation = await self_aware_system.validate_goal_decomposition(decomposed_goal["id"])
    assert validation["valid"] is True

@pytest.mark.asyncio
async def test_planning_worker_integration(self_aware_system):
    """Test the integration of the Goal Decomposition Engine with the Planning Worker."""
    # Create a planning task
    task_id = self_aware_system.cognitive_orchestrator.create_task(
        title="Plan Feature Implementation",
        description="Create a plan for implementing Feature Y",
        phase=CognitivePhase.PLAN,
        worker_type=WorkerType.PLANNING,
        priority=TaskPriority.HIGH,
        context={
            "goal_type": "DEVELOPMENT",
            "decomposition_strategy": "TOP_DOWN"
        }
    )
    
    # Get the task
    task = self_aware_system.cognitive_orchestrator.get_task(task_id)
    assert task is not None
    
    # Process the task
    planning_worker = None
    for worker_type, workers in self_aware_system.cognitive_orchestrator.workers.items():
        if worker_type == WorkerType.PLANNING:
            # Get the first planning worker from the list
            planning_worker = workers[0] if workers else None
            break
    
    assert planning_worker is not None
    
    # Process the task
    processed_task = await planning_worker.process_task(task)
    
    # Verify the result
    assert processed_task.result is not None
    assert processed_task.result["plan_created"] is True
    assert "decomposed_goal_id" in processed_task.result
    assert "subgoal_count" in processed_task.result
    assert processed_task.result["subgoal_count"] > 0
    assert "prioritized_subgoals" in processed_task.result
    assert "resource_estimate" in processed_task.result
    assert "critical_path" in processed_task.result 