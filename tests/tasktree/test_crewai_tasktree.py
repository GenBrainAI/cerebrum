"""
Test suite for CrewAI integration with task tree.
Tests the execution of CrewAI tasks within the task tree structure.
"""

import pytest
import logging
from pathlib import Path
from typing import Dict, Any, List
from src.server.models.task import Task
from src.server.models.tasks_manager import TasksManager
from src.server.persistence.in_memory_persistence import InMemoryPersistenceModel
from src.server.controllers.task_runner import TaskRunner
from src.server.models.agent import CrewAIConfig, CreateCrewRequest
from src.server.models.tasktree import TaskTree, TaskNode

logger = logging.getLogger(__name__)

@pytest.fixture
def persistence_model():
    """Create a persistence model for testing."""
    return InMemoryPersistenceModel()

@pytest.fixture
def crewai_config():
    """Create a sample CrewAI configuration."""
    return CrewAIConfig(
        create_crew=CreateCrewRequest(
            name="Test Crew",
            description="Test crew for task tree",
            tasks=[
                {
                    "name": "Task 0",
                    "description": "Task 0 description",
                    "agent_role": "Agent 0",
                    "expected_output": "Task 0 output",
                    "tools": []
                },
                {
                    "name": "Task 1",
                    "description": "Task 1 description",
                    "agent_role": "Agent 1",
                    "expected_output": "Task 1 output",
                    "tools": []
                },
                {
                    "name": "Task 2",
                    "description": "Task 2 description",
                    "agent_role": "Agent 2",
                    "expected_output": "Task 2 output",
                    "tools": []
                }
            ],
            agents=[
                {
                    "name": "Agent 0",
                    "role": "Agent 0",
                    "goal": "Goal 0",
                    "backstory": "Backstory 0",
                    "tools": []
                },
                {
                    "name": "Agent 1",
                    "role": "Agent 1",
                    "goal": "Goal 1",
                    "backstory": "Backstory 1",
                    "tools": []
                },
                {
                    "name": "Agent 2",
                    "role": "Agent 2",
                    "goal": "Goal 2",
                    "backstory": "Backstory 2",
                    "tools": []
                }
            ]
        )
    )

@pytest.mark.asyncio
async def test_crewai_task_tree_creation(persistence_model, crewai_config):
    """Test creation of task tree with CrewAI tasks."""
    try:
        logger.info("Testing CrewAI task tree creation...")
        
        # Store CrewAI config
        stored_config = persistence_model.crewai_config.create(crewai_config)
        assert stored_config is not None, "Failed to store CrewAI config"
        
        # Create task manager
        task_manager = TasksManager(
            name="Test Tree Manager",
            description="Manager for task tree testing",
            crewai_config_id=stored_config.id
        )
        stored_manager = persistence_model.tasksmanagers.create(task_manager)
        assert stored_manager is not None, "Failed to store task manager"
        
        # Create parent task
        parent_task = Task(
            name="Parent Tool Generation",
            description="Generate parent tool",
            tasksmanager_id=stored_manager.id,
            crewai_config_id=stored_config.id,
            agent_role="Parent Agent",
            input_data={
                "tool_request": {
                    "name": "ParentTool",
                    "description": "A parent tool"
                }
            }
        )
        stored_parent = persistence_model.tasks.create(parent_task)
        assert stored_parent is not None, "Failed to store parent task"
        
        # Create child task
        child_task = Task(
            name="Child Tool Generation",
            description="Generate child tool",
            tasksmanager_id=stored_manager.id,
            crewai_config_id=stored_config.id,
            agent_role="Child Agent",
            input_data={
                "tool_request": {
                    "name": "ChildTool",
                    "description": "A child tool"
                }
            }
        )
        stored_child = persistence_model.tasks.create(child_task)
        assert stored_child is not None, "Failed to store child task"
        
        # Create task tree
        task_tree = TaskTree()
        parent_node = TaskNode(task=stored_parent)
        child_node = TaskNode(task=stored_child)
        
        # Add dependency
        parent_node.add_child(child_node)
        task_tree.add_node(parent_node)
        
        # Verify tree structure
        assert len(task_tree.get_roots()) == 1, "Task tree should have one root"
        assert len(parent_node.children) == 1, "Parent node should have one child"
        assert child_node.parent == parent_node, "Child node should reference parent"
        
        logger.info("✅ CrewAI task tree creation test passed")
        
    except Exception as e:
        logger.error(f"Test failed: {str(e)}", exc_info=True)
        raise

@pytest.mark.asyncio
async def test_crewai_task_tree_execution(persistence_model, crewai_config):
    """Test execution of CrewAI tasks in task tree."""
    try:
        logger.info("Testing CrewAI task tree execution...")
        
        # Create task tree with dependencies
        stored_config = persistence_model.crewai_config.create(crewai_config)
        task_manager = TasksManager(
            name="Execution Tree Manager",
            description="Manager for execution testing",
            crewai_config_id=stored_config.id
        )
        stored_manager = persistence_model.tasksmanagers.create(task_manager)
        
        # Create tasks with dependencies
        tasks: List[Task] = []
        for i in range(3):
            task = Task(
                name=f"Tool Generation {i}",
                description=f"Generate tool {i}",
                tasksmanager_id=stored_manager.id,
                crewai_config_id=stored_config.id,
                agent_role=f"Agent {i}",
                input_data={
                    "tool_request": {
                        "name": f"Tool{i}",
                        "description": f"Tool {i} description"
                    }
                }
            )
            stored_task = persistence_model.tasks.create(task)
            tasks.append(stored_task)
        
        # Create task tree with sequential dependencies
        task_tree = TaskTree()
        nodes = [TaskNode(task=task) for task in tasks]
        
        # Add sequential dependencies
        for i in range(len(nodes) - 1):
            nodes[i].add_child(nodes[i + 1])
        
        # Add all nodes to the tree
        for node in nodes:
            task_tree.add_node(node)
        
        # Create task runner
        runner = TaskRunner(persistence_model)
        
        # Mock the plugin manager and CrewAI plugin
        from unittest.mock import MagicMock, AsyncMock
        from src.server.plugins.plugin_manager import PluginManager
        
        # Create a mock plugin that returns a successful result
        mock_plugin = MagicMock()
        mock_plugin.create_agent = AsyncMock(return_value=MagicMock())
        mock_plugin.execute_task = AsyncMock(return_value={
            "status": "completed",
            "response": "Task completed successfully",
            "generated_tool": {
                "name": "Tool0",  # This will be updated for each task
                "description": "Generated tool description",
                "parameters": []
            }
        })
        
        # Create a mock plugin manager
        runner._plugin_manager = MagicMock(spec=PluginManager)
        runner._plugin_manager.get_plugin = MagicMock(return_value=mock_plugin)
        
        # Execute tasks in order
        execution_results = []
        for i, node in enumerate(task_tree.get_execution_order()):
            # Update the mock response for each task
            mock_plugin.execute_task = AsyncMock(return_value={
                "status": "completed",
                "response": f"Task {i} completed successfully",
                "generated_tool": {
                    "name": f"Tool{i}",
                    "description": f"Generated tool {i} description",
                    "parameters": []
                }
            })
            
            result = await runner.run_task(
                tasksmanager_id=stored_manager.id,
                task_id=node.task.id
            )
            execution_results.append(result)
            
            # Verify execution result
            assert result is not None, f"Execution failed for task {node.task.name}"
            assert result['status'] in ['completed', 'success', 'failed'], f"Task {node.task.name} has invalid status"
            if result['status'] == 'failed':
                logger.error(f"Task {node.task.name} failed with error: {result.get('error', 'Unknown error')}")
                break
            
            # Verify generated tool
            assert 'generated_tool' in result, f"Missing generated tool for task {node.task.name}"
            tool = result['generated_tool']
            assert tool['name'] == f"Tool{len(execution_results)-1}", "Incorrect tool name"
        
        # Verify all tasks were executed in order
        assert len(execution_results) == len(tasks), "Not all tasks were executed"
        
        logger.info("✅ CrewAI task tree execution test passed")
        
    except Exception as e:
        logger.error(f"Test failed: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        raise

@pytest.mark.asyncio
async def test_crewai_task_tree_error_handling(persistence_model, crewai_config):
    """Test error handling in CrewAI task tree execution."""
    try:
        logger.info("Testing CrewAI task tree error handling...")
        
        # Create task tree with invalid configuration
        stored_config = persistence_model.crewai_config.create(crewai_config)
        task_manager = TasksManager(
            name="Error Test Manager",
            description="Manager for error testing",
            crewai_config_id=stored_config.id
        )
        stored_manager = persistence_model.tasksmanagers.create(task_manager)
        
        # Create task with invalid configuration
        invalid_task = Task(
            name="Invalid Tool Generation",
            description="Generate invalid tool",
            tasksmanager_id=stored_manager.id,
            crewai_config_id=stored_config.id,
            agent_role="Invalid Agent",  # Agent not in CrewAI config
            input_data={
                "tool_request": {
                    "name": "InvalidTool",
                    "description": "An invalid tool"
                }
            }
        )
        stored_task = persistence_model.tasks.create(invalid_task)
        
        # Create task tree
        task_tree = TaskTree()
        node = TaskNode(task=stored_task)
        task_tree.add_node(node)
        
        # Create task runner
        runner = TaskRunner(persistence_model)
        
        # Execute task and expect error status
        result = await runner.run_task(
            tasksmanager_id=stored_manager.id,
            task_id=stored_task.id
        )
        
        assert result is not None, "Task execution result should not be None"
        assert result['status'] == 'failed', "Task should have failed status"
        assert "Agent role 'Invalid Agent' not found in crew configuration" in str(result.get('error', '')), "Error should mention the invalid agent role"
        
        logger.info("✅ CrewAI task tree error handling test passed")
        
    except Exception as e:
        logger.error(f"Test failed: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        raise 