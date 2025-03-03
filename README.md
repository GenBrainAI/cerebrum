# Self-Aware Cerebrum

An AI framework with self-modification capabilities, designed to evolve and improve through a cognitive loop process.

## Overview

Self-Aware Cerebrum represents a new approach to AI framework development, one where the system grows and evolves through natural conversation. Rather than being constrained by traditional user interfaces and fixed capabilities, Cerebrum learns and adapts through dialogue with its users.

At its heart, Cerebrum is a self-modifying system that understands and responds to natural language. Users interact with it through simple conversation, describing what they want to achieve, and Cerebrum intelligently constructs and modifies its task structures to meet these needs.

## System Architecture

The Self-Aware Cerebrum consists of several key components:

### 1. AI Parameter Manager

The AI Parameter Manager optimizes and manages parameters for AI model interactions. It tracks performance metrics and learns optimal parameter settings for different types of tasks.

Key features:
- Parameter set management (create, update, delete)
- Performance tracking and analysis
- Automatic parameter optimization based on task type
- Parameter evolution with exploration/exploitation balance

### 2. Knowledge Integration System

The Knowledge Integration System manages different types of memory (semantic, episodic, procedural) and connects them through a knowledge graph.

Key features:
- Multiple memory types for different kinds of knowledge
- Knowledge graph for relationship tracking
- Context-aware knowledge retrieval
- Memory search and filtering capabilities

### 3. Development Cognitive Loop Orchestrator

The Development Cognitive Loop Orchestrator manages the system's self-improvement process through a four-phase cognitive cycle:

1. **Understand**: Analyze requirements and context
2. **Plan**: Create an implementation plan
3. **Execute**: Implement the plan
4. **Reflect**: Evaluate results and learn

Key features:
- Task management across cognitive phases
- Specialized workers for different phases
- Context tracking and management
- Continuous operation capabilities

### 4. Goal Decomposition Engine

The Goal Decomposition Engine breaks down high-level goals into manageable subgoals. It provides a structured approach to planning and executing complex tasks by decomposing them into smaller, more manageable pieces.

Key features:
- Goal decomposition using different strategies (TOP_DOWN, BOTTOM_UP, etc.)
- Resource estimation for subgoals and overall goals
- Subgoal prioritization based on dependencies, complexity, and risk
- Decomposition validation for completeness and consistency
- Knowledge integration for informed decomposition

### 5. Self-Aware Integration

The Self-Aware Integration combines all the components above into a cohesive system that can monitor its own performance, manage resources, execute tasks in parallel, and continuously improve through the cognitive loop process.

Key features:
- Integration of all core components
- Parallel task execution with resource awareness
- System access capabilities (package management, Git operations, testing)
- Observability and supervision mechanisms

For detailed documentation on the Self-Aware System, see [Self-Aware System Documentation](docs/self_aware_system.md).

## Getting Started

### Prerequisites

- Python 3.8+
- Required packages (install via `pip install -r requirements.txt`):
  - pydantic
  - networkx
  - streamlit
  - asyncio

### Installation

1. Clone the repository:
   ```
   git clone https://github.com/yourusername/cerebrum.git
   cd cerebrum
   ```

2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

### Running the System

#### Command Line Interface

The Self-Aware Cerebrum can be run from the command line:

```
python src/server/cli.py --help
```

Common commands:
- Start a cognitive cycle: `python src/server/cli.py cycle`
- Add semantic knowledge: `python src/server/cli.py add-semantic --concept "AI" --definition "Artificial Intelligence is the simulation of human intelligence by machines."`
- Create a task: `python src/server/cli.py create-task --title "Improve Knowledge System" --description "Enhance the knowledge retrieval capabilities" --phase understand`
- Get knowledge context: `python src/server/cli.py context --query "cognitive loop"`
- Decompose a goal: `python src/server/cli.py goal decompose --name "Implement Feature X" --description "Implement a new feature X for the system" --type DEVELOPMENT`

#### Streamlit UI

For a more user-friendly interface, run the Streamlit app:

```
streamlit run src/server/streamlit_app.py
```

The Streamlit UI provides:
- System dashboard with status and controls
- Task management interface
- Knowledge management tools
- Development context management
- Goal decomposition and management

## System Components in Detail

### AI Parameter Manager

The AI Parameter Manager maintains sets of parameters for AI model interactions and tracks their performance. It can:

- Create, update, and retrieve parameter sets
- Record performance metrics for task executions
- Analyze parameter impact on performance
- Evolve parameters based on performance history
- Provide optimal parameters for specific task types

### Knowledge Integration System

The Knowledge Integration System manages three types of memory:

1. **Semantic Memory**: Factual knowledge about concepts, entities, and their relationships
2. **Episodic Memory**: Memory of specific events, experiences, or interactions
3. **Procedural Memory**: Knowledge about how to perform tasks or processes

These memory types are connected through a knowledge graph that tracks relationships between knowledge items.

### Development Cognitive Loop Orchestrator

The Development Cognitive Loop Orchestrator manages the system's self-improvement process through a four-phase cognitive cycle:

1. **Understand Phase**: Analyze requirements and context
   - Worker: RequirementsWorker
   - Tasks: Requirement analysis, context gathering

2. **Plan Phase**: Create an implementation plan
   - Worker: PlanningWorker
   - Tasks: Solution design, task breakdown

3. **Execute Phase**: Implement the plan
   - Worker: ImplementationWorker
   - Tasks: Code generation, integration

4. **Reflect Phase**: Evaluate results and learn
   - Worker: EvaluationWorker
   - Tasks: Testing, performance analysis, knowledge update

### Goal Decomposition Engine

The Goal Decomposition Engine breaks down high-level goals into manageable subgoals. It supports:

1. **Goal Types**: Different types of goals (GENERAL, RESEARCH, DEVELOPMENT, etc.)
2. **Decomposition Strategies**: Various strategies for decomposing goals (TOP_DOWN, BOTTOM_UP, etc.)
3. **Resource Estimation**: Estimation of time, complexity, knowledge requirements, and risk
4. **Subgoal Prioritization**: Prioritization of subgoals based on various factors
5. **Decomposition Validation**: Validation of decompositions for completeness and consistency

The Goal Decomposition Engine can be accessed through both the CLI and Streamlit UI. For more information, see the [Goal Decomposition Engine documentation](docs/planning/goal_decomposition.md).

## Contributing

Contributions to the Self-Aware Cerebrum are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- The Cerebrum project is inspired by research in cognitive architectures and self-modifying systems.
- Special thanks to all contributors and researchers in the field of artificial general intelligence.

## Vector Store Setup

The Cerebrum system uses a vector store to index the codebase for semantic search. This vector store is not included in the repository to avoid committing large binary files to git.

After cloning the repository, you need to set up the vector store by running the following command:

```bash
# Set up the vector store
python scripts/setup_vector_store.py
```

This script will index the codebase and create the necessary vector store files in the `persistent_state/cerebrum_system/chroma_db` directory.

You can also specify a different codebase root directory and base path:

```bash
# Set up the vector store with custom paths
python scripts/setup_vector_store.py --codebase-root /path/to/codebase --base-path /path/to/base
```

For incremental indexing (only index files that have changed):

```bash
# Perform incremental indexing
python scripts/setup_vector_store.py --incremental
```
