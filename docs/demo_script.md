# Cerebrum Demo Script

## Preparation
1. Ensure all dependencies are installed:
   ```bash
   pip install -r requirements.txt
   ```
2. Start the Streamlit application:
   ```bash
   streamlit run src/chat.py
   ```

## Demo 1: Agentic Plugin System

### Step 1: Navigate to the Agentic Config View
1. In the Streamlit sidebar, select "Agentic Config" view
2. Click on the "Plugin Explorer" tab
3. Explore the available plugins (CrewAI, AutoGen, SmolAgents)
4. Highlight the capabilities of each plugin

### Step 2: Show Notebook Demo
1. Click on the "Notebooks" tab
2. Select "Plugin Handover Demo" from the dropdown
3. Walk through the notebook showing how different plugins work together
4. Point out the visualization of the handover flow
5. Explain how data is passed between plugins

## Demo 2: Task Handover

### Step 1: Navigate to the Task Hierarchy View
1. In the Streamlit sidebar, select "Task Hierarchy" view
2. Open the "Demonstration" expander
3. Click "Load Task Tree Demo"
4. Once loaded, explore the task hierarchy
5. Point out the handover relationships shown in the UI

### Step 2: Execute Task Sequence
1. Select the root task "Research Project"
2. Click "Run Task"
3. Watch the execution flow through the tasks
4. Highlight how data flows from one task to another
5. Show the results of each task in the sequence

## Demo 3: Task Tree Visualization

### Step 1: Explore the Task Tree Structure
1. In the Task Hierarchy view with the demo loaded
2. Point out the parent-child relationships
3. Highlight the different plugins used for different tasks
4. Explain the execution strategy (sequential vs parallel)

### Step 2: Show Task Tree Advanced Features
1. Click on different tasks to see their details
2. Highlight the input-output relationships
3. Explain how the tree handles dependencies
4. Demonstrate how execution adapts to the tree structure

## Key Discussion Points
1. How the plugin system enables heterogeneous agent frameworks to work together
2. How task handover enables complex workflows
3. How task trees facilitate hierarchical reasoning and execution
4. The flexibility of Cerebrum in supporting diverse AI use cases
