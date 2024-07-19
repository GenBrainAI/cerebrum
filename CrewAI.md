Agents
What is an Agent?¶
What is an Agent?

An agent is an autonomous unit programmed to:

Perform tasks
Make decisions
Communicate with other agents

Think of an agent as a member of a team, with specific skills and a particular job to do. Agents can have different roles like 'Researcher', 'Writer', or 'Customer Support', each contributing to the overall goal of the crew.
Agent Attributes¶
Attribute	Parameter	Description
Role	role	Defines the agent's function within the crew. It determines the kind of tasks the agent is best suited for.
Goal	goal	The individual objective that the agent aims to achieve. It guides the agent's decision-making process.
Backstory	backstory	Provides context to the agent's role and goal, enriching the interaction and collaboration dynamics.
LLM (optional)	llm	Represents the language model that will run the agent. It dynamically fetches the model name from the OPENAI_MODEL_NAME environment variable, defaulting to "gpt-4" if not specified.
Tools (optional)	tools	Set of capabilities or functions that the agent can use to perform tasks. Expected to be instances of custom classes compatible with the agent's execution environment. Tools are initialized with a default value of an empty list.
Function Calling LLM (optional)	function_calling_llm	Specifies the language model that will handle the tool calling for this agent, overriding the crew function calling LLM if passed. Default is None.
Max Iter (optional)	max_iter	Max Iter is the maximum number of iterations the agent can perform before being forced to give its best answer. Default is 25.
Max RPM (optional)	max_rpm	Max RPM is the maximum number of requests per minute the agent can perform to avoid rate limits. It's optional and can be left unspecified, with a default value of None.
Max Execution Time (optional)	max_execution_time	Max Execution Time is the Maximum execution time for an agent to execute a task. It's optional and can be left unspecified, with a default value of None, meaning no max execution time.
Verbose (optional)	verbose	Setting this to True configures the internal logger to provide detailed execution logs, aiding in debugging and monitoring. Default is False.
Allow Delegation (optional)	allow_delegation	Agents can delegate tasks or questions to one another, ensuring that each task is handled by the most suitable agent. Default is True.
Step Callback (optional)	step_callback	A function that is called after each step of the agent. This can be used to log the agent's actions or to perform other operations. It will overwrite the crew step_callback.
Cache (optional)	cache	Indicates if the agent should use a cache for tool usage. Default is True.
System Template (optional)	system_template	Specifies the system format for the agent. Default is None.
Prompt Template (optional)	prompt_template	Specifies the prompt format for the agent. Default is None.
Response Template (optional)	response_template	Specifies the response format for the agent. Default is None.
Creating an Agent¶
Agent Interaction

Agents can interact with each other using crewAI's built-in delegation and communication mechanisms. This allows for dynamic task management and problem-solving within the crew.

To create an agent, you would typically initialize an instance of the Agent class with the desired properties. Here's a conceptual example including all attributes:


# Example: Creating an agent with all attributes
from crewai import Agent

agent = Agent(
  role='Data Analyst',
  goal='Extract actionable insights',
  backstory="""You're a data analyst at a large company.
  You're responsible for analyzing data and providing insights
  to the business.
  You're currently working on a project to analyze the
  performance of our marketing campaigns.""",
  tools=[my_tool1, my_tool2],  # Optional, defaults to an empty list
  llm=my_llm,  # Optional
  function_calling_llm=my_llm,  # Optional
  max_iter=15,  # Optional
  max_rpm=None, # Optional
  max_execution_time=None, # Optional
  verbose=True,  # Optional
  allow_delegation=True,  # Optional
  step_callback=my_intermediate_step_callback,  # Optional
  cache=True,  # Optional
  system_template=my_system_template,  # Optional
  prompt_template=my_prompt_template,  # Optional
  response_template=my_response_template,  # Optional
  config=my_config,  # Optional
  crew=my_crew,  # Optional
  tools_handler=my_tools_handler,  # Optional
  cache_handler=my_cache_handler,  # Optional
  callbacks=[callback1, callback2],  # Optional
  agent_executor=my_agent_executor  # Optional
)
Setting prompt templates¶
Prompt templates are used to format the prompt for the agent. You can use to update the system, regular and response templates for the agent. Here's an example of how to set prompt templates:


agent = Agent(
        role="{topic} specialist",
        goal="Figure {goal} out",
        backstory="I am the master of {role}",
        system_template="""<|start_header_id|>system<|end_header_id|>

{{ .System }}<|eot_id|>""",
        prompt_template="""<|start_header_id|>user<|end_header_id|>

{{ .Prompt }}<|eot_id|>""",
        response_template="""<|start_header_id|>assistant<|end_header_id|>

{{ .Response }}<|eot_id|>""",
    )
Bring your Third Party Agents¶
Extend your Third Party Agents like LlamaIndex, Langchain, Autogen or fully custom agents using the the crewai's BaseAgent class.

BaseAgent includes attributes and methods required to integrate with your crews to run and delegate tasks to other agents within your own crew.

CrewAI is a universal multi agent framework that allows for all agents to work together to automate tasks and solve problems.


from crewai import Agent, Task, Crew
from custom_agent import CustomAgent # You need to build and extend your own agent logic with the CrewAI BaseAgent class then import it here.

from langchain.agents import load_tools

langchain_tools = load_tools(["google-serper"], llm=llm)

agent1 = CustomAgent(
    role="backstory agent",
    goal="who is {input}?",
    backstory="agent backstory",
    verbose=True,
)

task1 = Task(
    expected_output="a short biography of {input}",
    description="a short biography of {input}",
    agent=agent1,
)

agent2 = Agent(
    role="bio agent",
    goal="summarize the short bio for {input} and if needed do more research",
    backstory="agent backstory",
    verbose=True,
)

task2 = Task(
    description="a tldr summary of the short biography",
    expected_output="5 bullet point summary of the biography",
    agent=agent2,
    context=[task1],
)

my_crew = Crew(agents=[agent1, agent2], tasks=[task1, task2])
crew = my_crew.kickoff(inputs={"input": "Mark Twain"})
Conclusion¶
Agents are the building blocks of the CrewAI framework. By understanding how to define and interact with agents, you can create sophisticated AI systems that leverage the power of collaborative intelligence.


Tasks
Overview of a Task¶
What is a Task?

In the crewAI framework, tasks are specific assignments completed by agents. They provide all necessary details for execution, such as a description, the agent responsible, required tools, and more, facilitating a wide range of action complexities.

Tasks within crewAI can be collaborative, requiring multiple agents to work together. This is managed through the task properties and orchestrated by the Crew's process, enhancing teamwork and efficiency.

Task Attributes¶
Attribute	Parameters	Description
Description	description	A clear, concise statement of what the task entails.
Agent	agent	The agent responsible for the task, assigned either directly or by the crew's process.
Expected Output	expected_output	A detailed description of what the task's completion looks like.
Tools (optional)	tools	The functions or capabilities the agent can utilize to perform the task.
Async Execution (optional)	async_execution	If set, the task executes asynchronously, allowing progression without waiting for completion.
Context (optional)	context	Specifies tasks whose outputs are used as context for this task.
Config (optional)	config	Additional configuration details for the agent executing the task, allowing further customization.
Output JSON (optional)	output_json	Outputs a JSON object, requiring an OpenAI client. Only one output format can be set.
Output Pydantic (optional)	output_pydantic	Outputs a Pydantic model object, requiring an OpenAI client. Only one output format can be set.
Output File (optional)	output_file	Saves the task output to a file. If used with Output JSON or Output Pydantic, specifies how the output is saved.
Callback (optional)	callback	A Python callable that is executed with the task's output upon completion.
Human Input (optional)	human_input	Indicates if the task requires human feedback at the end, useful for tasks needing human oversight.
Creating a Task¶
Creating a task involves defining its scope, responsible agent, and any additional attributes for flexibility:


from crewai import Task

task = Task(
    description='Find and summarize the latest and most relevant news on AI',
    agent=sales_agent
)
Task Assignment

Directly specify an agent for assignment or let the hierarchical CrewAI's process decide based on roles, availability, etc.

Integrating Tools with Tasks¶
Leverage tools from the crewAI Toolkit and LangChain Tools for enhanced task performance and agent interaction.

Creating a Task with Tools¶

import os
os.environ["OPENAI_API_KEY"] = "Your Key"
os.environ["SERPER_API_KEY"] = "Your Key" # serper.dev API key

from crewai import Agent, Task, Crew
from crewai_tools import SerperDevTool

research_agent = Agent(
  role='Researcher',
  goal='Find and summarize the latest AI news',
  backstory="""You're a researcher at a large company.
  You're responsible for analyzing data and providing insights
  to the business.""",
  verbose=True
)

search_tool = SerperDevTool()

task = Task(
  description='Find and summarize the latest AI news',
  expected_output='A bullet list summary of the top 5 most important AI news',
  agent=research_agent,
  tools=[search_tool]
)

crew = Crew(
    agents=[research_agent],
    tasks=[task],
    verbose=2
)

result = crew.kickoff()
print(result)
This demonstrates how tasks with specific tools can override an agent's default set for tailored task execution.

Referring to Other Tasks¶
In crewAI, the output of one task is automatically relayed into the next one, but you can specifically define what tasks' output, including multiple, should be used as context for another task.

This is useful when you have a task that depends on the output of another task that is not performed immediately after it. This is done through the context attribute of the task:


# ...

research_ai_task = Task(
    description='Find and summarize the latest AI news',
    expected_output='A bullet list summary of the top 5 most important AI news',
    async_execution=True,
    agent=research_agent,
    tools=[search_tool]
)

research_ops_task = Task(
    description='Find and summarize the latest AI Ops news',
    expected_output='A bullet list summary of the top 5 most important AI Ops news',
    async_execution=True,
    agent=research_agent,
    tools=[search_tool]
)

write_blog_task = Task(
    description="Write a full blog post about the importance of AI and its latest news",
    expected_output='Full blog post that is 4 paragraphs long',
    agent=writer_agent,
    context=[research_ai_task, research_ops_task]
)

#...
Asynchronous Execution¶
You can define a task to be executed asynchronously. This means that the crew will not wait for it to be completed to continue with the next task. This is useful for tasks that take a long time to be completed, or that are not crucial for the next tasks to be performed.

You can then use the context attribute to define in a future task that it should wait for the output of the asynchronous task to be completed.


#...

list_ideas = Task(
    description="List of 5 interesting ideas to explore for an article about AI.",
    expected_output="Bullet point list of 5 ideas for an article.",
    agent=researcher,
    async_execution=True # Will be executed asynchronously
)

list_important_history = Task(
    description="Research the history of AI and give me the 5 most important events.",
    expected_output="Bullet point list of 5 important events.",
    agent=researcher,
    async_execution=True # Will be executed asynchronously
)

write_article = Task(
    description="Write an article about AI, its history, and interesting ideas.",
    expected_output="A 4 paragraph article about AI.",
    agent=writer,
    context=[list_ideas, list_important_history] # Will wait for the output of the two tasks to be completed
)

#...
Callback Mechanism¶
The callback function is executed after the task is completed, allowing for actions or notifications to be triggered based on the task's outcome.


# ...

def callback_function(output: TaskOutput):
    # Do something after the task is completed
    # Example: Send an email to the manager
    print(f"""
        Task completed!
        Task: {output.description}
        Output: {output.raw_output}
    """)

research_task = Task(
    description='Find and summarize the latest AI news',
    expected_output='A bullet list summary of the top 5 most important AI news',
    agent=research_agent,
    tools=[search_tool],
    callback=callback_function
)

#...
Accessing a Specific Task Output¶
Once a crew finishes running, you can access the output of a specific task by using the output attribute of the task object:


# ...
task1 = Task(
    description='Find and summarize the latest AI news',
    expected_output='A bullet list summary of the top 5 most important AI news',
    agent=research_agent,
    tools=[search_tool]
)

#...

crew = Crew(
    agents=[research_agent],
    tasks=[task1, task2, task3],
    verbose=2
)

result = crew.kickoff()

# Returns a TaskOutput object with the description and results of the task
print(f"""
    Task completed!
    Task: {task1.output.description}
    Output: {task1.output.raw_output}
""")
Tool Override Mechanism¶
Specifying tools in a task allows for dynamic adaptation of agent capabilities, emphasizing CrewAI's flexibility.

Error Handling and Validation Mechanisms¶
While creating and executing tasks, certain validation mechanisms are in place to ensure the robustness and reliability of task attributes. These include but are not limited to:

Ensuring only one output type is set per task to maintain clear output expectations.
Preventing the manual assignment of the id attribute to uphold the integrity of the unique identifier system.
These validations help in maintaining the consistency and reliability of task executions within the crewAI framework.

Creating Directories when Saving Files¶
You can now specify if a task should create directories when saving its output to a file. This is particularly useful for organizing outputs and ensuring that file paths are correctly structured.


# ...

save_output_task = Task(
    description='Save the summarized AI news to a file',
    expected_output='File saved successfully',
    agent=research_agent,
    tools=[file_save_tool],
    output_file='outputs/ai_news_summary.txt',
    create_directory=True
)

#...
Conclusion¶
Tasks are the driving force behind the actions of agents in crewAI. By properly defining tasks and their outcomes, you set the stage for your AI agents to work effectively, either independently or as a collaborative unit. Equipping tasks with appropriate tools, understanding the execution process, and following robust validation practices are crucial for maximizing CrewAI's potential, ensuring agents are effectively prepared for their assignments and that tasks are executed as intended.

Tools
Introduction¶
CrewAI tools empower agents with capabilities ranging from web searching and data analysis to collaboration and delegating tasks among coworkers. This documentation outlines how to create, integrate, and leverage these tools within the CrewAI framework, including a new focus on collaboration tools.

What is a Tool?¶
Definition

A tool in CrewAI is a skill or function that agents can utilize to perform various actions. This includes tools from the crewAI Toolkit and LangChain Tools, enabling everything from simple searches to complex interactions and effective teamwork among agents.

Key Characteristics of Tools¶
Utility: Crafted for tasks such as web searching, data analysis, content generation, and agent collaboration.
Integration: Boosts agent capabilities by seamlessly integrating tools into their workflow.
Customizability: Provides the flexibility to develop custom tools or utilize existing ones, catering to the specific needs of agents.
Error Handling: Incorporates robust error handling mechanisms to ensure smooth operation.
Caching Mechanism: Features intelligent caching to optimize performance and reduce redundant operations.
Using crewAI Tools¶
To enhance your agents' capabilities with crewAI tools, begin by installing our extra tools package:


pip install 'crewai[tools]'
Here's an example demonstrating their use:


import os
from crewai import Agent, Task, Crew
# Importing crewAI tools
from crewai_tools import (
    DirectoryReadTool,
    FileReadTool,
    SerperDevTool,
    WebsiteSearchTool
)

# Set up API keys
os.environ["SERPER_API_KEY"] = "Your Key" # serper.dev API key
os.environ["OPENAI_API_KEY"] = "Your Key"

# Instantiate tools
docs_tool = DirectoryReadTool(directory='./blog-posts')
file_tool = FileReadTool()
search_tool = SerperDevTool()
web_rag_tool = WebsiteSearchTool()

# Create agents
researcher = Agent(
    role='Market Research Analyst',
    goal='Provide up-to-date market analysis of the AI industry',
    backstory='An expert analyst with a keen eye for market trends.',
    tools=[search_tool, web_rag_tool],
    verbose=True
)

writer = Agent(
    role='Content Writer',
    goal='Craft engaging blog posts about the AI industry',
    backstory='A skilled writer with a passion for technology.',
    tools=[docs_tool, file_tool],
    verbose=True
)

# Define tasks
research = Task(
    description='Research the latest trends in the AI industry and provide a summary.',
    expected_output='A summary of the top 3 trending developments in the AI industry with a unique perspective on their significance.',
    agent=researcher
)

write = Task(
    description='Write an engaging blog post about the AI industry, based on the research analyst’s summary. Draw inspiration from the latest blog posts in the directory.',
    expected_output='A 4-paragraph blog post formatted in markdown with engaging, informative, and accessible content, avoiding complex jargon.',
    agent=writer,
    output_file='blog-posts/new_post.md'  # The final blog post will be saved here
)

# Assemble a crew
crew = Crew(
    agents=[researcher, writer],
    tasks=[research, write],
    verbose=2
)

# Execute tasks
crew.kickoff()
Available crewAI Tools¶
Error Handling: All tools are built with error handling capabilities, allowing agents to gracefully manage exceptions and continue their tasks.
Caching Mechanism: All tools support caching, enabling agents to efficiently reuse previously obtained results, reducing the load on external resources and speeding up the execution time. You can also define finer control over the caching mechanism using the cache_function attribute on the tool.
Here is a list of the available tools and their descriptions:

Tool	Description
CodeDocsSearchTool	A RAG tool optimized for searching through code documentation and related technical documents.
CSVSearchTool	A RAG tool designed for searching within CSV files, tailored to handle structured data.
DirectorySearchTool	A RAG tool for searching within directories, useful for navigating through file systems.
DOCXSearchTool	A RAG tool aimed at searching within DOCX documents, ideal for processing Word files.
DirectoryReadTool	Facilitates reading and processing of directory structures and their contents.
FileReadTool	Enables reading and extracting data from files, supporting various file formats.
GithubSearchTool	A RAG tool for searching within GitHub repositories, useful for code and documentation search.
SerperDevTool	A specialized tool for development purposes, with specific functionalities under development.
TXTSearchTool	A RAG tool focused on searching within text (.txt) files, suitable for unstructured data.
JSONSearchTool	A RAG tool designed for searching within JSON files, catering to structured data handling.
MDXSearchTool	A RAG tool tailored for searching within Markdown (MDX) files, useful for documentation.
PDFSearchTool	A RAG tool aimed at searching within PDF documents, ideal for processing scanned documents.
PGSearchTool	A RAG tool optimized for searching within PostgreSQL databases, suitable for database queries.
RagTool	A general-purpose RAG tool capable of handling various data sources and types.
ScrapeElementFromWebsiteTool	Enables scraping specific elements from websites, useful for targeted data extraction.
ScrapeWebsiteTool	Facilitates scraping entire websites, ideal for comprehensive data collection.
WebsiteSearchTool	A RAG tool for searching website content, optimized for web data extraction.
XMLSearchTool	A RAG tool designed for searching within XML files, suitable for structured data formats.
YoutubeChannelSearchTool	A RAG tool for searching within YouTube channels, useful for video content analysis.
YoutubeVideoSearchTool	A RAG tool aimed at searching within YouTube videos, ideal for video data extraction.
BrowserbaseTool	A tool for interacting with and extracting data from web browsers.
ExaSearchTool	A tool designed for performing exhaustive searches across various data sources.
Creating your own Tools¶
Custom Tool Creation

Developers can craft custom tools tailored for their agent’s needs or utilize pre-built options:

To create your own crewAI tools you will need to install our extra tools package:


pip install 'crewai[tools]'
Once you do that there are two main ways for one to create a crewAI tool:

Subclassing BaseTool¶

from crewai_tools import BaseTool

class MyCustomTool(BaseTool):
    name: str = "Name of my tool"
    description: str = "Clear description for what this tool is useful for, your agent will need this information to use it."

    def _run(self, argument: str) -> str:
        # Implementation goes here
        return "Result from custom tool"
Utilizing the tool Decorator¶

from crewai_tools import tool
@tool("Name of my tool")
def my_tool(question: str) -> str:
    """Clear description for what this tool is useful for, your agent will need this information to use it."""
    # Function logic here
    return "Result from your custom tool"
Custom Caching Mechanism¶
Caching

Tools can optionally implement a cache_function to fine-tune caching behavior. This function determines when to cache results based on specific conditions, offering granular control over caching logic.


from crewai_tools import tool

@tool
def multiplication_tool(first_number: int, second_number: int) -> str:
    """Useful for when you need to multiply two numbers together."""
    return first_number * second_number

def cache_func(args, result):
    # In this case, we only cache the result if it's a multiple of 2
    cache = result % 2 == 0
    return cache

multiplication_tool.cache_function = cache_func

writer1 = Agent(
        role="Writer",
        goal="You write lessons of math for kids.",
        backstory="You're an expert in writing and you love to teach kids but you know nothing of math.",
        tools=[multiplication_tool],
        allow_delegation=False,
    )
    #...
Conclusion¶
Tools are pivotal in extending the capabilities of CrewAI agents, enabling them to undertake a broad spectrum of tasks and collaborate effectively. When building solutions with CrewAI, leverage both custom and existing tools to empower your agents and enhance the AI ecosystem. Consider utilizing error handling, caching mechanisms, and the flexibility of tool arguments to optimize your agents' performance and capabilities.

Processes
Understanding Processes¶
Core Concept

In CrewAI, processes orchestrate the execution of tasks by agents, akin to project management in human teams. These processes ensure tasks are distributed and executed efficiently, in alignment with a predefined strategy.

Process Implementations¶
Sequential: Executes tasks sequentially, ensuring tasks are completed in an orderly progression.
Hierarchical: Organizes tasks in a managerial hierarchy, where tasks are delegated and executed based on a structured chain of command. A manager language model (manager_llm) or a custom manager agent (manager_agent) must be specified in the crew to enable the hierarchical process, facilitating the creation and management of tasks by the manager.
Consensual Process (Planned): Aiming for collaborative decision-making among agents on task execution, this process type introduces a democratic approach to task management within CrewAI. It is planned for future development and is not currently implemented in the codebase.
The Role of Processes in Teamwork¶
Processes enable individual agents to operate as a cohesive unit, streamlining their efforts to achieve common objectives with efficiency and coherence.

Assigning Processes to a Crew¶
To assign a process to a crew, specify the process type upon crew creation to set the execution strategy. For a hierarchical process, ensure to define manager_llm or manager_agent for the manager agent.


from crewai import Crew
from crewai.process import Process
from langchain_openai import ChatOpenAI

# Example: Creating a crew with a sequential process
crew = Crew(
    agents=my_agents,
    tasks=my_tasks,
    process=Process.sequential
)

# Example: Creating a crew with a hierarchical process
# Ensure to provide a manager_llm or manager_agent
crew = Crew(
    agents=my_agents,
    tasks=my_tasks,
    process=Process.hierarchical,
    manager_llm=ChatOpenAI(model="gpt-4")
    # or
    # manager_agent=my_manager_agent
)
Note: Ensure my_agents and my_tasks are defined prior to creating a Crew object, and for the hierarchical process, either manager_llm or manager_agent is also required.
Sequential Process¶
This method mirrors dynamic team workflows, progressing through tasks in a thoughtful and systematic manner. Task execution follows the predefined order in the task list, with the output of one task serving as context for the next.

To customize task context, utilize the context parameter in the Task class to specify outputs that should be used as context for subsequent tasks.

Hierarchical Process¶
Emulates a corporate hierarchy, CrewAI allows specifying a custom manager agent or automatically creates one, requiring the specification of a manager language model (manager_llm). This agent oversees task execution, including planning, delegation, and validation. Tasks are not pre-assigned; the manager allocates tasks to agents based on their capabilities, reviews outputs, and assesses task completion.

Process Class: Detailed Overview¶
The Process class is implemented as an enumeration (Enum), ensuring type safety and restricting process values to the defined types (sequential, hierarchical). The consensual process is planned for future inclusion, emphasizing our commitment to continuous development and innovation.

Additional Task Features¶
Asynchronous Execution: Tasks can now be executed asynchronously, allowing for parallel processing and efficiency improvements. This feature is designed to enable tasks to be carried out concurrently, enhancing the overall productivity of the crew.
Human Input Review: An optional feature that enables the review of task outputs by humans to ensure quality and accuracy before finalization. This additional step introduces a layer of oversight, providing an opportunity for human intervention and validation.
Output Customization: Tasks support various output formats, including JSON (output_json), Pydantic models (output_pydantic), and file outputs (output_file), providing flexibility in how task results are captured and utilized. This allows for a wide range of output possibilities, catering to different needs and requirements.
Conclusion¶
The structured collaboration facilitated by processes within CrewAI is crucial for enabling systematic teamwork among agents. This documentation has been updated to reflect the latest features, enhancements, and the planned integration of the Consensual Process, ensuring users have access to the most current and comprehensive information.

Previous
Tools

Crews
What is a Crew?¶
A crew in crewAI represents a collaborative group of agents working together to achieve a set of tasks. Each crew defines the strategy for task execution, agent collaboration, and the overall workflow.

Crew Attributes¶
Attribute	Parameters	Description
Tasks	tasks	A list of tasks assigned to the crew.
Agents	agents	A list of agents that are part of the crew.
Process (optional)	process	The process flow (e.g., sequential, hierarchical) the crew follows.
Verbose (optional)	verbose	The verbosity level for logging during execution.
Manager LLM (optional)	manager_llm	The language model used by the manager agent in a hierarchical process. Required when using a hierarchical process.
Function Calling LLM (optional)	function_calling_llm	If passed, the crew will use this LLM to do function calling for tools for all agents in the crew. Each agent can have its own LLM, which overrides the crew's LLM for function calling.
Config (optional)	config	Optional configuration settings for the crew, in Json or Dict[str, Any] format.
Max RPM (optional)	max_rpm	Maximum requests per minute the crew adheres to during execution.
Language (optional)	language	Language used for the crew, defaults to English.
Language File (optional)	language_file	Path to the language file to be used for the crew.
Memory (optional)	memory	Utilized for storing execution memories (short-term, long-term, entity memory).
Cache (optional)	cache	Specifies whether to use a cache for storing the results of tools' execution.
Embedder (optional)	embedder	Configuration for the embedder to be used by the crew. Mostly used by memory for now.
Full Output (optional)	full_output	Whether the crew should return the full output with all tasks outputs or just the final output.
Step Callback (optional)	step_callback	A function that is called after each step of every agent. This can be used to log the agent's actions or to perform other operations; it won't override the agent-specific step_callback.
Task Callback (optional)	task_callback	A function that is called after the completion of each task. Useful for monitoring or additional operations post-task execution.
Share Crew (optional)	share_crew	Whether you want to share the complete crew information and execution with the crewAI team to make the library better, and allow us to train models.
Output Log File (optional)	output_log_file	Whether you want to have a file with the complete crew output and execution. You can set it using True and it will default to the folder you are currently in and it will be called logs.txt or passing a string with the full path and name of the file.
Manager Agent (optional)	manager_agent	manager sets a custom agent that will be used as a manager.
Manager Callbacks (optional)	manager_callbacks	manager_callbacks takes a list of callback handlers to be executed by the manager agent when a hierarchical process is used.
Prompt File (optional)	prompt_file	Path to the prompt JSON file to be used for the crew.
Crew Max RPM

The max_rpm attribute sets the maximum number of requests per minute the crew can perform to avoid rate limits and will override individual agents' max_rpm settings if you set it.

Creating a Crew¶
When assembling a crew, you combine agents with complementary roles and tools, assign tasks, and select a process that dictates their execution order and interaction.

Example: Assembling a Crew¶

from crewai import Crew, Agent, Task, Process
from langchain_community.tools import DuckDuckGoSearchRun

# Define agents with specific roles and tools
researcher = Agent(
    role='Senior Research Analyst',
    goal='Discover innovative AI technologies',
    backstory="""You're a senior research analyst at a large company.
        You're responsible for analyzing data and providing insights
        to the business.
        You're currently working on a project to analyze the
        trends and innovations in the space of artificial intelligence.""",
    tools=[DuckDuckGoSearchRun()]
)

writer = Agent(
    role='Content Writer',
    goal='Write engaging articles on AI discoveries',
    backstory="""You're a senior writer at a large company.
        You're responsible for creating content to the business.
        You're currently working on a project to write about trends
        and innovations in the space of AI for your next meeting.""",
    verbose=True
)

# Create tasks for the agents
research_task = Task(
    description='Identify breakthrough AI technologies',
    agent=researcher,
    expected_output='A bullet list summary of the top 5 most important AI news'
)
write_article_task = Task(
    description='Draft an article on the latest AI technologies',
    agent=writer,
    expected_output='3 paragraph blog post on the latest AI technologies'
)

# Assemble the crew with a sequential process
my_crew = Crew(
    agents=[researcher, writer],
    tasks=[research_task, write_article_task],
    process=Process.sequential,
    full_output=True,
    verbose=True,
)
Memory Utilization¶
Crews can utilize memory (short-term, long-term, and entity memory) to enhance their execution and learning over time. This feature allows crews to store and recall execution memories, aiding in decision-making and task execution strategies.

Cache Utilization¶
Caches can be employed to store the results of tools' execution, making the process more efficient by reducing the need to re-execute identical tasks.

Crew Usage Metrics¶
After the crew execution, you can access the usage_metrics attribute to view the language model (LLM) usage metrics for all tasks executed by the crew. This provides insights into operational efficiency and areas for improvement.


# Access the crew's usage metrics
crew = Crew(agents=[agent1, agent2], tasks=[task1, task2])
crew.kickoff()
print(crew.usage_metrics)
Crew Execution Process¶
Sequential Process: Tasks are executed one after another, allowing for a linear flow of work.
Hierarchical Process: A manager agent coordinates the crew, delegating tasks and validating outcomes before proceeding. Note: A manager_llm or manager_agent is required for this process and it's essential for validating the process flow.
Kicking Off a Crew¶
Once your crew is assembled, initiate the workflow with the kickoff() method. This starts the execution process according to the defined process flow.


# Start the crew's task execution
result = my_crew.kickoff()
print(result)
Different ways to Kicking Off a Crew¶
Once your crew is assembled, initiate the workflow with the appropriate kickoff method. CrewAI provides several methods for better control over the kickoff process: kickoff(), kickoff_for_each(), kickoff_async(), and kickoff_for_each_async().

kickoff(): Starts the execution process according to the defined process flow. kickoff_for_each(): Executes tasks for each agent individually. kickoff_async(): Initiates the workflow asynchronously. kickoff_for_each_async(): Executes tasks for each agent individually in an asynchronous manner.


# Start the crew's task execution
result = my_crew.kickoff()
print(result)

# Example of using kickoff_for_each
inputs_array = [{'topic': 'AI in healthcare'}, {'topic': 'AI in finance'}]
results = my_crew.kickoff_for_each(inputs=inputs_array)
for result in results:
    print(result)

# Example of using kickoff_async
inputs = {'topic': 'AI in healthcare'}
async_result = my_crew.kickoff_async(inputs=inputs)
print(async_result)

# Example of using kickoff_for_each_async
inputs_array = [{'topic': 'AI in healthcare'}, {'topic': 'AI in finance'}]
async_results = my_crew.kickoff_for_each_async(inputs=inputs_array)
for async_result in async_results:
    print(async_result)
These methods provide flexibility in how you manage and execute tasks within your crew, allowing for both synchronous and asynchronous workflows tailored to your needs

Using LangChain Tools
Using LangChain Tools¶
LangChain Integration

CrewAI seamlessly integrates with LangChain’s comprehensive toolkit for search-based queries and more, here are the available built-in tools that are offered by Langchain LangChain Toolkit


from crewai import Agent
from langchain.agents import Tool
from langchain.utilities import GoogleSerperAPIWrapper

# Setup API keys
os.environ["SERPER_API_KEY"] = "Your Key"

search = GoogleSerperAPIWrapper()

# Create and assign the search tool to an agent
serper_tool = Tool(
  name="Intermediate Answer",
  func=search.run,
  description="Useful for search-based queries",
)

agent = Agent(
  role='Research Analyst',
  goal='Provide up-to-date market analysis',
  backstory='An expert analyst with a keen eye for market trends.',
  tools=[serper_tool]
)

# rest of the code ...
Conclusion¶
Tools are pivotal in extending the capabilities of CrewAI agents, enabling them to undertake a broad spectrum of tasks and collaborate effectively. When building solutions with CrewAI, leverage both custom and existing tools to empower your agents and enhance the AI ecosystem. Consider utilizing error handling, caching mechanisms, and the flexibility of tool arguments to optimize your agents' performance and capabilities.

Using LlamaIndex Tools
Using LlamaIndex Tools¶
LlamaIndex Integration

CrewAI seamlessly integrates with LlamaIndex’s comprehensive toolkit for RAG (Retrieval-Augmented Generation) and agentic pipelines, enabling advanced search-based queries and more. Here are the available built-in tools offered by LlamaIndex.


from crewai import Agent
from crewai_tools import LlamaIndexTool

# Example 1: Initialize from FunctionTool
from llama_index.core.tools import FunctionTool

your_python_function = lambda ...: ...
og_tool = FunctionTool.from_defaults(your_python_function, name="<name>", description='<description>')
tool = LlamaIndexTool.from_tool(og_tool)

# Example 2: Initialize from LlamaHub Tools
from llama_index.tools.wolfram_alpha import WolframAlphaToolSpec
wolfram_spec = WolframAlphaToolSpec(app_id="<app_id>")
wolfram_tools = wolfram_spec.to_tool_list()
tools = [LlamaIndexTool.from_tool(t) for t in wolfram_tools]

# Example 3: Initialize Tool from a LlamaIndex Query Engine
query_engine = index.as_query_engine()
query_tool = LlamaIndexTool.from_query_engine(
    query_engine,
    name="Uber 2019 10K Query Tool",
    description="Use this tool to lookup the 2019 Uber 10K Annual Report"
)

# Create and assign the tools to an agent
agent = Agent(
  role='Research Analyst',
  goal='Provide up-to-date market analysis',
  backstory='An expert analyst with a keen eye for market trends.',
  tools=[tool, *tools, query_tool]
)

# rest of the code ...
Steps to Get Started¶
To effectively use the LlamaIndexTool, follow these steps:

Package Installation: Confirm that the crewai[tools] package is installed in your Python environment.


pip install 'crewai[tools]'
Install and Use LlamaIndex: Follow LlamaIndex documentation LlamaIndex Documentation to set up a RAG/agent pipeline.

Using Sequential Process
Introduction¶
CrewAI offers a flexible framework for executing tasks in a structured manner, supporting both sequential and hierarchical processes. This guide outlines how to effectively implement these processes to ensure efficient task execution and project completion.

Sequential Process Overview¶
The sequential process ensures tasks are executed one after the other, following a linear progression. This approach is ideal for projects requiring tasks to be completed in a specific order.

Key Features¶
Linear Task Flow: Ensures orderly progression by handling tasks in a predetermined sequence.
Simplicity: Best suited for projects with clear, step-by-step tasks.
Easy Monitoring: Facilitates easy tracking of task completion and project progress.
Implementing the Sequential Process¶
To use the sequential process, assemble your crew and define tasks in the order they need to be executed.


from crewai import Crew, Process, Agent, Task

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

research_task = Task(description='Gather relevant data...', agent=researcher, expected_output='Raw Data')
analysis_task = Task(description='Analyze the data...', agent=analyst, expected_output='Data Insights')
writing_task = Task(description='Compose the report...', agent=writer, expected_output='Final Report')

# Form the crew with a sequential process
report_crew = Crew(
  agents=[researcher, analyst, writer],
  tasks=[research_task, analysis_task, writing_task],
  process=Process.sequential
)

# Execute the crew
result = report_crew.kickoff()
Workflow in Action¶
Initial Task: In a sequential process, the first agent completes their task and signals completion.
Subsequent Tasks: Agents pick up their tasks based on the process type, with outcomes of preceding tasks or manager directives guiding their execution.
Completion: The process concludes once the final task is executed, leading to project completion.
Advanced Features¶
Task Delegation¶
In sequential processes, if an agent has allow_delegation set to True, they can delegate tasks to other agents in the crew. This feature is automatically set up when there are multiple agents in the crew.

Asynchronous Execution¶
Tasks can be executed asynchronously, allowing for parallel processing when appropriate. To create an asynchronous task, set async_execution=True when defining the task.

Memory and Caching¶
CrewAI supports both memory and caching features: - Memory: Enable by setting memory=True when creating the Crew. This allows agents to retain information across tasks. - Caching: By default, caching is enabled. Set cache=False to disable it.

Callbacks¶
You can set callbacks at both the task and step level: - task_callback: Executed after each task completion. - step_callback: Executed after each step in an agent's execution.

Usage Metrics¶
CrewAI tracks token usage across all tasks and agents. You can access these metrics after execution.

Best Practices for Sequential Processes¶
Order Matters: Arrange tasks in a logical sequence where each task builds upon the previous one.
Clear Task Descriptions: Provide detailed descriptions for each task to guide the agents effectively.
Appropriate Agent Selection: Match agents' skills and roles to the requirements of each task.
Use Context: Leverage the context from previous tasks to inform subsequent ones