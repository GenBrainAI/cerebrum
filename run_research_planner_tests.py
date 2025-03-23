#!/usr/bin/env python
"""
Simple test runner for Research Planner tests
"""

import sys
import os
import asyncio
import unittest
from unittest.mock import AsyncMock, MagicMock, patch
import uuid
import tempfile
import shutil
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

class TestResearchPlanner(unittest.TestCase):
    """Simpler test suite for the Research Planner."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create a mock knowledge system
        self.mock_knowledge_system = AsyncMock()
        
        # Mock query_knowledge response - must match expected format in the implementation
        self.mock_knowledge_system.query_knowledge.return_value = {
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
        self.mock_knowledge_system.get_knowledge_context.return_value = {
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
        
        # Create a temporary directory for storage
        self.temp_dir = tempfile.mkdtemp()
        
        # Create the research planner
        self.research_planner = ResearchPlanner(
            knowledge_system=self.mock_knowledge_system,
            storage_dir=self.temp_dir
        )
        
        # Create a sample knowledge gap
        self.sample_gap = KnowledgeGap(
            id=str(uuid.uuid4()),
            topic="Reinforcement Learning",
            description="Limited understanding of reinforcement learning algorithms",
            confidence=0.4,
            importance=8,
            sources=["book1", "paper1"],
            related_gaps=[]
        )
    
    def tearDown(self):
        """Tear down test fixtures."""
        # Remove the temporary directory
        shutil.rmtree(self.temp_dir)
    
    async def test_identify_knowledge_gaps(self):
        """Test identifying knowledge gaps in a topic."""
        # Arrange
        topic = "Advanced Machine Learning Techniques"
        
        # Act
        gaps = await self.research_planner.identify_knowledge_gaps(topic)
        
        # Assert
        self.assertIsInstance(gaps, dict)
        self.assertTrue(len(gaps) > 0)
        
        # Check that gaps have correct structure
        for gap_id, gap in gaps.items():
            self.assertIsInstance(gap, KnowledgeGap)
            self.assertEqual(gap.id, gap_id)
            self.assertTrue(0.0 <= gap.confidence <= 1.0)
            self.assertTrue(1 <= gap.importance <= 10)
    
    async def test_create_research_plan(self):
        """Test creating a research plan for knowledge gaps."""
        # Arrange
        self.research_planner.knowledge_gaps[self.sample_gap.id] = self.sample_gap
        title = "Research Plan for ML"
        description = "A plan to improve understanding of machine learning"
        
        # Act
        plan = await self.research_planner.create_research_plan(
            title=title,
            description=description,
            knowledge_gaps=[self.sample_gap.id]
        )
        
        # Assert
        self.assertIsInstance(plan, ResearchPlan)
        self.assertEqual(plan.title, title)
        self.assertEqual(plan.description, description)
        self.assertIn(self.sample_gap.id, plan.knowledge_gaps)
        self.assertTrue(len(plan.tasks) > 0)
        self.assertIn(plan.id, self.research_planner.research_plans)
    
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
        self.assertEqual(valid_gap.confidence, 0.5)
        
        # Invalid confidence
        with self.assertRaises(ValueError) as context:
            KnowledgeGap(
                id="test",
                topic="Test Topic",
                description="Test Description",
                confidence=1.5,  # Invalid
                importance=5
            )
        self.assertIn("Confidence must be between 0.0 and 1.0", str(context.exception))
    
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
        self.assertEqual(reconstructed.id, original.id)
        self.assertEqual(reconstructed.topic, original.topic)
        self.assertEqual(reconstructed.description, original.description)
        self.assertEqual(reconstructed.confidence, original.confidence)
        self.assertEqual(reconstructed.importance, original.importance)
        self.assertEqual(reconstructed.sources, original.sources)
        self.assertEqual(reconstructed.related_gaps, original.related_gaps)

async def run_async_tests():
    """Run the async tests."""
    # Create an instance of the test class
    test_case = TestResearchPlanner()
    
    try:
        # Run setup
        test_case.setUp()
        
        # Run the async tests
        print("Running test_identify_knowledge_gaps...")
        await test_case.test_identify_knowledge_gaps()
        print("✅ test_identify_knowledge_gaps passed")
        
        print("Running test_create_research_plan...")
        await test_case.test_create_research_plan()
        print("✅ test_create_research_plan passed")
        
    finally:
        # Run teardown
        test_case.tearDown()

def run_sync_tests():
    """Run the synchronous tests."""
    # Create and run a test suite
    suite = unittest.TestSuite()
    suite.addTest(TestResearchPlanner('test_knowledge_gap_validation'))
    suite.addTest(TestResearchPlanner('test_knowledge_gap_serialization'))
    
    runner = unittest.TextTestRunner()
    result = runner.run(suite)
    
    return result.wasSuccessful()

if __name__ == "__main__":
    print("Running synchronous tests...")
    if run_sync_tests():
        print("✅ All synchronous tests passed")
    else:
        print("❌ Some synchronous tests failed")

    print("\nRunning asynchronous tests...")
    asyncio.run(run_async_tests())
    print("✅ All asynchronous tests completed") 