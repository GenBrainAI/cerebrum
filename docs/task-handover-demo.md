# Task Handover Demo

This demo showcases the task handover capability in Cerebrum, which allows tasks to pass data between each other in a workflow.

## What is Task Handover?

Task handover is a powerful feature that enables the creation of complex workflows by allowing tasks to pass their outputs as inputs to other tasks. This creates a pipeline where each task builds on the work of previous tasks.

Key capabilities:
- **Sequential Processing**: Run multiple tasks in sequence with automatic data passing
- **Dependency Management**: Tasks can specify which previous tasks they require data from
- **Complex Workflows**: Build complex DAG (Directed Acyclic Graph) workflows with multiple branches
- **Visibility and Control**: See task dependencies and execution progress

## Running the Demo

To run the task handover demo:

```bash
# Option 1: Use the convenience script
./run_handover_demo.py

# Option 2: Set up the demo state and run manually
python -m src.state_setup.task_handover_demo
streamlit run src/chat.py
```

## Demo Walkthrough

The demo sets up a task manager called "Task Handover Demo" with the following tasks:

1. **Research Task**: Gathers information on a topic
2. **Analysis Task**: Analyzes the research findings (depends on Research Task)
3. **Report Generation Task**: Generates a comprehensive report (depends on both Research and Analysis)
4. **Data Collection Task**: Collects numerical data on the topic
5. **Visualization Task**: Creates data visualizations (depends on Data Collection)
6. **Executive Summary Task**: Creates a final summary (depends on Report and Visualization)

### Using the Demo

1. Navigate to the **Task Handover** tab in the Task Hierarchy view
2. Select the "Task Handover Demo" task manager
3. You'll see a dependency graph showing how tasks are connected
4. Create a sequence to run, for example:
   - Research Task → Analysis Task → Report Generation Task
   - Or: Data Collection → Visualization Task
5. The system will validate your sequence to ensure all dependencies are met
6. Run the sequence to see how data passes between tasks

## Implementation Details

The task handover feature relies on several key components:

1. **Task Model**: Enhanced with `input_from_tasks`, `output_to_tasks`, and `output_data` fields
2. **TaskRunner**: Added `run_task_sequence` method to manage execution and data passing
3. **API Endpoint**: New endpoint at `/tasksmanager/{tasksmanager_id}/tasks/run-sequence`
4. **UI Component**: Added `TaskHandoverComponent` for visual selection and execution

## Extension Points

This feature can be extended in several ways:

1. **Workflow Templates**: Predefined sequences of tasks for common workflows
2. **Conditional Branching**: Add conditions that determine which branch to follow
3. **Parallel Execution**: Run independent tasks in parallel
4. **Progress Monitoring**: Enhanced tracking of task sequence execution
5. **Error Recovery**: More sophisticated error handling and recovery mechanisms

## Technical Documentation

For more technical details, see:
- Task handover unit tests at `tests/controllers/test_task_handover.py`
- The `run_task_sequence` method in `src/server/controllers/task_runner.py`
- API endpoint in `src/server/apis/task_api.py`
- UI component in `src/server/views/components/task_handover_component.py` 