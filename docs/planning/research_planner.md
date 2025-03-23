# Research Planner

The Research Planner is a self-aware component that identifies knowledge gaps, creates structured research plans, and prioritizes research tasks. It enables the system to effectively expand its knowledge in areas where it detects limitations.

## Core Components

### Knowledge Gap Identification

The Research Planner analyzes the system's knowledge about specific topics and identifies areas where:

1. Information is missing or incomplete
2. Existing knowledge has low confidence 
3. Conflicting information exists
4. Relationships between concepts are unclear

Knowledge gaps are represented by the `KnowledgeGap` class, which includes:
- Topic
- Description
- Confidence level (0.0-1.0)
- Importance rating (1-10)
- Information sources
- Related knowledge gaps

### Research Plan Creation

Once knowledge gaps are identified, the Research Planner creates a comprehensive `ResearchPlan` that includes:

- Title and description
- Collection of knowledge gaps to address
- Set of structured research tasks
- Estimated time requirements
- Task dependencies and sequencing
- Current status tracking

### Task Management

Research tasks are represented by the `ResearchTask` class, which includes:

- Title and description
- Research strategy type (Exploratory, Targeted, Comparative, Systematic)
- Estimated time requirements
- Associated knowledge gaps
- Priority level
- Information sources
- Dependencies
- Status tracking

The planner intelligently prioritizes tasks based on:
- Dependencies between tasks
- Importance of knowledge gaps
- Estimated confidence gain
- Resource efficiency

## Usage

### Initializing the Research Planner

```python
from src.server.planning.research_planner import ResearchPlanner
from src.server.knowledge.knowledge_integration import KnowledgeIntegration

# Initialize the knowledge system
knowledge_system = KnowledgeIntegration()

# Initialize the research planner with a storage directory
research_planner = ResearchPlanner(
    knowledge_system=knowledge_system,
    storage_dir="./storage/research_plans"
)
```

### Identifying Knowledge Gaps

```python
# Identify knowledge gaps about a specific topic
knowledge_gaps = await research_planner.identify_knowledge_gaps("Machine Learning")

# Display the identified gaps
for gap_id, gap in knowledge_gaps.items():
    print(f"Gap: {gap.topic} - {gap.description}")
    print(f"Confidence: {gap.confidence}, Importance: {gap.importance}")
```

### Creating Research Plans

```python
# Create a research plan from the identified gaps
plan = await research_planner.create_research_plan(
    title="Machine Learning Research",
    description="Comprehensive research plan for ML concepts",
    knowledge_gaps=knowledge_gaps
)

# Save the plan
await research_planner.save_research_plan(plan)
```

### Managing Research Tasks

```python
# Get a specific research plan
plan = await research_planner.get_research_plan(plan_id)

# Prioritize tasks
prioritized_tasks = await research_planner.prioritize_research_tasks(
    plan_id=plan.id,
    task_ids=list(plan.tasks.keys())
)

# Update task status
await research_planner.update_research_task(
    plan_id=plan.id,
    task_id=task_id,
    status="completed" 
)
```

## Integration with UI Components

The Research Planner includes a Streamlit UI component (`ResearchPlannerView`) that provides:

1. Knowledge gap visualization and analysis
2. Research plan creation and management
3. Task dashboard for monitoring and updating tasks
4. Progress tracking and reporting

```python
from src.server.ui.research_planner_view import ResearchPlannerView

# Create the UI component
planner_view = ResearchPlannerView(
    research_planner=research_planner,
    knowledge_system=knowledge_system
)

# Render the UI
planner_view.render()
```

## Integration with Goal Decomposition

The Research Planner works seamlessly with the Goal Decomposition Engine:

1. The Goal Decomposition Engine breaks down complex goals into manageable subgoals
2. Each subgoal can be analyzed by the Research Planner to identify knowledge gaps
3. Research plans can be created to address these gaps
4. The acquired knowledge can be integrated back into the system

Example workflow:

```python
from src.server.planning.goal_decomposition import GoalDecompositionEngine

# Initialize the goal engine
goal_engine = GoalDecompositionEngine(knowledge_system=knowledge_system)

# Decompose a high-level goal
goal_tree = await goal_engine.decompose_goal("Understand machine learning applications in healthcare")

# Extract subgoals
subgoals = [node.title for node in goal_tree.nodes.values() if node.node_type == "subgoal"]

# For each subgoal, identify knowledge gaps and create research plans
for subgoal in subgoals:
    gaps = await research_planner.identify_knowledge_gaps(subgoal)
    
    if gaps:
        plan = await research_planner.create_research_plan(
            title=f"Research: {subgoal}",
            description=f"Research plan for {subgoal}",
            knowledge_gaps=gaps
        )
        
        await research_planner.save_research_plan(plan)
```

## Technical Details

### Data Structures

The Research Planner uses several key data structures:

1. **KnowledgeGap**: Represents a gap in knowledge
2. **ResearchTask**: Represents a specific research activity
3. **ResearchPlan**: Encapsulates a complete research plan
4. **ResearchStrategyType**: Enum of research approaches

### Persistence

Research plans are serialized and stored as JSON files in the specified storage directory. The Research Planner provides methods to:

- Save research plans
- List all available plans
- Load specific plans
- Delete plans

### Async Support

All primary methods are implemented as async coroutines, allowing for:

- Non-blocking operations
- Integration with other async components
- Scalable performance

## Best Practices

When using the Research Planner:

1. **Be specific with topics**: More specific topics yield more focused knowledge gaps
2. **Analyze comprehensively**: Consider examining multiple related topics
3. **Prioritize regularly**: Re-prioritize tasks as new information becomes available
4. **Track progress**: Update task status to maintain accurate plan state
5. **Review outcomes**: After completing research tasks, re-evaluate knowledge gaps

## Future Enhancements

Planned enhancements for the Research Planner include:

1. Integration with external knowledge sources
2. Automated execution of research tasks
3. Machine learning for improved gap identification
4. Knowledge integration automation
5. Enhanced visualization of knowledge networks
6. Collaborative research planning 