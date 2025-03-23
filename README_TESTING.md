# Testing the Research Planner Component

This document provides an overview of the testing strategy for the Research Planner component in the Cerebrum project.

## Overview

The Research Planner consists of two main parts:
1. The core `ResearchPlanner` class - handles the business logic for identifying knowledge gaps, creating research plans, and managing research tasks
2. The `ResearchPlannerView` class - provides a Streamlit UI for interacting with the Research Planner

## Test Files

The project includes the following test files:
- `tests/server/planning/test_research_planner.py` - Unit tests for the core functionality
- `tests/server/ui/test_research_planner_view.py` - UI component tests
- `tests/integration/test_research_planning_integration.py` - Integration tests with other components
- `run_research_planner_tests.py` - Standalone script to run core functionality tests
- `run_ui_tests.py` - Standalone script to run UI component tests

## Running the Tests

### Option 1: Using pytest (requires GitHub credentials)
```bash
pytest -v tests/server/planning/test_research_planner.py
pytest -v tests/server/ui/test_research_planner_view.py
pytest -v tests/integration/test_research_planning_integration.py
```

### Option 2: Using standalone scripts (no external dependencies)
```bash
python run_research_planner_tests.py
python run_ui_tests.py
```

## Testing Strategy

### Core Functionality Tests
The core functionality tests focus on:
- Knowledge gap identification
- Research plan creation
- Research task prioritization
- Validation of data models (KnowledgeGap, ResearchTask, ResearchPlan)
- Serialization and deserialization of objects

### UI Component Tests
The UI component tests verify:
- Proper initialization of the UI
- Rendering of different tabs (Knowledge Gaps, Research Plans, Task Dashboard)
- User interactions through input fields and buttons
- Handling of state changes
- Visualization of data

## Testing Challenges and Solutions

### Challenge 1: Asynchronous Code
The Research Planner uses asynchronous methods for various operations. To test this, we:
- Use `asyncio.run()` to execute the asynchronous tests
- Create mock versions of async methods that return predefined values

### Challenge 2: Streamlit Session State
Streamlit's session state is global and managed by the Streamlit runtime. For testing, we:
- Created a custom `SessionState` class that behaves like both a dictionary and an object
- Mocked the various Streamlit UI components and session state behavior
- Patched the global Streamlit module during tests

### Challenge 3: Visualization Components
The UI uses Plotly for data visualization, which can be complex to mock. We:
- Created a comprehensive mock for Plotly modules (graph_objects, express)
- Bypassed actual rendering while verifying interaction with visualization functions

## Test Data

The tests use carefully constructed sample data, including:
- Knowledge gaps related to AI topics
- Research plans with various configurations
- Research tasks with dependencies and priorities

## Best Practices

1. **Isolate External Dependencies**: Most tests use mocks for external systems like the Knowledge Integration System
2. **Focus on Interfaces**: Tests verify the public interfaces, not the internal implementation details
3. **Test Typical Scenarios**: Cover common usage patterns and edge cases
4. **Maintain Test Independence**: Each test should be able to run independently of others
5. **Clear Assertions**: Each test makes clear assertions about expected results

## Troubleshooting

If you encounter GitHub credential issues when running the tests, use the standalone scripts which bypass these dependencies. 