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
from src.server.system.cognitive_loop import TaskStatus
from src.server.context.knowledge_integration import MemoryType


class TestSelfAwareSystem:
    """Tests for the Self-Aware System integration"""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for testing"""
        with tempfile.TemporaryDirectory() as tmpdirname:
            yield tmpdirname

    @pytest.fixture
    async def self_aware_system(self, temp_dir):
        """Create a self-aware system for testing"""
        system = SelfAwareSystem(storage_path=temp_dir)
        await system.initialize()
        return system

    @pytest.mark.asyncio
    async def test_initialization(self, self_aware_system):
        """Test initialization of the self-aware system"""
        # Add some basic knowledge for testing
        self_aware_system.add_semantic_knowledge(
            concept="Self-Aware Cerebrum",
            definition="A cognitive architecture that can understand and modify itself."
        )
        
        self_aware_system.add_procedural_knowledge(
            task_name="Run Cognitive Cycle",
            description="Execute a full cognitive cycle",
            steps=["Initialize", "Process", "Evaluate"],
            expected_outcome="Completed cognitive cycle"
        )
        
        # Verify that the system components are initialized
        assert self_aware_system.parameter_manager is not None
        assert self_aware_system.knowledge_system is not None
        assert self_aware_system.cognitive_orchestrator is not None
        
        # Verify that basic knowledge is loaded
        semantic_results = self_aware_system.knowledge_system.search_semantic_memory("cerebrum")
        procedural_results = self_aware_system.knowledge_system.search_procedural_memory("cognitive")
        
        assert len(semantic_results) > 0
        assert len(procedural_results) > 0

    @pytest.mark.asyncio
    async def test_add_semantic_knowledge(self, self_aware_system):
        """Test adding semantic knowledge"""
        item_id = self_aware_system.add_semantic_knowledge(
            concept="Neural Architecture",
            definition="The structure and organization of neural networks",
            related_concepts=["Deep Learning", "Machine Learning"]
        )
        
        # Verify that the item was added
        assert item_id is not None
        
        # Search for the added item
        results = self_aware_system.knowledge_system.search_semantic_memory("neural")
        assert len(results) > 0
        assert any("Neural Architecture" in result.concept for result in results)

    @pytest.mark.asyncio
    async def test_add_procedural_knowledge(self, self_aware_system):
        """Test adding procedural knowledge"""
        item_id = self_aware_system.add_procedural_knowledge(
            task_name="Optimize Parameters",
            description="Adjust model parameters for optimal performance",
            steps=["Analyze current performance", "Identify bottlenecks", "Adjust parameters", "Test new configuration"],
            expected_outcome="Improved model performance"
        )
        
        # Verify that the item was added
        assert item_id is not None
        
        # Search for the added item
        results = self_aware_system.knowledge_system.search_procedural_memory("optimize")
        assert len(results) > 0
        assert any("Optimize Parameters" in result.task_name for result in results)

    @pytest.mark.asyncio
    async def test_add_episodic_knowledge(self, self_aware_system):
        """Test adding episodic knowledge"""
        item_id = self_aware_system.add_episodic_knowledge(
            title="System Upgrade",
            description="Upgraded the system to version 2.0",
            timestamp=datetime.now(),
            actors=["Admin", "System"],
            tags=["upgrade", "maintenance"]
        )
        
        # Verify that the item was added
        assert item_id is not None
        
        # Search for the added item
        results = self_aware_system.knowledge_system.search_episodic_memory("upgrade")
        assert len(results) > 0
        assert any("System Upgrade" in result.title for result in results)

    @pytest.mark.asyncio
    async def test_create_cognitive_task(self, self_aware_system):
        """Test creating a cognitive task"""
        task_id = self_aware_system.create_cognitive_task(
            title="Analyze System Performance",
            description="Evaluate the current system performance and identify bottlenecks",
            phase=CognitivePhase.UNDERSTAND,
            worker_type=WorkerType.REQUIREMENTS,
            priority=TaskPriority.MEDIUM
        )
        
        # Verify that the task was created
        assert task_id is not None
        
        # Get the task and verify its properties
        task = self_aware_system.get_cognitive_task(task_id)
        assert task is not None
        assert task.title == "Analyze System Performance"
        assert task.phase == CognitivePhase.UNDERSTAND
        assert task.status == TaskStatus.PENDING

    @pytest.mark.asyncio
    async def test_get_knowledge_context(self, self_aware_system):
        """Test getting knowledge context"""
        # Add some knowledge first
        self_aware_system.add_semantic_knowledge(
            concept="Knowledge Context",
            definition="A collection of relevant information for a specific query."
        )
        
        self_aware_system.add_procedural_knowledge(
            task_name="Retrieve Context",
            description="Get relevant context for a query",
            steps=["Process query", "Search knowledge base", "Rank results", "Return top matches"],
            expected_outcome="Relevant context information"
        )
        
        # Add more knowledge to ensure we have enough context
        self_aware_system.add_semantic_knowledge(
            concept="Knowledge Retrieval",
            definition="The process of finding and extracting relevant information from a knowledge base."
        )
        
        # Get context for a query
        context = self_aware_system.get_knowledge_context("knowledge retrieval")
        
        # Verify the context
        assert context is not None
        assert isinstance(context, dict)
        
        # Check if we have entries in any of the memory types
        has_entries = False
        for memory_type in context:
            if len(context[memory_type]) > 0:
                has_entries = True
                break
        
        assert has_entries, "No entries found in any memory type"
        
        # If we have semantic entries, check for our concepts
        if len(context[MemoryType.SEMANTIC]) > 0:
            semantic_concepts = [item.get("concept", "") for item in context[MemoryType.SEMANTIC]]
            assert any(["Knowledge" in concept for concept in semantic_concepts]), "Expected knowledge concepts not found"

    @pytest.mark.asyncio
    async def test_update_development_context(self, self_aware_system):
        """Test updating development context"""
        # Update the context
        self_aware_system.update_development_context("test_key", "test_value")
        
        # Get the updated context
        context = self_aware_system.get_development_context("test_key")
        
        # Verify the context was updated
        assert context == "test_value"

    @pytest.mark.asyncio
    async def test_get_current_phase(self, self_aware_system):
        """Test getting the current phase"""
        # Get the current phase
        phase = self_aware_system.get_current_phase()
        
        # Verify the phase
        assert phase is not None
        assert isinstance(phase, CognitivePhase)

    @pytest.mark.asyncio
    async def test_get_tasks_by_phase(self, self_aware_system):
        """Test getting tasks by phase"""
        # Create a task
        self_aware_system.create_cognitive_task(
            title="Test Task",
            description="A test task",
            phase=CognitivePhase.UNDERSTAND,
            worker_type=WorkerType.REQUIREMENTS
        )
        
        # Get tasks for the phase
        tasks = self_aware_system.get_tasks_by_phase(CognitivePhase.UNDERSTAND)
        
        # Verify the tasks
        assert tasks is not None
        assert len(tasks) > 0
        assert any(task.title == "Test Task" for task in tasks)

    @pytest.mark.asyncio
    async def test_get_optimal_parameters(self, self_aware_system):
        """Test getting optimal parameters"""
        # Get optimal parameters
        params = self_aware_system.get_optimal_parameters("text_generation", "gpt-4")
        
        # Verify the parameters
        assert params is not None

    @pytest.mark.asyncio
    async def test_record_task_performance(self, self_aware_system):
        """Test recording task performance"""
        # Create a task
        task_id = self_aware_system.create_cognitive_task(
            title="Performance Test Task",
            description="A task for testing performance recording",
            phase=CognitivePhase.UNDERSTAND
        )
        
        # Record performance
        self_aware_system.record_task_performance(
            task_id=task_id,
            parameter_set_id="test_params",
            execution_time=1.5,
            token_count=100,
            success=True,
            quality_score=0.85
        )
        
        # No direct way to verify, but ensure it doesn't raise exceptions
        assert True 