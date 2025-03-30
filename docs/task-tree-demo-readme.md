# Task Tree Demo State

## Overview

The Task Tree Demo showcases Cerebrum's capability to orchestrate complex, hierarchical task execution flows with multiple agent frameworks working together. This demo presents a data processing pipeline that demonstrates:

- Hierarchical task structures with parent-child relationships
- Cross-framework task handover (data flowing between tasks)
- Multiple plugin integration (CrewAI, AutoGen, SmolAgents)
- Different execution strategies (sequential and parallel)
- Advanced task visualization

## Demo Architecture

The demo implements a data processing pipeline with the following structure:

```
Root: Data Pipeline Coordinator
  ├─ Data Acquisition (CrewAI)
  ├─ Market Analysis (AutoGen) ← Data Acquisition
  ├─ Technical Analysis (AutoGen) ← Data Acquisition
  └─ Report Generation (SmolAgents) ← Market Analysis, Technical Analysis
```

### Task Descriptions

1. **Data Pipeline Coordinator (Root)**: Orchestrates the entire pipeline and manages execution flow.
   
2. **Data Acquisition (CrewAI)**: Collects and prepares raw data from various sources, ensuring it's properly formatted for analysis.
   
3. **Market Analysis (AutoGen)**: Analyzes market-related aspects of the data, focusing on trends, competitive landscape, and market opportunities. Receives input from the Data Acquisition task.
   
4. **Technical Analysis (AutoGen)**: Analyzes technical aspects of the data, focusing on metrics, patterns, and technical indicators. Receives input from the Data Acquisition task.
   
5. **Report Generation (SmolAgents)**: Creates a comprehensive final report combining insights from both the Market Analysis and Technical Analysis tasks.

### Data Flow

The pipeline demonstrates sophisticated data handover between tasks:

- **Data Acquisition → Market Analysis**: Prepared datasets ready for market analysis
- **Data Acquisition → Technical Analysis**: Prepared datasets ready for technical analysis
- **Market Analysis → Report Generation**: Market insights, trends, and competitive analysis
- **Technical Analysis → Report Generation**: Technical indicators, patterns, and metrics

### Execution Strategy

The demo showcases multiple execution strategies:

- **Sequential execution** for the overall pipeline
- **Parallel execution** for the analysis tasks (Market Analysis and Technical Analysis)
- **Data dependency handling** where Report Generation waits for both analysis tasks to complete

## Technologies Demonstrated

1. **Task Tree Management**: Hierarchical organization of tasks with parent-child relationships
2. **Multi-Plugin Integration**: Seamless use of multiple agent frameworks:
   - CrewAI for data collection and preparation
   - AutoGen for parallel data analysis
   - SmolAgents for report generation
3. **Task Handover**: Data passing between tasks, including from one framework to another
4. **Execution Strategies**: Different approaches to task execution (sequential, parallel)
5. **Visualization**: Interactive visualization of the task tree structure and data flow

## Using the Demo

1. Navigate to the **Task Hierarchy** view in Cerebrum
2. Select the **Task Tree Demo** tab
3. Click **Generate Task Tree Demo** if not already generated
4. Click **Load Task Tree Demo** to load the state
5. Explore the task tree visualization to understand the structure and data flow
6. Navigate to the **Chat** view to interact with the system and execute the pipeline

## Key Features to Explore

1. **Task Structure**: Examine the parent-child relationships between tasks
2. **Data Dependencies**: Note how tasks depend on outputs from other tasks
3. **Plugin Diversity**: Observe how different frameworks are used for specialized tasks
4. **Execution Flow**: See how tasks are executed in sequence or in parallel based on their relationships
5. **Data Handover**: Understand how data flows from one task to another

## Implementation Details

The Task Tree Demo is implemented as a complete state in Cerebrum, with several key components:

- **Task Tree State**: A serialized state file in the `state/` directory
- **Task Tree Manager**: Handles the execution of the task tree
- **Task Tree Visualization**: Renders an interactive visualization of the tree structure
- **Task Hierarchy UI**: Integrated with the existing task hierarchy view

All components work together to provide a comprehensive demonstration of Cerebrum's task tree capabilities.

## Extending the Demo

This demo can be extended in several ways:

1. Adding more complex task relationships
2. Implementing different execution strategies
3. Integrating additional agent frameworks
4. Creating more sophisticated data transformation between tasks
5. Adding real-time execution monitoring

## Technical Notes

- The demo uses NetworkX and Matplotlib for visualization
- Task relationships are stored in the persistence model
- Execution metadata tracks the order and dependencies between tasks
- Plugin-specific configurations are included for each agent framework

## Related Documentation

- Task Tree API Documentation
- Plugin Integration Guide
- Execution Strategies Guide
- Task Handover Documentation
