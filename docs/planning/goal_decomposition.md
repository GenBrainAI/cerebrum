# Goal Decomposition Engine

The Goal Decomposition Engine is a component of the Self-Aware Cerebrum system that breaks down high-level goals into manageable subgoals. It provides a structured approach to planning and executing complex tasks by decomposing them into smaller, more manageable pieces.

## Overview

The Goal Decomposition Engine takes a high-level goal and decomposes it into a hierarchy of subgoals using various decomposition strategies. It also provides functionality for prioritizing subgoals, estimating resources, and validating decompositions.

## Key Features

- **Goal Decomposition**: Break down high-level goals into manageable subgoals using different strategies.
- **Resource Estimation**: Estimate the resources required for each subgoal and the overall goal.
- **Subgoal Prioritization**: Prioritize subgoals based on various factors such as dependencies, complexity, and risk.
- **Decomposition Validation**: Validate decompositions for completeness and consistency.
- **Knowledge Integration**: Leverage the Knowledge Integration System to inform the decomposition process.

## Goal Types

The engine supports different types of goals, each with its own decomposition patterns:

- **GENERAL**: General-purpose goals without a specific domain.
- **RESEARCH**: Goals focused on research and information gathering.
- **DEVELOPMENT**: Goals focused on software development.
- **ANALYSIS**: Goals focused on data analysis and interpretation.
- **PLANNING**: Goals focused on planning and organization.
- **LEARNING**: Goals focused on learning and skill acquisition.

## Decomposition Strategies

The engine supports different strategies for decomposing goals:

- **TOP_DOWN**: Start with the high-level goal and break it down into smaller subgoals.
- **BOTTOM_UP**: Start with basic tasks and group them into higher-level subgoals.
- **MIDDLE_OUT**: Start with key components and expand both up and down.
- **TEMPLATE_BASED**: Use predefined templates for common goal types.
- **KNOWLEDGE_BASED**: Use the Knowledge Integration System to inform the decomposition.

## Resource Estimation

For each subgoal, the engine estimates the following resources:

- **Time**: Estimated time required to complete the subgoal (in hours).
- **Complexity**: Complexity level of the subgoal (1-10).
- **Knowledge Requirements**: Specific knowledge areas required for the subgoal.
- **Dependencies**: Other subgoals that must be completed before this one.
- **Risk Level**: Risk level associated with the subgoal (1-10).

## Usage

### Command Line Interface

The Goal Decomposition Engine can be used through the command line interface:

```bash
# Decompose a goal
python -m src.server.cli goal decompose --name "Implement Feature X" --description "Implement a new feature X for the system" --type DEVELOPMENT

# Get subgoals for a decomposed goal
python -m src.server.cli goal subgoals <goal_id>

# Prioritize subgoals
python -m src.server.cli goal prioritize <goal_id>

# Validate a decomposition
python -m src.server.cli goal validate <goal_id>
```

### Streamlit UI

The Goal Decomposition Engine can also be used through the Streamlit UI:

1. Navigate to the "Goal Decomposition" page.
2. Use the "Decompose Goal" tab to decompose a new goal.
3. Use the "View Subgoals" tab to view the subgoals for a decomposed goal.
4. Use the "Prioritize Subgoals" tab to prioritize subgoals.
5. Use the "Validate Decomposition" tab to validate a decomposition.

## Integration with Other Components

The Goal Decomposition Engine integrates with other components of the Self-Aware Cerebrum system:

- **Knowledge Integration System**: Provides relevant knowledge for the decomposition process.
- **AI Parameter Manager**: Configures the AI models used for decomposition.
- **Self-Aware System**: Provides access to the Goal Decomposition Engine through the API.

## Future Enhancements

Planned enhancements for the Goal Decomposition Engine include:

- **Advanced Decomposition Strategies**: More sophisticated strategies for decomposing goals.
- **Machine Learning-Based Resource Estimation**: More accurate resource estimation using machine learning.
- **Interactive Decomposition**: Interactive decomposition process with user feedback.
- **Visualization Improvements**: Better visualization of goal decompositions.
- **Integration with Implementation Planner**: Tighter integration with the Implementation Planner.

## API Reference

### GoalDecompositionEngine

The main class for the Goal Decomposition Engine.

#### Methods

- `decompose_goal(goal, strategy=DecompositionStrategy.TOP_DOWN, context=None)`: Decompose a high-level goal into subgoals.
- `get_decomposed_goal(goal_id)`: Get a decomposed goal by ID.
- `get_all_decomposed_goals()`: Get all decomposed goals.
- `delete_decomposed_goal(goal_id)`: Delete a decomposed goal.
- `prioritize_subgoals(goal_id)`: Prioritize subgoals within a decomposed goal.
- `estimate_resources(goal_id)`: Estimate resources for a decomposed goal.
- `validate_decomposition(goal_id)`: Validate a goal decomposition.

### DecomposedGoal

A class representing a decomposed goal.

#### Properties

- `id`: The unique ID of the decomposed goal.
- `name`: The name of the goal.
- `description`: The description of the goal.
- `goal_type`: The type of the goal (e.g., DEVELOPMENT, RESEARCH).
- `strategy`: The strategy used to decompose the goal.
- `subgoals`: A dictionary of subgoals, keyed by subgoal ID.
- `root_subgoal_ids`: A list of IDs for the root subgoals.
- `total_resources`: The total resources required for the goal.
- `created_at`: The timestamp when the goal was created.
- `updated_at`: The timestamp when the goal was last updated.
- `status`: The status of the goal (e.g., pending, in_progress, completed).

### SubGoal

A class representing a subgoal within a decomposed goal.

#### Properties

- `id`: The unique ID of the subgoal.
- `name`: The name of the subgoal.
- `description`: The description of the subgoal.
- `goal_type`: The type of the subgoal.
- `priority`: The priority of the subgoal (1-10).
- `resources`: The resources required for the subgoal.
- `parent_id`: The ID of the parent subgoal, if any.
- `children_ids`: A list of IDs for the child subgoals.
- `status`: The status of the subgoal.

### ResourceEstimate

A class representing the resources required for a subgoal.

#### Properties

- `time_hours`: The estimated time required to complete the subgoal (in hours).
- `complexity`: The complexity level of the subgoal (1-10).
- `knowledge_requirements`: A list of specific knowledge areas required for the subgoal.
- `dependencies`: A list of IDs for other subgoals that must be completed before this one.
- `risk_level`: The risk level associated with the subgoal (1-10). 