#!/usr/bin/env python3
"""
Example script demonstrating how to use the Self-Aware System integration.

This script shows how to initialize the Self-Aware System and use its various components
to perform tasks like parallel execution, package management, git operations, testing,
resource monitoring, and metrics collection.
"""

import asyncio
import logging
import os
import sys
from datetime import datetime, timedelta

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))

from src.server.self_aware_integration import SelfAwareSystem

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

async def example_parallel_tasks(system):
    """Demonstrate parallel task execution."""
    logger.info("Demonstrating parallel task execution...")
    
    # Define some example tasks
    async def task1():
        logger.info("Task 1 starting")
        await asyncio.sleep(2)
        logger.info("Task 1 completed")
        return {"result": "Task 1 result"}
    
    async def task2():
        logger.info("Task 2 starting")
        await asyncio.sleep(1)
        logger.info("Task 2 completed")
        return {"result": "Task 2 result"}
    
    async def task3():
        logger.info("Task 3 starting")
        await asyncio.sleep(3)
        logger.info("Task 3 completed")
        return {"result": "Task 3 result"}
    
    # Create task definitions
    tasks = [
        {"coroutine": task1(), "resource_requirements": {"cpu": 0.1, "memory": 100}},
        {"coroutine": task2(), "resource_requirements": {"cpu": 0.1, "memory": 100}},
        {"coroutine": task3(), "resource_requirements": {"cpu": 0.1, "memory": 100}}
    ]
    
    # Execute tasks in parallel
    results = await system.execute_tasks_in_parallel(tasks)
    
    # Print results
    logger.info(f"Parallel execution results: {results}")
    
    return results

async def example_package_management(system):
    """Demonstrate package management."""
    logger.info("Demonstrating package management...")
    
    # List installed packages
    packages = await system.list_installed_packages()
    logger.info(f"Installed packages: {len(packages)} packages found")
    
    # Try to install a package (this will require approval)
    install_result = await system.install_package("requests")
    logger.info(f"Install result: {install_result}")
    
    # If approval is required, we would normally wait for approval here
    if not install_result.get("success") and "approval_request_id" in install_result:
        logger.info(f"Approval required with ID: {install_result['approval_request_id']}")
    
    return install_result

async def example_git_operations(system):
    """Demonstrate Git operations."""
    logger.info("Demonstrating Git operations...")
    
    # Get repository status (if in a Git repository)
    status = await system.get_repository_status()
    logger.info(f"Repository status: {status}")
    
    # Try to commit changes (this will require approval)
    if status.get("success") and status.get("has_changes", False):
        commit_result = await system.commit_changes("Example commit from Self-Aware System")
        logger.info(f"Commit result: {commit_result}")
    
    return status

async def example_test_operations(system):
    """Demonstrate test operations."""
    logger.info("Demonstrating test operations...")
    
    # Discover tests
    tests = await system.discover_tests()
    logger.info(f"Discovered tests: {len(tests)} tests found")
    
    # If tests were found, run them
    if tests:
        test_results = await system.run_tests()
        logger.info(f"Test results: {test_results.get('success')}, {test_results.get('total')} tests run")
        
        # Get test coverage
        coverage = await system.get_test_coverage()
        logger.info(f"Test coverage: {coverage.get('total_coverage')}%")
        
        return test_results
    
    return {"success": False, "message": "No tests found"}

async def example_resource_monitoring(system):
    """Demonstrate resource monitoring."""
    logger.info("Demonstrating resource monitoring...")
    
    # Get current resource usage
    usage = await system.get_current_resource_usage()
    logger.info(f"Current resource usage: {usage}")
    
    # Set a budget for CPU usage
    budget_result = await system.set_resource_budget("cpu", 90.0, "hourly")
    logger.info(f"CPU budget set: {budget_result}")
    
    # Check the budget
    budget_check = await system.check_resource_budget("cpu")
    logger.info(f"CPU budget check: {budget_check}")
    
    # Record some resource usage
    await system.record_resource_usage("api_calls", 10, "example_operation")
    logger.info("Recorded API call usage")
    
    return usage

async def example_metrics_collection(system):
    """Demonstrate metrics collection."""
    logger.info("Demonstrating metrics collection...")
    
    # Record some metrics
    await system.record_metric("example_metric", 42.0, {"source": "example"})
    await system.record_metric("example_metric", 43.0, {"source": "example"})
    await system.record_metric("example_metric", 44.0, {"source": "example"})
    
    # Get metrics
    metrics = await system.get_metrics("example_metric")
    logger.info(f"Example metrics: {metrics}")
    
    # Get system health
    health = await system.get_system_health()
    logger.info(f"System health: {health}")
    
    return health

async def example_knowledge_integration(system):
    """Demonstrate knowledge integration."""
    logger.info("Demonstrating knowledge integration...")
    
    # Add semantic knowledge
    system.add_semantic_knowledge(
        concept="Self-Aware Example",
        definition="An example script demonstrating the Self-Aware System capabilities.",
        related_concepts=["Example", "Demonstration", "Self-Aware System"],
        tags=["example", "documentation"]
    )
    
    # Add procedural knowledge
    system.add_procedural_knowledge(
        task_name="Run Example Script",
        description="How to run the example script for the Self-Aware System.",
        steps=[
            "Navigate to the project directory",
            "Run 'python src/server/examples/self_aware_example.py'",
            "Observe the output in the console"
        ],
        expected_outcome="The script runs successfully and demonstrates various capabilities.",
        tags=["example", "usage"]
    )
    
    # Add episodic knowledge
    system.add_episodic_knowledge(
        title="Example Script Execution",
        description="The example script was executed to demonstrate the Self-Aware System.",
        timestamp=datetime.now(),
        actors=["User"],
        tags=["example", "execution"]
    )
    
    # Get knowledge context
    context = system.get_knowledge_context("example")
    logger.info(f"Knowledge context for 'example': {len(context)} items found")
    
    return context

async def main():
    """Main function to run the example."""
    logger.info("Starting Self-Aware System example...")
    
    # Initialize the Self-Aware System
    system = SelfAwareSystem()
    logger.info("Self-Aware System initialized")
    
    try:
        # Run example functions
        await example_parallel_tasks(system)
        await example_package_management(system)
        await example_git_operations(system)
        await example_test_operations(system)
        await example_resource_monitoring(system)
        await example_metrics_collection(system)
        await example_knowledge_integration(system)
        
        # Start a cognitive cycle (this would normally run for longer)
        logger.info("Starting a cognitive cycle...")
        task_id = await system.start_cognitive_cycle()
        logger.info(f"Cognitive cycle started with task ID: {task_id}")
        
        # Wait a bit to let things run
        logger.info("Waiting for 5 seconds...")
        await asyncio.sleep(5)
        
    finally:
        # Shutdown the system
        logger.info("Shutting down the Self-Aware System...")
        await system.shutdown()
    
    logger.info("Example completed successfully")

if __name__ == "__main__":
    asyncio.run(main()) 