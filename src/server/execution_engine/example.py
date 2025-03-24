#!/usr/bin/env python
"""
Example usage of the ExecutionEngine and related components.
This demonstrates creating tasks, setting up context, and executing tasks with context propagation.
"""

import logging
import uuid
from datetime import datetime, timedelta

from .task_selector import Task, TaskStatus, TaskPriority, TaskDependency
from .context_manager import ContextType
from .execution_engine import ExecutionEngine

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    """Main execution example."""
    logger.info("Starting ExecutionEngine example")
    
    # Create the execution engine
    engine = ExecutionEngine()
    
    # Set up some context validation rules
    engine.context_validator.add_type_validator("project_name", str)
    engine.context_validator.add_range_validator("priority_factor", 1, 10)
    
    # Set up context propagation rules
    engine.context_propagator.add_rule(
        "input_data", 
        "processed_data", 
        lambda x: {"processed": True, "original": x}
    )
    
    # Create some tasks
    task1_id = engine.create_task(
        name="Initialize Project",
        description="Set up project structure and configuration",
        priority=TaskPriority.HIGH,
        estimated_duration=15.0,
        estimated_resources={"cpu": 1.0, "memory": 512},
        context_requirements=[],
        tags=["setup", "initialization"]
    )
    
    # Create a task that depends on the first task
    task2_id = engine.create_task(
        name="Process Data",
        description="Process input data from initialization",
        priority=TaskPriority.MEDIUM,
        dependencies=[TaskDependency(task1_id, "hard", "")],
        estimated_duration=30.0,
        estimated_resources={"cpu": 2.0, "memory": 1024},
        context_requirements=["input_data"],
        tags=["processing", "data"]
    )
    
    # Create another dependent task
    task3_id = engine.create_task(
        name="Generate Report",
        description="Generate final report using processed data",
        priority=TaskPriority.LOW,
        dependencies=[TaskDependency(task2_id, "hard", "")],
        estimated_duration=20.0,
        estimated_resources={"cpu": 1.0, "memory": 512},
        context_requirements=["processed_data"],
        tags=["reporting", "output"],
        metadata={"deadline": datetime.now() + timedelta(hours=2)}
    )
    
    # Set initial context
    engine.context_manager.set_context("project_name", "Self-Aware System Demo", ContextType.GLOBAL)
    engine.context_manager.set_context("priority_factor", 5, ContextType.SESSION)
    
    # Print initial execution state
    print("\nInitial execution state:")
    print_execution_state(engine)
    
    # Execute tasks until none are left
    while True:
        task = engine.select_next_task()
        if not task:
            logger.info("No more tasks to execute")
            break
        
        logger.info(f"Executing task: {task.name}")
        result = engine.execute_task(task.id)
        print(f"\nTask execution result: {result}")
        
        # After the first task, set some input data for the next task
        if task.id == task1_id:
            engine.context_manager.set_context(
                "input_data", 
                {"samples": 1000, "source": "database"}, 
                ContextType.TASK
            )
            logger.info("Added input_data to context for next task")
        
        # Print updated execution state
        print("\nExecution state after task execution:")
        print_execution_state(engine)
    
    # Print final execution history
    print("\nExecution history:")
    for i, entry in enumerate(engine.execution_history):
        print(f"{i+1}. {entry['task_name']} - Status: {entry['status']}, Duration: {entry['duration']:.2f}s")
    
    logger.info("ExecutionEngine example completed")

def print_execution_state(engine):
    """Print a formatted version of the execution state."""
    state = engine.get_execution_state()
    
    print("Task counts:")
    for status, count in state["task_counts"].items():
        print(f"  {status}: {count}")
    
    print("Context stats:")
    for context_type, count in state["context_stats"].items():
        print(f"  {context_type}: {count}")
    
    dependency_analysis = state["dependency_analysis"]
    if dependency_analysis and "empty" not in dependency_analysis:
        print("Dependency analysis:")
        print(f"  Total tasks: {dependency_analysis['total_tasks']}")
        print(f"  Independent tasks: {dependency_analysis['independent_tasks']}")
        print(f"  Terminal tasks: {dependency_analysis['terminal_tasks']}")
        print(f"  Max chain length: {dependency_analysis['max_chain_length']}")
        
        if dependency_analysis.get("bottleneck_tasks"):
            print(f"  Bottleneck tasks: {dependency_analysis['bottleneck_tasks']}")
        
        if dependency_analysis.get("circular_dependencies"):
            print(f"  Warning - Circular dependencies detected: {dependency_analysis['circular_dependencies']}")

if __name__ == "__main__":
    main() 