# Hierarchical Process

A comprehensive guide to understanding and applying the hierarchical process within your CrewAI projects, updated to reflect the latest coding practices and functionalities.

## 

[​

](https://docs.crewai.com/how-to/hierarchical-process#introduction)

Introduction

The hierarchical process in CrewAI introduces a structured approach to task management, simulating traditional organizational hierarchies for efficient task delegation and execution. This systematic workflow enhances project outcomes by ensuring tasks are handled with optimal efficiency and accuracy.

The hierarchical process is designed to leverage advanced models like GPT-4, optimizing token usage while handling complex tasks with greater efficiency.

## 

[​

](https://docs.crewai.com/how-to/hierarchical-process#hierarchical-process-overview)

Hierarchical Process Overview

By default, tasks in CrewAI are managed through a sequential process. However, adopting a hierarchical approach allows for a clear hierarchy in task management, where a ‘manager’ agent coordinates the workflow, delegates tasks, and validates outcomes for streamlined and effective execution. This manager agent can now be either automatically created by CrewAI or explicitly set by the user.

### 

[​

](https://docs.crewai.com/how-to/hierarchical-process#key-features)

Key Features

- **Task Delegation**: A manager agent allocates tasks among crew members based on their roles and capabilities.
- **Result Validation**: The manager evaluates outcomes to ensure they meet the required standards.
- **Efficient Workflow**: Emulates corporate structures, providing an organized approach to task management.
- **System Prompt Handling**: Optionally specify whether the system should use predefined prompts.
- **Stop Words Control**: Optionally specify whether stop words should be used, supporting various models including the o1 models.
- **Context Window Respect**: Prioritize important context by enabling respect of the context window, which is now the default behavior.
- **Delegation Control**: Delegation is now disabled by default to give users explicit control.
- **Max Requests Per Minute**: Configurable option to set the maximum number of requests per minute.
- **Max Iterations**: Limit the maximum number of iterations for obtaining a final answer.

## 

[​

](https://docs.crewai.com/how-to/hierarchical-process#implementing-the-hierarchical-process)

Implementing the Hierarchical Process

To utilize the hierarchical process, it’s essential to explicitly set the process attribute to `Process.hierarchical`, as the default behavior is `Process.sequential`. Define a crew with a designated manager and establish a clear chain of command.

Assign tools at the agent level to facilitate task delegation and execution by the designated agents under the manager’s guidance. Tools can also be specified at the task level for precise control over tool availability during task execution.

Configuring the `manager_llm` parameter is crucial for the hierarchical process. The system requires a manager LLM to be set up for proper function, ensuring tailored decision-making.

Code

Copy

```python
from langchain_openai import ChatOpenAI
from crewai import Crew, Process, Agent

# Agents are defined with attributes for backstory, cache, and verbose mode
researcher = Agent(
    role='Researcher',
    goal='Conduct in-depth analysis',
    backstory='Experienced data analyst with a knack for uncovering hidden trends.',
    cache=True,
    verbose=False,
    # tools=[]  # This can be optionally specified; defaults to an empty list
    use_system_prompt=True,  # Enable or disable system prompts for this agent
    max_rpm=30,  # Limit on the number of requests per minute
    max_iter=5  # Maximum number of iterations for a final answer
)
writer = Agent(
    role='Writer',
    goal='Create engaging content',
    backstory='Creative writer passionate about storytelling in technical domains.',
    cache=True,
    verbose=False,
    # tools=[]  # Optionally specify tools; defaults to an empty list
    use_system_prompt=True,  # Enable or disable system prompts for this agent
    max_rpm=30,  # Limit on the number of requests per minute
    max_iter=5  # Maximum number of iterations for a final answer
)

# Establishing the crew with a hierarchical process and additional configurations
project_crew = Crew(
    tasks=[...],  # Tasks to be delegated and executed under the manager's supervision
    agents=[researcher, writer],
    manager_llm=ChatOpenAI(temperature=0, model="gpt-4"),  # Mandatory if manager_agent is not set
    process=Process.hierarchical,  # Specifies the hierarchical management approach
    respect_context_window=True,  # Enable respect of the context window for tasks
    memory=True,  # Enable memory usage for enhanced task execution
    manager_agent=None,  # Optional: explicitly set a specific agent as manager instead of the manager_llm
    planning=True,  # Enable planning feature for pre-execution strategy
)
```

### 

[​

](https://docs.crewai.com/how-to/hierarchical-process#workflow-in-action)

Workflow in Action

1. **Task Assignment**: The manager assigns tasks strategically, considering each agent’s capabilities and available tools.
2. **Execution and Review**: Agents complete their tasks with the option for asynchronous execution and callback functions for streamlined workflows.
3. **Sequential Task Progression**: Despite being a hierarchical process, tasks follow a logical order for smooth progression, facilitated by the manager’s oversight.

## 

[​

](https://docs.crewai.com/how-to/hierarchical-process#conclusion)

Conclusion

Adopting the hierarchical process in CrewAI, with the correct configurations and understanding of the system’s capabilities, facilitates an organized and efficient approach to project management. Utilize the advanced features and customizations to tailor the workflow to your specific needs, ensuring optimal task execution and project success.


# Sequential Processes

A comprehensive guide to utilizing the sequential processes for task execution in CrewAI projects.

## 

[​

](https://docs.crewai.com/how-to/sequential-process#introduction)

Introduction

CrewAI offers a flexible framework for executing tasks in a structured manner, supporting both sequential and hierarchical processes. This guide outlines how to effectively implement these processes to ensure efficient task execution and project completion.

## 

[​

](https://docs.crewai.com/how-to/sequential-process#sequential-process-overview)

Sequential Process Overview

The sequential process ensures tasks are executed one after the other, following a linear progression. This approach is ideal for projects requiring tasks to be completed in a specific order.

### 

[​

](https://docs.crewai.com/how-to/sequential-process#key-features)

Key Features

- **Linear Task Flow**: Ensures orderly progression by handling tasks in a predetermined sequence.
- **Simplicity**: Best suited for projects with clear, step-by-step tasks.
- **Easy Monitoring**: Facilitates easy tracking of task completion and project progress.

## 

[​

](https://docs.crewai.com/how-to/sequential-process#implementing-the-sequential-process)

Implementing the Sequential Process

To use the sequential process, assemble your crew and define tasks in the order they need to be executed.

Code

Copy

```python
from crewai import Crew, Process, Agent, Task, TaskOutput, CrewOutput

# Define your agents
researcher = Agent(
  role='Researcher',
  goal='Conduct foundational research',
  backstory='An experienced researcher with a passion for uncovering insights'
)
analyst = Agent(
  role='Data Analyst',
  goal='Analyze research findings',
  backstory='A meticulous analyst with a knack for uncovering patterns'
)
writer = Agent(
  role='Writer',
  goal='Draft the final report',
  backstory='A skilled writer with a talent for crafting compelling narratives'
)

# Define your tasks
research_task = Task(
  description='Gather relevant data...', 
  agent=researcher, 
  expected_output='Raw Data'
)
analysis_task = Task(
  description='Analyze the data...', 
  agent=analyst, 
  expected_output='Data Insights'
)
writing_task = Task(
  description='Compose the report...', 
  agent=writer, 
  expected_output='Final Report'
)

# Form the crew with a sequential process
report_crew = Crew(
  agents=[researcher, analyst, writer],
  tasks=[research_task, analysis_task, writing_task],
  process=Process.sequential
)

# Execute the crew
result = report_crew.kickoff()

# Accessing the type-safe output
task_output: TaskOutput = result.tasks[0].output
crew_output: CrewOutput = result.output
```

### 

[​

](https://docs.crewai.com/how-to/sequential-process#note)

Note:

Each task in a sequential process **must** have an agent assigned. Ensure that every `Task` includes an `agent` parameter.

### 

[​

](https://docs.crewai.com/how-to/sequential-process#workflow-in-action)

Workflow in Action

1. **Initial Task**: In a sequential process, the first agent completes their task and signals completion.
2. **Subsequent Tasks**: Agents pick up their tasks based on the process type, with outcomes of preceding tasks or directives guiding their execution.
3. **Completion**: The process concludes once the final task is executed, leading to project completion.

## 

[​

](https://docs.crewai.com/how-to/sequential-process#advanced-features)

Advanced Features

### 

[​

](https://docs.crewai.com/how-to/sequential-process#task-delegation)

Task Delegation

In sequential processes, if an agent has `allow_delegation` set to `True`, they can delegate tasks to other agents in the crew. This feature is automatically set up when there are multiple agents in the crew.

### 

[​

](https://docs.crewai.com/how-to/sequential-process#asynchronous-execution)

Asynchronous Execution

Tasks can be executed asynchronously, allowing for parallel processing when appropriate. To create an asynchronous task, set `async_execution=True` when defining the task.

### 

[​

](https://docs.crewai.com/how-to/sequential-process#memory-and-caching)

Memory and Caching

CrewAI supports both memory and caching features:

- **Memory**: Enable by setting `memory=True` when creating the Crew. This allows agents to retain information across tasks.
- **Caching**: By default, caching is enabled. Set `cache=False` to disable it.

### 

[​

](https://docs.crewai.com/how-to/sequential-process#callbacks)

Callbacks

You can set callbacks at both the task and step level:

- `task_callback`: Executed after each task completion.
- `step_callback`: Executed after each step in an agent’s execution.

### 

[​

](https://docs.crewai.com/how-to/sequential-process#usage-metrics)

Usage Metrics

CrewAI tracks token usage across all tasks and agents. You can access these metrics after execution.

## 

[​

](https://docs.crewai.com/how-to/sequential-process#best-practices-for-sequential-processes)

Best Practices for Sequential Processes

1. **Order Matters**: Arrange tasks in a logical sequence where each task builds upon the previous one.
2. **Clear Task Descriptions**: Provide detailed descriptions for each task to guide the agents effectively.
3. **Appropriate Agent Selection**: Match agents’ skills and roles to the requirements of each task.
4. **Use Context**: Leverage the context from previous tasks to inform subsequent ones.

This updated documentation ensures that details accurately reflect the latest changes in the codebase and clearly describes how to leverage new features and configurations. The content is kept simple and direct to ensure easy understanding.