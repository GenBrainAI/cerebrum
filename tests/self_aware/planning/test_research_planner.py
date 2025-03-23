"""
Unit tests for the Research Planner module.

Tests knowledge gap identification, research plan creation, and task management.
"""

import pytest
import os
import json
import uuid
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from src.server.planning.research_planner import (
    ResearchPlanner,
    KnowledgeGap,
    ResearchTask,
    ResearchPlan,
    ResearchStrategyType
)

class TestResearchPlanner:
    """Test suite for the Research Planner."""
    
    @pytest.fixture
    def mock_knowledge_system(self):
        """Create a mock knowledge integration system."""
        mock_system = AsyncMock()
        
        # Mock query_knowledge response
        mock_system.query_knowledge.return_value = {
            "semantic_items": [
                {
                    "id": "item1",
                    "concept": "Machine Learning",
                    "related_concepts": ["Neural Networks", "Data Science"],
                    "confidence": 0.8
                },
                {
                    "id": "item2",
                    "concept": "Neural Networks",
                    "related_concepts": ["Deep Learning"],
                    "confidence": 0.7
                }
            ]
        }
        
        # Mock get_knowledge_context response
        mock_system.get_knowledge_context.return_value = {
            "semantic_memory": [
                {
                    "id": "mem1",
                    "concept": "Machine Learning",
                    "source": "Introduction to ML book",
                    "confidence": 0.8
                }
            ],
            "episodic_memory": [
                {
                    "id": "ep1",
                    "title": "ML Discussion",
                    "actors": ["John Doe", "Jane Smith"],
                    "confidence": 0.7
                }
            ],
            "procedural_memory": [
                {
                    "id": "proc1",
                    "task_name": "Train ML Model",
                    "description": "Steps to train a machine learning model",
                    "success_rate": 0.9
                }
            ]
        }
        
        return mock_system
    
    @pytest.fixture
    def temp_storage_dir(self, tmpdir):
        """Create a temporary directory for storage."""
        storage_dir = tmpdir.mkdir("research_plans")
        return str(storage_dir)
    
    @pytest.fixture
    def research_planner(self, mock_knowledge_system, temp_storage_dir):
        """Create a research planner instance with mock dependencies."""
        return ResearchPlanner(
            knowledge_system=mock_knowledge_system,
            storage_dir=temp_storage_dir
        )
    
    @pytest.fixture
    def sample_knowledge_gap(self):
        """Create a sample knowledge gap for testing."""
        return KnowledgeGap(
            id=str(uuid.uuid4()),
            topic="Reinforcement Learning",
            description="Limited understanding of reinforcement learning algorithms",
            confidence=0.4,
            importance=8,
            sources=["book1", "paper1"],
            related_gaps=[]
        )
    
    @pytest.mark.asyncio
    async def test_identify_knowledge_gaps(self, research_planner):
        """Test identifying knowledge gaps in a topic."""
        # Arrange
        topic = "Advanced Machine Learning Techniques"
        
        # Act
        gaps = await research_planner.identify_knowledge_gaps(topic)
        
        # Assert
        assert isinstance(gaps, dict)
        assert len(gaps) > 0
        
        # Check that at least one gap was identified for 'advanced'
        has_advanced_gap = any("advanced" in gap.topic.lower() for gap in gaps.values())
        assert has_advanced_gap
        
        # Check that gaps have correct structure
        for gap_id, gap in gaps.items():
            assert isinstance(gap, KnowledgeGap)
            assert gap.id == gap_id
            assert 0.0 <= gap.confidence <= 1.0
            assert 1 <= gap.importance <= 10
    
    @pytest.mark.asyncio
    async def test_create_research_plan(self, research_planner, sample_knowledge_gap):
        """Test creating a research plan for knowledge gaps."""
        # Arrange
        research_planner.knowledge_gaps[sample_knowledge_gap.id] = sample_knowledge_gap
        title = "Research Plan for ML"
        description = "A plan to improve understanding of machine learning"
        
        # Act
        plan = await research_planner.create_research_plan(
            title=title,
            description=description,
            knowledge_gaps=[sample_knowledge_gap.id]
        )
        
        # Assert
        assert isinstance(plan, ResearchPlan)
        assert plan.title == title
        assert plan.description == description
        assert sample_knowledge_gap.id in plan.knowledge_gaps
        assert len(plan.tasks) > 0
        assert plan.id in research_planner.research_plans
        
        # Check task creation
        for task in plan.tasks.values():
            assert isinstance(task, ResearchTask)
            assert sample_knowledge_gap.id in task.knowledge_gaps
            assert task.strategy in ResearchStrategyType
            assert task.estimated_time_hours > 0
            assert task.priority == sample_knowledge_gap.importance
    
    @pytest.mark.asyncio
    async def test_empty_knowledge_gaps_raises_error(self, research_planner):
        """Test that creating a plan with no valid knowledge gaps raises an error."""
        # Arrange
        title = "Invalid Research Plan"
        description = "This should fail"
        
        # Act & Assert
        with pytest.raises(ValueError, match="No valid knowledge gaps provided"):
            await research_planner.create_research_plan(
                title=title,
                description=description,
                knowledge_gaps=["nonexistent_id"]
            )
    
    @pytest.mark.asyncio
    async def test_prioritize_research_tasks(self, research_planner):
        """Test prioritizing research tasks in a plan."""
        # Arrange
        # Create tasks with dependencies
        task1 = ResearchTask(
            id="task1",
            title="Task 1",
            description="High priority independent task",
            strategy=ResearchStrategyType.EXPLORATORY,
            estimated_time_hours=4.0,
            knowledge_gaps=["gap1"],
            priority=10,
            dependencies=[]
        )
        
        task2 = ResearchTask(
            id="task2",
            title="Task 2",
            description="Medium priority dependent task",
            strategy=ResearchStrategyType.TARGETED,
            estimated_time_hours=2.0,
            knowledge_gaps=["gap2"],
            priority=5,
            dependencies=["task1"]
        )
        
        task3 = ResearchTask(
            id="task3",
            title="Task 3",
            description="Low priority independent task",
            strategy=ResearchStrategyType.SYSTEMATIC,
            estimated_time_hours=1.0,
            knowledge_gaps=["gap3"],
            priority=3,
            dependencies=[]
        )
        
        tasks = {
            "task1": task1,
            "task2": task2,
            "task3": task3
        }
        
        # Act
        sequence = await research_planner.prioritize_research_tasks(tasks=tasks)
        
        # Assert
        assert isinstance(sequence, list)
        assert len(sequence) == 3
        
        # Task1 should come before Task2 (dependency)
        task1_idx = sequence.index("task1")
        task2_idx = sequence.index("task2")
        assert task1_idx < task2_idx
        
        # Task3 is independent but lower priority, should come after Task1
        task3_idx = sequence.index("task3")
        assert task1_idx < task3_idx
    
    @pytest.mark.asyncio
    async def test_estimate_confidence_gain(self, research_planner, sample_knowledge_gap):
        """Test estimating confidence gain from completing research tasks."""
        # Arrange
        gap_id = sample_knowledge_gap.id
        research_planner.knowledge_gaps[gap_id] = sample_knowledge_gap
        
        # Create plan with task for this gap
        plan = await research_planner.create_research_plan(
            title="Test Plan",
            description="Test Description",
            knowledge_gaps=[gap_id]
        )
        
        task_ids = list(plan.tasks.keys())
        
        # Act
        confidence_gain = await research_planner.estimate_confidence_gain(
            knowledge_gap_id=gap_id,
            research_task_ids=task_ids
        )
        
        # Assert
        assert 0.0 <= confidence_gain <= (1.0 - sample_knowledge_gap.confidence)
        assert confidence_gain > 0.0  # Should have some positive gain
    
    @pytest.mark.asyncio
    async def test_evaluate_information_sources(self, research_planner):
        """Test evaluating information sources for a topic."""
        # Arrange
        topic = "Machine Learning"
        
        # Act
        sources = await research_planner.evaluate_information_sources(topic)
        
        # Assert
        assert isinstance(sources, list)
        assert len(sources) > 0
        
        # Check source structure
        for source in sources:
            assert "type" in source
            assert "name" in source
            assert "description" in source
            assert "relevance" in source
            assert "confidence" in source
    
    @pytest.mark.asyncio
    async def test_update_research_task(self, research_planner, sample_knowledge_gap):
        """Test updating a research task."""
        # Arrange
        # Create plan with task
        research_planner.knowledge_gaps[sample_knowledge_gap.id] = sample_knowledge_gap
        plan = await research_planner.create_research_plan(
            title="Test Plan",
            description="Test Description",
            knowledge_gaps=[sample_knowledge_gap.id]
        )
        
        task_id = list(plan.tasks.keys())[0]
        new_status = "in_progress"
        
        # Act
        result = await research_planner.update_research_task(
            plan_id=plan.id,
            task_id=task_id,
            status=new_status
        )
        
        # Assert
        assert result is True
        assert research_planner.research_plans[plan.id].tasks[task_id].status == new_status
    
    @pytest.mark.asyncio
    async def test_delete_research_plan(self, research_planner, sample_knowledge_gap):
        """Test deleting a research plan."""
        # Arrange
        # Create plan
        research_planner.knowledge_gaps[sample_knowledge_gap.id] = sample_knowledge_gap
        plan = await research_planner.create_research_plan(
            title="Test Plan",
            description="Test Description",
            knowledge_gaps=[sample_knowledge_gap.id]
        )
        
        # Act
        result = await research_planner.delete_research_plan(plan.id)
        
        # Assert
        assert result is True
        assert plan.id not in research_planner.research_plans
        
        # Check that the file was removed
        file_path = os.path.join(research_planner.storage_dir, f"{plan.id}.json")
        assert not os.path.exists(file_path)
        
        # Gaps should still exist (might be used by other plans)
        assert sample_knowledge_gap.id in research_planner.knowledge_gaps
    
    def test_knowledge_gap_validation(self):
        """Test KnowledgeGap validation."""
        # Valid gap
        valid_gap = KnowledgeGap(
            id="test",
            topic="Test Topic",
            description="Test Description",
            confidence=0.5,
            importance=5
        )
        assert valid_gap.confidence == 0.5
        
        # Invalid confidence
        with pytest.raises(ValueError, match="Confidence must be between 0.0 and 1.0"):
            KnowledgeGap(
                id="test",
                topic="Test Topic",
                description="Test Description",
                confidence=1.5,  # Invalid
                importance=5
            )
        
        # Invalid importance
        with pytest.raises(ValueError, match="Importance must be between 1 and 10"):
            KnowledgeGap(
                id="test",
                topic="Test Topic",
                description="Test Description",
                confidence=0.5,
                importance=11  # Invalid
            )
    
    def test_research_task_validation(self):
        """Test ResearchTask validation."""
        # Valid task
        valid_task = ResearchTask(
            id="test",
            title="Test Task",
            description="Test Description",
            strategy=ResearchStrategyType.EXPLORATORY,
            estimated_time_hours=4.0,
            knowledge_gaps=["gap1"],
            priority=5
        )
        assert valid_task.priority == 5
        
        # Invalid priority
        with pytest.raises(ValueError, match="Priority must be between 1 and 10"):
            ResearchTask(
                id="test",
                title="Test Task",
                description="Test Description",
                strategy=ResearchStrategyType.EXPLORATORY,
                estimated_time_hours=4.0,
                knowledge_gaps=["gap1"],
                priority=0  # Invalid
            )
        
        # Invalid estimated time
        with pytest.raises(ValueError, match="Estimated time must be positive"):
            ResearchTask(
                id="test",
                title="Test Task",
                description="Test Description",
                strategy=ResearchStrategyType.EXPLORATORY,
                estimated_time_hours=0.0,  # Invalid
                knowledge_gaps=["gap1"],
                priority=5
            )
    
    def test_research_plan_validation(self):
        """Test ResearchPlan validation."""
        # Valid plan
        valid_plan = ResearchPlan(
            id="test",
            title="Test Plan",
            description="Test Description",
            knowledge_gaps={},
            tasks={},
            total_estimated_time=10.0,
            creation_time=datetime.now().isoformat()
        )
        assert valid_plan.status == "pending"
        
        # Invalid title
        with pytest.raises(ValueError, match="Title cannot be empty"):
            ResearchPlan(
                id="test",
                title="",  # Invalid
                description="Test Description",
                knowledge_gaps={},
                tasks={},
                total_estimated_time=10.0,
                creation_time=datetime.now().isoformat()
            )
        
        # Invalid description
        with pytest.raises(ValueError, match="Description cannot be empty"):
            ResearchPlan(
                id="test",
                title="Test Plan",
                description="",  # Invalid
                knowledge_gaps={},
                tasks={},
                total_estimated_time=10.0,
                creation_time=datetime.now().isoformat()
            )
    
    def test_knowledge_gap_serialization(self):
        """Test serialization and deserialization of KnowledgeGap."""
        # Create original gap
        original = KnowledgeGap(
            id="gap1",
            topic="AI Ethics",
            description="Understanding ethical implications of AI",
            confidence=0.3,
            importance=9,
            sources=["paper1", "book1"],
            related_gaps=["gap2", "gap3"]
        )
        
        # Convert to dict
        gap_dict = original.to_dict()
        
        # Convert back to object
        reconstructed = KnowledgeGap.from_dict(gap_dict)
        
        # Verify all properties match
        assert reconstructed.id == original.id
        assert reconstructed.topic == original.topic
        assert reconstructed.description == original.description
        assert reconstructed.confidence == original.confidence
        assert reconstructed.importance == original.importance
        assert reconstructed.sources == original.sources
        assert reconstructed.related_gaps == original.related_gaps
    
    def test_research_task_serialization(self):
        """Test serialization and deserialization of ResearchTask."""
        # Create original task
        original = ResearchTask(
            id="task1",
            title="Ethics Research",
            description="Research AI ethics",
            strategy=ResearchStrategyType.SYSTEMATIC,
            estimated_time_hours=6.0,
            knowledge_gaps=["gap1"],
            priority=8,
            sources=[{"type": "paper", "name": "Ethics in AI"}],
            dependencies=["task2"],
            status="in_progress"
        )
        
        # Convert to dict
        task_dict = original.to_dict()
        
        # Convert back to object
        reconstructed = ResearchTask.from_dict(task_dict)
        
        # Verify all properties match
        assert reconstructed.id == original.id
        assert reconstructed.title == original.title
        assert reconstructed.description == original.description
        assert reconstructed.strategy == original.strategy
        assert reconstructed.estimated_time_hours == original.estimated_time_hours
        assert reconstructed.knowledge_gaps == original.knowledge_gaps
        assert reconstructed.priority == original.priority
        assert reconstructed.sources == original.sources
        assert reconstructed.dependencies == original.dependencies
        assert reconstructed.status == original.status
    
    def test_research_plan_serialization(self):
        """Test serialization and deserialization of ResearchPlan."""
        # Create sample gaps and tasks
        gap = KnowledgeGap(
            id="gap1",
            topic="AI Ethics",
            description="Understanding ethical implications of AI",
            confidence=0.3,
            importance=9
        )
        
        task = ResearchTask(
            id="task1",
            title="Ethics Research",
            description="Research AI ethics",
            strategy=ResearchStrategyType.SYSTEMATIC,
            estimated_time_hours=6.0,
            knowledge_gaps=["gap1"],
            priority=8
        )
        
        # Create original plan
        original = ResearchPlan(
            id="plan1",
            title="Ethics Research Plan",
            description="Plan to research AI ethics",
            knowledge_gaps={"gap1": gap},
            tasks={"task1": task},
            total_estimated_time=6.0,
            creation_time=datetime.now().isoformat(),
            task_sequence=["task1"],
            status="in_progress",
            metadata={"owner": "John"}
        )
        
        # Convert to dict
        plan_dict = original.to_dict()
        
        # Convert back to object
        reconstructed = ResearchPlan.from_dict(plan_dict)
        
        # Verify all properties match
        assert reconstructed.id == original.id
        assert reconstructed.title == original.title
        assert reconstructed.description == original.description
        assert reconstructed.total_estimated_time == original.total_estimated_time
        assert reconstructed.creation_time == original.creation_time
        assert reconstructed.task_sequence == original.task_sequence
        assert reconstructed.status == original.status
        assert reconstructed.metadata == original.metadata
        
        # Check nested objects
        assert len(reconstructed.knowledge_gaps) == len(original.knowledge_gaps)
        assert len(reconstructed.tasks) == len(original.tasks)
        
        recon_gap = reconstructed.knowledge_gaps["gap1"]
        orig_gap = original.knowledge_gaps["gap1"]
        assert recon_gap.id == orig_gap.id
        assert recon_gap.topic == orig_gap.topic
        
        recon_task = reconstructed.tasks["task1"]
        orig_task = original.tasks["task1"]
        assert recon_task.id == orig_task.id
        assert recon_task.title == orig_task.title
    
    @pytest.mark.asyncio
    async def test_load_plans_from_storage(self, research_planner, temp_storage_dir, sample_knowledge_gap):
        """Test loading research plans from storage."""
        # Arrange
        # Create and save a plan
        research_planner.knowledge_gaps[sample_knowledge_gap.id] = sample_knowledge_gap
        plan = await research_planner.create_research_plan(
            title="Test Plan",
            description="Test Description",
            knowledge_gaps=[sample_knowledge_gap.id]
        )
        
        # Create a new planner instance that should load the saved plan
        new_planner = ResearchPlanner(
            knowledge_system=research_planner.knowledge_system,
            storage_dir=temp_storage_dir
        )
        
        # Assert
        assert plan.id in new_planner.research_plans
        loaded_plan = new_planner.research_plans[plan.id]
        assert loaded_plan.title == plan.title
        assert loaded_plan.description == plan.description
        
        # Check that gaps were loaded
        assert sample_knowledge_gap.id in new_planner.knowledge_gaps
    
    def test_extract_key_terms(self, research_planner):
        """Test extracting key terms from text."""
        # Arrange
        text = "The impact of deep learning on computer vision and natural language processing"
        
        # Act
        terms = research_planner._extract_key_terms(text)
        
        # Assert
        assert isinstance(terms, list)
        assert "impact" in terms
        assert "deep" in terms
        assert "learning" in terms
        assert "computer" in terms
        assert "vision" in terms
        assert "natural" in terms
        assert "language" in terms
        assert "processing" in terms
        
        # Common words should be filtered out
        assert "the" not in terms
        assert "of" not in terms
        assert "on" not in terms
        assert "and" not in terms
    
    def test_share_words(self, research_planner):
        """Test detecting shared words between texts."""
        # Texts with shared words
        text1 = "Deep learning architectures"
        text2 = "Learning in neural networks"
        
        # Should share 'learning'
        assert research_planner._share_words(text1, text2) is False  # Only one word in common
        
        # Texts with multiple shared words
        text3 = "Deep learning architectures for computer vision"
        text4 = "Computer vision using deep learning techniques"
        
        # Should share 'deep', 'learning', 'computer', 'vision'
        assert research_planner._share_words(text3, text4) is True
        
        # Texts with no shared significant words
        text5 = "Reinforcement learning algorithms"
        text6 = "Natural language processing models"
        
        # No significant shared words
        assert research_planner._share_words(text5, text6) is False 