"""
Test suite for Planning Engine integration with Self-Aware System.

This module tests the integration of Planning Engine components with
the Self-Aware System, including goal decomposition, research planning,
implementation planning, resource allocation, and plan visualization.
"""

import os
import sys
import asyncio
import unittest
import json
from datetime import datetime
from unittest.mock import patch, MagicMock

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.server.self_aware_integration import SelfAwareSystem
from src.server.planning.planning_engine import (
    PlanningEngine,
    PlanType,
    IntegratedPlan,
    PlanningMetrics,
    PlanVersion
)
from src.server.planning.planning_workflow import PlanningWorkflow
from src.server.planning.planning_visualization import (
    VisualizationType,
    OutputFormat
)
from src.server.planning.research_planner import KnowledgeGap

class TestPlanningIntegration(unittest.TestCase):
    """Test Planning Engine integration with Self-Aware System."""
    
    def setUp(self):
        """Set up test environment."""
        # Create temporary directories for test data
        os.makedirs("tests/self_aware/planning/test_data/resources", exist_ok=True)
        os.makedirs("tests/self_aware/planning/test_data/planning/implementation", exist_ok=True)
        os.makedirs("tests/self_aware/planning/test_data/planning/research", exist_ok=True)
        os.makedirs("tests/self_aware/planning/test_data/planning/goals", exist_ok=True)
        os.makedirs("tests/self_aware/planning/test_data/planning/allocation", exist_ok=True)
        os.makedirs("tests/self_aware/planning/test_data/planning/config", exist_ok=True)
        
        # Create config file in the correct location
        config_file = "tests/self_aware/planning/test_data/planning/config/default_config.json"
        with open(config_file, 'w') as f:
            json.dump({
                "default_storage_path": "tests/self_aware/planning/test_data",
                "optimization_goal": "BALANCED",
                "max_plan_versions": 10
            }, f)
            
        # Add the knowledge gaps directory
        os.makedirs("tests/self_aware/planning/test_data/planning/knowledge_gaps", exist_ok=True)
        
        # Initialize test event loop
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        
        # Initialize self-aware system
        self.system = SelfAwareSystem(
            storage_path="tests/self_aware/planning/test_data"
        )
        
        # Run async initialization
        self.loop.run_until_complete(self.system.initialize())
        
        # Mock resource pool and add it to the resource allocation manager
        from src.server.planning.resource_allocation import ResourceType, ResourcePool
        resource_types = {
            ResourceType.CPU: 100.0,
            ResourceType.MEMORY: 1024.0,
            ResourceType.STORAGE: 10240.0,
            ResourceType.TIME: 3600.0
        }
        
        pool_id = "test-pool-1"
        test_pool = ResourcePool(
            id=pool_id,
            name="Test Resource Pool",
            description="A resource pool for testing",
            resources=resource_types,
            cost_per_unit={rt: 1.0 for rt in resource_types},
            creation_time=datetime.now().isoformat()
        )
        
        # Add the pool to the manager
        self.system.planning_engine.resource_allocation_manager.resource_pools[pool_id] = test_pool
        
        # Mock the knowledge_system.query_knowledge method
        if self.system.knowledge_system:
            self.system.knowledge_system.query_knowledge = MagicMock(return_value={
                "relevant_data": ["Test data 1", "Test data 2"],
                "knowledge_score": 0.8
            })
        
        # Mock the research_planner's methods
        if self.system.planning_engine and self.system.planning_engine.research_planner:
            # Create knowledge gaps and register them in the research planner
            gap1 = KnowledgeGap(
                id="gap-1",
                topic="Test Gap 1",
                description="A knowledge gap for testing",
                confidence=0.3,
                importance=8,
                sources=["test-source-1"]
            )
            
            gap2 = KnowledgeGap(
                id="gap-2",
                topic="Test Gap 2",
                description="Another knowledge gap for testing",
                confidence=0.5,
                importance=6,
                sources=["test-source-2"]
            )
            
            # Register the knowledge gaps in the research planner
            self.system.planning_engine.research_planner.knowledge_gaps = {
                "gap-1": gap1,
                "gap-2": gap2
            }
            
            # Create an async mock
            async def mock_identify_knowledge_gaps(*args, **kwargs):
                return {
                    "gap-1": gap1,
                    "gap-2": gap2
                }
            
            self.system.planning_engine.research_planner.identify_knowledge_gaps = mock_identify_knowledge_gaps
    
    def tearDown(self):
        """Clean up after tests."""
        # Clean up temporary files
        # Note: In a real test, you would delete files here, but for this implementation
        # we'll leave the test data for inspection
        pass
    
    def test_planning_engine_initialization(self):
        """Test that Planning Engine is properly initialized."""
        # Check that planning engine components are initialized
        self.assertIsNotNone(self.system.planning_engine)
        self.assertIsNotNone(self.system.planning_workflow)
        self.assertIsNotNone(self.system.planning_metrics_collector)
        self.assertIsNotNone(self.system.planning_visualization)
        
        # Check that planning engine has access to required components
        self.assertIsNotNone(self.system.planning_engine.goal_decomposition_engine)
        self.assertIsNotNone(self.system.planning_engine.research_planner)
        self.assertIsNotNone(self.system.planning_engine.implementation_planner)
        self.assertIsNotNone(self.system.planning_engine.resource_allocation_manager)
    
    def test_create_integrated_plan(self):
        """Test creating an integrated plan."""
        # Define a test goal
        test_goal = {
            "name": "Integration Test Goal",
            "description": "Create integration test suite",
            "requirements": ["Support core functionality", "Include edge cases"],
            "type": "DEVELOPMENT"
        }
        
        # Create the integrated plan
        plan_result = self.loop.run_until_complete(
            self.system.create_integrated_plan(
                name="Test Integration Plan",
                description="A test plan for integration testing",
                goal_requirements=test_goal,
                goal_type="DEVELOPMENT",
                strategy="TOP_DOWN"
            )
        )
        
        # Verify the plan was created
        self.assertIsNotNone(plan_result)
        self.assertIn("id", plan_result)
        self.assertIn("name", plan_result)
        self.assertEqual(plan_result["name"], "Test Integration Plan")
        self.assertIn("goal_decomposition_id", plan_result)
        self.assertIn("status", plan_result)
        
        # Verify the plan can be retrieved
        plan_id = plan_result["id"]
        plan_data = self.loop.run_until_complete(
            self.system.get_integrated_plan(plan_id)
        )
        
        self.assertIsNotNone(plan_data)
        self.assertEqual(plan_data["id"], plan_id)
    
    def test_update_integrated_plan(self):
        """Test updating an integrated plan."""
        # Define a test goal
        test_goal = {
            "name": "Update Test Goal",
            "description": "Test updating an integrated plan",
            "requirements": ["Initial requirement"],
            "type": "DEVELOPMENT"
        }
        
        plan_result = self.loop.run_until_complete(
            self.system.create_integrated_plan(
                name="Update Test Plan",
                description="A test plan for update testing",
                goal_requirements=test_goal,
                goal_type="DEVELOPMENT",
                strategy="TOP_DOWN"
            )
        )
        
        plan_id = plan_result["id"]
        
        # Update the plan
        updates = {
            "name": "Updated Plan Name",
            "description": "Updated plan description",
            "metadata": {
                "updated": True,
                "update_reason": "Testing update functionality"
            }
        }
        
        update_result = self.loop.run_until_complete(
            self.system.update_integrated_plan(
                plan_id=plan_id,
                updates=updates,
                change_description="Updated plan details for testing"
            )
        )
        
        # Verify the update
        self.assertIsNotNone(update_result)
        self.assertEqual(update_result["id"], plan_id)
        self.assertEqual(update_result["name"], "Updated Plan Name")
        
        # Retrieve the updated plan
        updated_plan = self.loop.run_until_complete(
            self.system.get_integrated_plan(plan_id)
        )
        
        self.assertEqual(updated_plan["name"], "Updated Plan Name")
        self.assertEqual(updated_plan["description"], "Updated plan description")
        self.assertTrue(updated_plan["metadata"]["updated"])
        
        # Verify version history was updated
        self.assertGreaterEqual(len(updated_plan["version_history"]), 1)
    
    def test_list_integrated_plans(self):
        """Test listing integrated plans with filtering."""
        # Create test plans with different attributes
        goal1 = {
            "name": "Research Goal",
            "description": "A goal for research planning",
            "requirements": ["Research A", "Research B"],
            "type": "RESEARCH"
        }
        goal2 = {
            "name": "Implementation Goal",
            "description": "A goal for implementation planning",
            "requirements": ["Implementation A", "Implementation B"],
            "type": "DEVELOPMENT"
        }
        
        # Create first plan
        self.loop.run_until_complete(
            self.system.create_integrated_plan(
                name="Research Plan",
                description="A research plan",
                goal_requirements=goal1,
                goal_type="RESEARCH",
                strategy="TOP_DOWN"
            )
        )
        
        # Create second plan
        self.loop.run_until_complete(
            self.system.create_integrated_plan(
                name="Implementation Plan",
                description="An implementation plan",
                goal_requirements=goal2,
                goal_type="DEVELOPMENT",
                strategy="TOP_DOWN"
            )
        )
        
        # List all plans
        all_plans = self.loop.run_until_complete(
            self.system.list_integrated_plans()
        )
        
        # Should have at least the two plans we just created
        self.assertGreaterEqual(len(all_plans), 2, "Should have at least 2 plans")
    
    def test_research_driven_workflow(self):
        """Test creating and executing a research-driven workflow."""
        # Define initial goal
        initial_goal = {
            "name": "Research Workflow Goal",
            "description": "A goal for testing research-driven workflow",
            "goal_type": "RESEARCH",
            "requirements": ["Research requirement 1", "Research requirement 2"],
            "knowledge_gaps": ["Gap 1", "Gap 2"]
        }
        
        # Create workflow
        workflow_result = self.loop.run_until_complete(
            self.system.create_research_driven_workflow(
                name="Research Workflow",
                description="A test research workflow",
                initial_goal=initial_goal
            )
        )
        
        # Verify workflow was created
        self.assertIsNotNone(workflow_result)
        self.assertIn("workflow_id", workflow_result)
        self.assertEqual(workflow_result["name"], "Research Workflow")
        self.assertEqual(workflow_result["type"], "research_driven")
        
        # Get workflow status
        workflow_id = workflow_result["workflow_id"]
        status = self.loop.run_until_complete(
            self.system.get_planning_workflow_status(workflow_id)
        )
        
        # Verify workflow structure
        self.assertEqual(status["status"], "PENDING")
        self.assertIn("goal_decomposition", status["steps"])
        self.assertIn("research_planning", status["steps"])
        
        # Execute workflow (this would be a long-running operation in reality)
        # For testing, we'll use mocks to avoid full execution
        with patch.object(self.system.planning_workflow, 'execute_workflow') as mock_execute:
            mock_execute.return_value = {
                "workflow_id": workflow_id,
                "status": "completed",
                "result": {
                    "integrated_plan_id": "mock-plan-id",
                    "goal_id": "mock-goal-id",
                    "research_plan_count": 2,
                    "has_implementation": True,
                    "has_resource_allocation": True
                },
                "completed_steps": ["goal_decomposition", "research_planning", "research_analysis",
                                   "goal_refinement", "implementation_planning", 
                                   "resource_allocation", "plan_integration"]
            }
            
            execution_result = self.loop.run_until_complete(
                self.system.execute_planning_workflow(workflow_id)
            )
            
            # Verify execution result
            self.assertEqual(execution_result["status"], "completed")
            self.assertIn("integrated_plan_id", execution_result["result"])
            
            # Verify mock was called correctly
            mock_execute.assert_called_once_with(workflow_id)
    
    def test_implementation_focused_workflow(self):
        """Test creating and executing an implementation-focused workflow."""
        # Define requirements and constraints
        requirements = [
            "Implement feature X",
            "Support API Y",
            "Handle edge case Z"
        ]
        
        constraints = [
            "Must complete in 2 weeks",
            "Must use existing database",
            "Must maintain backward compatibility"
        ]
        
        # Create workflow
        workflow_result = self.loop.run_until_complete(
            self.system.create_implementation_focused_workflow(
                name="Implementation Workflow",
                description="A test implementation workflow",
                implementation_requirements=requirements,
                constraints=constraints
            )
        )
        
        # Verify workflow was created
        self.assertIsNotNone(workflow_result)
        self.assertIn("workflow_id", workflow_result)
        self.assertEqual(workflow_result["name"], "Implementation Workflow")
        self.assertEqual(workflow_result["type"], "implementation_focused")
        
        # Get workflow status
        workflow_id = workflow_result["workflow_id"]
        status = self.loop.run_until_complete(
            self.system.get_planning_workflow_status(workflow_id)
        )
        
        # Verify workflow structure
        self.assertEqual(status["status"], "PENDING")
        self.assertIn("solution_design", status["steps"])
        self.assertIn("implementation_planning", status["steps"])
        
        # Execute workflow (using mocks for testing)
        with patch.object(self.system.planning_workflow, 'execute_workflow') as mock_execute:
            mock_execute.return_value = {
                "workflow_id": workflow_id,
                "status": "completed",
                "result": {
                    "integrated_plan_id": "mock-plan-id",
                    "solution_design_id": "mock-design-id",
                    "implementation_plan_id": "mock-implementation-id",
                    "has_resource_allocation": True
                },
                "completed_steps": ["solution_design", "implementation_planning", 
                                   "dependency_analysis", "resource_allocation", 
                                   "plan_integration"]
            }
            
            execution_result = self.loop.run_until_complete(
                self.system.execute_planning_workflow(workflow_id)
            )
            
            # Verify execution result
            self.assertEqual(execution_result["status"], "completed")
            self.assertIn("integrated_plan_id", execution_result["result"])
            
            # Verify mock was called correctly
            mock_execute.assert_called_once_with(workflow_id)
    
    def test_plan_visualization(self):
        """Test visualizing an integrated plan."""
        # Create a test plan
        test_goal = {
            "name": "Visualization Goal",
            "description": "A goal for visualization testing",
            "requirements": ["Visualization requirement"],
            "type": "ANALYSIS"
        }
        
        plan_result = self.loop.run_until_complete(
            self.system.create_integrated_plan(
                name="Visualization Test Plan",
                description="A test plan for visualization testing",
                goal_requirements=test_goal,
                goal_type="ANALYSIS",
                strategy="TOP_DOWN"
            )
        )
        
        plan_id = plan_result["id"]
        
        # Test visualizations (using mocks to avoid generating real visualizations)
        with patch.object(self.system.planning_visualization, 'visualize_integrated_plan') as mock_vis:
            mock_vis.return_value = {
                "id": "mock-vis-id",
                "plan_id": plan_id,
                "type": VisualizationType.GOAL_HIERARCHY.value,
                "format": OutputFormat.HTML.value,
                "timestamp": datetime.now().isoformat(),
                "content_type": "text/html",
                "content": "<html><body>Goal Hierarchy Visualization</body></html>"
            }
            
            vis_result = self.loop.run_until_complete(
                self.system.visualize_integrated_plan(
                    plan_id=plan_id,
                    visualization_type="goal_hierarchy",
                    output_format="html"
                )
            )
            
            # Verify visualization result
            self.assertIsNotNone(vis_result)
            self.assertEqual(vis_result["plan_id"], plan_id)
            self.assertEqual(vis_result["type"], "goal_hierarchy")
            self.assertEqual(vis_result["format"], "html")
            
            # Verify mock was called correctly
            mock_vis.assert_called_once()
    
    def test_plan_metrics(self):
        """Test retrieving plan metrics."""
        # Create a test plan with metrics
        test_goal = {
            "name": "Metrics Goal",
            "description": "A goal for metrics testing",
            "requirements": ["Metrics requirement"],
            "type": "ANALYSIS"
        }
        
        plan_result = self.loop.run_until_complete(
            self.system.create_integrated_plan(
                name="Metrics Test Plan",
                description="A test plan for metrics testing",
                goal_requirements=test_goal,
                goal_type="ANALYSIS",
                strategy="TOP_DOWN"
            )
        )
        
        plan_id = plan_result["id"]
        
        # Test metrics retrieval (using mocks)
        with patch.object(self.system.planning_metrics_collector, 'generate_metrics_report') as mock_metrics:
            mock_metrics.return_value = {
                "plan_id": plan_id,
                "report_time": datetime.now().isoformat(),
                "metrics": {
                    "time": {"latest_value": 5.2, "snapshot_count": 1},
                    "complexity": {"latest_value": 0.75, "snapshot_count": 1},
                    "confidence": {"latest_value": 0.85, "snapshot_count": 1}
                },
                "trends": {
                    "time": {"mean": 5.2, "trend_direction": "stable"},
                    "complexity": {"mean": 0.75, "trend_direction": "stable"},
                    "confidence": {"mean": 0.85, "trend_direction": "stable"}
                }
            }
            
            metrics_result = self.loop.run_until_complete(
                self.system.get_plan_metrics(plan_id)
            )
            
            # Verify metrics result
            self.assertIsNotNone(metrics_result)
            self.assertEqual(metrics_result["plan_id"], plan_id)
            self.assertIn("metrics", metrics_result)
            self.assertIn("trends", metrics_result)
            
            # Verify mock was called correctly
            mock_metrics.assert_called_once_with(plan_id=plan_id, include_trends=True)
    
    def test_plan_comparison(self):
        """Test comparing multiple plans."""
        # Create test plans
        goal1 = {
            "name": "Comparison Goal 1",
            "description": "First goal for comparison testing",
            "requirements": ["Research A", "Research B"],
            "type": "RESEARCH"
        }
        goal2 = {
            "name": "Comparison Goal 2",
            "description": "Second goal for comparison testing",
            "requirements": ["Implementation A", "Implementation B"],
            "type": "DEVELOPMENT"
        }
        
        plan1 = self.loop.run_until_complete(
            self.system.create_integrated_plan(
                name="Comparison Plan 1",
                description="First comparison test plan",
                goal_requirements=goal1,
                goal_type="RESEARCH",
                strategy="TOP_DOWN"
            )
        )
        
        plan2 = self.loop.run_until_complete(
            self.system.create_integrated_plan(
                name="Comparison Plan 2",
                description="Second comparison test plan",
                goal_requirements=goal2,
                goal_type="DEVELOPMENT",
                strategy="TOP_DOWN"
            )
        )
        
        plan_ids = [plan1["id"], plan2["id"]]
        comparison_metrics = ["planning_time", "complexity_score", "confidence_score"]
        
        # Test comparison (using mocks)
        with patch.object(self.system.planning_visualization, 'compare_plans') as mock_compare:
            mock_compare.return_value = {
                "id": "mock-comparison-id",
                "type": VisualizationType.COMPARISON.value,
                "format": OutputFormat.HTML.value,
                "timestamp": datetime.now().isoformat(),
                "content_type": "text/html",
                "content": "<html><body>Plan Comparison</body></html>",
                "metadata": {
                    "plan_ids": plan_ids,
                    "comparison_metrics": comparison_metrics
                }
            }
            
            comparison_result = self.loop.run_until_complete(
                self.system.compare_plans(
                    plan_ids=plan_ids,
                    comparison_metrics=comparison_metrics,
                    output_format="html"
                )
            )
            
            # Verify comparison result
            self.assertIsNotNone(comparison_result)
            self.assertEqual(comparison_result["type"], "comparison")
            self.assertEqual(comparison_result["format"], "html")
            self.assertEqual(comparison_result["plan_count"], 2)
            
            # Verify mock was called correctly
            mock_compare.assert_called_once()

if __name__ == "__main__":
    unittest.main() 