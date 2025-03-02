import pytest
import os
import shutil
import tempfile
from datetime import datetime

from src.server.context.parameter_manager import AIParameterManager, ParameterSet, TaskType


class TestAIParameterManager:
    """Tests for the AI Parameter Manager"""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for testing"""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)

    @pytest.fixture
    def parameter_manager(self, temp_dir):
        """Create a parameter manager with a temporary storage path"""
        manager = AIParameterManager(storage_path=temp_dir)
        return manager

    def test_create_parameter_set(self, parameter_manager):
        """Test creating a parameter set"""
        param_id = parameter_manager.create_parameter_set(
            model_name="test-model",
            temperature=0.5,
            top_p=0.9,
            max_tokens=1000
        )
        
        # Verify the parameter set was created
        assert param_id in parameter_manager.parameter_sets
        param_set = parameter_manager.parameter_sets[param_id]
        assert param_set.model_name == "test-model"
        assert param_set.temperature == 0.5
        assert param_set.top_p == 0.9
        assert param_set.max_tokens == 1000

    def test_get_parameter_set(self, parameter_manager):
        """Test retrieving a parameter set"""
        param_id = parameter_manager.create_parameter_set(
            model_name="test-model",
            temperature=0.5
        )
        
        # Retrieve the parameter set
        param_set = parameter_manager.get_parameter_set(param_id)
        assert param_set is not None
        assert param_set.model_name == "test-model"
        assert param_set.temperature == 0.5

    def test_update_parameter_set(self, parameter_manager):
        """Test updating a parameter set"""
        param_id = parameter_manager.create_parameter_set(
            model_name="test-model",
            temperature=0.5
        )
        
        # Update the parameter set
        result = parameter_manager.update_parameter_set(
            param_id,
            temperature=0.7,
            max_tokens=2000
        )
        
        assert result is True
        param_set = parameter_manager.get_parameter_set(param_id)
        assert param_set.temperature == 0.7
        assert param_set.max_tokens == 2000
        assert param_set.model_name == "test-model"  # Unchanged

    def test_delete_parameter_set(self, parameter_manager):
        """Test deleting a parameter set"""
        param_id = parameter_manager.create_parameter_set(
            model_name="test-model"
        )
        
        # Delete the parameter set
        result = parameter_manager.delete_parameter_set(param_id)
        assert result is True
        assert param_id not in parameter_manager.parameter_sets

    def test_record_performance(self, parameter_manager):
        """Test recording performance metrics"""
        param_id = parameter_manager.create_parameter_set(
            model_name="test-model"
        )
        
        # Record performance
        parameter_manager.record_performance(
            task_id="test-task",
            parameter_set_id=param_id,
            execution_time=1.5,
            token_count=100,
            success=True,
            quality_score=0.8
        )
        
        # Verify performance was recorded
        assert len(parameter_manager.performance_history) == 1
        perf = parameter_manager.performance_history[0]
        assert perf.task_id == "test-task"
        assert perf.parameter_set_id == param_id
        assert perf.execution_time == 1.5
        assert perf.token_count == 100
        assert perf.success is True
        assert perf.quality_score == 0.8

    def test_get_optimal_parameters(self, parameter_manager):
        """Test getting optimal parameters for a task type"""
        # Create a parameter set and record performance
        param_id = parameter_manager.create_parameter_set(
            model_name="test-model",
            temperature=0.5
        )
        
        parameter_manager.record_performance(
            task_id="code_generation_1",
            parameter_set_id=param_id,
            execution_time=1.5,
            token_count=100,
            success=True,
            quality_score=0.8
        )
        
        # Get optimal parameters
        optimal_params = parameter_manager.get_optimal_parameters(
            task_type="code_generation",
            model_name="test-model"
        )
        
        assert optimal_params is not None
        assert optimal_params.model_name == "test-model"

    def test_evolve_parameters(self, parameter_manager):
        """Test evolving parameters based on performance"""
        # Create a parameter set and record performance
        param_id = parameter_manager.create_parameter_set(
            model_name="test-model",
            temperature=0.5
        )
        
        parameter_manager.record_performance(
            task_id="code_generation_1",
            parameter_set_id=param_id,
            execution_time=1.5,
            token_count=100,
            success=True,
            quality_score=0.8
        )
        
        # Evolve parameters with no exploration (to ensure deterministic test)
        evolved_params = parameter_manager.evolve_parameters(
            task_type="code_generation",
            model_name="test-model",
            exploration_rate=0.0
        )
        
        assert evolved_params is not None
        assert evolved_params.model_name == "test-model"
        # Should return the current best parameters since exploration_rate is 0
        assert evolved_params.temperature == 0.5

    def test_analyze_parameter_impact(self, parameter_manager):
        """Test analyzing parameter impact on performance"""
        # Create parameter sets with different temperatures
        param_id1 = parameter_manager.create_parameter_set(
            model_name="test-model",
            temperature=0.2
        )
        
        param_id2 = parameter_manager.create_parameter_set(
            model_name="test-model",
            temperature=0.5
        )
        
        param_id3 = parameter_manager.create_parameter_set(
            model_name="test-model",
            temperature=0.8
        )
        
        # Record performance for each
        parameter_manager.record_performance(
            task_id="code_generation_1",
            parameter_set_id=param_id1,
            execution_time=1.5,
            token_count=100,
            success=True,
            quality_score=0.7
        )
        
        parameter_manager.record_performance(
            task_id="code_generation_2",
            parameter_set_id=param_id2,
            execution_time=1.2,
            token_count=120,
            success=True,
            quality_score=0.8
        )
        
        parameter_manager.record_performance(
            task_id="code_generation_3",
            parameter_set_id=param_id3,
            execution_time=1.8,
            token_count=150,
            success=True,
            quality_score=0.6
        )
        
        # Analyze parameter impact
        impact = parameter_manager.analyze_parameter_impact("code_generation")
        
        assert impact is not None
        assert "temperature" in impact
        # The exact values might vary, but we should have some temperature ranges
        assert len(impact["temperature"]) > 0 