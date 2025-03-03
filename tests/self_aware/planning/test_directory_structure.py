"""
Unit tests for the planning directory structure and initialization of the Goal Decomposition Engine.
"""

import pytest
import os
import importlib
import sys
from pathlib import Path

class TestDirectoryStructure:
    """Test suite for the planning directory structure."""
    
    def test_planning_directory_exists(self):
        """Test that the planning directory exists."""
        planning_dir = Path("src/server/planning")
        assert planning_dir.exists(), "Planning directory does not exist"
        assert planning_dir.is_dir(), "Planning path is not a directory"
    
    def test_init_file_exists(self):
        """Test that the __init__.py file exists in the planning directory."""
        init_file = Path("src/server/planning/__init__.py")
        assert init_file.exists(), "__init__.py file does not exist in planning directory"
        assert init_file.is_file(), "__init__.py path is not a file"
    
    def test_goal_decomposition_file_exists(self):
        """Test that the goal_decomposition.py file exists in the planning directory."""
        goal_decomposition_file = Path("src/server/planning/goal_decomposition.py")
        assert goal_decomposition_file.exists(), "goal_decomposition.py file does not exist in planning directory"
        assert goal_decomposition_file.is_file(), "goal_decomposition.py path is not a file"

class TestModuleImports:
    """Test suite for module imports."""
    
    def test_planning_package_importable(self):
        """Test that the planning package can be imported."""
        try:
            import src.server.planning
            assert True, "Planning package imported successfully"
        except ImportError as e:
            pytest.fail(f"Failed to import planning package: {e}")
    
    def test_goal_decomposition_importable(self):
        """Test that the goal_decomposition module can be imported."""
        try:
            import src.server.planning.goal_decomposition
            assert True, "Goal decomposition module imported successfully"
        except ImportError as e:
            pytest.fail(f"Failed to import goal_decomposition module: {e}")
    
    def test_goal_decomposition_classes_importable(self):
        """Test that the goal decomposition classes can be imported."""
        try:
            from src.server.planning.goal_decomposition import (
                GoalDecompositionEngine,
                GoalType,
                DecompositionStrategy,
                ResourceEstimate,
                SubGoal,
                DecomposedGoal
            )
            assert True, "Goal decomposition classes imported successfully"
        except ImportError as e:
            pytest.fail(f"Failed to import goal decomposition classes: {e}")

class TestSelfAwareIntegrationImports:
    """Test suite for self-aware integration imports."""
    
    def test_goal_decomposition_imported_in_self_aware_integration(self):
        """Test that the goal_decomposition module is imported in self_aware_integration.py."""
        with open("src/server/self_aware_integration.py", "r") as f:
            content = f.read()
        
        assert "from src.server.planning.goal_decomposition import" in content, \
            "Goal decomposition import not found in self_aware_integration.py"
        
        assert "GoalDecompositionEngine" in content, \
            "GoalDecompositionEngine import not found in self_aware_integration.py"
        
        assert "GoalType" in content, \
            "GoalType import not found in self_aware_integration.py"
        
        assert "DecompositionStrategy" in content, \
            "DecompositionStrategy import not found in self_aware_integration.py"
    
    def test_goal_decomposition_engine_initialized_in_self_aware_system(self):
        """Test that the GoalDecompositionEngine is initialized in the SelfAwareSystem."""
        with open("src/server/self_aware_integration.py", "r") as f:
            content = f.read()
        
        assert "self.goal_decomposition_engine = GoalDecompositionEngine" in content, \
            "GoalDecompositionEngine initialization not found in SelfAwareSystem"
        
        assert "knowledge_system=self.knowledge_system" in content, \
            "Knowledge system not passed to GoalDecompositionEngine initialization"
    
    def test_goal_decomposition_methods_in_self_aware_system(self):
        """Test that the goal decomposition methods are defined in the SelfAwareSystem."""
        with open("src/server/self_aware_integration.py", "r") as f:
            content = f.read()
        
        assert "async def decompose_goal" in content, \
            "decompose_goal method not found in SelfAwareSystem"
        
        assert "async def get_decomposed_goal" in content, \
            "get_decomposed_goal method not found in SelfAwareSystem"
        
        assert "async def prioritize_subgoals" in content, \
            "prioritize_subgoals method not found in SelfAwareSystem"
        
        assert "async def estimate_goal_resources" in content, \
            "estimate_goal_resources method not found in SelfAwareSystem"
        
        assert "async def validate_goal_decomposition" in content, \
            "validate_goal_decomposition method not found in SelfAwareSystem"

class TestPlanningWorkerIntegration:
    """Test suite for planning worker integration."""
    
    def test_planning_worker_updated_with_goal_decomposition_engine(self):
        """Test that the PlanningWorker is updated to use the GoalDecompositionEngine."""
        with open("src/server/system/cognitive_loop.py", "r") as f:
            content = f.read()
        
        assert "def __init__(self, knowledge_system=None, parameter_manager=None, goal_decomposition_engine=None)" in content, \
            "PlanningWorker constructor not updated to accept goal_decomposition_engine"
        
        assert "self.goal_decomposition_engine = goal_decomposition_engine" in content, \
            "goal_decomposition_engine not stored in PlanningWorker"
        
        assert "if self.goal_decomposition_engine:" in content, \
            "PlanningWorker not checking for goal_decomposition_engine"
        
        assert "await self.goal_decomposition_engine.decompose_goal" in content, \
            "PlanningWorker not using goal_decomposition_engine.decompose_goal"
    
    def test_register_specialized_workers_updated(self):
        """Test that the register_specialized_workers method is updated to pass the goal_decomposition_engine."""
        with open("src/server/self_aware_integration.py", "r") as f:
            content = f.read()
        
        assert "goal_decomposition_engine=self.goal_decomposition_engine" in content, \
            "goal_decomposition_engine not passed to PlanningWorker in register_specialized_workers" 