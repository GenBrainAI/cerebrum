import pytest
import os
import shutil
import tempfile
import asyncio
from datetime import datetime

from src.server.self_aware_integration import (
    SelfAwareSystem,
    CognitivePhase,
    WorkerType,
    TaskPriority
)


class TestSelfAwareSystem:
    """Tests for the Self-Aware System integration"""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for testing"""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)

    @pytest.fixture
    def self_aware_system(self, temp_dir):
        """Create a self-aware system with a temporary storage path"""
        system = SelfAwareSystem(storage_path=temp_dir)
        return system

    def test_initialization(self, self_aware_system):
        """Test system initialization"""
        # Verify that the system components are initialized
        assert self_aware_system.parameter_manager is not None
        assert self_aware_system.knowledge_system is not None
        assert self_aware_system.cognitive_orchestrator is not None
        
        # Verify that basic knowledge is initialized
        semantic_results = self_aware_system.knowledge_system.search_semantic_memory("Self-Aware Cerebrum")
        assert len(semantic_results) > 0
        
        procedural_results = self_aware_system.knowledge_system.search_procedural_memory("Run Cognitive Cycle")
        assert len(procedural_results) > 0

    def test_add_semantic_knowledge(self, self_aware_system):
        """Test adding semantic knowledge"""
        item_id = self_aware_system.add_semantic_knowledge(
            concept="AI Testing",
            definition="The process of testing AI systems to ensure they work correctly.",
            related_concepts=["AI", "Testing"],
            tags=["testing", "quality assurance"]
        )
        
        # Verify the knowledge was added
        semantic_results = self_aware_system.knowledge_system.search_semantic_memory("AI Testing")
        assert len(semantic_results) > 0
        assert semantic_results[0].concept == "AI Testing"
        assert semantic_results[0].definition == "The process of testing AI systems to ensure they work correctly."
        assert "AI" in semantic_results[0].related_concepts
        assert "Testing" in semantic_results[0].related_concepts
        assert "testing" in semantic_results[0].tags
        assert "quality assurance" in semantic_results[0].tags

    def test_add_procedural_knowledge(self, self_aware_system):
        """Test adding procedural knowledge"""
        item_id = self_aware_system.add_procedural_knowledge(
            task_name="Test AI System",
            description="Steps to test an AI system.",
            steps=[
                "Define test objectives",
                "Create test cases",
                "Execute tests",
                "Analyze results",
                "Report findings"
            ],
            expected_outcome="A thoroughly tested AI system with known behavior.",
            tags=["testing", "methodology"]
        )
        
        # Verify the knowledge was added
        procedural_results = self_aware_system.knowledge_system.search_procedural_memory("Test AI System")
        assert len(procedural_results) > 0
        assert procedural_results[0].task_name == "Test AI System"
        assert procedural_results[0].description == "Steps to test an AI system."
        assert len(procedural_results[0].steps) == 5
        assert "Define test objectives" in procedural_results[0].steps
        assert procedural_results[0].expected_outcome == "A thoroughly tested AI system with known behavior."
        assert "testing" in procedural_results[0].tags
        assert "methodology" in procedural_results[0].tags

    def test_add_episodic_knowledge(self, self_aware_system):
        """Test adding episodic knowledge"""
        item_id = self_aware_system.add_episodic_knowledge(
            title="First System Test",
            description="Conducted the first test of the Self-Aware Cerebrum system.",
            actors=["Tester", "Self-Aware Cerebrum"],
            tags=["testing", "milestone"]
        )
        
        # Verify the knowledge was added
        episodic_results = self_aware_system.knowledge_system.search_episodic_memory("First System Test")
        assert len(episodic_results) > 0
        assert episodic_results[0].title == "First System Test"
        assert episodic_results[0].description == "Conducted the first test of the Self-Aware Cerebrum system."
        assert "Tester" in episodic_results[0].actors
        assert "Self-Aware Cerebrum" in episodic_results[0].actors
        assert "testing" in episodic_results[0].tags
        assert "milestone" in episodic_results[0].tags

    def test_create_cognitive_task(self, self_aware_system):
        """Test creating a cognitive task"""
        task_id = self_aware_system.create_cognitive_task(
            title="Test Task",
            description="A test task",
            phase=CognitivePhase.UNDERSTAND,
            worker_type=WorkerType.REQUIREMENTS,
            priority=TaskPriority.HIGH
        )
        
        # Verify the task was created
        task = self_aware_system.get_cognitive_task(task_id)
        assert task is not None
        assert task.title == "Test Task"
        assert task.description == "A test task"
        assert task.phase == CognitivePhase.UNDERSTAND
        assert task.worker_type == WorkerType.REQUIREMENTS
        assert task.priority == TaskPriority.HIGH

    def test_get_knowledge_context(self, self_aware_system):
        """Test getting knowledge context"""
        # Add some knowledge
        self_aware_system.add_semantic_knowledge(
            concept="AI Testing",
            definition="The process of testing AI systems."
        )
        
        self_aware_system.add_episodic_knowledge(
            title="Test Execution",
            description="Executed tests on the AI system."
        )
        
        self_aware_system.add_procedural_knowledge(
            task_name="Run Tests",
            description="Steps to run tests.",
            steps=["Step 1", "Step 2"],
            expected_outcome="Completed tests"
        )
        
        # Get knowledge context
        context = self_aware_system.get_knowledge_context("testing")
        
        # Verify that we got some results
        assert context is not None
        assert any(len(items) > 0 for items in context.values())

    def test_update_development_context(self, self_aware_system):
        """Test updating development context"""
        # Update context
        self_aware_system.update_development_context("test_key", "test_value")
        
        # Verify the context was updated
        value = self_aware_system.get_development_context("test_key")
        assert value == "test_value"
        
        # Update with a complex value
        self_aware_system.update_development_context("complex_key", {"nested": "value"})
        
        # Verify the context was updated
        value = self_aware_system.get_development_context("complex_key")
        assert value == {"nested": "value"}
        
        # Get the entire context
        context = self_aware_system.get_development_context()
        assert context["test_key"] == "test_value"
        assert context["complex_key"] == {"nested": "value"}

    def test_get_current_phase(self, self_aware_system):
        """Test getting the current phase"""
        # Default phase should be UNDERSTAND
        phase = self_aware_system.get_current_phase()
        assert phase == CognitivePhase.UNDERSTAND

    def test_get_tasks_by_phase(self, self_aware_system):
        """Test getting tasks by phase"""
        # Create tasks in different phases
        understand_id = self_aware_system.create_cognitive_task(
            title="Understand Task",
            description="An understand task",
            phase=CognitivePhase.UNDERSTAND
        )
        
        plan_id = self_aware_system.create_cognitive_task(
            title="Plan Task",
            description="A plan task",
            phase=CognitivePhase.PLAN
        )
        
        # Get tasks by phase
        understand_tasks = self_aware_system.get_tasks_by_phase(CognitivePhase.UNDERSTAND)
        assert len(understand_tasks) > 0
        assert any(task.id == understand_id for task in understand_tasks)
        
        plan_tasks = self_aware_system.get_tasks_by_phase(CognitivePhase.PLAN)
        assert len(plan_tasks) > 0
        assert any(task.id == plan_id for task in plan_tasks)

    @pytest.mark.asyncio
    async def test_start_cognitive_cycle(self, self_aware_system):
        """Test starting a cognitive cycle"""
        # This is a more complex test that involves async operations
        # We'll just verify that it doesn't raise an exception
        try:
            task_id = await self_aware_system.start_cognitive_cycle()
            assert task_id is not None
        except Exception as e:
            pytest.fail(f"start_cognitive_cycle raised an exception: {e}")

    def test_get_optimal_parameters(self, self_aware_system):
        """Test getting optimal parameters"""
        # Get optimal parameters for a task type
        params = self_aware_system.get_optimal_parameters("code_generation", "test-model")
        
        # Verify that we got parameters
        assert params is not None
        assert params.model_name == "test-model"

    def test_record_task_performance(self, self_aware_system):
        """Test recording task performance"""
        # Create a parameter set
        param_id = self_aware_system.parameter_manager.create_parameter_set(
            model_name="test-model"
        )
        
        # Record performance
        self_aware_system.record_task_performance(
            task_id="test-task",
            parameter_set_id=param_id,
            execution_time=1.5,
            token_count=100,
            success=True,
            quality_score=0.8
        )
        
        # Verify that performance was recorded
        assert len(self_aware_system.parameter_manager.performance_history) > 0
        perf = self_aware_system.parameter_manager.performance_history[-1]
        assert perf.task_id == "test-task"
        assert perf.parameter_set_id == param_id
        assert perf.execution_time == 1.5
        assert perf.token_count == 100
        assert perf.success is True
        assert perf.quality_score == 0.8 