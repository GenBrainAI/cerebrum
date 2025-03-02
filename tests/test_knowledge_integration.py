import pytest
import os
import shutil
import tempfile
from datetime import datetime

from src.server.context.knowledge_integration import (
    KnowledgeIntegrationSystem,
    MemoryType,
    SemanticMemoryItem,
    EpisodicMemoryItem,
    ProceduralMemoryItem
)


class TestKnowledgeIntegrationSystem:
    """Tests for the Knowledge Integration System"""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for testing"""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)

    @pytest.fixture
    def knowledge_system(self, temp_dir):
        """Create a knowledge system with a temporary storage path"""
        system = KnowledgeIntegrationSystem(storage_path=temp_dir)
        return system

    def test_add_semantic_memory(self, knowledge_system):
        """Test adding semantic memory"""
        item_id = knowledge_system.add_semantic_memory(
            concept="AI",
            definition="Artificial Intelligence is the simulation of human intelligence by machines.",
            related_concepts=["Machine Learning", "Neural Networks"],
            tags=["technology", "computer science"]
        )
        
        # Verify the memory item was added
        assert item_id in knowledge_system.semantic_memory
        item = knowledge_system.semantic_memory[item_id]
        assert item.concept == "AI"
        assert item.definition == "Artificial Intelligence is the simulation of human intelligence by machines."
        assert "Machine Learning" in item.related_concepts
        assert "Neural Networks" in item.related_concepts
        assert "technology" in item.tags
        assert "computer science" in item.tags

    def test_add_episodic_memory(self, knowledge_system):
        """Test adding episodic memory"""
        item_id = knowledge_system.add_episodic_memory(
            title="First AI Experiment",
            description="Conducted the first experiment with the AI system.",
            actors=["Researcher", "AI System"],
            tags=["experiment", "milestone"]
        )
        
        # Verify the memory item was added
        assert item_id in knowledge_system.episodic_memory
        item = knowledge_system.episodic_memory[item_id]
        assert item.title == "First AI Experiment"
        assert item.description == "Conducted the first experiment with the AI system."
        assert "Researcher" in item.actors
        assert "AI System" in item.actors
        assert "experiment" in item.tags
        assert "milestone" in item.tags

    def test_add_procedural_memory(self, knowledge_system):
        """Test adding procedural memory"""
        item_id = knowledge_system.add_procedural_memory(
            task_name="Train Neural Network",
            description="Steps to train a neural network model.",
            steps=[
                "Prepare the dataset",
                "Define the model architecture",
                "Configure training parameters",
                "Train the model",
                "Evaluate the results"
            ],
            expected_outcome="A trained neural network model with good performance.",
            tags=["machine learning", "tutorial"]
        )
        
        # Verify the memory item was added
        assert item_id in knowledge_system.procedural_memory
        item = knowledge_system.procedural_memory[item_id]
        assert item.task_name == "Train Neural Network"
        assert item.description == "Steps to train a neural network model."
        assert len(item.steps) == 5
        assert "Prepare the dataset" in item.steps
        assert item.expected_outcome == "A trained neural network model with good performance."
        assert "machine learning" in item.tags
        assert "tutorial" in item.tags

    def test_get_semantic_memory(self, knowledge_system):
        """Test retrieving semantic memory"""
        item_id = knowledge_system.add_semantic_memory(
            concept="AI",
            definition="Artificial Intelligence"
        )
        
        # Retrieve the memory item
        item = knowledge_system.get_semantic_memory(item_id)
        assert item is not None
        assert item.concept == "AI"
        assert item.definition == "Artificial Intelligence"

    def test_get_episodic_memory(self, knowledge_system):
        """Test retrieving episodic memory"""
        item_id = knowledge_system.add_episodic_memory(
            title="First AI Experiment",
            description="Conducted the first experiment"
        )
        
        # Retrieve the memory item
        item = knowledge_system.get_episodic_memory(item_id)
        assert item is not None
        assert item.title == "First AI Experiment"
        assert item.description == "Conducted the first experiment"

    def test_get_procedural_memory(self, knowledge_system):
        """Test retrieving procedural memory"""
        item_id = knowledge_system.add_procedural_memory(
            task_name="Train Neural Network",
            description="Steps to train a neural network model.",
            steps=["Step 1", "Step 2"],
            expected_outcome="A trained model"
        )
        
        # Retrieve the memory item
        item = knowledge_system.get_procedural_memory(item_id)
        assert item is not None
        assert item.task_name == "Train Neural Network"
        assert item.description == "Steps to train a neural network model."
        assert len(item.steps) == 2
        assert item.expected_outcome == "A trained model"

    def test_search_semantic_memory(self, knowledge_system):
        """Test searching semantic memory"""
        # Add some semantic memory items
        knowledge_system.add_semantic_memory(
            concept="AI",
            definition="Artificial Intelligence is the simulation of human intelligence by machines."
        )
        
        knowledge_system.add_semantic_memory(
            concept="Machine Learning",
            definition="A subset of AI that enables systems to learn from data."
        )
        
        # Search for items
        results = knowledge_system.search_semantic_memory("intelligence")
        assert len(results) > 0
        assert any(item.concept == "AI" for item in results)
        
        results = knowledge_system.search_semantic_memory("learn")
        assert len(results) > 0
        assert any(item.concept == "Machine Learning" for item in results)

    def test_search_episodic_memory(self, knowledge_system):
        """Test searching episodic memory"""
        # Add some episodic memory items
        knowledge_system.add_episodic_memory(
            title="First Experiment",
            description="Conducted the first experiment with the AI system."
        )
        
        knowledge_system.add_episodic_memory(
            title="Model Training",
            description="Trained the model on the dataset."
        )
        
        # Search for items
        results = knowledge_system.search_episodic_memory("experiment")
        assert len(results) > 0
        assert any(item.title == "First Experiment" for item in results)
        
        results = knowledge_system.search_episodic_memory("training")
        assert len(results) > 0
        assert any(item.title == "Model Training" for item in results)

    def test_search_procedural_memory(self, knowledge_system):
        """Test searching procedural memory"""
        # Add some procedural memory items
        knowledge_system.add_procedural_memory(
            task_name="Train Neural Network",
            description="Steps to train a neural network model.",
            steps=["Step 1", "Step 2"],
            expected_outcome="A trained model"
        )
        
        knowledge_system.add_procedural_memory(
            task_name="Deploy Model",
            description="Steps to deploy a trained model to production.",
            steps=["Step 1", "Step 2"],
            expected_outcome="A deployed model"
        )
        
        # Search for items
        results = knowledge_system.search_procedural_memory("train")
        assert len(results) > 0
        assert any(item.task_name == "Train Neural Network" for item in results)
        
        results = knowledge_system.search_procedural_memory("deploy")
        assert len(results) > 0
        assert any(item.task_name == "Deploy Model" for item in results)

    def test_search_by_tags(self, knowledge_system):
        """Test searching by tags"""
        # Add items with tags
        knowledge_system.add_semantic_memory(
            concept="AI",
            definition="Artificial Intelligence",
            tags=["technology", "computer science"]
        )
        
        knowledge_system.add_episodic_memory(
            title="First Experiment",
            description="Conducted the first experiment",
            tags=["experiment", "technology"]
        )
        
        knowledge_system.add_procedural_memory(
            task_name="Train Model",
            description="Steps to train a model",
            steps=["Step 1", "Step 2"],
            expected_outcome="A trained model",
            tags=["tutorial", "technology"]
        )
        
        # Search by tags
        results = knowledge_system.search_by_tags(["technology"])
        assert len(results[MemoryType.SEMANTIC]) > 0
        assert len(results[MemoryType.EPISODIC]) > 0
        assert len(results[MemoryType.PROCEDURAL]) > 0
        
        results = knowledge_system.search_by_tags(["experiment"])
        assert len(results[MemoryType.EPISODIC]) > 0
        
        results = knowledge_system.search_by_tags(["tutorial"])
        assert len(results[MemoryType.PROCEDURAL]) > 0

    def test_create_relation(self, knowledge_system):
        """Test creating relations between knowledge items"""
        # Add some items
        semantic_id = knowledge_system.add_semantic_memory(
            concept="AI",
            definition="Artificial Intelligence"
        )
        
        episodic_id = knowledge_system.add_episodic_memory(
            title="AI Experiment",
            description="Conducted an AI experiment"
        )
        
        # Create a relation
        result = knowledge_system.create_relation(
            source_id=episodic_id,
            target_id=semantic_id,
            relation_type="involves"
        )
        
        assert result is True

    def test_get_knowledge_context(self, knowledge_system):
        """Test getting knowledge context for a query"""
        # Add some items
        knowledge_system.add_semantic_memory(
            concept="AI",
            definition="Artificial Intelligence"
        )
        
        knowledge_system.add_episodic_memory(
            title="AI Experiment",
            description="Conducted an AI experiment"
        )
        
        knowledge_system.add_procedural_memory(
            task_name="Train AI Model",
            description="Steps to train an AI model",
            steps=["Step 1", "Step 2"],
            expected_outcome="A trained model"
        )
        
        # Get knowledge context
        context = knowledge_system.get_knowledge_context("AI")
        
        assert context is not None
        assert len(context[MemoryType.SEMANTIC]) > 0 or len(context[MemoryType.EPISODIC]) > 0 or len(context[MemoryType.PROCEDURAL]) > 0

    def test_update_memory_item(self, knowledge_system):
        """Test updating a memory item"""
        # Add an item
        item_id = knowledge_system.add_semantic_memory(
            concept="AI",
            definition="Artificial Intelligence"
        )
        
        # Update the item
        result = knowledge_system.update_memory_item(
            item_id=item_id,
            definition="Artificial Intelligence is the simulation of human intelligence by machines."
        )
        
        assert result is True
        item = knowledge_system.get_semantic_memory(item_id)
        assert item.definition == "Artificial Intelligence is the simulation of human intelligence by machines."

    def test_delete_memory_item(self, knowledge_system):
        """Test deleting a memory item"""
        # Add an item
        item_id = knowledge_system.add_semantic_memory(
            concept="AI",
            definition="Artificial Intelligence"
        )
        
        # Delete the item
        result = knowledge_system.delete_memory_item(item_id)
        assert result is True
        assert item_id not in knowledge_system.semantic_memory 