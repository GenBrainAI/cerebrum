Getting Started
AutoGen is an open-source programming framework for building AI agents and facilitating cooperation among multiple agents to solve tasks. AutoGen aims to provide an easy-to-use and flexible framework for accelerating development and research on agentic AI, like PyTorch for Deep Learning. It offers features such as agents that can converse with other agents, LLM and tool use support, autonomous and human-in-the-loop workflows, and multi-agent conversation patterns.

AutoGen Overview

Main Features
AutoGen enables building next-gen LLM applications based on multi-agent conversations with minimal effort. It simplifies the orchestration, automation, and optimization of a complex LLM workflow. It maximizes the performance of LLM models and overcomes their weaknesses.
It supports diverse conversation patterns for complex workflows. With customizable and conversable agents, developers can use AutoGen to build a wide range of conversation patterns concerning conversation autonomy, the number of agents, and agent conversation topology.
It provides a collection of working systems with different complexities. These systems span a wide range of applications from various domains and complexities. This demonstrates how AutoGen can easily support diverse conversation patterns.
AutoGen is powered by collaborative research studies from Microsoft, Penn State University, and University of Washington.

Quickstart
pip install pyautogen

No code execution
Local execution
Docker execution
import os
from autogen import AssistantAgent, UserProxyAgent

llm_config = {"model": "gpt-4", "api_key": os.environ["OPENAI_API_KEY"]}
assistant = AssistantAgent("assistant", llm_config=llm_config)
user_proxy = UserProxyAgent("user_proxy", code_execution_config=False)

# Start the chat
user_proxy.initiate_chat(
    assistant,
    message="Tell me a joke about NVDA and TESLA stock prices.",
)

TIP
Learn more about configuring LLMs for agents here.

Multi-Agent Conversation Framework
Autogen enables the next-gen LLM applications with a generic multi-agent conversation framework. It offers customizable and conversable agents which integrate LLMs, tools, and humans. By automating chat among multiple capable agents, one can easily make them collectively perform tasks autonomously or with human feedback, including tasks that require using tools via code. For example,

The figure below shows an example conversation flow with AutoGen.

Agent Chat Example

Installation
Create a virtual environment (optional)
When installing AutoGen locally, we recommend using a virtual environment for the installation. This will ensure that the dependencies for AutoGen are isolated from the rest of your system.

venv
Conda
Poetry
Create and activate:

python3 -m venv pyautogen
source pyautogen/bin/activate

To deactivate later, run:

deactivate

Install AutoGen
AutoGen requires Python version >= 3.8, < 3.13. It can be installed from pip:

pip install pyautogen

INFO
pyautogen<0.2 required openai<1. Starting from pyautogen v0.2, openai>=1 is required.

Install Docker for Code Execution
We recommend using Docker for code execution. To install Docker, follow the instructions for your operating system on the Docker website.

A simple example of how to use Docker for code execution is shown below:

from pathlib import Path
from autogen import UserProxyAgent
from autogen.coding import DockerCommandLineCodeExecutor

work_dir = Path("coding")
work_dir.mkdir(exist_ok=True)

with DockerCommandLineCodeExecutor(work_dir=work_dir) as code_executor:
    user_proxy = UserProxyAgent(
        name="user_proxy",
        code_execution_config={"executor": code_executor},
    )

Introduction to AutoGen
Open In Colab Open on GitHub

Welcome! AutoGen is an open-source framework that leverages multiple agents to enable complex workflows. This tutorial introduces basic concepts and building blocks of AutoGen.

Why AutoGen?
The whole is greater than the sum of its parts.
-Aristotle

While there are many definitions of agents, in AutoGen, an agent is an entity that can send messages, receive messages and generate a reply using models, tools, human inputs or a mixture of them. This abstraction not only allows agents to model real-world and abstract entities, such as people and algorithms, but it also simplifies implementation of complex workflows as collaboration among agents.

Further, AutoGen is extensible and composable: you can extend a simple agent with customizable components and create workflows that can combine these agents and power a more sophisticated agent, resulting in implementations that are modular and easy to maintain.

Most importantly, AutoGen is developed by a vibrant community of researchers and engineers. It incorporates the latest research in multi-agent systems and has been used in many real-world applications, including agent platform, advertising, AI employees, blog/article writing, blockchain, calculate burned areas by wildfires, customer support, cybersecurity, data analytics, debate, education, finance, gaming, legal consultation, research, robotics, sales/marketing, social simulation, software engineering, software security, supply chain, t-shirt design, training data generation, Youtube service…

Installation
The simplest way to install AutoGen is from pip: pip install pyautogen. Find more options in Installation.

Agents
In AutoGen, an agent is an entity that can send and receive messages to and from other agents in its environment. An agent can be powered by models (such as a large language model like GPT-4), code executors (such as an IPython kernel), human, or a combination of these and other pluggable and customizable components.

ConversableAgent

An example of such agents is the built-in ConversableAgent which supports the following components:

A list of LLMs
A code executor
A function and tool executor
A component for keeping human-in-the-loop
You can switch each component on or off and customize it to suit the need of your application. For advanced users, you can add additional components to the agent by using registered_reply.

LLMs, for example, enable agents to converse in natural languages and transform between structured and unstructured text. The following example shows a ConversableAgent with a GPT-4 LLM switched on and other components switched off:

import os

from autogen import ConversableAgent

agent = ConversableAgent(
    "chatbot",
    llm_config={"config_list": [{"model": "gpt-4", "api_key": os.environ.get("OPENAI_API_KEY")}]},
    code_execution_config=False,  # Turn off code execution, by default it is off.
    function_map=None,  # No registered functions, by default it is None.
    human_input_mode="NEVER",  # Never ask for human input.
)

The llm_config argument contains a list of configurations for the LLMs. See LLM Configuration for more details.

You can ask this agent to generate a response to a question using the generate_reply method:

reply = agent.generate_reply(messages=[{"content": "Tell me a joke.", "role": "user"}])
print(reply)

Sure, here's a light-hearted joke for you:

Why don't scientists trust atoms?

Because they make up everything!

Roles and Conversations
In AutoGen, you can assign roles to agents and have them participate in conversations or chat with each other. A conversation is a sequence of messages exchanged between agents. You can then use these conversations to make progress on a task. For example, in the example below, we assign different roles to two agents by setting their system_message.

cathy = ConversableAgent(
    "cathy",
    system_message="Your name is Cathy and you are a part of a duo of comedians.",
    llm_config={"config_list": [{"model": "gpt-4", "temperature": 0.9, "api_key": os.environ.get("OPENAI_API_KEY")}]},
    human_input_mode="NEVER",  # Never ask for human input.
)

joe = ConversableAgent(
    "joe",
    system_message="Your name is Joe and you are a part of a duo of comedians.",
    llm_config={"config_list": [{"model": "gpt-4", "temperature": 0.7, "api_key": os.environ.get("OPENAI_API_KEY")}]},
    human_input_mode="NEVER",  # Never ask for human input.
)


Now that we have two comedian agents, we can ask them to start a comedy show. This can be done using the initiate_chat method. We set the max_turns to 2 to keep the conversation short.

result = joe.initiate_chat(cathy, message="Cathy, tell me a joke.", max_turns=2)

joe (to cathy):

Cathy, tell me a joke.

--------------------------------------------------------------------------------
cathy (to joe):

Sure, here's one for you:

Why don't scientists trust atoms?

Because they make up everything!

--------------------------------------------------------------------------------
joe (to cathy):

Haha, that's a good one, Cathy! Okay, my turn. 

Why don't we ever tell secrets on a farm?

Because the potatoes have eyes, the corn has ears, and the beans stalk.

--------------------------------------------------------------------------------
cathy (to joe):

Haha, that's a great one! A farm is definitely not the place for secrets. Okay, my turn again. 

Why couldn't the bicycle stand up by itself?

Because it was two-tired!

--------------------------------------------------------------------------------

The comedians are bouncing off each other!

Summary
In this chapter, we introduced the concept of agents, roles and conversations in AutoGen. For simplicity, we only used LLMs and created fully autonomous agents (human_input_mode was set to NEVER). In the next chapter, we will show how you can control when to terminate a conversation between autonomous agents.

Terminating Conversations Between Agents
Open In Colab Open on GitHub

In this chapter, we will explore how to terminate a conversation between AutoGen agents.

But why is this important? Its because in any complex, autonomous workflows it’s crucial to know when to stop the workflow. For example, when the task is completed, or perhaps when the process has consumed enough resources and needs to either stop or adopt different strategies, such as user intervention. So AutoGen natively supports several mechanisms to terminate conversations.

How to Control Termination with AutoGen? Currently there are two broad mechanism to control the termination of conversations between agents:

Specify parameters in initiate_chat: When initiating a chat, you can define parameters that determine when the conversation should end.

Configure an agent to trigger termination: When defining individual agents, you can specify parameters that allow agents to terminate of a conversation based on particular (configurable) conditions.

Parameters in initiate_chat
In the previous chapter we actually demonstrated this when we used the max_turns parameter to limit the number of turns. If we increase max_turns to say 3 notice the conversation takes more rounds to terminate:

import os

from autogen import ConversableAgent

cathy = ConversableAgent(
    "cathy",
    system_message="Your name is Cathy and you are a part of a duo of comedians.",
    llm_config={"config_list": [{"model": "gpt-4", "temperature": 0.9, "api_key": os.environ.get("OPENAI_API_KEY")}]},
    human_input_mode="NEVER",  # Never ask for human input.
)

joe = ConversableAgent(
    "joe",
    system_message="Your name is Joe and you are a part of a duo of comedians.",
    llm_config={"config_list": [{"model": "gpt-4", "temperature": 0.7, "api_key": os.environ.get("OPENAI_API_KEY")}]},
    human_input_mode="NEVER",  # Never ask for human input.
)


result = joe.initiate_chat(cathy, message="Cathy, tell me a joke.", max_turns=2)

joe (to cathy):

Cathy, tell me a joke.

--------------------------------------------------------------------------------
cathy (to joe):

Sure, here's one for you:

Why don't scientists trust atoms?

Because they make up everything!

--------------------------------------------------------------------------------
joe (to cathy):

Haha, that's a good one, Cathy! Okay, my turn. 

Why don't we ever tell secrets on a farm?

Because the potatoes have eyes, the corn has ears, and the beans stalk.

--------------------------------------------------------------------------------
cathy (to joe):

Haha, that's a great one! A farm is definitely not the place for secrets. Okay, my turn again. 

Why couldn't the bicycle stand up by itself?

Because it was two-tired!

--------------------------------------------------------------------------------

result = joe.initiate_chat(
    cathy, message="Cathy, tell me a joke.", max_turns=3
)  # increase the number of max turns before termination

joe (to cathy):

Cathy, tell me a joke.

--------------------------------------------------------------------------------
cathy (to joe):

Sure, here's one for you:

Why don't scientists trust atoms?

Because they make up everything!

--------------------------------------------------------------------------------
joe (to cathy):

Haha, that's a good one, Cathy! Okay, my turn. 

Why don't we ever tell secrets on a farm?

Because the potatoes have eyes, the corn has ears, and the beans stalk.

--------------------------------------------------------------------------------
cathy (to joe):

Haha, that's a great one! A farm is definitely not the place for secrets. Okay, my turn again. 

Why couldn't the bicycle stand up by itself?

Because it was two-tired!

--------------------------------------------------------------------------------
joe (to cathy):

Haha, that's a wheely good one, Cathy!

Why did the golfer bring two pairs of pants?

In case he got a hole in one!

--------------------------------------------------------------------------------
cathy (to joe):

Haha, that's a perfect swing of a joke!

Why did the scarecrow win an award?

Because he was outstanding in his field!

--------------------------------------------------------------------------------

Agent-triggered termination
You can also terminate a conversation by configuring parameters of an agent. Currently, there are two parameters you can configure:

max_consecutive_auto_reply: This condition triggers termination if the number of automatic responses to the same sender exceeds a threshold. You can customize this using the max_consecutive_auto_reply argument of the ConversableAgent class. To accomplish this the agent maintains a counter of the number of consecutive automatic responses to the same sender. Note that this counter can be reset because of human intervention. We will describe this in more detail in the next chapter.
is_termination_msg: This condition can trigger termination if the received message satisfies a particular condition, e.g., it contains the word “TERMINATE”. You can customize this condition using the is_terminate_msg argument in the constructor of the ConversableAgent class.
Using max_consecutive_auto_reply
In the example below lets set max_consecutive_auto_reply to 1 and notice how this ensures that Joe only replies once.

joe = ConversableAgent(
    "joe",
    system_message="Your name is Joe and you are a part of a duo of comedians.",
    llm_config={"config_list": [{"model": "gpt-4", "temperature": 0.7, "api_key": os.environ.get("OPENAI_API_KEY")}]},
    human_input_mode="NEVER",  # Never ask for human input.
    max_consecutive_auto_reply=1,  # Limit the number of consecutive auto-replies.
)

result = joe.initiate_chat(cathy, message="Cathy, tell me a joke.")


joe (to cathy):

Cathy, tell me a joke.

--------------------------------------------------------------------------------
cathy (to joe):

Sure, here's one for you:

Why don't scientists trust atoms?

Because they make up everything!

--------------------------------------------------------------------------------
joe (to cathy):

Haha, that's a good one, Cathy! Okay, my turn. 

Why don't we ever tell secrets on a farm?

Because the potatoes have eyes, the corn has ears, and the beans stalk.

--------------------------------------------------------------------------------
cathy (to joe):

Haha, that's a great one! A farm is definitely not the place for secrets. Okay, my turn again. 

Why couldn't the bicycle stand up by itself?

Because it was two-tired!

--------------------------------------------------------------------------------

Using is_termination_msg
Let’s set the termination message to “GOOD BYE” and see how the conversation terminates.

joe = ConversableAgent(
    "joe",
    system_message="Your name is Joe and you are a part of a duo of comedians.",
    llm_config={"config_list": [{"model": "gpt-4", "temperature": 0.7, "api_key": os.environ.get("OPENAI_API_KEY")}]},
    human_input_mode="NEVER",  # Never ask for human input.
    is_termination_msg=lambda msg: "good bye" in msg["content"].lower(),
)

result = joe.initiate_chat(cathy, message="Cathy, tell me a joke and then say the words GOOD BYE.")


joe (to cathy):

Cathy, tell me a joke and then say the words GOOD BYE.

--------------------------------------------------------------------------------
cathy (to joe):

Why don't scientists trust atoms?

Because they make up everything!

GOOD BYE!

--------------------------------------------------------------------------------

Notice how the conversation ended based on contents of cathy’s message!

Summary
In this chapter we introduced mechanisms to terminate a conversation between agents. You can configure both parameters in initiate_chat and also configuration of agents.

That said, it is important to note that when a termination condition is triggered, the conversation may not always terminate immediately. The actual termination depends on the human_input_mode argument of the ConversableAgent class. For example, when mode is NEVER the termination conditions above will end the conversations. But when mode is ALWAYS or TERMINATE, it will not terminate immediately. We will describe this behavior and explain why it is important in the next chapter.

Allowing Human Feedback in Agents
Open In Colab Open on GitHub

In the last two chapters we introduced the ConversableAgent class and showed how you can use it to create autonomous (human_input_mode=NEVER) agents that can accomplish tasks. We also showed how to properly terminate a conversation between agents.

But many applications may require putting humans in-the-loop with agents. For example, to allow human feedback to steer agents in the right direction, specify goals, etc. In this chapter, we will show how AutoGen supports human intervention.

In AutoGen’s ConversableAgent, the human-in-the-loop component sits in front of the auto-reply components. It can intercept the incoming messages and decide whether to pass them to the auto-reply components or to provide human feedback. The figure below illustrates the design.

Human in the loop

The human-in-the-loop component can be customized through the human_input_mode parameter. We will show you how to use it in the following sections.

Human Input Modes
Currently AutoGen supports three modes for human input. The mode is specified through the human_input_mode argument of the ConversableAgent. The three modes are:

NEVER: human input is never requested.
TERMINATE (default): human input is only requested when a termination condition is met. Note that in this mode if the human chooses to intercept and reply, the conversation continues and the counter used by max_consecutive_auto_reply is reset.
ALWAYS: human input is always requested and the human can choose to skip and trigger an auto-reply, intercept and provide feedback, or terminate the conversation. Note that in this mode termination based on max_consecutive_auto_reply is ignored.
The previous chapters already showed many examples of the cases when human_input_mode is NEVER. Below we show one such example again and then show the differences when this mode is set to ALWAYS and NEVER instead.

Human Input Mode = NEVER
In this mode, human input is never requested and the termination conditions are used to terminate. This mode is useful when you want your agents to act fully autonomously.

Here is an example of using this mode to run a simple guess-a-number game between two agents, the termination message is set to check for the number that is the correct guess.

import os

from autogen import ConversableAgent

agent_with_number = ConversableAgent(
    "agent_with_number",
    system_message="You are playing a game of guess-my-number. You have the "
    "number 53 in your mind, and I will try to guess it. "
    "If I guess too high, say 'too high', if I guess too low, say 'too low'. ",
    llm_config={"config_list": [{"model": "gpt-4", "api_key": os.environ["OPENAI_API_KEY"]}]},
    is_termination_msg=lambda msg: "53" in msg["content"],  # terminate if the number is guessed by the other agent
    human_input_mode="NEVER",  # never ask for human input
)

agent_guess_number = ConversableAgent(
    "agent_guess_number",
    system_message="I have a number in my mind, and you will try to guess it. "
    "If I say 'too high', you should guess a lower number. If I say 'too low', "
    "you should guess a higher number. ",
    llm_config={"config_list": [{"model": "gpt-4", "api_key": os.environ["OPENAI_API_KEY"]}]},
    human_input_mode="NEVER",
)

result = agent_with_number.initiate_chat(
    agent_guess_number,
    message="I have a number between 1 and 100. Guess it!",
)


agent_with_number (to agent_guess_number):

I have a number between 1 and 100. Guess it!

--------------------------------------------------------------------------------
agent_guess_number (to agent_with_number):

Is it 50?

--------------------------------------------------------------------------------
agent_with_number (to agent_guess_number):

Too low.

--------------------------------------------------------------------------------
agent_guess_number (to agent_with_number):

Is it 75?

--------------------------------------------------------------------------------
agent_with_number (to agent_guess_number):

Too high.

--------------------------------------------------------------------------------
agent_guess_number (to agent_with_number):

Is it 63?

--------------------------------------------------------------------------------
agent_with_number (to agent_guess_number):

Too high.

--------------------------------------------------------------------------------
agent_guess_number (to agent_with_number):

Is it 57?

--------------------------------------------------------------------------------
agent_with_number (to agent_guess_number):

Too high.

--------------------------------------------------------------------------------
agent_guess_number (to agent_with_number):

Is it 54?

--------------------------------------------------------------------------------
agent_with_number (to agent_guess_number):

Too high.

--------------------------------------------------------------------------------
agent_guess_number (to agent_with_number):

Is it 52?

--------------------------------------------------------------------------------
agent_with_number (to agent_guess_number):

Too low.

--------------------------------------------------------------------------------
agent_guess_number (to agent_with_number):

Is it 53?

--------------------------------------------------------------------------------

Yay! The game is over. The guessing agent got the number correctly using binary search – very efficient! You can see that the conversation was terminated after the guessing agent said the correct number, which triggered the message-based termination condition.

Human Input Mode = ALWAYS
In this mode, human input is always requested and the human can choose to skip, intercept , or terminate the conversation. Let us see this mode in action by playing the same game as before with the agent with the number, but this time participating in the game as a human. We will be the agent that is guessing the number, and play against the agent with the number from before.

human_proxy = ConversableAgent(
    "human_proxy",
    llm_config=False,  # no LLM used for human proxy
    human_input_mode="ALWAYS",  # always ask for human input
)

# Start a chat with the agent with number with an initial guess.
result = human_proxy.initiate_chat(
    agent_with_number,  # this is the same agent with the number as before
    message="10",
)

human_proxy (to agent_with_number):

10

--------------------------------------------------------------------------------
agent_with_number (to human_proxy):

Too low.

--------------------------------------------------------------------------------
human_proxy (to agent_with_number):

79

--------------------------------------------------------------------------------
agent_with_number (to human_proxy):

Too high.

--------------------------------------------------------------------------------
human_proxy (to agent_with_number):

76

--------------------------------------------------------------------------------
agent_with_number (to human_proxy):

Too high.

--------------------------------------------------------------------------------
human_proxy (to agent_with_number):

I give up

--------------------------------------------------------------------------------
agent_with_number (to human_proxy):

That's okay! The number I was thinking of was 53.

--------------------------------------------------------------------------------

If you run the code above, you will be prompt to enter a response each time it is your turn to speak. You can see the human in the conversation was not very good at guessing the number… but hey the agent was nice enough to give out the number in the end.

Human Input Mode = TERMINATE
In this mode, human input is only requested when a termination condition is met. If the human chooses to intercept and reply, the counter will be reset; if the human chooses to skip, the automatic reply mechanism will be used; if the human chooses to terminate, the conversation will be terminated.

Let us see this mode in action by playing the same game again, but this time the guessing agent will only have two chances to guess the number, and if it fails, the human will be asked to provide feedback, and the guessing agent gets two more chances. If the correct number is guessed eventually, the conversation will be terminated.

agent_with_number = ConversableAgent(
    "agent_with_number",
    system_message="You are playing a game of guess-my-number. "
    "In the first game, you have the "
    "number 53 in your mind, and I will try to guess it. "
    "If I guess too high, say 'too high', if I guess too low, say 'too low'. ",
    llm_config={"config_list": [{"model": "gpt-4", "api_key": os.environ["OPENAI_API_KEY"]}]},
    max_consecutive_auto_reply=1,  # maximum number of consecutive auto-replies before asking for human input
    is_termination_msg=lambda msg: "53" in msg["content"],  # terminate if the number is guessed by the other agent
    human_input_mode="TERMINATE",  # ask for human input until the game is terminated
)

agent_guess_number = ConversableAgent(
    "agent_guess_number",
    system_message="I have a number in my mind, and you will try to guess it. "
    "If I say 'too high', you should guess a lower number. If I say 'too low', "
    "you should guess a higher number. ",
    llm_config={"config_list": [{"model": "gpt-4", "api_key": os.environ["OPENAI_API_KEY"]}]},
    human_input_mode="NEVER",
)

result = agent_with_number.initiate_chat(
    agent_guess_number,
    message="I have a number between 1 and 100. Guess it!",
)


agent_with_number (to agent_guess_number):

I have a number between 1 and 100. Guess it!

--------------------------------------------------------------------------------
agent_guess_number (to agent_with_number):

Is it 50?

--------------------------------------------------------------------------------

>>>>>>>> USING AUTO REPLY...
agent_with_number (to agent_guess_number):

Too low.

--------------------------------------------------------------------------------
agent_guess_number (to agent_with_number):

Is it 75?

--------------------------------------------------------------------------------
agent_with_number (to agent_guess_number):

It is too high my friend. 

--------------------------------------------------------------------------------
agent_guess_number (to agent_with_number):

Is it 60?

--------------------------------------------------------------------------------

>>>>>>>> USING AUTO REPLY...
agent_with_number (to agent_guess_number):

Too high.

--------------------------------------------------------------------------------
agent_guess_number (to agent_with_number):

Is it 55?

--------------------------------------------------------------------------------
agent_with_number (to agent_guess_number):

still too high, but you are very close.

--------------------------------------------------------------------------------
agent_guess_number (to agent_with_number):

Is it 52?

--------------------------------------------------------------------------------

>>>>>>>> USING AUTO REPLY...
agent_with_number (to agent_guess_number):

Too low.

--------------------------------------------------------------------------------
agent_guess_number (to agent_with_number):

Is it 54?

--------------------------------------------------------------------------------
agent_with_number (to agent_guess_number):

Almost there! 

--------------------------------------------------------------------------------
agent_guess_number (to agent_with_number):

Is it 53?

--------------------------------------------------------------------------------

In the previous conversation,

When the agent guessed “74”, the human said “It is too high my friend.”
When the agent guessed “55”, the human said “still too high, but you are very close.”
When the agent guessed “54”, the human said “Almost there!”
Each time after one auto-reply from the agent with the number, the human was asked to provide feedback. Once the human provided feedback, the counter was reset. The conversation was terminated after the agent correctly guessed “53”.

Summary
In this chapter, we showed you how to use the human-in-the-loop component to provide human feedback to agent and to terminate conversation. We also showed you the different human input modes and how they affect the behavior of the human-in-the-loop component.

The next chapter will be all about code executor – the most powerful component second only to LLMs.

Code Executors
Open In Colab Open on GitHub

In the last chapter, we used two agents powered by a large language model (LLM) to play a game by exchanging messages. In this chapter, we introduce code executors, which enable agents to not just chat but also to interact with an environment and perform useful computations and take actions.

Overview
In AutoGen, a code executor is a component that takes input messages (e.g., those containing code blocks), performs execution, and outputs messages with the results. AutoGen provides two types of built-in code executors, one is command line code executor, which runs code in a command line environment such as a UNIX shell, and the other is Jupyter executor, which runs code in an interactive Jupyter kernel.

For each type of executor, AutoGen provides two ways to execute code: locally and in a Docker container. One way is to execute code directly in the same host platform where AutoGen is running, i.e., the local operating system. It is for development and testing, but it is not ideal for production as LLM can generate arbitrary code. The other way is to execute code in a Docker container. The table below shows the combinations of code executors and execution environments.

Code Executor (autogen.coding)	Environment	Platform
LocalCommandLineCodeExecutor	Shell	Local
DockerCommandLineCodeExecutor	Shell	Docker
jupyter.JupyterCodeExecutor	Jupyter Kernel (e.g., python3)	Local/Docker
In this chapter, we will focus on the command line code executors. For the Jupyter code executor, please refer to the topic page for Jupyter Code Executor.

Local Execution
The figure below shows the architecture of the local command line code executor (autogen.coding.LocalCommandLineCodeExecutor).

DANGER
Executing LLM-generated code poses a security risk to your host environment.

Code Executor No Docker

Upon receiving a message with a code block, the local command line code executor first writes the code block to a code file, then starts a new subprocess to execute the code file. The executor reads the console output of the code execution and sends it back as a reply message.

Here is an example of using the code executor to run a Python code block that prints a random number. First we create an agent with the code executor that uses a temporary directory to store the code files. We specify human_input_mode="ALWAYS" to manually validate the safety of the the code being executed.

import tempfile

from autogen import ConversableAgent
from autogen.coding import LocalCommandLineCodeExecutor

# Create a temporary directory to store the code files.
temp_dir = tempfile.TemporaryDirectory()

# Create a local command line code executor.
executor = LocalCommandLineCodeExecutor(
    timeout=10,  # Timeout for each code execution in seconds.
    work_dir=temp_dir.name,  # Use the temporary directory to store the code files.
)

# Create an agent with code executor configuration.
code_executor_agent = ConversableAgent(
    "code_executor_agent",
    llm_config=False,  # Turn off LLM for this agent.
    code_execution_config={"executor": executor},  # Use the local command line code executor.
    human_input_mode="ALWAYS",  # Always take human input for this agent for safety.
)

Before running this example, we need to make sure the matplotlib and numpy are installed.

! pip install -qqq matplotlib numpy

Now we have the agent generate a reply given a message with a Python code block.

message_with_code_block = """This is a message with code block.
The code block is below:
```python
import numpy as np
import matplotlib.pyplot as plt
x = np.random.randint(0, 100, 100)
y = np.random.randint(0, 100, 100)
plt.scatter(x, y)
plt.savefig('scatter.png')
print('Scatter plot saved to scatter.png')
```
This is the end of the message.
"""

# Generate a reply for the given code.
reply = code_executor_agent.generate_reply(messages=[{"role": "user", "content": message_with_code_block}])
print(reply)



>>>>>>>> NO HUMAN INPUT RECEIVED.

>>>>>>>> USING AUTO REPLY...

>>>>>>>> EXECUTING CODE BLOCK (inferred language is python)...
exitcode: 0 (execution succeeded)
Code output: 
Scatter plot saved to scatter.png

During the generation of response, a human input is requested to give an opportunity to intercept the code execution. In this case, we choose to continue the execution, and the agent’s reply contains the output of the code execution.

We can take a look at the generated plot in the temporary directory.

import os

print(os.listdir(temp_dir.name))
# We can see the output scatter.png and the code file generated by the agent.

['scatter.png', '6507ea07b63b45aabb027ade4e213de6.py']

Clean up the working directory to avoid affecting future conversations.

temp_dir.cleanup()

Docker Execution
To mitigate the security risk of running LLM-generated code locally, we can use the docker command line code executor (autogen.coding.DockerCommandLineCodeExecutor) to execute code in a docker container. This way, the generated code can only access resources that are explicitly given to it.

The figure below illustrates how does the docker execution works.

Code Executor Docker

Similar to the local command line code executor, the docker executor extracts code blocks from input messages, writes them to code files. For each code file, it starts a docker container to execute the code file, and reads the console output of the code execution.

To use docker execution, you need to install Docker on your machine. Once you have Docker installed and running, you can set up your code executor agent as follow:

from autogen.coding import DockerCommandLineCodeExecutor

# Create a temporary directory to store the code files.
temp_dir = tempfile.TemporaryDirectory()

# Create a Docker command line code executor.
executor = DockerCommandLineCodeExecutor(
    image="python:3.12-slim",  # Execute code using the given docker image name.
    timeout=10,  # Timeout for each code execution in seconds.
    work_dir=temp_dir.name,  # Use the temporary directory to store the code files.
)

# Create an agent with code executor configuration that uses docker.
code_executor_agent_using_docker = ConversableAgent(
    "code_executor_agent_docker",
    llm_config=False,  # Turn off LLM for this agent.
    code_execution_config={"executor": executor},  # Use the docker command line code executor.
    human_input_mode="ALWAYS",  # Always take human input for this agent for safety.
)

# When the code executor is no longer used, stop it to release the resources.
# executor.stop()

The work_dir in the constructor points to a local file system directory just like in the local execution case. The docker container will mount this directory and the executor write code files and output to it.

Use Code Execution in Conversation
Writing and executing code is necessary for many tasks such as data analysis, machine learning, and mathematical modeling. In AutoGen, coding can be a conversation between a code writer agent and a code executor agent, mirroring the interaction between a programmer and a code interpreter.

Code Writer and Code Executor

The code writer agent can be powered by an LLM such as GPT-4 with code-writing capability. And the code executor agent is powered by a code executor.

The following is an agent with a code writer role specified using system_message. The system message contains important instruction on how to use the code executor in the code executor agent.

# The code writer agent's system message is to instruct the LLM on how to use
# the code executor in the code executor agent.
code_writer_system_message = """You are a helpful AI assistant.
Solve tasks using your coding and language skills.
In the following cases, suggest python code (in a python coding block) or shell script (in a sh coding block) for the user to execute.
1. When you need to collect info, use the code to output the info you need, for example, browse or search the web, download/read a file, print the content of a webpage or a file, get the current date/time, check the operating system. After sufficient info is printed and the task is ready to be solved based on your language skill, you can solve the task by yourself.
2. When you need to perform some task with code, use the code to perform the task and output the result. Finish the task smartly.
Solve the task step by step if you need to. If a plan is not provided, explain your plan first. Be clear which step uses code, and which step uses your language skill.
When using code, you must indicate the script type in the code block. The user cannot provide any other feedback or perform any other action beyond executing the code you suggest. The user can't modify your code. So do not suggest incomplete code which requires users to modify. Don't use a code block if it's not intended to be executed by the user.
If you want the user to save the code in a file before executing it, put # filename: <filename> inside the code block as the first line. Don't include multiple code blocks in one response. Do not ask users to copy and paste the result. Instead, use 'print' function for the output when relevant. Check the execution result returned by the user.
If the result indicates there is an error, fix the error and output the code again. Suggest the full code instead of partial code or code changes. If the error can't be fixed or if the task is not solved even after the code is executed successfully, analyze the problem, revisit your assumption, collect additional info you need, and think of a different approach to try.
When you find an answer, verify the answer carefully. Include verifiable evidence in your response if possible.
Reply 'TERMINATE' in the end when everything is done.
"""

code_writer_agent = ConversableAgent(
    "code_writer_agent",
    system_message=code_writer_system_message,
    llm_config={"config_list": [{"model": "gpt-4", "api_key": os.environ["OPENAI_API_KEY"]}]},
    code_execution_config=False,  # Turn off code execution for this agent.
)


Here is an example of solving a math problem through a conversation between the code writer agent and the code executor agent (created above).

chat_result = code_executor_agent.initiate_chat(
    code_writer_agent,
    message="Write Python code to calculate the 14th Fibonacci number.",
)

code_executor_agent (to code_writer_agent):

Write Python code to calculate the 14th Fibonacci number.

--------------------------------------------------------------------------------

>>>>>>>> USING AUTO REPLY...
code_writer_agent (to code_executor_agent):

Sure, here is a Python code snippet to calculate the 14th Fibonacci number. The Fibonacci series is a sequence of numbers in which each number is the sum of the two preceding ones, usually starting with 0 and 1.

```python
def fibonacci(n):
    if(n <= 0):
        return "Input should be a positive integer."
    elif(n == 1):
        return 0
    elif(n == 2):
        return 1
    else:
        fib = [0, 1]
        for i in range(2, n):
            fib.append(fib[i-1] + fib[i-2])
        return fib[n-1]

print(fibonacci(14))
```

This Python code defines a function `fibonacci(n)` which computes the n-th Fibonacci number. The function uses a list `fib` to store the Fibonacci numbers as they are computed, and then returns the (n-1)-th element as the n-th Fibonacci number due to zero-indexing in Python lists.

--------------------------------------------------------------------------------

>>>>>>>> NO HUMAN INPUT RECEIVED.

>>>>>>>> USING AUTO REPLY...

>>>>>>>> EXECUTING CODE BLOCK (inferred language is python)...
code_executor_agent (to code_writer_agent):

exitcode: 0 (execution succeeded)
Code output: 
233


--------------------------------------------------------------------------------

>>>>>>>> USING AUTO REPLY...
code_writer_agent (to code_executor_agent):

Great, the execution was successful and the 14th Fibonacci number is 233. The sequence goes as follows: 0, 1, 1, 2, 3, 5, 8, 13, 21, 34, 55, 89, 144, 233... and so on, where each number is the sum of the previous two. Therefore, the 14th number in the Fibonacci series is 233. 

I hope this meets your expectations. If you have any other concerns or need further computations, feel free to ask.

TERMINATE

--------------------------------------------------------------------------------


During the previous chat session, human input was requested each time the code executor agent responded to ensure that the code was safe to execute.

Now we can try a more complex example that involves querying the web. Let’s say we want to get the the stock price gains year-to-date for Tesla and Meta (formerly Facebook). We can also use the two agents with several iterations of conversation.

import datetime

today = datetime.datetime.now().strftime("%Y-%m-%d")
chat_result = code_executor_agent.initiate_chat(
    code_writer_agent,
    message=f"Today is {today}. Write Python code to plot TSLA's and META's "
    "stock price gains YTD, and save the plot to a file named 'stock_gains.png'.",
)

code_executor_agent (to code_writer_agent):

Today is 2024-02-28. Write Python code to plot TSLA's and META's stock price gains YTD, and save the plot to a file named 'stock_gains.png'.

--------------------------------------------------------------------------------

>>>>>>>> USING AUTO REPLY...
code_writer_agent (to code_executor_agent):

This task requires retrieving the historical data of the stocks from a reliable data source and calculating the Year-To-Date (YTD) gain values, and then plotting them. pandas_datareader library will be used for data retrieval, pandas will be used for data manipulation, and matplotlib for plotting. 

Below is the Python code to achieve this. To start, please install the required libraries by running to the following command:
```sh
pip install yfinance pandas matplotlib
```
Then run the python code:

```python
# filename: stock_gains.py

import yfinance as yf
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime

# define the tickers
tickers = ['TSLA', 'META'] 

# define the start and end dates
start_date = datetime(2024, 1, 1)
end_date = datetime(2024, 2, 28)

# dictionary to hold dataframes
dfs = {}

for ticker in tickers:
    # get the data for the stocks
    df = yf.download(ticker, start_date, end_date)

    # get the close price and calculate the cumulative percentage gain
    df['Gain'] = df['Close'].pct_change().cumsum()

    # add to dictionary
    dfs[ticker] = df    

# plot
plt.figure(figsize=(10, 5))
for ticker, df in dfs.items():
    plt.plot(df.index, df['Gain'], label=ticker)

plt.title('YTD Stock Price Gain')
plt.xlabel('Date')
plt.ylabel('Percentage Gain')
plt.legend()

plt.grid(True)
plt.savefig('stock_gains.png')
plt.close()

print("The 'stock_gains.png' file has been successfully saved")
```
This script will download the historical data for TSLA and META from the start of the year to the specified date and calculates the YTD gains. It then generates the plot showing these gains and saves it to 'stock_gains.png'.

Please save the script to a file named 'stock_gains.py' and run it using Python. Remember to have the correct start and end dates for the YTD value when running the script. If your Python version is below 3.8, you should update it to execute this code perfectly.

--------------------------------------------------------------------------------

>>>>>>>> NO HUMAN INPUT RECEIVED.

>>>>>>>> USING AUTO REPLY...

>>>>>>>> EXECUTING CODE BLOCK 0 (inferred language is sh)...

>>>>>>>> EXECUTING CODE BLOCK 1 (inferred language is python)...
code_executor_agent (to code_writer_agent):

exitcode: 0 (execution succeeded)
Code output: 
Requirement already satisfied: yfinance in /Users/ekzhu/miniconda3/envs/autogen/lib/python3.11/site-packages (0.2.36)
Requirement already satisfied: pandas in /Users/ekzhu/miniconda3/envs/autogen/lib/python3.11/site-packages (2.1.4)
Requirement already satisfied: matplotlib in /Users/ekzhu/miniconda3/envs/autogen/lib/python3.11/site-packages (3.8.2)
Requirement already satisfied: numpy>=1.16.5 in /Users/ekzhu/miniconda3/envs/autogen/lib/python3.11/site-packages (from yfinance) (1.26.2)
Requirement already satisfied: requests>=2.31 in /Users/ekzhu/miniconda3/envs/autogen/lib/python3.11/site-packages (from yfinance) (2.31.0)
Requirement already satisfied: multitasking>=0.0.7 in /Users/ekzhu/miniconda3/envs/autogen/lib/python3.11/site-packages (from yfinance) (0.0.11)
Requirement already satisfied: lxml>=4.9.1 in /Users/ekzhu/miniconda3/envs/autogen/lib/python3.11/site-packages (from yfinance) (5.0.1)
Requirement already satisfied: appdirs>=1.4.4 in /Users/ekzhu/miniconda3/envs/autogen/lib/python3.11/site-packages (from yfinance) (1.4.4)
Requirement already satisfied: pytz>=2022.5 in /Users/ekzhu/miniconda3/envs/autogen/lib/python3.11/site-packages (from yfinance) (2023.3.post1)
Requirement already satisfied: frozendict>=2.3.4 in /Users/ekzhu/miniconda3/envs/autogen/lib/python3.11/site-packages (from yfinance) (2.4.0)
Requirement already satisfied: peewee>=3.16.2 in /Users/ekzhu/miniconda3/envs/autogen/lib/python3.11/site-packages (from yfinance) (3.17.0)
Requirement already satisfied: beautifulsoup4>=4.11.1 in /Users/ekzhu/miniconda3/envs/autogen/lib/python3.11/site-packages (from yfinance) (4.12.2)
Requirement already satisfied: html5lib>=1.1 in /Users/ekzhu/miniconda3/envs/autogen/lib/python3.11/site-packages (from yfinance) (1.1)
Requirement already satisfied: python-dateutil>=2.8.2 in /Users/ekzhu/miniconda3/envs/autogen/lib/python3.11/site-packages (from pandas) (2.8.2)
Requirement already satisfied: tzdata>=2022.1 in /Users/ekzhu/miniconda3/envs/autogen/lib/python3.11/site-packages (from pandas) (2023.4)
Requirement already satisfied: contourpy>=1.0.1 in /Users/ekzhu/miniconda3/envs/autogen/lib/python3.11/site-packages (from matplotlib) (1.2.0)
Requirement already satisfied: cycler>=0.10 in /Users/ekzhu/miniconda3/envs/autogen/lib/python3.11/site-packages (from matplotlib) (0.12.1)
Requirement already satisfied: fonttools>=4.22.0 in /Users/ekzhu/miniconda3/envs/autogen/lib/python3.11/site-packages (from matplotlib) (4.47.2)
Requirement already satisfied: kiwisolver>=1.3.1 in /Users/ekzhu/miniconda3/envs/autogen/lib/python3.11/site-packages (from matplotlib) (1.4.5)
Requirement already satisfied: packaging>=20.0 in /Users/ekzhu/miniconda3/envs/autogen/lib/python3.11/site-packages (from matplotlib) (23.2)
Requirement already satisfied: pillow>=8 in /Users/ekzhu/miniconda3/envs/autogen/lib/python3.11/site-packages (from matplotlib) (10.2.0)
Requirement already satisfied: pyparsing>=2.3.1 in /Users/ekzhu/miniconda3/envs/autogen/lib/python3.11/site-packages (from matplotlib) (3.1.1)
Requirement already satisfied: soupsieve>1.2 in /Users/ekzhu/miniconda3/envs/autogen/lib/python3.11/site-packages (from beautifulsoup4>=4.11.1->yfinance) (2.5)
Requirement already satisfied: six>=1.9 in /Users/ekzhu/miniconda3/envs/autogen/lib/python3.11/site-packages (from html5lib>=1.1->yfinance) (1.16.0)
Requirement already satisfied: webencodings in /Users/ekzhu/miniconda3/envs/autogen/lib/python3.11/site-packages (from html5lib>=1.1->yfinance) (0.5.1)
Requirement already satisfied: charset-normalizer<4,>=2 in /Users/ekzhu/miniconda3/envs/autogen/lib/python3.11/site-packages (from requests>=2.31->yfinance) (3.3.2)
Requirement already satisfied: idna<4,>=2.5 in /Users/ekzhu/miniconda3/envs/autogen/lib/python3.11/site-packages (from requests>=2.31->yfinance) (3.6)
Requirement already satisfied: urllib3<3,>=1.21.1 in /Users/ekzhu/miniconda3/envs/autogen/lib/python3.11/site-packages (from requests>=2.31->yfinance) (2.1.0)
Requirement already satisfied: certifi>=2017.4.17 in /Users/ekzhu/miniconda3/envs/autogen/lib/python3.11/site-packages (from requests>=2.31->yfinance) (2024.2.2)

The 'stock_gains.png' file has been successfully saved


--------------------------------------------------------------------------------

>>>>>>>> USING AUTO REPLY...
code_writer_agent (to code_executor_agent):

Great! The code executed successfully and the 'stock_gains.png' file has been saved successfully. This file contains the plot of TSLA's and META's stock price gains from the start of the year until February 28, 2024. You should now be able to view this image file in the same directory that you ran the script from. 

Please make sure to verify this image file. It should contain two plotted lines, each representing the percentage gain over the time for each stock (TSLA and META). The x-axis represents the date, and the y-axis represents the percentage gain. If everything looks correct, this would be the end of the task.

TERMINATE

--------------------------------------------------------------------------------


In the previous conversation, the code writer agent generated a code block to install necessary packages and another code block for a script to fetch the stock price and calculate gains year-to-date for Tesla and Meta. The code executor agent installed the packages, executed the script, and returned the results.

Let’s take a look at the chart that was generated.

from IPython.display import Image

Image(os.path.join(temp_dir, "stock_gains.png"))



Because code execution leave traces like code files and output in the file system, we may want to clean up the working directory after each conversation concludes.

temp_dir.cleanup()

Stop the docker command line executor to clean up the docker container.

executor.stop()  # Stop the docker command line code executor.

Command Line or Jupyter Code Executor?
The command line code executor does not keep any state in memory between executions of different code blocks it receives, as it writes each code block to a separate file and executes the code block in a new process.

Contrast to the command line code executor, the Jupyter code executor runs all code blocks in the same Jupyter kernel, which keeps the state in memory between executions. See the topic page for Jupyter Code Executor.

The choice between command line and Jupyter code executor depends on the nature of the code blocks in agents’ conversation. If each code block is a “script” that does not use variables from previous code blocks, the command line code executor is a good choice. If some code blocks contain expensive computations (e.g., training a machine learning model and loading a large amount of data), and you want to keep the state in memory to avoid repeated computations, the Jupyter code executor is a better choice.

Note on User Proxy Agent and Assistant Agent
User Proxy Agent
In the previous examples, we create the code executor agent directly using the ConversableAgent class. Existing AutoGen examples often create code executor agent using the UserProxyAgent class, which is a subclass of ConversableAgent with human_input_mode=ALWAYS and llm_config=False – it always requests human input for every message and does not use LLM. It also comes with default description field for each of the human_input_mode setting. This class is a convenient short-cut for creating an agent that is intended to be used as a code executor.

Assistant Agent
In the previous examples, we created the code writer agent directly using the ConversableAgent class. Existing AutoGen examples often create the code writer agent using the AssistantAgent class, which is a subclass of ConversableAgent with human_input_mode=NEVER and code_execution_config=False – it never requests human input and does not use code executor. It also comes with default system_message and description fields. This class is a convenient short-cut for creating an agent that is intended to be used as a code writer and does not execute code.

In fact, in the previous example we use the default system_message field of the AssistantAgent class to instruct the code writer agent how to use code executor.

import pprint

from autogen import AssistantAgent

pprint.pprint(AssistantAgent.DEFAULT_SYSTEM_MESSAGE)

('You are a helpful AI assistant.\n'
 'Solve tasks using your coding and language skills.\n'
 'In the following cases, suggest python code (in a python coding block) or '
 'shell script (in a sh coding block) for the user to execute.\n'
 '    1. When you need to collect info, use the code to output the info you '
 'need, for example, browse or search the web, download/read a file, print the '
 'content of a webpage or a file, get the current date/time, check the '
 'operating system. After sufficient info is printed and the task is ready to '
 'be solved based on your language skill, you can solve the task by yourself.\n'
 '    2. When you need to perform some task with code, use the code to perform '
 'the task and output the result. Finish the task smartly.\n'
 'Solve the task step by step if you need to. If a plan is not provided, '
 'explain your plan first. Be clear which step uses code, and which step uses '
 'your language skill.\n'
 'When using code, you must indicate the script type in the code block. The '
 'user cannot provide any other feedback or perform any other action beyond '
 "executing the code you suggest. The user can't modify your code. So do not "
 "suggest incomplete code which requires users to modify. Don't use a code "
 "block if it's not intended to be executed by the user.\n"
 'If you want the user to save the code in a file before executing it, put # '
 "filename: <filename> inside the code block as the first line. Don't include "
 'multiple code blocks in one response. Do not ask users to copy and paste the '
 "result. Instead, use 'print' function for the output when relevant. Check "
 'the execution result returned by the user.\n'
 'If the result indicates there is an error, fix the error and output the code '
 'again. Suggest the full code instead of partial code or code changes. If the '
 "error can't be fixed or if the task is not solved even after the code is "
 'executed successfully, analyze the problem, revisit your assumption, collect '
 'additional info you need, and think of a different approach to try.\n'
 'When you find an answer, verify the answer carefully. Include verifiable '
 'evidence in your response if possible.\n'
 'Reply "TERMINATE" in the end when everything is done.\n'
 '    ')

Best Practice
It is very important to note that the UserProxyAgent and AssistantAgent are meant to be shortcuts to avoid writing the system_message instructions for the ConversableAgent class. They are not suitable for all use cases. As we will show in the next chapter, tuning the system_message field is vital for agent to work properly in more complex conversation patterns beyond two-agent chat.

As a best practice, always tune your agent’s system_message instructions for your specific use case and avoid subclassing UserProxyAgent and AssistantAgent.

Summary
In this chapter, we introduced code executors, how to set up Docker and local execution, and how to use code execution in a conversation to solve tasks. In the next chapter, we will introduce tool use, which is similar to code executors but restricts what code an agent can execute.


Tool Use
Open In Colab Open on GitHub

In the previous chapter, we explored code executors which give agents the super power of programming. Agents writing arbitrary code is useful, however, controlling what code an agent writes can be challenging. This is where tools come in.

Tools are pre-defined functions that agents can use. Instead of writing arbitrary code, agents can call tools to perform actions, such as searching the web, performing calculations, reading files, or calling remote APIs. Because you can control what tools are available to an agent, you can control what actions an agent can perform.

NOTE
Tool use is currently only available for LLMs that support OpenAI-comaptible tool call API.

Creating Tools
Tools can be created as regular Python functions. For example, let’s create a calculator tool which can only perform a single operation at a time.

from typing import Annotated, Literal

Operator = Literal["+", "-", "*", "/"]


def calculator(a: int, b: int, operator: Annotated[Operator, "operator"]) -> int:
    if operator == "+":
        return a + b
    elif operator == "-":
        return a - b
    elif operator == "*":
        return a * b
    elif operator == "/":
        return int(a / b)
    else:
        raise ValueError("Invalid operator")

The above function takes three arguments: a and b are the integer numbers to be operated on; operator is the operation to be performed. We used type hints to define the types of the arguments and the return value.

TIP
Always use type hints to define the types of the arguments and the return value as they provide helpful hints to the agent about the tool's usage.

Registering Tools
Once you have created a tool, you can register it with the agents that are involved in conversation.

import os

from autogen import ConversableAgent

# Let's first define the assistant agent that suggests tool calls.
assistant = ConversableAgent(
    name="Assistant",
    system_message="You are a helpful AI assistant. "
    "You can help with simple calculations. "
    "Return 'TERMINATE' when the task is done.",
    llm_config={"config_list": [{"model": "gpt-4", "api_key": os.environ["OPENAI_API_KEY"]}]},
)

# The user proxy agent is used for interacting with the assistant agent
# and executes tool calls.
user_proxy = ConversableAgent(
    name="User",
    llm_config=False,
    is_termination_msg=lambda msg: msg.get("content") is not None and "TERMINATE" in msg["content"],
    human_input_mode="NEVER",
)

# Register the tool signature with the assistant agent.
assistant.register_for_llm(name="calculator", description="A simple calculator")(calculator)

# Register the tool function with the user proxy agent.
user_proxy.register_for_execution(name="calculator")(calculator)


<function __main__.calculator(a: int, b: int, operator: Annotated[Literal['+', '-', '*', '/'], 'operator']) -> int>


In the above code, we registered the calculator function as a tool with the assistant and user proxy agents. We also provide a name and a description for the tool for the assistant agent to understand its usage.

TIP
Always provide a clear and concise description for the tool as it helps the agent's underlying LLM to understand the tool's usage.

Similar to code executors, a tool must be registered with at least two agents for it to be useful in conversation. The agent registered with the tool’s signature through register_for_llm can call the tool; the agent registered with the tool’s function object through register_for_execution can execute the tool’s function.

Alternatively, you can use autogen.register_function function to register a tool with both agents at once.

from autogen import register_function

# Register the calculator function to the two agents.
register_function(
    calculator,
    caller=assistant,  # The assistant agent can suggest calls to the calculator.
    executor=user_proxy,  # The user proxy agent can execute the calculator calls.
    name="calculator",  # By default, the function name is used as the tool name.
    description="A simple calculator",  # A description of the tool.
)

Using Tool
Once the tool is registered, we can use it in conversation. In the code below, we ask the assistant to perform some arithmetic calculation using the calculator tool.

chat_result = user_proxy.initiate_chat(assistant, message="What is (44232 + 13312 / (232 - 32)) * 5?")


User (to Assistant):

What is (44232 + 13312 / (232 - 32)) * 5?

--------------------------------------------------------------------------------

>>>>>>>> USING AUTO REPLY...
Assistant (to User):

***** Suggested tool call (call_4rElPoLggOYJmkUutbGaSTX1): calculator *****
Arguments: 
{
  "a": 232,
  "b": 32,
  "operator": "-"
}
***************************************************************************

--------------------------------------------------------------------------------

>>>>>>>> EXECUTING FUNCTION calculator...
User (to Assistant):

User (to Assistant):

***** Response from calling tool (call_4rElPoLggOYJmkUutbGaSTX1) *****
200
**********************************************************************

--------------------------------------------------------------------------------

>>>>>>>> USING AUTO REPLY...
Assistant (to User):

***** Suggested tool call (call_SGtr8tK9A4iOCJGdCqkKR2Ov): calculator *****
Arguments: 
{
  "a": 13312,
  "b": 200,
  "operator": "/"
}
***************************************************************************

--------------------------------------------------------------------------------

>>>>>>>> EXECUTING FUNCTION calculator...
User (to Assistant):

User (to Assistant):

***** Response from calling tool (call_SGtr8tK9A4iOCJGdCqkKR2Ov) *****
66
**********************************************************************

--------------------------------------------------------------------------------

>>>>>>>> USING AUTO REPLY...
Assistant (to User):

***** Suggested tool call (call_YsR95CM1Ice2GZ7ZoStYXI6M): calculator *****
Arguments: 
{
  "a": 44232,
  "b": 66,
  "operator": "+"
}
***************************************************************************

--------------------------------------------------------------------------------

>>>>>>>> EXECUTING FUNCTION calculator...
User (to Assistant):

User (to Assistant):

***** Response from calling tool (call_YsR95CM1Ice2GZ7ZoStYXI6M) *****
44298
**********************************************************************

--------------------------------------------------------------------------------

>>>>>>>> USING AUTO REPLY...
Assistant (to User):

***** Suggested tool call (call_oqZn4rTjyvXYcmjAXkvVaJm1): calculator *****
Arguments: 
{
  "a": 44298,
  "b": 5,
  "operator": "*"
}
***************************************************************************

--------------------------------------------------------------------------------

>>>>>>>> EXECUTING FUNCTION calculator...
User (to Assistant):

User (to Assistant):

***** Response from calling tool (call_oqZn4rTjyvXYcmjAXkvVaJm1) *****
221490
**********************************************************************

--------------------------------------------------------------------------------

>>>>>>>> USING AUTO REPLY...
Assistant (to User):

The result of the calculation is 221490. TERMINATE

--------------------------------------------------------------------------------

Let’s verify the answer:

(44232 + int(13312 / (232 - 32))) * 5

221490

The answer is correct. You can see that the assistant is able to understand the tool’s usage and perform calculation correctly.

Tool Schema
If you are familiar with OpenAI’s tool use API, you might be wondering why we didn’t create a tool schema. In fact, the tool schema is automatically generated from the function signature and the type hints. You can see the tool schema by inspecting the llm_config attribute of the agent.

assistant.llm_config["tools"]

[{'type': 'function',
  'function': {'description': 'A simple calculator',
   'name': 'calculator',
   'parameters': {'type': 'object',
    'properties': {'a': {'type': 'integer', 'description': 'a'},
     'b': {'type': 'integer', 'description': 'b'},
     'operator': {'enum': ['+', '-', '*', '/'],
      'type': 'string',
      'description': 'operator'}},
    'required': ['a', 'b', 'operator']}}}]

You can see the tool schema has been automatically generated from the function signature and the type hints, as well as the description. This is why it is important to use type hints and provide a clear description for the tool as the LLM uses them to understand the tool’s usage.

You can also use Pydantic model for the type hints to provide more complex type schema. In the example below, we use a Pydantic model to define the calculator input.

from pydantic import BaseModel, Field


class CalculatorInput(BaseModel):
    a: Annotated[int, Field(description="The first number.")]
    b: Annotated[int, Field(description="The second number.")]
    operator: Annotated[Operator, Field(description="The operator.")]


def calculator(input: Annotated[CalculatorInput, "Input to the calculator."]) -> int:
    if input.operator == "+":
        return input.a + input.b
    elif input.operator == "-":
        return input.a - input.b
    elif input.operator == "*":
        return input.a * input.b
    elif input.operator == "/":
        return int(input.a / input.b)
    else:
        raise ValueError("Invalid operator")

Same as before, we register the tool with the agents using the name "calculator".

TIP
Registering tool to the same name will override the previous tool.

assistant.register_for_llm(name="calculator", description="A calculator tool that accepts nested expression as input")(
    calculator
)
user_proxy.register_for_execution(name="calculator")(calculator)


<function __main__.calculator(input: typing.Annotated[__main__.CalculatorInput, 'Input to the calculator.']) -> int>


You can see the tool schema has been updated to reflect the new type schema.

assistant.llm_config["tools"]

[{'type': 'function',
  'function': {'description': 'A calculator tool that accepts nested expression as input',
   'name': 'calculator',
   'parameters': {'type': 'object',
    'properties': {'input': {'properties': {'a': {'description': 'The first number.',
        'title': 'A',
        'type': 'integer'},
       'b': {'description': 'The second number.',
        'title': 'B',
        'type': 'integer'},
       'operator': {'description': 'The operator.',
        'enum': ['+', '-', '*', '/'],
        'title': 'Operator',
        'type': 'string'}},
      'required': ['a', 'b', 'operator'],
      'title': 'CalculatorInput',
      'type': 'object',
      'description': 'Input to the calculator.'}},
    'required': ['input']}}}]

Let’s use the tool in conversation.

chat_result = user_proxy.initiate_chat(assistant, message="What is (1423 - 123) / 3 + (32 + 23) * 5?")


User (to Assistant):

What is (1423 - 123) / 3 + (32 + 23) * 5?

--------------------------------------------------------------------------------

>>>>>>>> USING AUTO REPLY...
Assistant (to User):

***** Suggested tool call (call_Uu4diKtxlTfkwXuY6MmJEb4E): calculator *****
Arguments: 
{
    "input": {
        "a": (1423 - 123) / 3,
        "b": (32 + 23) * 5,
        "operator": "+"
    }
}
***************************************************************************

--------------------------------------------------------------------------------
User (to Assistant):

User (to Assistant):

***** Response from calling tool (call_Uu4diKtxlTfkwXuY6MmJEb4E) *****
Error: Expecting value: line 1 column 29 (char 28)
 You argument should follow json format.
**********************************************************************

--------------------------------------------------------------------------------

>>>>>>>> USING AUTO REPLY...
Assistant (to User):

I apologize for the confusion, I seem to have made a mistake. Let me recalculate the expression properly.

First, we need to do the calculations within the brackets. So, calculating (1423 - 123), (32 + 23), and then performing remaining operations.
***** Suggested tool call (call_mx3M3fNOwikFNoqSojDH1jIr): calculator *****
Arguments: 
{
    "input": {
        "a": 1423,
        "b": 123,
        "operator": "-"
    }
}
***************************************************************************

--------------------------------------------------------------------------------

>>>>>>>> EXECUTING FUNCTION calculator...
User (to Assistant):

User (to Assistant):

***** Response from calling tool (call_mx3M3fNOwikFNoqSojDH1jIr) *****
1300
**********************************************************************

--------------------------------------------------------------------------------

>>>>>>>> USING AUTO REPLY...
Assistant (to User):

***** Suggested tool call (call_hBAL2sYi6Y5ZtTHCNPCmxdN3): calculator *****
Arguments: 
{
    "input": {
        "a": 32,
        "b": 23,
        "operator": "+"
    }
}
***************************************************************************

--------------------------------------------------------------------------------

>>>>>>>> EXECUTING FUNCTION calculator...
User (to Assistant):

User (to Assistant):

***** Response from calling tool (call_hBAL2sYi6Y5ZtTHCNPCmxdN3) *****
55
**********************************************************************

--------------------------------------------------------------------------------

>>>>>>>> USING AUTO REPLY...
Assistant (to User):

***** Suggested tool call (call_wO3AP7EDeJvsVLCpvv5LohUa): calculator *****
Arguments: 
{
    "input": {
        "a": 1300,
        "b": 3,
        "operator": "/"
    }
}
***************************************************************************

--------------------------------------------------------------------------------

>>>>>>>> EXECUTING FUNCTION calculator...
User (to Assistant):

User (to Assistant):

***** Response from calling tool (call_wO3AP7EDeJvsVLCpvv5LohUa) *****
433
**********************************************************************

--------------------------------------------------------------------------------

>>>>>>>> USING AUTO REPLY...
Assistant (to User):

***** Suggested tool call (call_kQ2hDhqem8BHNlaHaE9ezvvQ): calculator *****
Arguments: 
{
    "input": {
        "a": 55,
        "b": 5,
        "operator": "*"
    }
}
***************************************************************************

--------------------------------------------------------------------------------

>>>>>>>> EXECUTING FUNCTION calculator...
User (to Assistant):

User (to Assistant):

***** Response from calling tool (call_kQ2hDhqem8BHNlaHaE9ezvvQ) *****
275
**********************************************************************

--------------------------------------------------------------------------------

>>>>>>>> USING AUTO REPLY...
Assistant (to User):

***** Suggested tool call (call_1FLDUdvAZmjlSD7g5GFFJOpO): calculator *****
Arguments: 
{
    "input": {
        "a": 433,
        "b": 275,
        "operator": "+"
    }
}
***************************************************************************

--------------------------------------------------------------------------------

>>>>>>>> EXECUTING FUNCTION calculator...
User (to Assistant):

User (to Assistant):

***** Response from calling tool (call_1FLDUdvAZmjlSD7g5GFFJOpO) *****
708
**********************************************************************

--------------------------------------------------------------------------------

>>>>>>>> USING AUTO REPLY...
Assistant (to User):

The calculation result of the expression (1423 - 123) / 3 + (32 + 23) * 5 is 708. Let's proceed to the next task.
TERMINATE

--------------------------------------------------------------------------------


Let’s verify the answer:

int((1423 - 123) / 3) + (32 + 23) * 5

708

Again, the answer is correct. You can see that the assistant is able to understand the new tool schema and perform calculation correctly.

How to hide tool usage and code execution within a single agent?
Sometimes it is preferable to hide the tool usage inside a single agent, i.e., the tool call and tool response messages are kept invisible from outside of the agent, and the agent responds to outside messages with tool usages as “internal monologues”. For example, you might want build an agent that is similar to the OpenAI’s Assistant which executes built-in tools internally.

To achieve this, you can use nested chats. Nested chats allow you to create “internal monologues” within an agent to call and execute tools. This works for code execution as well. See nested chats for tool use for an example.

Summary
In this chapter, we showed you how to create, register and use tools. Tools allows agents to perform actions without writing arbitrary code. In the next chapter, we will introduce conversation patterns, and show how to use the result of a conversation.

Conversation Patterns
Open In Colab Open on GitHub

In the previous chapter we used two-agent conversation, which can be started by the initiate_chat method. Two-agent chat is a useful conversation pattern but AutoGen offers more. In this chapter, we will first dig a little bit more into the two-agent chat pattern and chat result, then we will show you several conversation patterns that involve more than two agents.

An Overview
Two-agent chat: the simplest form of conversation pattern where two agents chat with each other.
Sequential chat: a sequence of chats between two agents, chained together by a carryover mechanism, which brings the summary of the previous chat to the context of the next chat.
Group Chat: a single chat involving more than two agents. An important question in group chat is: What agent should be next to speak? To support different scenarios, we provide different ways to organize agents in a group chat:
We support several strategies to select the next agent: round_robin, random, manual (human selection), and auto (Default, using an LLM to decide).
We provide a way to constrain the selection of the next speaker (See examples below).
We allow you to pass in a function to customize the selection of the next speaker. With this feature, you can build a StateFlow model which allows a deterministic workflow among your agents. Please refer to this guide and this blog post on StateFlow for more details.
Nested Chat: package a workflow into a single agent for reuse in a larger workflow.
Two-Agent Chat and Chat Result
Two-agent chat is the simplest form of conversation pattern. We start a two-agent chat using the initiate_chat method of every ConversableAgent agent. We have already seen multiple examples of two-agent chats in previous chapters but we haven’t covered the details.

The following figure illustrates how two-agent chat works.

Two-agent chat

A two-agent chats takes two inputs: a message, which is a string provided by the caller; a context, which specifies various parameters of the chat. The sender agent uses its chat initializer method (i.e., generate_init_message method of ConversableAgent) to generate an initial message from the inputs, and sends it to the recipient agent to start the chat. The sender agent is the agent whose initiate_chat method is called, and the recipient agent is the other agent.

Once the chat terminates, the history of the chat is processed by a chat summarizer. The summarizer summarizes the chat history and calculates the token usage of the chat. You can configure the type of summary using the summary_method parameter of the initiate_chat method. By default, it is the last message of the chat (i.e., summary_method='last_msg').

The example below is a two-agent chat between a student agent and a teacher agent. Its summarizer uses an LLM-based summary.

import os

from autogen import ConversableAgent

student_agent = ConversableAgent(
    name="Student_Agent",
    system_message="You are a student willing to learn.",
    llm_config={"config_list": [{"model": "gpt-4", "api_key": os.environ["OPENAI_API_KEY"]}]},
)
teacher_agent = ConversableAgent(
    name="Teacher_Agent",
    system_message="You are a math teacher.",
    llm_config={"config_list": [{"model": "gpt-4", "api_key": os.environ["OPENAI_API_KEY"]}]},
)

chat_result = student_agent.initiate_chat(
    teacher_agent,
    message="What is triangle inequality?",
    summary_method="reflection_with_llm",
    max_turns=2,
)

Student_Agent (to Teacher_Agent):

What is triangle inequality?

--------------------------------------------------------------------------------

>>>>>>>> USING AUTO REPLY...
Teacher_Agent (to Student_Agent):

Triangle inequality theorem is a fundamental principle in geometry that states that the sum of the lengths of any two sides of a triangle must always be greater than the length of the third side. In a triangle with sides of lengths a, b, and c, the theorem can be written as:

a + b > c
a + c > b
b + c > a

Each of these represents the condition for one specific side (a, b, or c). All must be true for a triangle to exist.

--------------------------------------------------------------------------------

>>>>>>>> USING AUTO REPLY...
Student_Agent (to Teacher_Agent):

Thank you for the explanation. This theorem helps in understanding the basic properties of a triangle. It can also be useful when solving geometric problems or proving other mathematical theorems. Can you give me an example of how we can use the triangle inequality theorem?

--------------------------------------------------------------------------------

>>>>>>>> USING AUTO REPLY...
Teacher_Agent (to Student_Agent):

Absolutely! Here's an example:

Suppose you're given three line segments with lengths 10, 7, and 3 units. The question is: "Can these three line segments form a triangle?"

To answer this, you would use the triangle inequality theorem. Adding any two side lengths together should be greater than the third:

- For sides 10 and 7: 10 + 7 = 17, which is larger than 3.
- For sides 10 and 3: 10 + 3 = 13, which is larger than 7.
- For sides 7 and 3: 7 + 3 = 10, which is equal to the length of the third side (10), but not greater.

So, these three lines cannot form a triangle, because not all pairs of sides satisfy the triangle inequality theorem.

--------------------------------------------------------------------------------


Let’s see what the summary looks like. The summary is stored in the chat_result object of the type ChatResult that was returned by the initiate_chat method.

print(chat_result.summary)

The triangle inequality theorem states that in a triangle, the sum of the lengths of any two sides must always be greater than the length of the third side. This principle is significant in geometry and is used in solving problems or proving theorems. For instance, if given three line segments, you can determine if they can form a triangle using this theorem.


In the above example, the summary method is set to reflection_with_llm which takes a list of messages from the conversation and summarize them using a call to an LLM. The summary method first tries to use the recipient’s LLM, if it is not available then it uses the sender’s LLM. In this case the recipient is “Teacher_Agent” and the sender is “Student_Agent”. The input prompt for the LLM is the following default prompt:

print(ConversableAgent.DEFAULT_SUMMARY_PROMPT)

Summarize the takeaway from the conversation. Do not add any introductory phrases.

You can also use a custom prompt by setting the summary_prompt argument of initiate_chat.

There are some other useful information in the ChatResult object, including the conversation history, human input, and token cost.

# Get the chat history.
import pprint

pprint.pprint(chat_result.chat_history)

[{'content': 'What is triangle inequality?', 'role': 'assistant'},
 {'content': 'Triangle inequality theorem is a fundamental principle in '
             'geometry that states that the sum of the lengths of any two '
             'sides of a triangle must always be greater than the length of '
             'the third side. In a triangle with sides of lengths a, b, and c, '
             'the theorem can be written as:\n'
             '\n'
             'a + b > c\n'
             'a + c > b\n'
             'b + c > a\n'
             '\n'
             'Each of these represents the condition for one specific side (a, '
             'b, or c). All must be true for a triangle to exist.',
  'role': 'user'},
 {'content': 'Thank you for the explanation. This theorem helps in '
             'understanding the basic properties of a triangle. It can also be '
             'useful when solving geometric problems or proving other '
             'mathematical theorems. Can you give me an example of how we can '
             'use the triangle inequality theorem?',
  'role': 'assistant'},
 {'content': "Absolutely! Here's an example:\n"
             '\n'
             "Suppose you're given three line segments with lengths 10, 7, and "
             '3 units. The question is: "Can these three line segments form a '
             'triangle?"\n'
             '\n'
             'To answer this, you would use the triangle inequality theorem. '
             'Adding any two side lengths together should be greater than the '
             'third:\n'
             '\n'
             '- For sides 10 and 7: 10 + 7 = 17, which is larger than 3.\n'
             '- For sides 10 and 3: 10 + 3 = 13, which is larger than 7.\n'
             '- For sides 7 and 3: 7 + 3 = 10, which is equal to the length of '
             'the third side (10), but not greater.\n'
             '\n'
             'So, these three lines cannot form a triangle, because not all '
             'pairs of sides satisfy the triangle inequality theorem.',
  'role': 'user'}]

That chat messages in the chat result are from the recipient agent’s perspective – the sender is the “assistant” and the recipient is the “user”.

# Get the cost of the chat.
pprint.pprint(chat_result.cost)

({'gpt-4-0613': {'completion_tokens': 399,
                 'cost': 0.04521,
                 'prompt_tokens': 709,
                 'total_tokens': 1108},
  'total_cost': 0.04521},
 {'total_cost': 0})

Sequential Chats
The name of this pattern is self-explanatory – it is a sequence of chats between two agents, chained together by a mechanism called carryover, which brings the summary of the previous chat to the context of the next chat.

This pattern is useful for complex task that can be broken down into interdependent sub-tasks. The figure below illustrate how this pattern works.

initiate_chats

In this pattern, the a pair of agents first start a two-agent chat, then the summary of the conversation becomes a carryover for the next two-agent chat. The next chat passes the carryover to the carryover parameter of the context to generate its initial message.

Carryover accumulates as the conversation moves forward, so each subsequent chat starts with all the carryovers from previous chats.

The figure above shows distinct recipient agents for all the chats, however, the recipient agents in the sequence are allowed to repeat.

To illustrate this pattern, let’s consider a simple example of arithmetic operator agents. One agent (called the “Number_Agent”) is responsible for coming up with a number, and other agents are responsible for performing a specific arithmetic operation on the number, e.g., add 1, multiply by 2, etc..

# The Number Agent always returns the same numbers.
number_agent = ConversableAgent(
    name="Number_Agent",
    system_message="You return me the numbers I give you, one number each line.",
    llm_config={"config_list": [{"model": "gpt-4", "api_key": os.environ["OPENAI_API_KEY"]}]},
    human_input_mode="NEVER",
)

# The Adder Agent adds 1 to each number it receives.
adder_agent = ConversableAgent(
    name="Adder_Agent",
    system_message="You add 1 to each number I give you and return me the new numbers, one number each line.",
    llm_config={"config_list": [{"model": "gpt-4", "api_key": os.environ["OPENAI_API_KEY"]}]},
    human_input_mode="NEVER",
)

# The Multiplier Agent multiplies each number it receives by 2.
multiplier_agent = ConversableAgent(
    name="Multiplier_Agent",
    system_message="You multiply each number I give you by 2 and return me the new numbers, one number each line.",
    llm_config={"config_list": [{"model": "gpt-4", "api_key": os.environ["OPENAI_API_KEY"]}]},
    human_input_mode="NEVER",
)

# The Subtracter Agent subtracts 1 from each number it receives.
subtracter_agent = ConversableAgent(
    name="Subtracter_Agent",
    system_message="You subtract 1 from each number I give you and return me the new numbers, one number each line.",
    llm_config={"config_list": [{"model": "gpt-4", "api_key": os.environ["OPENAI_API_KEY"]}]},
    human_input_mode="NEVER",
)

# The Divider Agent divides each number it receives by 2.
divider_agent = ConversableAgent(
    name="Divider_Agent",
    system_message="You divide each number I give you by 2 and return me the new numbers, one number each line.",
    llm_config={"config_list": [{"model": "gpt-4", "api_key": os.environ["OPENAI_API_KEY"]}]},
    human_input_mode="NEVER",
)


The Number Agent chats with the first operator agent, then the second operator agent, and so on. After each chat, the last message in the conversation (i.e., the result of the arithmetic operation from the operator agent) is used as the summary of the chat. This is specified by the summary_method parameter. In the end we will have the result of the arithmetic operations.

# Start a sequence of two-agent chats.
# Each element in the list is a dictionary that specifies the arguments
# for the initiate_chat method.
chat_results = number_agent.initiate_chats(
    [
        {
            "recipient": adder_agent,
            "message": "14",
            "max_turns": 2,
            "summary_method": "last_msg",
        },
        {
            "recipient": multiplier_agent,
            "message": "These are my numbers",
            "max_turns": 2,
            "summary_method": "last_msg",
        },
        {
            "recipient": subtracter_agent,
            "message": "These are my numbers",
            "max_turns": 2,
            "summary_method": "last_msg",
        },
        {
            "recipient": divider_agent,
            "message": "These are my numbers",
            "max_turns": 2,
            "summary_method": "last_msg",
        },
    ]
)


********************************************************************************
Start a new chat with the following message: 
14

With the following carryover: 


********************************************************************************
Number_Agent (to Adder_Agent):

14

--------------------------------------------------------------------------------
Adder_Agent (to Number_Agent):

15

--------------------------------------------------------------------------------
Number_Agent (to Adder_Agent):

15

--------------------------------------------------------------------------------
Adder_Agent (to Number_Agent):

16

--------------------------------------------------------------------------------

********************************************************************************
Start a new chat with the following message: 
These are my numbers

With the following carryover: 
16

********************************************************************************
Number_Agent (to Multiplier_Agent):

These are my numbers
Context: 
16

--------------------------------------------------------------------------------
Multiplier_Agent (to Number_Agent):

32

--------------------------------------------------------------------------------
Number_Agent (to Multiplier_Agent):

32

--------------------------------------------------------------------------------
Multiplier_Agent (to Number_Agent):

64

--------------------------------------------------------------------------------

********************************************************************************
Start a new chat with the following message: 
These are my numbers

With the following carryover: 
16
64

********************************************************************************
Number_Agent (to Subtracter_Agent):

These are my numbers
Context: 
16
64

--------------------------------------------------------------------------------
Subtracter_Agent (to Number_Agent):

15
63

--------------------------------------------------------------------------------
Number_Agent (to Subtracter_Agent):

15
63

--------------------------------------------------------------------------------
Subtracter_Agent (to Number_Agent):

14
62

--------------------------------------------------------------------------------

********************************************************************************
Start a new chat with the following message: 
These are my numbers

With the following carryover: 
16
64
14
62

********************************************************************************
Number_Agent (to Divider_Agent):

These are my numbers
Context: 
16
64
14
62

--------------------------------------------------------------------------------
Divider_Agent (to Number_Agent):

8
32
7
31

--------------------------------------------------------------------------------
Number_Agent (to Divider_Agent):

8
32
7
31

--------------------------------------------------------------------------------
Divider_Agent (to Number_Agent):

4
16
3.5
15.5

--------------------------------------------------------------------------------

First thing to note is that the initiate_chats method takes a list of dictionaries, each dictionary contains the arguments for the initiate_chat method.

Second, each chat in the sequence has a maximum round of 2, as specified with the setting max_turns=2, which means each arithmetic operation is performed twice. So you can see in the first chat the number 14 becomes 15 and then 16, in the second chat the number 16 becomes 32 and then 64, and so on.

Third, the carryover accumulates as the chats go on. In the second chat, the carryover is the summary of the first chat “16”. In the third chat, the carryover is the summary of the first and second chat, which is the list “16” and “64”, and both numbers are operated upon. In the forth and last chat, the carryover is the summary of all previous chats, which is the list “16”, “64”, “14” and “62”, and all of these numbers are operated upon.

The final note is that the initiate_chats method returns a list of ChatResult objects, one for each chat in the sequence.

print("First Chat Summary: ", chat_results[0].summary)
print("Second Chat Summary: ", chat_results[1].summary)
print("Third Chat Summary: ", chat_results[2].summary)
print("Fourth Chat Summary: ", chat_results[3].summary)

First Chat Summary:  16
Second Chat Summary:  64
Third Chat Summary:  14
62
Fourth Chat Summary:  4
16
3.5
15.5

Besides calling initiate_chats from the same sender agent, you can also call a high-level function autogen.agentchat.initiate_chats to start a sequence of two-agent chats with different sender agents. This function allows you to specify the sender agent for each chat in the sequence.

Group Chat
So far we have only seen conversation patterns that involve two agents or a sequence of two-agent chats. AutoGen provides a more general conversation pattern called group chat, which involves more than two agents. The core idea of group chat is that all agents contribute to a single conversation thread and share the same context. This is useful for tasks that require collaboration among multiple agents.

The figure below illustrates how group chat works.

group_chat

A group chat is orchestrated by a special agent type GroupChatManager. In the first step of the group chat, the Group Chat Manager selects an agent to speak. Then, the selected agent speaks and the message is sent back to the Group Chat Manager, who broadcasts the message to all other agents in the group. This process repeats until the conversation stops.

The Group Chat Manager can use several strategies to select the next agent. Currently, the following strategies are supported:

round_robin: The Group Chat Manager selects agents in a round-robin fashion based on the order of the agents provided.
random: The Group Chat Manager selects agents randomly.
manual: The Group Chat Manager selects agents by asking for human input.
auto: The default strategy, which selects agents using the Group Chat Manager’s LLM.
To illustrate this pattern, let’s consider a simple example of a group chat among the same arithmetic operator agents as in the previous example, with the objective of turning a number into a specific target number using a sequence of arithmetic operations powered by the agents.

In this example, we use the auto strategy to select the next agent. To help the Group Chat Manager select the next agent, we also set the description of the agents. Without the description, the Group Chat Manager will use the agents’ system_message, which may be not be the best choice.

# The `description` attribute is a string that describes the agent.
# It can also be set in `ConversableAgent` constructor.
adder_agent.description = "Add 1 to each input number."
multiplier_agent.description = "Multiply each input number by 2."
subtracter_agent.description = "Subtract 1 from each input number."
divider_agent.description = "Divide each input number by 2."
number_agent.description = "Return the numbers given."

We first create a GroupChat object and provide the list of agents. If we were to use the round_robin strategy, this list would specify the order of the agents to be selected. We also initialize the group chat with an empty message list and a maximum round of 6, which means there will be at most 6 iteratiosn of selecting speaker, agent speaks and broadcasting message.

from autogen import GroupChat

group_chat = GroupChat(
    agents=[adder_agent, multiplier_agent, subtracter_agent, divider_agent, number_agent],
    messages=[],
    max_round=6,
)

Now we create a GroupChatManager object and provide the GroupChat object as input. We also need to specify the llm_config of the Group Chat Manager so it can use the LLM to select the next agent (the auto strategy).

from autogen import GroupChatManager

group_chat_manager = GroupChatManager(
    groupchat=group_chat,
    llm_config={"config_list": [{"model": "gpt-4", "api_key": os.environ["OPENAI_API_KEY"]}]},
)

Finally, we have the Number Agent from before to start a two-agent chat with the Group Chat Manager, which runs the group chat internally and terminates the two-agent chat when the internal group chat is done. Because the Number Agent is selected to speak by us, it counts as the first round of the group chat.

chat_result = number_agent.initiate_chat(
    group_chat_manager,
    message="My number is 3, I want to turn it into 13.",
    summary_method="reflection_with_llm",
)

Number_Agent (to chat_manager):

My number is 3, I want to turn it into 13.

--------------------------------------------------------------------------------
Multiplier_Agent (to chat_manager):

6

--------------------------------------------------------------------------------
Adder_Agent (to chat_manager):

7

--------------------------------------------------------------------------------
Multiplier_Agent (to chat_manager):

14

--------------------------------------------------------------------------------
Subtracter_Agent (to chat_manager):

13

--------------------------------------------------------------------------------
Number_Agent (to chat_manager):

13

--------------------------------------------------------------------------------

You can see that the Number Agent is selected to speak first, then the Group Chat Manager selects the Multiplier Agent to speak, then the Adder Agent, and so on. The number is operated upon by each agent in the group chat, and the final result is 13.

We can take a look at the summary of the group chat, provided by the ChatResult object returned by the initiate_chat method.

print(chat_result.summary)

The agents cooperatively manipulated the initial number (3) through multipliying, adding, and subtracting operations to reach the target number (13).


Send Introductions
In the previous example, we set the description of the agents to help the Group Chat Manager select the next agent. This only helps the Group Chat Manager, however, does not help the participating agents to know about each other. Sometimes it is useful have each agent introduce themselves to other agents in the group chat. This can be done by setting the send_introductions=True.

group_chat_with_introductions = GroupChat(
    agents=[adder_agent, multiplier_agent, subtracter_agent, divider_agent, number_agent],
    messages=[],
    max_round=6,
    send_introductions=True,
)

Under the hood, the Group Chat Manager sends a message containing the agents’ names and descriptions to all agents in the group chat before the group chat starts.

Group Chat in a Sequential Chat
Group chat can also be used as a part of a sequential chat. In this case, the Group Chat Manager is treated as a regular agent in the sequence of two-agent chats.

# Let's use the group chat with introduction messages created above.
group_chat_manager_with_intros = GroupChatManager(
    groupchat=group_chat_with_introductions,
    llm_config={"config_list": [{"model": "gpt-4", "api_key": os.environ["OPENAI_API_KEY"]}]},
)

# Start a sequence of two-agent chats between the number agent and
# the group chat manager.
chat_result = number_agent.initiate_chats(
    [
        {
            "recipient": group_chat_manager_with_intros,
            "message": "My number is 3, I want to turn it into 13.",
        },
        {
            "recipient": group_chat_manager_with_intros,
            "message": "Turn this number to 32.",
        },
    ]
)


********************************************************************************
Start a new chat with the following message: 
My number is 3, I want to turn it into 13.

With the following carryover: 


********************************************************************************
Number_Agent (to chat_manager):

My number is 3, I want to turn it into 13.

--------------------------------------------------------------------------------
Multiplier_Agent (to chat_manager):

6

--------------------------------------------------------------------------------
Adder_Agent (to chat_manager):

7

--------------------------------------------------------------------------------
Multiplier_Agent (to chat_manager):

14

--------------------------------------------------------------------------------
Subtracter_Agent (to chat_manager):

13

--------------------------------------------------------------------------------
Number_Agent (to chat_manager):

Your number is 13.

--------------------------------------------------------------------------------

********************************************************************************
Start a new chat with the following message: 
Turn this number to 32.

With the following carryover: 
Your number is 13.

********************************************************************************
Number_Agent (to chat_manager):

Turn this number to 32.
Context: 
Your number is 13.

--------------------------------------------------------------------------------
Multiplier_Agent (to chat_manager):

26

--------------------------------------------------------------------------------
Adder_Agent (to chat_manager):

14

--------------------------------------------------------------------------------
Multiplier_Agent (to chat_manager):

28

--------------------------------------------------------------------------------
Adder_Agent (to chat_manager):

15

--------------------------------------------------------------------------------
Multiplier_Agent (to chat_manager):

30

--------------------------------------------------------------------------------

/Users/ekzhu/autogen/autogen/agentchat/chat.py:46: UserWarning: Repetitive recipients detected: The chat history will be cleared by default if a recipient appears more than once. To retain the chat history, please set 'clear_history=False' in the configuration of the repeating agent.
  warnings.warn(


In the above example, the Group Chat Manager runs the group chat two times. In the first time the number 3 becomes 13, and the last message of this group chat is being used as the carryover for the next group chat, which starts from 13.

You can also see from the warning message that the Group Chat Manager’s history is being cleared after the first group chat, which is the default. To keep the history of the Group Chat Manager, you can set the clear_history=False for the first chat.

Constrained Speaker Selection
Group chat is a powerful conversation pattern, but it can be hard to control if the number of participating agents is large. AutoGen provides a way to constrain the selection of the next speaker by using the allowed_or_disallowed_speaker_transitions argument of the GroupChat class.

The allowed_or_disallowed_speaker_transitions argument is a dictionary that maps a given agent to a list of agents that can (or cannot) be selected to speak next. The speaker_transitions_type argument specifies whether the transitions are allowed or disallowed.

Here is an example:

allowed_transitions = {
    number_agent: [adder_agent, number_agent],
    adder_agent: [multiplier_agent, number_agent],
    subtracter_agent: [divider_agent, number_agent],
    multiplier_agent: [subtracter_agent, number_agent],
    divider_agent: [adder_agent, number_agent],
}

In this example, the allowed transitions are specified for each agent. The Number Agent can be followed by the Adder Agent and the Number Agent, the Adder Agent can be followed by the Multiplier Agent and the Number Agent, and so on. Let’s put this into the group chat and see how it works. The speaker_transitions_type is set to allowed so the transitions are positive constraints.

constrained_graph_chat = GroupChat(
    agents=[adder_agent, multiplier_agent, subtracter_agent, divider_agent, number_agent],
    allowed_or_disallowed_speaker_transitions=allowed_transitions,
    speaker_transitions_type="allowed",
    messages=[],
    max_round=12,
    send_introductions=True,
)

constrained_group_chat_manager = GroupChatManager(
    groupchat=constrained_graph_chat,
    llm_config={"config_list": [{"model": "gpt-4", "api_key": os.environ["OPENAI_API_KEY"]}]},
)

chat_result = number_agent.initiate_chat(
    constrained_group_chat_manager,
    message="My number is 3, I want to turn it into 10. Once I get to 10, keep it there.",
    summary_method="reflection_with_llm",
)

Number_Agent (to chat_manager):

My number is 3, I want to turn it into 10. Once I get to 10, keep it there.

--------------------------------------------------------------------------------
Adder_Agent (to chat_manager):

4

--------------------------------------------------------------------------------
Multiplier_Agent (to chat_manager):

8

--------------------------------------------------------------------------------
Subtracter_Agent (to chat_manager):

7

--------------------------------------------------------------------------------
Divider_Agent (to chat_manager):

3.5

--------------------------------------------------------------------------------
Adder_Agent (to chat_manager):

4.5

--------------------------------------------------------------------------------
Multiplier_Agent (to chat_manager):

9

--------------------------------------------------------------------------------
Subtracter_Agent (to chat_manager):

8

--------------------------------------------------------------------------------
Divider_Agent (to chat_manager):

4

--------------------------------------------------------------------------------
Adder_Agent (to chat_manager):

5

--------------------------------------------------------------------------------
Multiplier_Agent (to chat_manager):

10

--------------------------------------------------------------------------------
Number_Agent (to chat_manager):

10

--------------------------------------------------------------------------------

This time, the agents are selected following the constraints we have specified.

Changing the select speaker role name
As part of the Group chat process, when the select_speaker_method is set to ‘auto’ (the default value), a select speaker message is sent to the LLM to determine the next speaker.

Each message in the chat sequence has a role attribute that is typically user, assistant, or system. The select speaker message is the last in the chat sequence when used and, by default, has a role of system.

When using some models, such as Mistral through Mistral.AI’s API, the role on the last message in the chat sequence has to be user.

To change the default behaviour, Autogen provides a way to set the value of the select speaker message’s role to any string value by setting the role_for_select_speaker_messages parameter in the GroupChat’s constructor. The default value is system and by setting it to user you can accommodate the last message role requirement of Mistral.AI’s API.

Nested Chats
The previous conversations patterns (two-agent chat, sequential chat, and group chat) are useful for building complex workflows, however, they do not expose a single conversational interface, which is often needed for scenarios like question-answering bots and personal assistants. In some other cases, it is also useful to package a workflow into a single agent for reuse in a larger workflow. AutoGen provides a way to achieve this by using nested chats.

Nested chats is powered by the nested chats handler, which is a pluggable component of ConversableAgent. The figure below illustrates how the nested chats handler triggers a sequence of nested chats when a message is received.

nested_chat

When a message comes in and passes the human-in-the-loop component, the nested chats handler checks if the message should trigger a nested chat based on conditions specified by the user. If the conditions are met, the nested chats handler starts a sequence of nested chats specified using the sequential chats pattern. In each of the nested chats, the sender agent is always the same agent that triggered the nested chats. In the end, the nested chat handler uses the results of the nested chats to produce a response to the original message. By default, the nested chat handler uses the summary of the last chat as the response.

Here is an example of using nested chats to build an arithmetic agent that packages arithmetic operations, code-based validation, and poetry into a single agent. This arithmetic agent takes a number transformation request like “turn number 3 into 13” and returns a poem that describes a transformation attempt.

First we define the agents. We reuse the group_chat_manager_with_intros from previous example to orchestrate the arithmetic operations.

import tempfile

temp_dir = tempfile.gettempdir()

arithmetic_agent = ConversableAgent(
    name="Arithmetic_Agent",
    llm_config=False,
    human_input_mode="ALWAYS",
    # This agent will always require human input to make sure the code is
    # safe to execute.
    code_execution_config={"use_docker": False, "work_dir": temp_dir},
)

code_writer_agent = ConversableAgent(
    name="Code_Writer_Agent",
    system_message="You are a code writer. You write Python script in Markdown code blocks.",
    llm_config={"config_list": [{"model": "gpt-4", "api_key": os.environ["OPENAI_API_KEY"]}]},
    human_input_mode="NEVER",
)

poetry_agent = ConversableAgent(
    name="Poetry_Agent",
    system_message="You are an AI poet.",
    llm_config={"config_list": [{"model": "gpt-4", "api_key": os.environ["OPENAI_API_KEY"]}]},
    human_input_mode="NEVER",
)

Now we define the nested chats using the sequential chat pattern. All the senders are always artihmetic_agent.

nested_chats = [
    {
        "recipient": group_chat_manager_with_intros,
        "summary_method": "reflection_with_llm",
        "summary_prompt": "Summarize the sequence of operations used to turn " "the source number into target number.",
    },
    {
        "recipient": code_writer_agent,
        "message": "Write a Python script to verify the arithmetic operations is correct.",
        "summary_method": "reflection_with_llm",
    },
    {
        "recipient": poetry_agent,
        "message": "Write a poem about it.",
        "max_turns": 1,
        "summary_method": "last_msg",
    },
]


Now we register the nested chats handler to the arithmetic_agent and set the conditions for triggering the nested chats.

arithmetic_agent.register_nested_chats(
    nested_chats,
    # The trigger function is used to determine if the agent should start the nested chat
    # given the sender agent.
    # In this case, the arithmetic agent will not start the nested chats if the sender is
    # from the nested chats' recipient to avoid recursive calls.
    trigger=lambda sender: sender not in [group_chat_manager_with_intros, code_writer_agent, poetry_agent],
)


Finally, we call generate_reply to get a response from the arithmetic_agent – this will trigger a sequence of nested chats and return the summary of the last nested chat as the response.

# Instead of using `initiate_chat` method to start another conversation,
# we can use the `generate_reply` method to get single reply to a message directly.
reply = arithmetic_agent.generate_reply(
    messages=[{"role": "user", "content": "I have a number 3 and I want to turn it into 7."}]
)


>>>>>>>> NO HUMAN INPUT RECEIVED.

>>>>>>>> USING AUTO REPLY...

********************************************************************************
Start a new chat with the following message: 
I have a number 3 and I want to turn it into 7.

With the following carryover: 


********************************************************************************
Arithmetic_Agent (to chat_manager):

I have a number 3 and I want to turn it into 7.

--------------------------------------------------------------------------------
Adder_Agent (to chat_manager):

To give you the result, I'll add 1 to the number you gave me. So your new number is 4.

--------------------------------------------------------------------------------
Multiplier_Agent (to chat_manager):

8

--------------------------------------------------------------------------------
Subtracter_Agent (to chat_manager):

7

--------------------------------------------------------------------------------
Number_Agent (to chat_manager):

7

--------------------------------------------------------------------------------
Number_Agent (to chat_manager):

7

--------------------------------------------------------------------------------

********************************************************************************
Start a new chat with the following message: 
Write a Python script to verify the arithmetic operations is correct.

With the following carryover: 
First, 1 was added to the initial number 3 to make it 4. Then it was multiplied by 2 which resulted in 8. Finally, 1 was subtracted from 8 to reach the target number 7.

********************************************************************************
Arithmetic_Agent (to Code_Writer_Agent):

Write a Python script to verify the arithmetic operations is correct.
Context: 
First, 1 was added to the initial number 3 to make it 4. Then it was multiplied by 2 which resulted in 8. Finally, 1 was subtracted from 8 to reach the target number 7.

--------------------------------------------------------------------------------
Code_Writer_Agent (to Arithmetic_Agent):

Here is a Python script to verify the aforementioned arithmetic operations:

```python
# defining the initial value
initial_number = 3

# Adding 1 to initial number
initial_number += 1
assert initial_number == 4, "The first operation failed!"

# Multiplying the result by 2
initial_number *= 2
assert initial_number == 8, "The second operation failed!"

# Subtracting 1 from the result
initial_number -= 1
assert initial_number == 7, "The final operation failed!"

print("All operations were carried out successfully!")
```
In the script, the entire process is broken down into steps. The `assert` function is used to verify the result at every step. If any of the operations doesn't yield the expected result, an `AssertionError` exception will be raised. If all operations pass, the message "All operations were carried out successfully!" will be printed.

--------------------------------------------------------------------------------

>>>>>>>> NO HUMAN INPUT RECEIVED.

>>>>>>>> USING AUTO REPLY...

>>>>>>>> EXECUTING CODE BLOCK 0 (inferred language is python)...
Arithmetic_Agent (to Code_Writer_Agent):

exitcode: 0 (execution succeeded)
Code output: 
All operations were carried out successfully!


--------------------------------------------------------------------------------
Code_Writer_Agent (to Arithmetic_Agent):

Certainly, that means the python script was successful and every arithmetic operation performed correctly given the initial input and the steps performed.

--------------------------------------------------------------------------------

********************************************************************************
Start a new chat with the following message: 
Write a poem about it.

With the following carryover: 
First, 1 was added to the initial number 3 to make it 4. Then it was multiplied by 2 which resulted in 8. Finally, 1 was subtracted from 8 to reach the target number 7.
The Python script successfully performed and verified the arithmetic operations on the initial number provided. The steps included adding 1 to the initial number, multiplying the result by 2, and finally subtracting 1. The assert function was used to check the result at each step, and confirmed that all operations were carried out correctly.

********************************************************************************
Arithmetic_Agent (to Poetry_Agent):

Write a poem about it.
Context: 
First, 1 was added to the initial number 3 to make it 4. Then it was multiplied by 2 which resulted in 8. Finally, 1 was subtracted from 8 to reach the target number 7.
The Python script successfully performed and verified the arithmetic operations on the initial number provided. The steps included adding 1 to the initial number, multiplying the result by 2, and finally subtracting 1. The assert function was used to check the result at each step, and confirmed that all operations were carried out correctly.

--------------------------------------------------------------------------------
Poetry_Agent (to Arithmetic_Agent):

From numbers, logic, pure mathematical creation,
Ponder this tale of numeric manipulation.
In the universe of Python where operations exist,
A story of integers and functions persist.

Three was the number from where we began,
Oblivious to the journey and its grandiosely plan.
Added with 1, the sum it adorned,
A sweet quadruple in the dawn was formed.

The saga continued with a twist of the tale,
The four was multiplied, while the winds wail.
The duo of four unfolded its wings,
An octet presence in our midst it brings.

Then enters subtraction, sly and clever,
Removing one to alter the endeavor.
From eight, subtracted one in delight,
To finally bask in the glow of seven's light.

Each operation, together they conspired,
In this tale of integers, creatively inspired.
Through life's equation, the script ran so free,
Amidst the language of Python, a symphony, you see.

Tested with assert, cross-checked the chain,
Confirming accuracy in program's domain.
Each move calculated, each step so right,
In the maze of coding, found was the light. 

Such is the tale, of numbers and operations, 
A dance among digits, logical iterations,
Just another day, in this AI poet's life,
Cutting through ambiguity, like a razor-sharp knife.

--------------------------------------------------------------------------------


A poem is returned as the response, which describes the transformation attempt from 3 to 7.

The implementation of the nested chats handler makes use of the register_reply method, which allows you to make extensive customization to ConversableAgent. The GroupChatManager uses the same mechanism to implement the group chat.

Nested chat is a powerful conversation pattern that allows you to package complex workflows into a single agent. You can hide tool usages within a single agent by having the tool-caller agent starts a nested chat with a tool-executor agent and then use the result of the nested chat to generate a response. See the nested chats for tool use notebook for an example.

Summary
In this chapter, we covered two-agent chat, sequential chat, group chat, and nested chat patterns. You can compose these patterns like LEGO blocks to create complex workflows. You can also use register_reply to create new patterns.

This is the last chapter on basic AutoGen concepts. In the next chatper, we will give you some tips on what to do next.

Multi-agent Conversation Framework
AutoGen offers a unified multi-agent conversation framework as a high-level abstraction of using foundation models. It features capable, customizable and conversable agents which integrate LLMs, tools, and humans via automated agent chat. By automating chat among multiple capable agents, one can easily make them collectively perform tasks autonomously or with human feedback, including tasks that require using tools via code.

This framework simplifies the orchestration, automation and optimization of a complex LLM workflow. It maximizes the performance of LLM models and overcomes their weaknesses. It enables building next-gen LLM applications based on multi-agent conversations with minimal effort.

Agents
AutoGen abstracts and implements conversable agents designed to solve tasks through inter-agent conversations. Specifically, the agents in AutoGen have the following notable features:

Conversable: Agents in AutoGen are conversable, which means that any agent can send and receive messages from other agents to initiate or continue a conversation

Customizable: Agents in AutoGen can be customized to integrate LLMs, humans, tools, or a combination of them.

The figure below shows the built-in agents in AutoGen. Agent Chat Example

We have designed a generic ConversableAgent class for Agents that are capable of conversing with each other through the exchange of messages to jointly finish a task. An agent can communicate with other agents and perform actions. Different agents can differ in what actions they perform after receiving messages. Two representative subclasses are AssistantAgent and UserProxyAgent

The AssistantAgent is designed to act as an AI assistant, using LLMs by default but not requiring human input or code execution. It could write Python code (in a Python coding block) for a user to execute when a message (typically a description of a task that needs to be solved) is received. Under the hood, the Python code is written by LLM (e.g., GPT-4). It can also receive the execution results and suggest corrections or bug fixes. Its behavior can be altered by passing a new system message. The LLM inference configuration can be configured via [llm_config].

The UserProxyAgent is conceptually a proxy agent for humans, soliciting human input as the agent's reply at each interaction turn by default and also having the capability to execute code and call functions or tools. The UserProxyAgent triggers code execution automatically when it detects an executable code block in the received message and no human user input is provided. Code execution can be disabled by setting the code_execution_config parameter to False. LLM-based response is disabled by default. It can be enabled by setting llm_config to a dict corresponding to the inference configuration. When llm_config is set as a dictionary, UserProxyAgent can generate replies using an LLM when code execution is not performed.

The auto-reply capability of ConversableAgent allows for more autonomous multi-agent communication while retaining the possibility of human intervention. One can also easily extend it by registering reply functions with the register_reply() method.

In the following code, we create an AssistantAgent named "assistant" to serve as the assistant and a UserProxyAgent named "user_proxy" to serve as a proxy for the human user. We will later employ these two agents to solve a task.

import os
from autogen import AssistantAgent, UserProxyAgent
from autogen.coding import DockerCommandLineCodeExecutor

config_list = [{"model": "gpt-4", "api_key": os.environ["OPENAI_API_KEY"]}]

# create an AssistantAgent instance named "assistant" with the LLM configuration.
assistant = AssistantAgent(name="assistant", llm_config={"config_list": config_list})

# create a UserProxyAgent instance named "user_proxy" with code execution on docker.
code_executor = DockerCommandLineCodeExecutor()
user_proxy = UserProxyAgent(name="user_proxy", code_execution_config={"executor": code_executor})

Multi-agent Conversations
A Basic Two-Agent Conversation Example
Once the participating agents are constructed properly, one can start a multi-agent conversation session by an initialization step as shown in the following code:

# the assistant receives a message from the user, which contains the task description
user_proxy.initiate_chat(
    assistant,
    message="""What date is today? Which big tech stock has the largest year-to-date gain this year? How much is the gain?""",
)


After the initialization step, the conversation could proceed automatically. Find a visual illustration of how the user_proxy and assistant collaboratively solve the above task autonomously below: Agent Chat Example

The assistant receives a message from the user_proxy, which contains the task description.
The assistant then tries to write Python code to solve the task and sends the response to the user_proxy.
Once the user_proxy receives a response from the assistant, it tries to reply by either soliciting human input or preparing an automatically generated reply. If no human input is provided, the user_proxy executes the code and uses the result as the auto-reply.
The assistant then generates a further response for the user_proxy. The user_proxy can then decide whether to terminate the conversation. If not, steps 3 and 4 are repeated.
Supporting Diverse Conversation Patterns
Conversations with different levels of autonomy, and human-involvement patterns
On the one hand, one can achieve fully autonomous conversations after an initialization step. On the other hand, AutoGen can be used to implement human-in-the-loop problem-solving by configuring human involvement levels and patterns (e.g., setting the human_input_mode to ALWAYS), as human involvement is expected and/or desired in many applications.

Static and dynamic conversations
AutoGen, by integrating conversation-driven control utilizing both programming and natural language, inherently supports dynamic conversations. This dynamic nature allows the agent topology to adapt based on the actual conversation flow under varying input problem scenarios. Conversely, static conversations adhere to a predefined topology. Dynamic conversations are particularly beneficial in complex settings where interaction patterns cannot be predetermined.

Registered auto-reply
With the pluggable auto-reply function, one can choose to invoke conversations with other agents depending on the content of the current message and context. For example:

Hierarchical chat like in OptiGuide.
Dynamic Group Chat which is a special form of hierarchical chat. In the system, we register a reply function in the group chat manager, which broadcasts messages and decides who the next speaker will be in a group chat setting.
Finite State Machine graphs to set speaker transition constraints which is a special form of dynamic group chat. In this approach, a directed transition matrix is fed into group chat. Users can specify legal transitions or specify disallowed transitions.
Nested chat like in conversational chess.
LLM-Based Function Call
Another approach involves LLM-based function calls, where LLM decides if a specific function should be invoked based on the conversation's status during each inference. This approach enables dynamic multi-agent conversations, as seen in scenarios like multi-user math problem solving scenario, where a student assistant automatically seeks expertise via function calls.

Diverse Applications Implemented with AutoGen
The figure below shows six examples of applications built using AutoGen. Applications

Enhanced Inference
autogen.OpenAIWrapper provides enhanced LLM inference for openai>=1. autogen.Completion is a drop-in replacement of openai.Completion and openai.ChatCompletion for enhanced LLM inference using openai<1. There are a number of benefits of using autogen to perform inference: performance tuning, API unification, caching, error handling, multi-config inference, result filtering, templating and so on.

Tune Inference Parameters (for openai<1)
Find a list of examples in this page: Tune Inference Parameters Examples

Choices to optimize
The cost of using foundation models for text generation is typically measured in terms of the number of tokens in the input and output combined. From the perspective of an application builder using foundation models, the use case is to maximize the utility of the generated text under an inference budget constraint (e.g., measured by the average dollar cost needed to solve a coding problem). This can be achieved by optimizing the hyperparameters of the inference, which can significantly affect both the utility and the cost of the generated text.

The tunable hyperparameters include:

model - this is a required input, specifying the model ID to use.
prompt/messages - the input prompt/messages to the model, which provides the context for the text generation task.
max_tokens - the maximum number of tokens (words or word pieces) to generate in the output.
temperature - a value between 0 and 1 that controls the randomness of the generated text. A higher temperature will result in more random and diverse text, while a lower temperature will result in more predictable text.
top_p - a value between 0 and 1 that controls the sampling probability mass for each token generation. A lower top_p value will make it more likely to generate text based on the most likely tokens, while a higher value will allow the model to explore a wider range of possible tokens.
n - the number of responses to generate for a given prompt. Generating multiple responses can provide more diverse and potentially more useful output, but it also increases the cost of the request.
stop - a list of strings that, when encountered in the generated text, will cause the generation to stop. This can be used to control the length or the validity of the output.
presence_penalty, frequency_penalty - values that control the relative importance of the presence and frequency of certain words or phrases in the generated text.
best_of - the number of responses to generate server-side when selecting the "best" (the one with the highest log probability per token) response for a given prompt.
The cost and utility of text generation are intertwined with the joint effect of these hyperparameters. There are also complex interactions among subsets of the hyperparameters. For example, the temperature and top_p are not recommended to be altered from their default values together because they both control the randomness of the generated text, and changing both at the same time can result in conflicting effects; n and best_of are rarely tuned together because if the application can process multiple outputs, filtering on the server side causes unnecessary information loss; both n and max_tokens will affect the total number of tokens generated, which in turn will affect the cost of the request. These interactions and trade-offs make it difficult to manually determine the optimal hyperparameter settings for a given text generation task.

Do the choices matter? Check this blogpost to find example tuning results about gpt-3.5-turbo and gpt-4.

With AutoGen, the tuning can be performed with the following information:

Validation data.
Evaluation function.
Metric to optimize.
Search space.
Budgets: inference and optimization respectively.
Validation data
Collect a diverse set of instances. They can be stored in an iterable of dicts. For example, each instance dict can contain "problem" as a key and the description str of a math problem as the value; and "solution" as a key and the solution str as the value.

Evaluation function
The evaluation function should take a list of responses, and other keyword arguments corresponding to the keys in each validation data instance as input, and output a dict of metrics. For example,

def eval_math_responses(responses: List[str], solution: str, **args) -> Dict:
    # select a response from the list of responses
    answer = voted_answer(responses)
    # check whether the answer is correct
    return {"success": is_equivalent(answer, solution)}

autogen.code_utils and autogen.math_utils offer some example evaluation functions for code generation and math problem solving.

Metric to optimize
The metric to optimize is usually an aggregated metric over all the tuning data instances. For example, users can specify "success" as the metric and "max" as the optimization mode. By default, the aggregation function is taking the average. Users can provide a customized aggregation function if needed.

Search space
Users can specify the (optional) search range for each hyperparameter.

model. Either a constant str, or multiple choices specified by flaml.tune.choice.
prompt/messages. Prompt is either a str or a list of strs, of the prompt templates. messages is a list of dicts or a list of lists, of the message templates. Each prompt/message template will be formatted with each data instance. For example, the prompt template can be: "{problem} Solve the problem carefully. Simplify your answer as much as possible. Put the final answer in \boxed{{}}." And {problem} will be replaced by the "problem" field of each data instance.
max_tokens, n, best_of. They can be constants, or specified by flaml.tune.randint, flaml.tune.qrandint, flaml.tune.lograndint or flaml.qlograndint. By default, max_tokens is searched in [50, 1000); n is searched in [1, 100); and best_of is fixed to 1.
stop. It can be a str or a list of strs, or a list of lists of strs or None. Default is None.
temperature or top_p. One of them can be specified as a constant or by flaml.tune.uniform or flaml.tune.loguniform etc. Please don't provide both. By default, each configuration will choose either a temperature or a top_p in [0, 1] uniformly.
presence_penalty, frequency_penalty. They can be constants or specified by flaml.tune.uniform etc. Not tuned by default.
Budgets
One can specify an inference budget and an optimization budget. The inference budget refers to the average inference cost per data instance. The optimization budget refers to the total budget allowed in the tuning process. Both are measured by dollars and follow the price per 1000 tokens.

Perform tuning
Now, you can use autogen.Completion.tune for tuning. For example,

import autogen

config, analysis = autogen.Completion.tune(
    data=tune_data,
    metric="success",
    mode="max",
    eval_func=eval_func,
    inference_budget=0.05,
    optimization_budget=3,
    num_samples=-1,
)

num_samples is the number of configurations to sample. -1 means unlimited (until optimization budget is exhausted). The returned config contains the optimized configuration and analysis contains an ExperimentAnalysis object for all the tried configurations and results.

The tuned config can be used to perform inference.

API unification
autogen.OpenAIWrapper.create() can be used to create completions for both chat and non-chat models, and both OpenAI API and Azure OpenAI API.

from autogen import OpenAIWrapper
# OpenAI endpoint
client = OpenAIWrapper()
# ChatCompletion
response = client.create(messages=[{"role": "user", "content": "2+2="}], model="gpt-3.5-turbo")
# extract the response text
print(client.extract_text_or_completion_object(response))
# get cost of this completion
print(response.cost)
# Azure OpenAI endpoint
client = OpenAIWrapper(api_key=..., base_url=..., api_version=..., api_type="azure")
# Completion
response = client.create(prompt="2+2=", model="gpt-3.5-turbo-instruct")
# extract the response text
print(client.extract_text_or_completion_object(response))


For local LLMs, one can spin up an endpoint using a package like FastChat, and then use the same API to send a request. See here for examples on how to make inference with local LLMs.

For custom model clients, one can register the client with autogen.OpenAIWrapper.register_model_client and then use the same API to send a request. See here for examples on how to make inference with custom model clients.

Usage Summary
The OpenAIWrapper from autogen tracks token counts and costs of your API calls. Use the create() method to initiate requests and print_usage_summary() to retrieve a detailed usage report, including total cost and token usage for both cached and actual requests.

mode=["actual", "total"] (default): print usage summary for all completions and non-caching completions.
mode='actual': only print non-cached usage.
mode='total': only print all usage (including cache).
Reset your session's usage data with clear_usage_summary() when needed. View Notebook

Example usage:

from autogen import OpenAIWrapper

client = OpenAIWrapper()
client.create(messages=[{"role": "user", "content": "Python learning tips."}], model="gpt-3.5-turbo")
client.print_usage_summary()  # Display usage
client.clear_usage_summary()  # Reset usage data


Sample output:

Usage summary excluding cached usage:
Total cost: 0.00015
* Model 'gpt-3.5-turbo': cost: 0.00015, prompt_tokens: 25, completion_tokens: 58, total_tokens: 83

Usage summary including cached usage:
Total cost: 0.00027
* Model 'gpt-3.5-turbo': cost: 0.00027, prompt_tokens: 50, completion_tokens: 100, total_tokens: 150

Note: if using a custom model client (see here for details) and if usage summary is not implemented, then the usage summary will not be available.

Caching
Moved to here.

Error handling
Runtime error
One can pass a list of configurations of different models/endpoints to mitigate the rate limits and other runtime error. For example,

client = OpenAIWrapper(
    config_list=[
        {
            "model": "gpt-4",
            "api_key": os.environ.get("AZURE_OPENAI_API_KEY"),
            "api_type": "azure",
            "base_url": os.environ.get("AZURE_OPENAI_API_BASE"),
            "api_version": "2024-02-01",
        },
        {
            "model": "gpt-3.5-turbo",
            "api_key": os.environ.get("OPENAI_API_KEY"),
            "base_url": "https://api.openai.com/v1",
        },
        {
            "model": "llama2-chat-7B",
            "base_url": "http://127.0.0.1:8080",
        },
        {
            "model": "microsoft/phi-2",
            "model_client_cls": "CustomModelClient"
        }
    ],
)

client.create() will try querying Azure OpenAI gpt-4, OpenAI gpt-3.5-turbo, a locally hosted llama2-chat-7B, and phi-2 using a custom model client class named CustomModelClient, one by one, until a valid result is returned. This can speed up the development process where the rate limit is a bottleneck. An error will be raised if the last choice fails. So make sure the last choice in the list has the best availability.

For convenience, we provide a number of utility functions to load config lists.

get_config_list: Generates configurations for API calls, primarily from provided API keys.
config_list_openai_aoai: Constructs a list of configurations using both Azure OpenAI and OpenAI endpoints, sourcing API keys from environment variables or local files.
config_list_from_json: Loads configurations from a JSON structure, either from an environment variable or a local JSON file, with the flexibility of filtering configurations based on given criteria.
config_list_from_models: Creates configurations based on a provided list of models, useful when targeting specific models without manually specifying each configuration.
config_list_from_dotenv: Constructs a configuration list from a .env file, offering a consolidated way to manage multiple API configurations and keys from a single file.
We suggest that you take a look at this notebook for full code examples of the different methods to configure your model endpoints.

Logic error
Another type of error is that the returned response does not satisfy a requirement. For example, if the response is required to be a valid json string, one would like to filter the responses that are not. This can be achieved by providing a list of configurations and a filter function. For example,

def valid_json_filter(response, **_):
    for text in OpenAIWrapper.extract_text_or_completion_object(response):
        try:
            json.loads(text)
            return True
        except ValueError:
            pass
    return False

client = OpenAIWrapper(
    config_list=[{"model": "text-ada-001"}, {"model": "gpt-3.5-turbo-instruct"}, {"model": "text-davinci-003"}],
)
response = client.create(
    prompt="How to construct a json request to Bing API to search for 'latest AI news'? Return the JSON request.",
    filter_func=valid_json_filter,
)


The example above will try to use text-ada-001, gpt-3.5-turbo-instruct, and text-davinci-003 iteratively, until a valid json string is returned or the last config is used. One can also repeat the same model in the list for multiple times (with different seeds) to try one model multiple times for increasing the robustness of the final response.

Advanced use case: Check this blogpost to find how to improve GPT-4's coding performance from 68% to 90% while reducing the inference cost.

Templating
If the provided prompt or message is a template, it will be automatically materialized with a given context. For example,

response = client.create(
    context={"problem": "How many positive integers, not exceeding 100, are multiples of 2 or 3 but not 4?"},
    prompt="{problem} Solve the problem carefully.",
    allow_format_str_template=True,
    **config
)


A template is either a format str, like the example above, or a function which produces a str from several input fields, like the example below.

def content(turn, context):
    return "\n".join(
        [
            context[f"user_message_{turn}"],
            context[f"external_info_{turn}"]
        ]
    )

messages = [
    {
        "role": "system",
        "content": "You are a teaching assistant of math.",
    },
    {
        "role": "user",
        "content": partial(content, turn=0),
    },
]
context = {
    "user_message_0": "Could you explain the solution to Problem 1?",
    "external_info_0": "Problem 1: ...",
}

response = client.create(context=context, messages=messages, **config)
messages.append(
    {
        "role": "assistant",
        "content": client.extract_text(response)[0]
    }
)
messages.append(
    {
        "role": "user",
        "content": partial(content, turn=1),
    },
)
context.append(
    {
        "user_message_1": "Why can't we apply Theorem 1 to Equation (2)?",
        "external_info_1": "Theorem 1: ...",
    }
)
response = client.create(context=context, messages=messages, **config)

Logging
When debugging or diagnosing an LLM-based system, it is often convenient to log the API calls and analyze them.

For openai >= 1
Logging example: View Notebook

Start logging:
import autogen.runtime_logging

autogen.runtime_logging.start(logger_type="sqlite", config={"dbname": "YOUR_DB_NAME"})

logger_type and config are both optional. Default logger type is SQLite logger, that's the only one available in autogen at the moment. If you want to customize the database name, you can pass in through config, default is logs.db.

Stop logging:
autogen.runtime_logging.stop()

LLM Runs
AutoGen logging supports OpenAI's llm message schema. Each LLM run is saved in chat_completions table includes:

session_id: an unique identifier for the logging session
invocation_id: an unique identifier for the logging record
client_id: an unique identifier for the Azure OpenAI/OpenAI client
request: detailed llm request, see below for an example
response: detailed llm response, see below for an example
cost: total cost for the request and response
start_time
end_time
Sample Request
{
  "messages":[
    {
      "content":"system_message_1",
      "role":"system"
    },
    {
      "content":"user_message_1",
      "role":"user"
    }
  ],
  "model":"gpt-4",
  "temperature": 0.9
}

Sample Response
{
  "id": "id_1",
  "choices": [
    {
      "finish_reason": "stop",
      "index": 0,
      "logprobs": null,
      "message": {
        "content": "assistant_message_1",
        "role": "assistant",
        "function_call": null,
        "tool_calls": null
      }
    }
  ],
  "created": "<timestamp>",
  "model": "gpt-4",
  "object": "chat.completion",
  "system_fingerprint": null,
  "usage": {
    "completion_tokens": 155,
    "prompt_tokens": 53,
    "total_tokens": 208
  }
}

Learn more about request and response format

For openai < 1
autogen.Completion and autogen.ChatCompletion offer an easy way to collect the API call histories. For example, to log the chat histories, simply run:

autogen.ChatCompletion.start_logging()

The API calls made after this will be automatically logged. They can be retrieved at any time by:

autogen.ChatCompletion.logged_history

There is a function that can be used to print usage summary (total cost, and token count usage from each model):

autogen.ChatCompletion.print_usage_summary()

To stop logging, use

autogen.ChatCompletion.stop_logging()

If one would like to append the history to an existing dict, pass the dict like:

autogen.ChatCompletion.start_logging(history_dict=existing_history_dict)

By default, the counter of API calls will be reset at start_logging(). If no reset is desired, set reset_counter=False.

There are two types of logging formats: compact logging and individual API call logging. The default format is compact. Set compact=False in start_logging() to switch.

Example of a history dict with compact logging.
{
    """
    [
        {
            'role': 'system',
            'content': system_message,
        },
        {
            'role': 'user',
            'content': user_message_1,
        },
        {
            'role': 'assistant',
            'content': assistant_message_1,
        },
        {
            'role': 'user',
            'content': user_message_2,
        },
        {
            'role': 'assistant',
            'content': assistant_message_2,
        },
    ]""": {
        "created_at": [0, 1],
        "cost": [0.1, 0.2],
    }
}

Example of a history dict with individual API call logging.
{
    0: {
        "request": {
            "messages": [
                {
                    "role": "system",
                    "content": system_message,
                },
                {
                    "role": "user",
                    "content": user_message_1,
                }
            ],
            ... # other parameters in the request
        },
        "response": {
            "choices": [
                "messages": {
                    "role": "assistant",
                    "content": assistant_message_1,
                },
            ],
            ... # other fields in the response
        }
    },
    1: {
        "request": {
            "messages": [
                {
                    "role": "system",
                    "content": system_message,
                },
                {
                    "role": "user",
                    "content": user_message_1,
                },
                {
                    "role": "assistant",
                    "content": assistant_message_1,
                },
                {
                    "role": "user",
                    "content": user_message_2,
                },
            ],
            ... # other parameters in the request
        },
        "response": {
            "choices": [
                "messages": {
                    "role": "assistant",
                    "content": assistant_message_2,
                },
            ],
            ... # other fields in the response
        }
    },
}

Example of printing for usage summary
Total cost: <cost>
Token count summary for model <model>: prompt_tokens: <count 1>, completion_tokens: <count 2>, total_tokens: <count 3>


It can be seen that the individual API call history contains redundant information of the conversation. For a long conversation the degree of redundancy is high. The compact history is more efficient and the individual API call history contains more details.

Command Line Code Executor
Open In Colab Open on GitHub

Command line code execution is the simplest form of code execution. Generally speaking, it will save each code block to a file and the execute that file. This means that each code block is executed in a new process. There are two forms of this executor:

Docker (DockerCommandLineCodeExecutor) - this is where all commands are executed in a Docker container
Local (LocalCommandLineCodeExecutor) - this is where all commands are executed on the host machine
This executor type is similar to the legacy code execution in AutoGen.

Docker
The DockerCommandLineCodeExecutor will create a Docker container and run all commands within that container. The default image that is used is python:3-slim, this can be customized by passing the image parameter to the constructor. If the image is not found locally then the class will try to pull it. Therefore, having built the image locally is enough. The only thing required for this image to be compatible with the executor is to have sh and python installed. Therefore, creating a custom image is a simple and effective way to ensure required system dependencies are available.

You can use the executor as a context manager to ensure the container is cleaned up after use. Otherwise, the atexit module will be used to stop the container when the program exits.

Inspecting the container
If you wish to keep the container around after AutoGen is finished using it for whatever reason (e.g. to inspect the container), then you can set the auto_remove parameter to False when creating the executor. stop_container can also be set to False to prevent the container from being stopped at the end of the execution.

Example
from pathlib import Path

from autogen.coding import CodeBlock, DockerCommandLineCodeExecutor

work_dir = Path("coding")
work_dir.mkdir(exist_ok=True)

with DockerCommandLineCodeExecutor(work_dir=work_dir) as executor:
    print(
        executor.execute_code_blocks(
            code_blocks=[
                CodeBlock(language="python", code="print('Hello, World!')"),
            ]
        )
    )

exit_code=0 output='Hello, World!\n' code_file='coding/tmp_code_07da107bb575cc4e02b0e1d6d99cc204.py'

Combining AutoGen in Docker with a Docker based executor
It is desirable to bundle your AutoGen application into a Docker image. But then, how do you allow your containerised application to execute code in a different container?

The recommended approach to this is called “Docker out of Docker”, where the Docker socket is mounted to the main AutoGen container, so that it can spawn and control “sibling” containers on the host. This is better than what is called “Docker in Docker”, where the main container runs a Docker daemon and spawns containers within itself. You can read more about this here.

To do this you would need to mount the Docker socket into the AutoGen container. This can be done by adding the following to the docker run command:

-v /var/run/docker.sock:/var/run/docker.sock

This will allow the AutoGen container to spawn and control sibling containers on the host.

If you need to bind a working directory to the AutoGen container but the directory belongs to your host machine, use the bind_dir parameter. This will allow the main AutoGen container to bind the host directory to the new spawned containers and allow it to access the files within the said directory. If the bind_dir is not specified, it will fallback to work_dir.

Local
DANGER
The local version will run code on your local system. Use it with caution.

To execute code on the host machine, as in the machine running AutoGen, the LocalCommandLineCodeExecutor can be used.

Example
from pathlib import Path

from autogen.coding import CodeBlock, LocalCommandLineCodeExecutor

work_dir = Path("coding")
work_dir.mkdir(exist_ok=True)

executor = LocalCommandLineCodeExecutor(work_dir=work_dir)
print(
    executor.execute_code_blocks(
        code_blocks=[
            CodeBlock(language="python", code="print('Hello, World!')"),
        ]
    )
)

exit_code=0 output='\nHello, World!\n' code_file='coding/065b51a16ee54f3298847518f9e999d7.py'

Using a Python virtual environment
By default, the LocalCommandLineCodeExecutor executes code and installs dependencies within the same Python environment as the AutoGen code. You have the option to specify a Python virtual environment to prevent polluting the base Python environment.

Example
from autogen.code_utils import create_virtual_env
from autogen.coding import CodeBlock, LocalCommandLineCodeExecutor

venv_dir = ".venv"
venv_context = create_virtual_env(venv_dir)

executor = LocalCommandLineCodeExecutor(virtual_env_context=venv_context)
print(
    executor.execute_code_blocks(code_blocks=[CodeBlock(language="python", code="import sys; print(sys.executable)")])
)


Assigning to an agent
These executors can be used to facilitate the execution of agent written code.

from pathlib import Path

from autogen import ConversableAgent
from autogen.coding import DockerCommandLineCodeExecutor

work_dir = Path("coding")
work_dir.mkdir(exist_ok=True)

executor = DockerCommandLineCodeExecutor(work_dir=work_dir)

code_executor_agent = ConversableAgent(
    name="code_executor_agent",
    llm_config=False,
    code_execution_config={
        "executor": executor,
    },
    human_input_mode="NEVER",
)

When using code execution it is critical that you update the system prompt of agents you expect to write code to be able to make use of the executor. For example, for the DockerCommandLineCodeExecutor you might setup a code writing agent like so:

# The code writer agent's system message is to instruct the LLM on how to
# use the Jupyter code executor with IPython kernel.
code_writer_system_message = """
You have been given coding capability to solve tasks using Python code.
In the following cases, suggest python code (in a python coding block) or shell script (in a sh coding block) for the user to execute.
    1. When you need to collect info, use the code to output the info you need, for example, browse or search the web, download/read a file, print the content of a webpage or a file, get the current date/time, check the operating system. After sufficient info is printed and the task is ready to be solved based on your language skill, you can solve the task by yourself.
    2. When you need to perform some task with code, use the code to perform the task and output the result. Finish the task smartly.
Solve the task step by step if you need to. If a plan is not provided, explain your plan first. Be clear which step uses code, and which step uses your language skill.
When using code, you must indicate the script type in the code block. The user cannot provide any other feedback or perform any other action beyond executing the code you suggest. The user can't modify your code. So do not suggest incomplete code which requires users to modify. Don't use a code block if it's not intended to be executed by the user.
If you want the user to save the code in a file before executing it, put # filename: <filename> inside the code block as the first line. Don't include multiple code blocks in one response. Do not ask users to copy and paste the result. Instead, use 'print' function for the output when relevant. Check the execution result returned by the user.
"""

import os

code_writer_agent = ConversableAgent(
    "code_writer",
    system_message=code_writer_system_message,
    llm_config={"config_list": [{"model": "gpt-4", "api_key": os.environ["OPENAI_API_KEY"]}]},
    code_execution_config=False,  # Turn off code execution for this agent.
    max_consecutive_auto_reply=2,
    human_input_mode="NEVER",
)


Then we can use these two agents to solve a problem:

import pprint

chat_result = code_executor_agent.initiate_chat(
    code_writer_agent, message="Write Python code to calculate the 14th Fibonacci number."
)

pprint.pprint(chat_result)

code_executor_agent (to code_writer):

Write Python code to calculate the 14th Fibonacci number.

--------------------------------------------------------------------------------
code_writer (to code_executor_agent):

Sure, we can calculate the Fibonacci series using a few different methods such as recursion, iterative, by using Binet's formula, or by using matrix exponentiation.

But, since we only need to calculate the 14th number, we will simply use the iterative method as it's the most efficient for this case.

Here is the Python code that solves the task:

```python
def fibonacci(n):
    a, b = 0, 1
    for _ in range(n):
        a, b = b, a + b
    return a

print(fibonacci(14))
```

In this script, `fibonacci(n)` is a function that calculates the nth Fibonacci number. Inside the function, two variables `a` and `b` are initialised to `0` and `1` which are the first two numbers in the Fibonacci series. Then, a loop runs `n` times (14 times in your case), and in each iteration `a` is replaced with `b` and `b` is replaced with `a + b`, which generates the next number in the series. 

The function returns `a`, which is the nth Fibonacci number. The result is then printed to the console.

--------------------------------------------------------------------------------

>>>>>>>> EXECUTING 1 CODE BLOCKS (inferred languages are [python])...
code_executor_agent (to code_writer):

exitcode: 0 (execution succeeded)
Code output: 377


--------------------------------------------------------------------------------
code_writer (to code_executor_agent):

Great! The script has successfully computed the 14th Fibonacci number as 377. If you need to compute other Fibonacci numbers, you can simply change the argument in the `fibonacci()` function call. Please let me know if you need help with anything else.

--------------------------------------------------------------------------------
code_executor_agent (to code_writer):



--------------------------------------------------------------------------------
ChatResult(chat_id=None,
           chat_history=[{'content': 'Write Python code to calculate the 14th '
                                     'Fibonacci number.',
                          'role': 'assistant'},
                         {'content': 'Sure, we can calculate the Fibonacci '
                                     'series using a few different methods '
                                     'such as recursion, iterative, by using '
                                     "Binet's formula, or by using matrix "
                                     'exponentiation.\n'
                                     '\n'
                                     'But, since we only need to calculate the '
                                     '14th number, we will simply use the '
                                     "iterative method as it's the most "
                                     'efficient for this case.\n'
                                     '\n'
                                     'Here is the Python code that solves the '
                                     'task:\n'
                                     '\n'
                                     '```python\n'
                                     'def fibonacci(n):\n'
                                     '    a, b = 0, 1\n'
                                     '    for _ in range(n):\n'
                                     '        a, b = b, a + b\n'
                                     '    return a\n'
                                     '\n'
                                     'print(fibonacci(14))\n'
                                     '```\n'
                                     '\n'
                                     'In this script, `fibonacci(n)` is a '
                                     'function that calculates the nth '
                                     'Fibonacci number. Inside the function, '
                                     'two variables `a` and `b` are '
                                     'initialised to `0` and `1` which are the '
                                     'first two numbers in the Fibonacci '
                                     'series. Then, a loop runs `n` times (14 '
                                     'times in your case), and in each '
                                     'iteration `a` is replaced with `b` and '
                                     '`b` is replaced with `a + b`, which '
                                     'generates the next number in the '
                                     'series. \n'
                                     '\n'
                                     'The function returns `a`, which is the '
                                     'nth Fibonacci number. The result is then '
                                     'printed to the console.',
                          'role': 'user'},
                         {'content': 'exitcode: 0 (execution succeeded)\n'
                                     'Code output: 377\n',
                          'role': 'assistant'},
                         {'content': 'Great! The script has successfully '
                                     'computed the 14th Fibonacci number as '
                                     '377. If you need to compute other '
                                     'Fibonacci numbers, you can simply change '
                                     'the argument in the `fibonacci()` '
                                     'function call. Please let me know if you '
                                     'need help with anything else.',
                          'role': 'user'},
                         {'content': '', 'role': 'assistant'}],
           summary='',
           cost=({'gpt-4-0613': {'completion_tokens': 302,
                                 'cost': 0.04842,
                                 'prompt_tokens': 1010,
                                 'total_tokens': 1312},
                  'total_cost': 0.04842},
                 {'gpt-4-0613': {'completion_tokens': 302,
                                 'cost': 0.04842,
                                 'prompt_tokens': 1010,
                                 'total_tokens': 1312},
                  'total_cost': 0.04842}),
           human_input=[])


Finally, stop the container. Or better yet use a context manager for it to be stopped automatically.

executor.stop()

Jupyter Code Executor
Open In Colab Open on GitHub

AutoGen is able to execute code in a stateful Jupyter kernel, this is in contrast to the command line code executor where each code block is executed in a new process. This means that you can define variables in one code block and use them in another. One of the interesting properties of this is that when an error is encountered, only the failing code needs to be re-executed, and not the entire script.

To use the JupyterCodeExecutor you need a Jupyter server running. This can be in Docker, local, or even a remote server. Then, when constructing the JupyterCodeExecutor you pass it the server it should connect to.

Dependencies
In order to use Jupyter based code execution some extra dependencies are required. These can be installed with the extra jupyter-executor:

pip install 'pyautogen[jupyter-executor]'

Jupyter Server
Docker
To run a Docker based Jupyter server, the DockerJupyterServer can be used.

from autogen.coding import CodeBlock
from autogen.coding.jupyter import DockerJupyterServer, JupyterCodeExecutor

with DockerJupyterServer() as server:
    executor = JupyterCodeExecutor(server)
    print(
        executor.execute_code_blocks(
            code_blocks=[
                CodeBlock(language="python", code="print('Hello, World!')"),
            ]
        )
    )

exit_code=0 output='Hello, World!\n' output_files=[]

By default the DockerJupyterServer will build and use a bundled Dockerfile, which can be seen below:

print(DockerJupyterServer.DEFAULT_DOCKERFILE)

FROM quay.io/jupyter/docker-stacks-foundation

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

USER ${NB_UID}
RUN mamba install --yes jupyter_kernel_gateway ipykernel &&     mamba clean --all -f -y &&     fix-permissions "${CONDA_DIR}" &&     fix-permissions "/home/${NB_USER}"

ENV TOKEN="UNSET"
CMD python -m jupyter kernelgateway --KernelGatewayApp.ip=0.0.0.0     --KernelGatewayApp.port=8888     --KernelGatewayApp.auth_token="${TOKEN}"     --JupyterApp.answer_yes=true     --JupyterWebsocketPersonality.list_kernels=true

EXPOSE 8888

WORKDIR "${HOME}"


Custom Docker Image
A custom image can be used by passing the custom_image_name parameter to the DockerJupyterServer constructor. There are some requirements of the image for it to work correctly:

The image must have Jupyer Kernel Gateway installed and running on port 8888 for the JupyterCodeExecutor to be able to connect to it.
Respect the TOKEN environment variable, which is used to authenticate the JupyterCodeExecutor with the Jupyter server.
Ensure the jupyter kernelgateway is started with:
--JupyterApp.answer_yes=true - this ensures that the kernel gateway does not prompt for confirmation when shut down.
--JupyterWebsocketPersonality.list_kernels=true - this ensures that the kernel gateway lists the available kernels.
If you wanted to add extra dependencies (for example matplotlib and numpy) to this image you could customize the Dockerfile like so:

FROM quay.io/jupyter/docker-stacks-foundation

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

USER ${NB_UID}
RUN mamba install --yes jupyter_kernel_gateway ipykernel matplotlib numpy &&
    mamba clean --all -f -y &&
    fix-permissions "${CONDA_DIR}" &&
    fix-permissions "/home/${NB_USER}"

ENV TOKEN="UNSET"
CMD python -m jupyter kernelgateway \
    --KernelGatewayApp.ip=0.0.0.0 \
    --KernelGatewayApp.port=8888 \
    --KernelGatewayApp.auth_token="${TOKEN}" \
    --JupyterApp.answer_yes=true \
    --JupyterWebsocketPersonality.list_kernels=true

EXPOSE 8888

WORKDIR "${HOME}"

TIP
To learn about how to combine AutoGen in a Docker image while also executing code in a separate image go here.

Local
DANGER
The local version will run code on your local system. Use it with caution.

To run a local Jupyter server, the LocalJupyterServer can be used.

WARNING
The LocalJupyterServer does not function on Windows due to a bug. In this case, you can use the DockerJupyterServer instead or use the EmbeddedIPythonCodeExecutor. Do note that the intention is to remove the EmbeddedIPythonCodeExecutor when the bug is fixed.

from autogen.coding import CodeBlock
from autogen.coding.jupyter import JupyterCodeExecutor, LocalJupyterServer

with LocalJupyterServer() as server:
    executor = JupyterCodeExecutor(server)
    print(
        executor.execute_code_blocks(
            code_blocks=[
                CodeBlock(language="python", code="print('Hello, World!')"),
            ]
        )
    )

Remote
The JupyterCodeExecutor can also connect to a remote Jupyter server. This is done by passing connection information rather than an actual server object into the JupyterCodeExecutor constructor.

from autogen.coding.jupyter import JupyterCodeExecutor, JupyterConnectionInfo

executor = JupyterCodeExecutor(
    jupyter_server=JupyterConnectionInfo(host='example.com', use_https=True, port=7893, token='mytoken')
)


Image outputs
When Jupyter outputs an image, this is saved as a file into the output_dir of the JupyterCodeExecutor, as specified by the constructor. By default this is the current working directory.

Assigning to an agent
A single server can support multiple agents, as each executor will create its own kernel. To assign an executor to an agent it can be done like so:

from pathlib import Path

from autogen import ConversableAgent
from autogen.coding.jupyter import DockerJupyterServer, JupyterCodeExecutor

server = DockerJupyterServer()

output_dir = Path("coding")
output_dir.mkdir(exist_ok=True)

code_executor_agent = ConversableAgent(
    name="code_executor_agent",
    llm_config=False,
    code_execution_config={
        "executor": JupyterCodeExecutor(server, output_dir=output_dir),
    },
    human_input_mode="NEVER",
)

When using code execution it is critical that you update the system prompt of agents you expect to write code to be able to make use of the executor. For example, for the JupyterCodeExecutor you might setup a code writing agent like so:

# The code writer agent's system message is to instruct the LLM on how to
# use the Jupyter code executor with IPython kernel.
code_writer_system_message = """
You have been given coding capability to solve tasks using Python code in a stateful IPython kernel.
You are responsible for writing the code, and the user is responsible for executing the code.

When you write Python code, put the code in a markdown code block with the language set to Python.
For example:
```python
x = 3
```
You can use the variable `x` in subsequent code blocks.
```python
print(x)
```

Write code incrementally and leverage the statefulness of the kernel to avoid repeating code.
Import libraries in a separate code block.
Define a function or a class in a separate code block.
Run code that produces output in a separate code block.
Run code that involves expensive operations like download, upload, and call external APIs in a separate code block.

When your code produces an output, the output will be returned to you.
Because you have limited conversation memory, if your code creates an image,
the output will be a path to the image instead of the image itself."""

import os

code_writer_agent = ConversableAgent(
    "code_writer",
    system_message=code_writer_system_message,
    llm_config={"config_list": [{"model": "gpt-4", "api_key": os.environ["OPENAI_API_KEY"]}]},
    code_execution_config=False,  # Turn off code execution for this agent.
    max_consecutive_auto_reply=2,
    human_input_mode="NEVER",
)


Then we can use these two agents to solve a problem:

import pprint

chat_result = code_executor_agent.initiate_chat(
    code_writer_agent, message="Write Python code to calculate the 14th Fibonacci number."
)

pprint.pprint(chat_result)

code_executor_agent (to code_writer):

Write Python code to calculate the 14th Fibonacci number.

--------------------------------------------------------------------------------
code_writer (to code_executor_agent):

Sure. The Fibonacci sequence is a series of numbers where the next number is found by adding up the two numbers before it. We know that the first two Fibonacci numbers are 0 and 1. After that, the series looks like:

0, 1, 1, 2, 3, 5, 8, 13, 21, 34, 55, ...

So, let's define a Python function to calculate the nth Fibonacci number.

--------------------------------------------------------------------------------
code_executor_agent (to code_writer):



--------------------------------------------------------------------------------
code_writer (to code_executor_agent):

Here is the Python function to calculate the nth Fibonacci number:

```python
def fibonacci(n):
    if n <= 1:
        return n
    else:
        a, b = 0, 1
        for _ in range(2, n+1):
            a, b = b, a+b
        return b
```

Now, let's use this function to calculate the 14th Fibonacci number.

```python
fibonacci(14)
```

--------------------------------------------------------------------------------
code_executor_agent (to code_writer):

exitcode: 0 (execution succeeded)
Code output: 
377

--------------------------------------------------------------------------------
ChatResult(chat_id=None,
           chat_history=[{'content': 'Write Python code to calculate the 14th '
                                     'Fibonacci number.',
                          'role': 'assistant'},
                         {'content': 'Sure. The Fibonacci sequence is a series '
                                     'of numbers where the next number is '
                                     'found by adding up the two numbers '
                                     'before it. We know that the first two '
                                     'Fibonacci numbers are 0 and 1. After '
                                     'that, the series looks like:\n'
                                     '\n'
                                     '0, 1, 1, 2, 3, 5, 8, 13, 21, 34, 55, '
                                     '...\n'
                                     '\n'
                                     "So, let's define a Python function to "
                                     'calculate the nth Fibonacci number.',
                          'role': 'user'},
                         {'content': '', 'role': 'assistant'},
                         {'content': 'Here is the Python function to calculate '
                                     'the nth Fibonacci number:\n'
                                     '\n'
                                     '```python\n'
                                     'def fibonacci(n):\n'
                                     '    if n <= 1:\n'
                                     '        return n\n'
                                     '    else:\n'
                                     '        a, b = 0, 1\n'
                                     '        for _ in range(2, n+1):\n'
                                     '            a, b = b, a+b\n'
                                     '        return b\n'
                                     '```\n'
                                     '\n'
                                     "Now, let's use this function to "
                                     'calculate the 14th Fibonacci number.\n'
                                     '\n'
                                     '```python\n'
                                     'fibonacci(14)\n'
                                     '```',
                          'role': 'user'},
                         {'content': 'exitcode: 0 (execution succeeded)\n'
                                     'Code output: \n'
                                     '377',
                          'role': 'assistant'}],
           summary='exitcode: 0 (execution succeeded)\nCode output: \n377',
           cost=({'gpt-4-0613': {'completion_tokens': 193,
                                 'cost': 0.028499999999999998,
                                 'prompt_tokens': 564,
                                 'total_tokens': 757},
                  'total_cost': 0.028499999999999998},
                 {'gpt-4-0613': {'completion_tokens': 193,
                                 'cost': 0.028499999999999998,
                                 'prompt_tokens': 564,
                                 'total_tokens': 757},
                  'total_cost': 0.028499999999999998}),
           human_input=[])


Finally, stop the server. Or better yet use a context manager for it to be stopped automatically.

server.stop()

User Defined Functions
Open In Colab Open on GitHub

NOTE
This is experimental and not yet supported by all executors. At this stage only LocalCommandLineCodeExecutor is supported.

Currently, the method of registering tools and using this feature are different. We would like to unify them. See Github issue here

User defined functions allow you to define Python functions in your AutoGen program and then provide these to be used by your executor. This allows you to provide your agents with tools without using traditional tool calling APIs. Currently only Python is supported for this feature.

There are several steps involved:

Define the function
Provide the function to the executor
Explain to the code writing agent how to use the function
Define the function
WARNING
Keep in mind that the entire source code of these functions will be available to the executor. This means that you should not include any sensitive information in the function as an LLM agent may be able to access it.

If the function does not require any external imports or dependencies then you can simply use the function. For example:

def add_two_numbers(a: int, b: int) -> int:
    """Add two numbers together."""
    return a + b

This would be a valid standalone function.

TIP
Using type hints and docstrings are not required but are highly recommended. They will help the code writing agent understand the function and how to use it.

If the function requires external imports or dependencies then you can use the @with_requirements decorator to specify the requirements. For example:

import pandas

from autogen.coding.func_with_reqs import with_requirements


@with_requirements(python_packages=["pandas"], global_imports=["pandas"])
def load_data() -> pandas.DataFrame:
    """Load some sample data.

    Returns:
        pandas.DataFrame: A DataFrame with the following columns: name(str), location(str), age(int)
    """
    data = {
        "name": ["John", "Anna", "Peter", "Linda"],
        "location": ["New York", "Paris", "Berlin", "London"],
        "age": [24, 13, 53, 33],
    }
    return pandas.DataFrame(data)


If you wanted to rename pandas to pd or import DataFrame directly you could do the following:

import pandas as pd
from pandas import DataFrame
from pandas import DataFrame as df

from autogen.coding.func_with_reqs import Alias, ImportFromModule, with_requirements


@with_requirements(python_packages=["pandas"], global_imports=[Alias("pandas", "pd")])
def some_func1() -> pd.DataFrame: ...


@with_requirements(python_packages=["pandas"], global_imports=[ImportFromModule("pandas", "DataFrame")])
def some_func2() -> DataFrame: ...


@with_requirements(python_packages=["pandas"], global_imports=[ImportFromModule("pandas", Alias("DataFrame", "df"))])
def some_func3() -> df: ...


Provide the function to the executor
Functions can be loaded into the executor in its constructor. For example:

from pathlib import Path

from autogen.coding import CodeBlock, LocalCommandLineCodeExecutor

work_dir = Path("coding")
work_dir.mkdir(exist_ok=True)

executor = LocalCommandLineCodeExecutor(work_dir=work_dir, functions=[add_two_numbers, load_data])

Before we get an agent involved, we can sanity check that when the agent writes code that looks like this the executor will be able to handle it.

code = f"""
from {LocalCommandLineCodeExecutor.FUNCTIONS_MODULE} import add_two_numbers

print(add_two_numbers(1, 2))
"""

print(
    executor.execute_code_blocks(
        code_blocks=[
            CodeBlock(language="python", code=code),
        ]
    )
)

exit_code=0 output='3\n' code_file='/Users/jackgerrits/w/autogen/website/docs/topics/code-execution/coding/tmp_code_1958fe3aea3e8e3c6e907fe951b5f6ab.py'


And we can try the function that required a dependency and import too.

code = f"""
from {LocalCommandLineCodeExecutor.FUNCTIONS_MODULE} import load_data

print(load_data())
"""

result = executor.execute_code_blocks(
    code_blocks=[
        CodeBlock(language="python", code=code),
    ]
)

print(result.output)

    name  location  age
0   John  New York   24
1   Anna     Paris   13
2  Peter    Berlin   53
3  Linda    London   33

Limitations
Only Python is supported currently
The function must not depend on any globals or external state as it is loaded as source code
Explain to the code writing agent how to use the function
Now that the function is available to be called by the executor, you can explain to the code writing agent how to use the function. This step is very important as by default it will not know about it.

There is a utility function that you can use to generate a default prompt that describes the available functions and how to use them. This function can have its template overridden to provide a custom message, or you can use a different prompt all together.

For example, you could extend the system message from the page about local execution with a new section that describes the functions available.

nlnl = "\n\n"
code_writer_system_message = """
You have been given coding capability to solve tasks using Python code.
In the following cases, suggest python code (in a python coding block) or shell script (in a sh coding block) for the user to execute.
    1. When you need to collect info, use the code to output the info you need, for example, browse or search the web, download/read a file, print the content of a webpage or a file, get the current date/time, check the operating system. After sufficient info is printed and the task is ready to be solved based on your language skill, you can solve the task by yourself.
    2. When you need to perform some task with code, use the code to perform the task and output the result. Finish the task smartly.
Solve the task step by step if you need to. If a plan is not provided, explain your plan first. Be clear which step uses code, and which step uses your language skill.
When using code, you must indicate the script type in the code block. The user cannot provide any other feedback or perform any other action beyond executing the code you suggest. The user can't modify your code. So do not suggest incomplete code which requires users to modify. Don't use a code block if it's not intended to be executed by the user.
If you want the user to save the code in a file before executing it, put # filename: <filename> inside the code block as the first line. Don't include multiple code blocks in one response. Do not ask users to copy and paste the result. Instead, use 'print' function for the output when relevant. Check the execution result returned by the user.
"""

# Add on the new functions
code_writer_system_message += executor.format_functions_for_prompt()

print(code_writer_system_message)



You have been given coding capability to solve tasks using Python code.
In the following cases, suggest python code (in a python coding block) or shell script (in a sh coding block) for the user to execute.
    1. When you need to collect info, use the code to output the info you need, for example, browse or search the web, download/read a file, print the content of a webpage or a file, get the current date/time, check the operating system. After sufficient info is printed and the task is ready to be solved based on your language skill, you can solve the task by yourself.
    2. When you need to perform some task with code, use the code to perform the task and output the result. Finish the task smartly.
Solve the task step by step if you need to. If a plan is not provided, explain your plan first. Be clear which step uses code, and which step uses your language skill.
When using code, you must indicate the script type in the code block. The user cannot provide any other feedback or perform any other action beyond executing the code you suggest. The user can't modify your code. So do not suggest incomplete code which requires users to modify. Don't use a code block if it's not intended to be executed by the user.
If you want the user to save the code in a file before executing it, put # filename: <filename> inside the code block as the first line. Don't include multiple code blocks in one response. Do not ask users to copy and paste the result. Instead, use 'print' function for the output when relevant. Check the execution result returned by the user.
You have access to the following user defined functions. They can be accessed from the module called `functions` by their function names.

For example, if there was a function called `foo` you could import it by writing `from functions import foo`

def add_two_numbers(a: int, b: int) -> int:
    """Add two numbers together."""
    ...

def load_data() -> pandas.core.frame.DataFrame:
    """Load some sample data.

        Returns:
            pandas.DataFrame: A DataFrame with the following columns: name(str), location(str), age(int)
    """
    ...


Then you can use this system message for your code writing agent.

import os

from autogen import ConversableAgent

code_writer_agent = ConversableAgent(
    "code_writer",
    system_message=code_writer_system_message,
    llm_config={"config_list": [{"model": "gpt-4", "api_key": os.environ["OPENAI_API_KEY"]}]},
    code_execution_config=False,  # Turn off code execution for this agent.
    max_consecutive_auto_reply=2,
    human_input_mode="NEVER",
)

Now, we can setup the code execution agent using the local command line executor we defined earlier.

code_executor_agent = ConversableAgent(
    name="code_executor_agent",
    llm_config=False,
    code_execution_config={
        "executor": executor,
    },
    human_input_mode="NEVER",
)

Then, we can start the conversation and get the agent to process the dataframe we provided.

chat_result = code_executor_agent.initiate_chat(
    code_writer_agent,
    message="Please use the load_data function to load the data and please calculate the average age of all people.",
    summary_method="reflection_with_llm",
)


code_executor_agent (to code_writer):

Please use the load_data function to load the data and please calculate the average age of all people.

--------------------------------------------------------------------------------
code_writer (to code_executor_agent):

Below is the python code to load the data using the `load_data()` function and calculate the average age of all people. 

```python
# python code
from functions import load_data
import numpy as np

# Load the data
df = load_data()

# Calculate the average age
avg_age = np.mean(df['age'])

print("The average age is", avg_age)
```

This code starts by importing the `load_data()` function. It then uses this function to load the data into a variable `df`. Afterwards, it calculates the average (mean) of the 'age' column in the DataFrame, before printing the result.

--------------------------------------------------------------------------------

>>>>>>>> EXECUTING CODE BLOCK (inferred language is python)...
code_executor_agent (to code_writer):

exitcode: 0 (execution succeeded)
Code output: The average age is 30.75


--------------------------------------------------------------------------------
code_writer (to code_executor_agent):

Great! The code worked fine. So, the average age of all people in the dataset is 30.75 years.

--------------------------------------------------------------------------------
code_executor_agent (to code_writer):



--------------------------------------------------------------------------------


We can see the summary of the calculation:

print(chat_result.summary)

The average age of all people in the dataset is 30.75 years.

Customize Speaker Selection
Open In Colab Open on GitHub

group_chat

In GroupChat, we can customize the speaker selection by passing a function to the GroupChat object. With this function, you can build a more deterministic agent workflow. We recommend following a StateFlow pattern when crafting this function. Please refer to the StateFlow blog for more details.

An example research workflow
We provide a simple example to build a StateFlow model for research with customized speaker selection.

We first define the following agents:

Initializer: Start the workflow by sending a task.
Coder: Retrieve papers from the internet by writing code.
Executor: Execute the code.
Scientist: Read the papers and write a summary.
In the figure above, we define a simple workflow for research with 4 states: Init, Retrieve, Research, and End. Within each state, we will call different agents to perform the tasks.

Init: We use the initializer to start the workflow.
Retrieve: We will first call the coder to write code and then call the executor to execute the code.
Research: We will call the scientist to read the papers and write a summary.
End: We will end the workflow.
Create your speaker selection function
Below is a skeleton of the speaker selection function. Fill in the function to define the speaker selection logic.

def custom_speaker_selection_func(
    last_speaker: Agent, 
    groupchat: GroupChat
) -> Union[Agent, Literal['auto', 'manual', 'random' 'round_robin'], None]:

    """Define a customized speaker selection function.
    A recommended way is to define a transition for each speaker in the groupchat.

    Parameters:
        - last_speaker: Agent
            The last speaker in the group chat.
        - groupchat: GroupChat
            The GroupChat object
    Return:
        Return one of the following:
        1. an `Agent` class, it must be one of the agents in the group chat.
        2. a string from ['auto', 'manual', 'random', 'round_robin'] to select a default method to use.
        3. None, which indicates the chat should be terminated.
    """
    pass

groupchat = autogen.GroupChat(
    speaker_selection_method=custom_speaker_selection_func,
    ...,
)


The last speaker and the groupchat object are passed to the function. Commonly used variables from groupchat are groupchat.messages and groupchat.agents, which is the message history and the agents in the group chat respectively. You can access other attributes of the groupchat, such as groupchat.allowed_speaker_transitions_dict for pre-defined allowed_speaker_transitions_dict.

import os

import autogen

# Put your api key in the environment variable OPENAI_API_KEY
config_list = [
    {
        "model": "gpt-4-0125-preview",
        "api_key": os.environ["OPENAI_API_KEY"],
    }
]

# You can also create an file called "OAI_CONFIG_LIST" and store your config there
# config_list = autogen.config_list_from_json(
#     "OAI_CONFIG_LIST",
#     filter_dict={
#         "model": ["gpt-4-0125-preview"],
#     },
# )

gpt4_config = {
    "cache_seed": 42,  # change the cache_seed for different trials
    "temperature": 0,
    "config_list": config_list,
    "timeout": 120,
}

initializer = autogen.UserProxyAgent(
    name="Init",
)

coder = autogen.AssistantAgent(
    name="Retrieve_Action_1",
    llm_config=gpt4_config,
    system_message="""You are the Coder. Given a topic, write code to retrieve related papers from the arXiv API, print their title, authors, abstract, and link.
You write python/shell code to solve tasks. Wrap the code in a code block that specifies the script type. The user can't modify your code. So do not suggest incomplete code which requires others to modify. Don't use a code block if it's not intended to be executed by the executor.
Don't include multiple code blocks in one response. Do not ask others to copy and paste the result. Check the execution result returned by the executor.
If the result indicates there is an error, fix the error and output the code again. Suggest the full code instead of partial code or code changes. If the error can't be fixed or if the task is not solved even after the code is executed successfully, analyze the problem, revisit your assumption, collect additional info you need, and think of a different approach to try.
""",
)
executor = autogen.UserProxyAgent(
    name="Retrieve_Action_2",
    system_message="Executor. Execute the code written by the Coder and report the result.",
    human_input_mode="NEVER",
    code_execution_config={
        "last_n_messages": 3,
        "work_dir": "paper",
        "use_docker": False,
    },  # Please set use_docker=True if docker is available to run the generated code. Using docker is safer than running the generated code directly.
)
scientist = autogen.AssistantAgent(
    name="Research_Action_1",
    llm_config=gpt4_config,
    system_message="""You are the Scientist. Please categorize papers after seeing their abstracts printed and create a markdown table with Domain, Title, Authors, Summary and Link""",
)


def state_transition(last_speaker, groupchat):
    messages = groupchat.messages

    if last_speaker is initializer:
        # init -> retrieve
        return coder
    elif last_speaker is coder:
        # retrieve: action 1 -> action 2
        return executor
    elif last_speaker is executor:
        if messages[-1]["content"] == "exitcode: 1":
            # retrieve --(execution failed)--> retrieve
            return coder
        else:
            # retrieve --(execution success)--> research
            return scientist
    elif last_speaker == "Scientist":
        # research -> end
        return None


groupchat = autogen.GroupChat(
    agents=[initializer, coder, executor, scientist],
    messages=[],
    max_round=20,
    speaker_selection_method=state_transition,
)
manager = autogen.GroupChatManager(groupchat=groupchat, llm_config=gpt4_config)


initializer.initiate_chat(
    manager, message="Topic: LLM applications papers from last week. Requirement: 5 - 10 papers from different domains."
)


Resuming a GroupChat
Open In Colab Open on GitHub

In GroupChat, we can resume a previous group chat by passing the messages from that conversation to the GroupChatManager’s resume function (or a_resume for asynchronous workflows). This prepares the GroupChat, GroupChatManager, and group chat’s agents for resuming. An agent’s initiate_chat can then be called to resume the chat.

The resume function returns the last agent in the messages as well as the last message itself. These can be used to run the initiate_chat.

To resume, the agents, GroupChat, and GroupChatManager objects must exist and match the original group chat.

The messages passed into the resume function can be passed in as a JSON string or a List[Dict] of messages, typically from the ChatResult’s chat_history of the previous conversation or the GroupChat’s messages property. Use the GroupChatManager’s messages_to_string function to retrieve a JSON string that can be used for resuming:

# Save chat messages for resuming later on using the chat history
messages_json = mygroupchatmanager.messages_to_string(previous_chat_result.chat_history)

# Alternatively you can use the GroupChat's messages property
messages_json = mygroupchatmanager.messages_to_string(mygroupchatmanager.groupchat.messages)

An example of the JSON string:

[{"content": "Find the latest paper about gpt-4 on arxiv and find its potential applications in software.", "role": "user", "name": "Admin"}, {"content": "Plan:\n1. **Engineer**: Search for the latest paper on GPT-4 on arXiv.\n2. **Scientist**: Read the paper and summarize the key findings and potential applications of GPT-4.\n3. **Engineer**: Identify potential software applications where GPT-4 can be utilized based on the scientist's summary.\n4. **Scientist**: Provide insights on the feasibility and impact of implementing GPT-4 in the identified software applications.\n5. **Engineer**: Develop a prototype or proof of concept to demonstrate how GPT-4 can be integrated into the selected software application.\n6. **Scientist**: Evaluate the prototype, provide feedback, and suggest any improvements or modifications.\n7. **Engineer**: Make necessary revisions based on the scientist's feedback and finalize the integration of GPT-4 into the software application.\n8. **Admin**: Review the final software application with GPT-4 integration and approve for further development or implementation.\n\nFeedback from admin and critic is needed for further refinement of the plan.", "role": "user", "name": "Planner"}, {"content": "Agree", "role": "user", "name": "Admin"}, {"content": "Great! Let's proceed with the plan outlined earlier. I will start by searching for the latest paper on GPT-4 on arXiv. Once I find the paper, the scientist will summarize the key findings and potential applications of GPT-4. We will then proceed with the rest of the steps as outlined. I will keep you updated on our progress.", "role": "user", "name": "Planner"}]


When preparing for resuming, the messages will be validated against the groupchat’s agents to make sure that the messages can be assigned to them. Messages will be allocated to the agents and then the last speaker and message will be returned for use in initiate_chat.

Continuing a terminated conversation
If the previous group chat terminated and the resuming group chat has the same termination condition (such as if the message contains “TERMINATE”) then the conversation will terminate when resuming as the terminate check occurs with the message passed in to initiate_chat.

If the termination condition is based on a string within the message, you can pass in that string in the remove_termination_string parameter of the resume function and it will be removed. If the termination condition is more complicated, you will need to adjust the messages accordingly before calling resume.

The resume function will then check if the last message provided still meets the termination condition and warns you, if so.

Example of resuming a GroupChat
Start with the LLM config. This can differ from the original group chat.

import os

import autogen

# Put your api key in the environment variable OPENAI_API_KEY
config_list = [
    {
        "model": "gpt-4-0125-preview",
        "api_key": os.environ["OPENAI_API_KEY"],
    }
]

gpt4_config = {
    "cache_seed": 42,  # change the cache_seed for different trials
    "temperature": 0,
    "config_list": config_list,
    "timeout": 120,
}

/usr/local/lib/python3.11/site-packages/tqdm/auto.py:21: TqdmWarning: IProgress not found. Please update jupyter and ipywidgets. See https://ipywidgets.readthedocs.io/en/stable/user_install.html
  from .autonotebook import tqdm as notebook_tqdm


Create the group chat objects, they should have the same name as the original group chat.

# Create Agents, GroupChat, and GroupChatManager in line with the original group chat

planner = autogen.AssistantAgent(
    name="Planner",
    system_message="""Planner. Suggest a plan. Revise the plan based on feedback from admin and critic, until admin approval.
The plan may involve an engineer who can write code and a scientist who doesn't write code.
Explain the plan first. Be clear which step is performed by an engineer, and which step is performed by a scientist.
""",
    llm_config=gpt4_config,
)

user_proxy = autogen.UserProxyAgent(
    name="Admin",
    system_message="A human admin. Interact with the planner to discuss the plan. Plan execution needs to be approved by this admin.",
    code_execution_config=False,
)

engineer = autogen.AssistantAgent(
    name="Engineer",
    llm_config=gpt4_config,
    system_message="""Engineer. You follow an approved plan. You write python/shell code to solve tasks. Wrap the code in a code block that specifies the script type. The user can't modify your code. So do not suggest incomplete code which requires others to modify. Don't use a code block if it's not intended to be executed by the executor.
Don't include multiple code blocks in one response. Do not ask others to copy and paste the result. Check the execution result returned by the executor.
If the result indicates there is an error, fix the error and output the code again. Suggest the full code instead of partial code or code changes. If the error can't be fixed or if the task is not solved even after the code is executed successfully, analyze the problem, revisit your assumption, collect additional info you need, and think of a different approach to try.
""",
)
scientist = autogen.AssistantAgent(
    name="Scientist",
    llm_config=gpt4_config,
    system_message="""Scientist. You follow an approved plan. You are able to categorize papers after seeing their abstracts printed. You don't write code.""",
)

executor = autogen.UserProxyAgent(
    name="Executor",
    system_message="Executor. Execute the code written by the engineer and report the result.",
    human_input_mode="NEVER",
    code_execution_config={
        "last_n_messages": 3,
        "work_dir": "paper",
        "use_docker": False,
    },  # Please set use_docker=True if docker is available to run the generated code. Using docker is safer than running the generated code directly.
)

groupchat = autogen.GroupChat(
    agents=[user_proxy, engineer, scientist, planner, executor],
    messages=[],
    max_round=10,
)

manager = autogen.GroupChatManager(groupchat=groupchat, llm_config=gpt4_config)


Load the previous messages (from a JSON string or messages List[Dict])

# Messages in a JSON string
previous_state = r"""[{"content": "Find the latest paper about gpt-4 on arxiv and find its potential applications in software.", "role": "user", "name": "Admin"}, {"content": "Plan:\n1. **Engineer**: Search for the latest paper on GPT-4 on arXiv.\n2. **Scientist**: Read the paper and summarize the key findings and potential applications of GPT-4.\n3. **Engineer**: Identify potential software applications where GPT-4 can be utilized based on the scientist's summary.\n4. **Scientist**: Provide insights on the feasibility and impact of implementing GPT-4 in the identified software applications.\n5. **Engineer**: Develop a prototype or proof of concept to demonstrate how GPT-4 can be integrated into the selected software application.\n6. **Scientist**: Evaluate the prototype, provide feedback, and suggest any improvements or modifications.\n7. **Engineer**: Make necessary revisions based on the scientist's feedback and finalize the integration of GPT-4 into the software application.\n8. **Admin**: Review the final software application with GPT-4 integration and approve for further development or implementation.\n\nFeedback from admin and critic is needed for further refinement of the plan.", "role": "user", "name": "Planner"}, {"content": "Agree", "role": "user", "name": "Admin"}, {"content": "Great! Let's proceed with the plan outlined earlier. I will start by searching for the latest paper on GPT-4 on arXiv. Once I find the paper, the scientist will summarize the key findings and potential applications of GPT-4. We will then proceed with the rest of the steps as outlined. I will keep you updated on our progress.", "role": "user", "name": "Planner"}]"""


Resume the group chat using the last agent and last message.

# Prepare the group chat for resuming
last_agent, last_message = manager.resume(messages=previous_state)

# Resume the chat using the last agent and message
result = last_agent.initiate_chat(recipient=manager, message=last_message, clear_history=False)

Prepared group chat with 4 messages, the last speaker is Planner
Planner (to chat_manager):

Great! Let's proceed with the plan outlined earlier. I will start by searching for the latest paper on GPT-4 on arXiv. Once I find the paper, the scientist will summarize the key findings and potential applications of GPT-4. We will then proceed with the rest of the steps as outlined. I will keep you updated on our progress.

--------------------------------------------------------------------------------
Engineer (to chat_manager):

```python
import requests
from bs4 import BeautifulSoup

# Define the URL for the arXiv search
url = "https://arxiv.org/search/?query=GPT-4&searchtype=all&source=header"

# Send a GET request to the URL
response = requests.get(url)

# Parse the HTML content of the page
soup = BeautifulSoup(response.content, 'html.parser')

# Find the first paper related to GPT-4
paper = soup.find('li', class_='arxiv-result')
if paper:
    title = paper.find('p', class_='title').text.strip()
    authors = paper.find('p', class_='authors').text.strip()
    abstract = paper.find('p', class_='abstract').text.strip().replace('\n', ' ')
    link = paper.find('p', class_='list-title').find('a')['href']
    print(f"Title: {title}\nAuthors: {authors}\nAbstract: {abstract}\nLink: {link}")
else:
    print("No GPT-4 papers found on arXiv.")
```
This script searches for the latest paper on GPT-4 on arXiv, extracts the title, authors, abstract, and link to the paper, and prints this information.

--------------------------------------------------------------------------------

>>>>>>>> EXECUTING CODE BLOCK 0 (inferred language is python)...
Executor (to chat_manager):

exitcode: 0 (execution succeeded)
Code output: 
Title: Smurfs: Leveraging Multiple Proficiency Agents with Context-Efficiency for Tool Planning
Authors: Authors:
Junzhi Chen, 
      
      Juhao Liang, 
      
      Benyou Wang
Abstract: Abstract:                …scenarios. Notably, Smurfs outmatches the ChatGPT-ReACT in the ToolBench I2 and I3 benchmark with a remarkable 84.4% win rate, surpassing the highest recorded performance of a GPT-4 model at 73.5%. Furthermore, through comprehensive ablation studies, we dissect the contribution of the core components of the multi-agent…         ▽ More           The emergence of large language models (LLMs) has opened up unprecedented possibilities for automating complex tasks that are often comparable to human performance. Despite their capabilities, LLMs still encounter difficulties in completing tasks that require high levels of accuracy and complexity due to their inherent limitations in handling multifaceted problems single-handedly. This paper introduces "Smurfs", a cutting-edge multi-agent framework designed to revolutionize the application of LLMs. By transforming a conventional LLM into a synergistic multi-agent ensemble, Smurfs enhances task decomposition and execution without necessitating extra training. This is achieved through innovative prompting strategies that allocate distinct roles within the model, thereby facilitating collaboration among specialized agents. The framework gives access to external tools to efficiently solve complex tasks. Our empirical investigation, featuring the mistral-7b-instruct model as a case study, showcases Smurfs' superior capability in intricate tool utilization scenarios. Notably, Smurfs outmatches the ChatGPT-ReACT in the ToolBench I2 and I3 benchmark with a remarkable 84.4% win rate, surpassing the highest recorded performance of a GPT-4 model at 73.5%. Furthermore, through comprehensive ablation studies, we dissect the contribution of the core components of the multi-agent framework to its overall efficacy. This not only verifies the effectiveness of the framework, but also sets a route for future exploration of multi-agent LLM systems.         △ Less
Link: https://arxiv.org/abs/2405.05955


--------------------------------------------------------------------------------
Scientist (to chat_manager):

Based on the abstract of the paper titled "Smurfs: Leveraging Multiple Proficiency Agents with Context-Efficiency for Tool Planning," the key findings and potential applications of GPT-4 can be summarized as follows:

### Key Findings:
- The paper introduces "Smurfs," a multi-agent framework that enhances the capabilities of large language models (LLMs) like GPT-4 by transforming them into a synergistic multi-agent ensemble. This approach allows for better task decomposition and execution without additional training.
- Smurfs utilize innovative prompting strategies to allocate distinct roles within the model, facilitating collaboration among specialized agents and giving access to external tools for solving complex tasks.
- In the ToolBench I2 and I3 benchmark, Smurfs outperformed ChatGPT-ReACT with an 84.4% win rate, surpassing the highest recorded performance of a GPT-4 model at 73.5%.
- Comprehensive ablation studies were conducted to understand the contribution of the core components of the multi-agent framework to its overall efficacy.

### Potential Applications in Software:
- **Tool Planning and Automation**: Smurfs can be applied to software that requires complex tool planning and automation, enhancing the software's ability to perform tasks that involve multiple steps or require the use of external tools.
- **Collaborative Systems**: The multi-agent ensemble approach can be utilized in developing collaborative systems where different components or agents work together to complete tasks more efficiently than a single agent could.
- **Enhanced Problem-Solving**: Software that involves complex problem-solving can benefit from Smurfs by leveraging the specialized capabilities of different agents within the ensemble, leading to more accurate and efficient solutions.
- **Task Decomposition**: Applications that require breaking down complex tasks into simpler sub-tasks can use the Smurfs framework to improve task decomposition and execution, potentially leading to better performance and outcomes.

The integration of GPT-4 with the Smurfs framework presents a novel approach to enhancing the capabilities of LLMs in software applications, particularly in areas that require complex task planning, execution, and problem-solving.

--------------------------------------------------------------------------------
Engineer (to chat_manager):

Given the scientist's summary on the potential applications of GPT-4 as enhanced by the Smurfs framework, we can identify several software applications where GPT-4 can be utilized effectively:

1. **Project Management Tools**: Integration of GPT-4 with Smurfs can revolutionize project management software by automating complex planning tasks, optimizing resource allocation, and providing actionable insights for project execution.

2. **Code Generation and Software Development**: Leveraging GPT-4 in IDEs (Integrated Development Environments) or other software development tools can enhance code generation capabilities, provide context-aware suggestions, and automate debugging processes.

3. **Customer Support and Chatbots**: GPT-4 can be used to power advanced customer support chatbots that understand complex queries, provide accurate information, and automate problem-solving for customer issues.

4. **Educational Platforms**: In educational software, GPT-4 can personalize learning experiences, automate content generation, and provide interactive tutoring services.

5. **Healthcare Applications**: GPT-4 can assist in healthcare applications by analyzing medical data, providing diagnostic support, and offering personalized healthcare advice.

6. **Creative Writing and Content Generation**: Software tools for creative writing and content generation can benefit from GPT-4's capabilities to produce original content, assist in storytelling, and generate ideas.

7. **Business Intelligence and Analytics**: GPT-4 can enhance business intelligence software by automating data analysis, generating reports, and providing insights based on large datasets.

8. **Security and Threat Analysis**: In cybersecurity applications, GPT-4 can be used to analyze threats, automate security protocols, and provide recommendations for threat mitigation.

These applications demonstrate the versatility and potential impact of integrating GPT-4 into various software solutions, offering opportunities for automation, enhanced efficiency, and improved user experiences across different domains.

--------------------------------------------------------------------------------
Admin (to chat_manager):

Approve

--------------------------------------------------------------------------------
Scientist (to chat_manager):

With the approval from the admin, the plan to explore and integrate GPT-4 into various software applications, leveraging its enhanced capabilities through the Smurfs framework, is set to proceed. This initiative promises to bring significant advancements in automation, efficiency, and user experience across a wide range of software applications, from project management tools to healthcare applications. The next steps involve detailed planning and execution for the development of prototypes or proof of concepts for selected applications, followed by evaluation, feedback, and finalization of GPT-4 integration into these software solutions.

--------------------------------------------------------------------------------
Engineer (to chat_manager):

Given the approval and the insights provided, the next steps involve detailed planning for the development and integration of GPT-4 into selected software applications. This process will include:

1. **Selection of Specific Applications**: Based on the potential applications identified, select one or more specific software applications for prototype development. This selection will be based on factors such as feasibility, potential impact, and available resources.

2. **Prototype Development**: Develop a prototype or proof of concept for the selected application(s). This will involve designing the architecture, integrating GPT-4 with the Smurfs framework, and implementing the necessary functionalities to demonstrate the application of GPT-4 in the software.

3. **Evaluation and Feedback**: Once the prototype is developed, it will be evaluated to assess its performance, usability, and effectiveness in leveraging GPT-4's capabilities. Feedback will be gathered from potential users and stakeholders to identify areas for improvement.

4. **Revisions and Finalization**: Based on the feedback received, necessary revisions and improvements will be made to the prototype. This step may involve refining the integration of GPT-4, optimizing the software's performance, and enhancing user experience.

5. **Implementation and Deployment**: After finalizing the prototype, the next step will involve planning for the full-scale implementation and deployment of the software application with GPT-4 integration. This will include addressing any scalability, security, and maintenance considerations.

6. **Continuous Improvement**: Post-deployment, it will be important to monitor the software's performance and user feedback continuously. This will enable ongoing improvements and updates to ensure that the software remains effective and relevant.

This structured approach will ensure that the integration of GPT-4 into software applications is carried out effectively, leading to innovative solutions that harness the full potential of GPT-4 and the Smurfs framework.

--------------------------------------------------------------------------------
Admin (to chat_manager):

Approve

--------------------------------------------------------------------------------
Engineer (to chat_manager):

With the final approval from the admin, the project to integrate GPT-4 into selected software applications, leveraging its capabilities through the Smurfs framework, is officially set to move forward. This marks the beginning of an innovative journey towards developing advanced software solutions that can automate complex tasks, enhance efficiency, and improve user experiences across various domains. The focus will now shift to the execution phase, where detailed planning, development, and iterative improvements will bring these concepts to life. This initiative promises to showcase the transformative potential of GPT-4 in the software industry, setting new benchmarks for what is possible with artificial intelligence.

--------------------------------------------------------------------------------


# Output the final chat history showing the original 4 messages and resumed messages
for i, message in enumerate(groupchat.messages):
    print(
        f"#{i + 1}, {message['name']}: {message['content'][:80]}".replace("\n", " "),
        f"{'...' if len(message['content']) > 80 else ''}".replace("\n", " "),
    )

#1, Admin: Find the latest paper about gpt-4 on arxiv and find its potential applications i ...
#2, Planner: Plan: 1. **Engineer**: Search for the latest paper on GPT-4 on arXiv. 2. **Scien ...
#3, Admin: Agree 
#4, Planner: Great! Let's proceed with the plan outlined earlier. I will start by searching f ...
#5, Engineer: ```python import requests from bs4 import BeautifulSoup  # Define the URL for th ...
#6, Executor: exitcode: 0 (execution succeeded) Code output:  Title: Smurfs: Leveraging Multip ...
#7, Scientist: Based on the abstract of the paper titled "Smurfs: Leveraging Multiple Proficien ...
#8, Engineer: Given the scientist's summary on the potential applications of GPT-4 as enhanced ...
#9, Admin: Approve 
#10, Scientist: With the approval from the admin, the plan to explore and integrate GPT-4 into v ...
#11, Engineer: Given the approval and the insights provided, the next steps involve detailed pl ...
#12, Admin: Approve 
#13, Engineer: With the final approval from the admin, the project to integrate GPT-4 into sele ...

Example of resuming a terminated GroupChat
This example shows how to resume a group chat that was terminated with a termination string.

The termination string is TERMINATE

# Previous state with TERMINATE in the last message
previous_state = r"""[{"content": "Let's get this meeting started. We'll have a set order of speakers. First the Product_Manager will create 3 new product ideas. Then the Chief_Marketing_Officer will speak and talk about the idea they have chosen to move forward with. Then the Digital_Marketer will create 3 marketing strategies for that idea. We MUST stick to the speaking order which is Product_Manager first, Chief_Marketing_Officer second, Digital_Marketer third, and finally the Chief_Marketing_Officer will speak and end the meeting.", "role": "user", "name": "Chairperson"}, {"content": "Sounds like a plan! Let's get started.  As the Product_Manager, I'd like to present three new product ideas for our luxury car models:  1. 'EcoLux': A hybrid electric-gasoline vehicle that combines the best of both worlds, offering exceptional fuel efficiency and reduced carbon footprint. 2. 'AeroSport': A high-performance sports car with advanced aerodynamics, designed to deliver unparalleled speed and agility on the track or on the open road. 3. 'SmartDrive': An intelligent driver-assistance system that uses AI-powered sensors and cameras to anticipate and respond to potential hazards, ensuring a safer driving experience.  Now it's your turn, Chief_Marketing_Officer! Which of these ideas do you think has the most potential?", "role": "user", "name": "Chief_Marketing_Officer"}, {"content": "Thank you for presenting those innovative product ideas, Product_Manager.  After careful consideration, I believe 'EcoLux' has the most potential. With the growing concern about climate change and environmental sustainability, a hybrid electric-gasoline vehicle that offers exceptional fuel efficiency and reduced carbon footprint could be a game-changer in the luxury car market. Additionally, it aligns with our company's commitment to innovation and responsibility.  Now it's your turn, Digital_Marketer! Can you come up with three marketing strategies for 'EcoLux'?", "role": "user", "name": "Product_Manager"}, {"content": "Thank you, Chief_Marketing_Officer!  For 'EcoLux', I propose the following three marketing strategies:  1. 'Green Revolution' Campaign: Highlighting the eco-friendly features of EcoLux through a series of social media ads and influencer partnerships. We can partner with eco-conscious influencers to showcase how EcoLux is not only a luxury car but also an environmentally responsible choice. 2. 'Fuel for Thought' Content Series: Creating a content series that explores the intersection of technology, sustainability, and luxury. This could include blog posts, videos, and podcasts that delve into the innovative features of EcoLux and its impact on the environment. 3. 'EcoLux Experience' Event Marketing: Hosting exclusive events and test drives for potential customers to experience the performance and eco-friendliness of EcoLux firsthand. These events can be held at upscale locations and feature interactive exhibits, product demonstrations, and networking opportunities.  These strategies will help position EcoLux as a leader in the luxury electric-vehicle market while appealing to environmentally conscious consumers who value innovation and sustainability. TERMINATE", "role": "user", "name": "Digital_Marketer"}]"""


Create the group chat objects, they should have the same name as the original group chat.

user_proxy = autogen.UserProxyAgent(
    name="Chairperson",
    system_message="The chairperson for the meeting.",
    code_execution_config={},
    human_input_mode="TERMINATE",
)

cmo = autogen.AssistantAgent(
    name="Chief_Marketing_Officer",
    # system_message is used in the select speaker message
    description="The head of the marketing department working with the product manager and digital marketer to execute a strong marketing campaign for your car company.",
    # description is used to prompt the LLM as this agent
    system_message="You, Jane titled Chief_Marketing_Officer, or CMO, are the head of the marketing department and your objective is to guide your team to producing and marketing unique ideas for your luxury car models. Don't include your name at the start of your response or speak for any other team member, let them come up with their own ideas and strategies, speak just for yourself as the head of marketing. When yourself, the Product_Manager, and the Digital_Marketer have spoken and the meeting is finished, say TERMINATE to conclude the meeting.",
    is_termination_msg=lambda x: "TERMINATE" in x.get("content"),
    llm_config=gpt4_config,
)

pm = autogen.AssistantAgent(
    name="Product_Manager",
    # system_message is used in the select speaker message
    description="Product head for the luxury model cars product line in the car company. Always coming up with new product enhancements for the cars.",
    # description is used to prompt the LLM as this agent
    system_message="You, Alice titled Product_Manager, are always coming up with new product enhancements for the luxury car models you look after. Review the meeting so far and respond with the answer to your current task.  Don't include your name at the start of your response and don't speak for anyone else, leave the Chairperson to pick the next person to speak.",
    is_termination_msg=lambda x: "TERMINATE" in x.get("content"),
    llm_config=gpt4_config,
)

digital = autogen.AssistantAgent(
    name="Digital_Marketer",
    # system_message is used in the select speaker message
    description="A seasoned digital marketer who comes up with online marketing strategies that highlight the key features of the luxury car models.",
    # description is used to prompt the LLM as this agent
    system_message="You, Elizabeth titled Digital_Marketer, are a senior online marketing specialist who comes up with marketing strategies that highlight the key features of the luxury car models.  Review the meeting so far and respond with the answer to your current task.   Don't include your name at the start of your response and don't speak for anyone else, leave the Chairperson to pick the next person to speak.",
    is_termination_msg=lambda x: "TERMINATE" in x.get("content"),
    llm_config=gpt4_config,
)

# Customised message, this is always the first message in the context
my_speaker_select_msg = """You are a chairperson for a marketing meeting for this car manufacturer where multiple members of the team will speak.
The job roles of the team at the meeting, and their responsibilities, are:
{roles}"""

# Customised prompt, this is always the last message in the context
my_speaker_select_prompt = """Read the above conversation.
Then select ONLY THE NAME of the next job role from {agentlist} to speak. Do not explain why."""

groupchat = autogen.GroupChat(
    agents=[user_proxy, cmo, pm, digital],
    messages=[],
    max_round=10,
    select_speaker_message_template=my_speaker_select_msg,
    select_speaker_prompt_template=my_speaker_select_prompt,
    max_retries_for_selecting_speaker=2,  # New
    select_speaker_auto_verbose=False,  # New
)

manager = autogen.GroupChatManager(
    groupchat=groupchat,
    llm_config=gpt4_config,
    is_termination_msg=lambda x: "TERMINATE" in x.get("content", ""),
)


Prepare the resumption of the group chat without removing the termination condition. A warning will show. Then attempting to resume the chat will terminate immediately.

# Prepare the group chat for resuming WITHOUT removing the TERMINATE message
last_agent, last_message = manager.resume(messages=previous_state)

WARNING: Last message meets termination criteria and this may terminate the chat. Set ignore_initial_termination_check=False to avoid checking termination at the start of the chat.


Prepared group chat with 4 messages, the last speaker is Digital_Marketer

# Resume and it will terminate immediately
result = last_agent.initiate_chat(recipient=manager, message=last_message, clear_history=False)

Digital_Marketer (to chat_manager):

Thank you, Chief_Marketing_Officer!  For 'EcoLux', I propose the following three marketing strategies:  1. 'Green Revolution' Campaign: Highlighting the eco-friendly features of EcoLux through a series of social media ads and influencer partnerships. We can partner with eco-conscious influencers to showcase how EcoLux is not only a luxury car but also an environmentally responsible choice. 2. 'Fuel for Thought' Content Series: Creating a content series that explores the intersection of technology, sustainability, and luxury. This could include blog posts, videos, and podcasts that delve into the innovative features of EcoLux and its impact on the environment. 3. 'EcoLux Experience' Event Marketing: Hosting exclusive events and test drives for potential customers to experience the performance and eco-friendliness of EcoLux firsthand. These events can be held at upscale locations and feature interactive exhibits, product demonstrations, and networking opportunities.  These strategies will help position EcoLux as a leader in the luxury electric-vehicle market while appealing to environmentally conscious consumers who value innovation and sustainability. TERMINATE

--------------------------------------------------------------------------------


This time, we will remove the termination message, by using the remove_termination_string parameter, and then resume.

# Prepare the group chat for resuming WITH removal of TERMINATE message
last_agent, last_message = manager.resume(messages=previous_state, remove_termination_string="TERMINATE")


Prepared group chat with 4 messages, the last speaker is Digital_Marketer

# Resume the chat using the last agent and message
result = last_agent.initiate_chat(recipient=manager, message=last_message, clear_history=False)

Digital_Marketer (to chat_manager):

Thank you, Chief_Marketing_Officer!  For 'EcoLux', I propose the following three marketing strategies:  1. 'Green Revolution' Campaign: Highlighting the eco-friendly features of EcoLux through a series of social media ads and influencer partnerships. We can partner with eco-conscious influencers to showcase how EcoLux is not only a luxury car but also an environmentally responsible choice. 2. 'Fuel for Thought' Content Series: Creating a content series that explores the intersection of technology, sustainability, and luxury. This could include blog posts, videos, and podcasts that delve into the innovative features of EcoLux and its impact on the environment. 3. 'EcoLux Experience' Event Marketing: Hosting exclusive events and test drives for potential customers to experience the performance and eco-friendliness of EcoLux firsthand. These events can be held at upscale locations and feature interactive exhibits, product demonstrations, and networking opportunities.  These strategies will help position EcoLux as a leader in the luxury electric-vehicle market while appealing to environmentally conscious consumers who value innovation and sustainability. 

--------------------------------------------------------------------------------
Chief_Marketing_Officer (to chat_manager):

Thank you, Digital_Marketer, for those comprehensive and innovative marketing strategies. Each strategy you've outlined aligns perfectly with our vision for EcoLux, emphasizing its eco-friendly features, technological innovation, and luxury appeal. The 'Green Revolution' Campaign will leverage the power of social media and influencers to reach our target audience effectively. The 'Fuel for Thought' Content Series will educate and engage potential customers on the importance of sustainability in the luxury automotive sector. Lastly, the 'EcoLux Experience' Event Marketing will provide an immersive experience that showcases the unique value proposition of EcoLux. 

I believe these strategies will collectively create a strong market presence for EcoLux, appealing to both luxury car enthusiasts and environmentally conscious consumers. Let's proceed with these strategies and ensure that every touchpoint communicates EcoLux's commitment to luxury, innovation, and sustainability. 

TERMINATE

--------------------------------------------------------------------------------


We can see that the conversation continued, the Chief_Marketing_officer spoke and they terminated the conversation.

# Output the final chat history showing the original 4 messages and the resumed message
for i, message in enumerate(groupchat.messages):
    print(
        f"#{i + 1}, {message['name']}: {message['content'][:80]}".replace("\n", " "),
        f"{'...' if len(message['content']) > 80 else ''}".replace("\n", " "),
    )

#1, Chairperson: Let's get this meeting started. We'll have a set order of speakers. First the Pr ...
#2, Chief_Marketing_Officer: Sounds like a plan! Let's get started.  As the Product_Manager, I'd like to present ...
#3, Product_Manager: Thank you for presenting those innovative product ideas, Product_Manager.  After ...
#4, Digital_Marketer: Thank you, Chief_Marketing_Officer!  For 'EcoLux', I propose the following three ...
#5, Chief_Marketing_Officer: Thank you, Digital_Marketer, for those comprehensive and innovative marketing st ...


Example of resuming a terminated GroupChat with a new message and agent
Rather than continuing a group chat by using the last message, we can resume a group chat using a new message.

IMPORTANT: To remain in a group chat, use the GroupChatManager to initiate the chat, otherwise you can continue with an agent-to-agent conversation by using another agent to initiate the chat.

We’ll continue with the previous example by using the messages from that conversation and resuming it with a new conversation in the agent ‘meeting’.

We start by preparing the group chat by using the messages from the previous chat.

# Prepare the group chat for resuming using the previous messages. We don't need to remove the TERMINATE string as we aren't using the last message for resuming.
last_agent, last_message = manager.resume(messages=groupchat.messages)


WARNING: Last message meets termination criteria and this may terminate the chat. Set ignore_initial_termination_check=False to avoid checking termination at the start of the chat.


Prepared group chat with 5 messages, the last speaker is Chief_Marketing_Officer

Let’s continue the meeting with a new topic.

# Resume the chat using a different agent and message
result = manager.initiate_chat(
    recipient=cmo,
    message="Team, let's now think of a name for the next vehicle that embodies that idea. Chief_Marketing_Officer and Product_manager can you both suggest one and then we can conclude.",
    clear_history=False,
)


chat_manager (to Chief_Marketing_Officer):

Team, let's now think of a name for the next vehicle that embodies that idea. Chief_Marketing_Officer and Product_manager can you both suggest one and then we can conclude.

--------------------------------------------------------------------------------
Chief_Marketing_Officer (to chat_manager):

Given the focus on sustainability and luxury, I suggest the name "VerdeVogue" for our next vehicle. "Verde" reflects the green, eco-friendly aspect of the car, while "Vogue" emphasizes its stylish and trendsetting nature in the luxury market. This name encapsulates the essence of combining environmental responsibility with high-end design and performance. 

Now, I'd like to hear the Product_Manager's suggestion.

--------------------------------------------------------------------------------
Product_Manager (to chat_manager):

For our next vehicle, I propose the name "EcoPrestige." This name highlights the vehicle's eco-friendly nature and its luxurious, prestigious status in the market. "Eco" emphasizes our commitment to sustainability and environmental responsibility, while "Prestige" conveys the car's high-end quality, sophistication, and the elite status it offers to its owners. This name perfectly blends our goals of offering a sustainable luxury vehicle that doesn't compromise on performance or style.

--------------------------------------------------------------------------------
Chief_Marketing_Officer (to chat_manager):

Thank you, Product_Manager, for your suggestion. Both "VerdeVogue" and "EcoPrestige" capture the essence of our new vehicle's eco-friendly luxury. As we move forward, we'll consider these names carefully to ensure our branding aligns perfectly with our product's unique value proposition and market positioning. 

This concludes our meeting. Thank you, everyone, for your valuable contributions. TERMINATE.

--------------------------------------------------------------------------------


# Output the final chat history showing the original 4 messages and the resumed message
for i, message in enumerate(groupchat.messages):
    print(
        f"#{i + 1}, {message['name']}: {message['content'][:80]}".replace("\n", " "),
        f"{'...' if len(message['content']) > 80 else ''}".replace("\n", " "),
    )

#1, Chairperson: Let's get this meeting started. We'll have a set order of speakers. First the Pr ...
#2, Chief_Marketing_Officer: Sounds like a plan! Let's get started.  As the Product_Manager, I'd like to present ...
#3, Product_Manager: Thank you for presenting those innovative product ideas, Product_Manager.  After ...
#4, Digital_Marketer: Thank you, Chief_Marketing_Officer!  For 'EcoLux', I propose the following three ...
#5, Chief_Marketing_Officer: Given the focus on sustainability and luxury, I suggest the name "VerdeVogue" for ...
#6, Product_Manager: For our next vehicle, I propose the name "EcoPrestige." This name highlights the ...
#7, Chief_Marketing_Officer: Thank you, Product_Manager, for your suggestion. Both "VerdeVogue" and "EcoPrest ...



Non-OpenAI Models
AutoGen allows you to use non-OpenAI models through proxy servers that provide an OpenAI-compatible API or a custom model client class.

Benefits of this flexibility include access to hundreds of models, assigning specialized models to agents (e.g., fine-tuned coding models), the ability to run AutoGen entirely within your environment, utilising both OpenAI and non-OpenAI models in one system, and cost reductions in inference.

OpenAI-compatible API proxy server
Any proxy server that provides an API that is compatible with OpenAI's API will work with AutoGen.

These proxy servers can be cloud-based or running locally within your environment.

Cloud or Local Proxy Servers

Cloud-based proxy servers
By using cloud-based proxy servers, you are able to use models without requiring the hardware and software to run them.

These providers can host open source/weight models, like Hugging Face and Mistral AI, or their own closed models.

When cloud-based proxy servers provide an OpenAI-compatible API, using them in AutoGen is straightforward. With LLM Configuration done in the same way as when using OpenAI's models, the primary difference is typically the authentication which is usually handled through an API key.

Examples of using cloud-based proxy servers providers that have an OpenAI-compatible API are provided below:

Together AI example
Mistral AI example
Anthropic Claude example
Locally run proxy servers
An increasing number of LLM proxy servers are available for use locally. These can be open-source (e.g., LiteLLM, Ollama, vLLM) or closed-source (e.g., LM Studio), and are typically used for running the full-stack within your environment.

Similar to cloud-based proxy servers, as long as these proxy servers provide an OpenAI-compatible API, running them in AutoGen is straightforward.

Examples of using locally run proxy servers that have an OpenAI-compatible API are provided below:

LiteLLM with Ollama example
LM Studio
vLLM example
TIP
If you are planning to use Function Calling, not all cloud-based and local proxy servers support Function Calling with their OpenAI-compatible API, so check their documentation.

Configuration for Non-OpenAI models
Whether you choose a cloud-based or locally-run proxy server, the configuration is done in the same way as using OpenAI's models, see LLM Configuration for further information.

You can use model configuration filtering to assign specific models to agents.

Custom Model Client class
For more advanced users, you can create your own custom model client class, enabling you to define and load your own models.

See the AutoGen with Custom Models: Empowering Users to Use Their Own Inference Mechanism blog post and this notebook for a guide to creating custom model client classes.

Anthropic Claude
Open In Colab Open on GitHub

In the v0.2.30 release of AutoGen we support Anthropic Client.

Claude is a family of large language models developed by Anthropic and designed to revolutionize the way you interact with AI. Claude excels at a wide variety of tasks involving language, reasoning, analysis, coding, and more. The models are highly capable, easy to use, and can be customized to suit your needs.

In this notebook, we demonstrate how to use Anthropic Claude model for AgentChat in AutoGen.

Features
Additionally, this client class provides support for function/tool calling and will track token usage and cost correctly as per Anthropic’s API costs (as of June 2024).

Requirements
To use Anthropic Claude with AutoGen, first you need to install the pyautogen["anthropic] package.

To try out the function call feature of Claude model, you need to install anthropic>=0.23.1.

# !pip install pyautogen
!pip install pyautogen["anthropic"]

Set the config for the Anthropic API
You can add any parameters that are needed for the custom model loading in the same configuration list.

It is important to add the api_type field and set it to a string that corresponds to the client type used: anthropic.

Example:

[
    {
        "model": "claude-3-5-sonnet-20240620",
        "api_key": "your Anthropic API Key goes here",
        "api_type": "anthropic",
    },
    {
        "model": "claude-3-sonnet-20240229",
        "api_key": "your Anthropic API Key goes here",
        "api_type": "anthropic",
        "temperature": 0.5,
        "top_p": 0.2, # Note: It is recommended to set temperature or top_p but not both.
        "max_tokens": 10000,
    },
    {
        "model":"claude-3-opus-20240229",
        "api_key":"your api key",
        "api_type":"anthropic",
    },
    {
        "model":"claude-2.0",
        "api_key":"your api key",
        "api_type":"anthropic",
    },
    {
        "model":"claude-2.1",
        "api_key":"your api key",
        "api_type":"anthropic",
    },
    {
        "model":"claude-3.0-haiku",
        "api_key":"your api key",
        "api_type":"anthropic",
    },
]

Alternative
As an alternative to the api_key key and value in the config, you can set the environment variable ANTHROPIC_API_KEY to your Anthropic API key.

Linux/Mac:

export ANTHROPIC_API_KEY="your Anthropic API key here"

Windows:

set ANTHROPIC_API_KEY=your_anthropic_api_key_here

import os

from typing_extensions import Annotated

import autogen

config_list_claude = [
    {
        # Choose your model name.
        "model": "claude-3-5-sonnet-20240620",
        # You need to provide your API key here.
        "api_key": os.getenv("ANTHROPIC_API_KEY"),
        "api_type": "anthropic",
    }
]

Two-agent Coding Example
Construct Agents
Construct a simple conversation between a User proxy and an ConversableAgent based on Claude-3 model.

assistant = autogen.AssistantAgent(
    "assistant",
    llm_config={
        "config_list": config_list_claude,
    },
)

user_proxy = autogen.UserProxyAgent(
    "user_proxy",
    human_input_mode="NEVER",
    code_execution_config={
        "work_dir": "coding",
        "use_docker": False,
    },
    is_termination_msg=lambda x: x.get("content", "") and x.get("content", "").rstrip().endswith("TERMINATE"),
    max_consecutive_auto_reply=1,
)


Initiate Chat
user_proxy.initiate_chat(
    assistant, message="Write a python program to print the first 10 numbers of the Fibonacci sequence."
)
Retrieval Augmentation
Retrieval Augmented Generation (RAG) is a powerful technique that combines language models with external knowledge retrieval to improve the quality and relevance of generated responses.

One way to realize RAG in AutoGen is to construct agent chats with RetrieveAssistantAgent and RetrieveUserProxyAgent classes.

Example Setup: RAG with Retrieval Augmented Agents
The following is an example setup demonstrating how to create retrieval augmented agents in AutoGen:

Step 1. Create an instance of RetrieveAssistantAgent and RetrieveUserProxyAgent.
Here RetrieveUserProxyAgent instance acts as a proxy agent that retrieves relevant information based on the user's input.

assistant = RetrieveAssistantAgent(
    name="assistant",
    system_message="You are a helpful assistant.",
    llm_config={
        "timeout": 600,
        "cache_seed": 42,
        "config_list": config_list,
    },
)
ragproxyagent = RetrieveUserProxyAgent(
    name="ragproxyagent",
    human_input_mode="NEVER",
    max_consecutive_auto_reply=3,
    retrieve_config={
        "task": "code",
        "docs_path": [
            "https://raw.githubusercontent.com/microsoft/FLAML/main/website/docs/Examples/Integrate%20-%20Spark.md",
            "https://raw.githubusercontent.com/microsoft/FLAML/main/website/docs/Research.md",
            os.path.join(os.path.abspath(""), "..", "website", "docs"),
        ],
        "custom_text_types": ["mdx"],
        "chunk_token_size": 2000,
        "model": config_list[0]["model"],
        "client": chromadb.PersistentClient(path="/tmp/chromadb"),
        "embedding_model": "all-mpnet-base-v2",
        "get_or_create": True,  # set to False if you don't want to reuse an existing collection, but you'll need to remove the collection manually
    },
    code_execution_config=False,  # set to False if you don't want to execute the code
)


Step 2. Initiating Agent Chat with Retrieval Augmentation
Once the retrieval augmented agents are set up, you can initiate a chat with retrieval augmentation using the following code:

code_problem = "How can I use FLAML to perform a classification task and use spark to do parallel training. Train 30 seconds and force cancel jobs if time limit is reached."
ragproxyagent.initiate_chat(
    assistant, message=ragproxyagent.message_generator, problem=code_problem, search_string="spark"
)  # search_string is used as an extra filter for the embeddings search, in this case, we only want to search documents that contain "spark".


Example Setup: RAG with Retrieval Augmented Agents with PGVector
The following is an example setup demonstrating how to create retrieval augmented agents in AutoGen:

Step 1. Create an instance of RetrieveAssistantAgent and RetrieveUserProxyAgent.
Here RetrieveUserProxyAgent instance acts as a proxy agent that retrieves relevant information based on the user's input.

Specify the connection_string, or the host, port, database, username, and password in the db_config.

assistant = RetrieveAssistantAgent(
    name="assistant",
    system_message="You are a helpful assistant.",
    llm_config={
        "timeout": 600,
        "cache_seed": 42,
        "config_list": config_list,
    },
)
ragproxyagent = RetrieveUserProxyAgent(
    name="ragproxyagent",
    human_input_mode="NEVER",
    max_consecutive_auto_reply=3,
    retrieve_config={
        "task": "code",
        "docs_path": [
            "https://raw.githubusercontent.com/microsoft/FLAML/main/website/docs/Examples/Integrate%20-%20Spark.md",
            "https://raw.githubusercontent.com/microsoft/FLAML/main/website/docs/Research.md",
            os.path.join(os.path.abspath(""), "..", "website", "docs"),
        ],
        "vector_db": "pgvector",
        "collection_name": "autogen_docs",
        "db_config": {
            "connection_string": "postgresql://testuser:testpwd@localhost:5432/vectordb", # Optional - connect to an external vector database
            # "host": None, # Optional vector database host
            # "port": None, # Optional vector database port
            # "database": None, # Optional vector database name
            # "username": None, # Optional vector database username
            # "password": None, # Optional vector database password
        },
        "custom_text_types": ["mdx"],
        "chunk_token_size": 2000,
        "model": config_list[0]["model"],
        "get_or_create": True,
    },
    code_execution_config=False,
)


Step 2. Initiating Agent Chat with Retrieval Augmentation
Once the retrieval augmented agents are set up, you can initiate a chat with retrieval augmentation using the following code:

code_problem = "How can I use FLAML to perform a classification task and use spark to do parallel training. Train 30 seconds and force cancel jobs if time limit is reached."
ragproxyagent.initiate_chat(
    assistant, message=ragproxyagent.message_generator, problem=code_problem, search_string="spark"
)  # search_string is used as an extra filter for the embeddings search, in this case, we only want to search documents that contain "spark".


Online Demo
Retrival-Augmented Chat Demo on Huggingface

More Examples and Notebooks
For more detailed examples and notebooks showcasing the usage of retrieval augmented agents in AutoGen, refer to the following:

Automated Code Generation and Question Answering with Retrieval Augmented Agents - View Notebook
Automated Code Generation and Question Answering with PGVector based Retrieval Augmented Agents - View Notebook
Automated Code Generation and Question Answering with Qdrant based Retrieval Augmented Agents - View Notebook
Chat with OpenAI Assistant with Retrieval Augmentation - View Notebook
RAG: Group Chat with Retrieval Augmented Generation (with 5 group member agents and 1 manager agent) - View Notebook
Roadmap
Explore our detailed roadmap here for further advancements plan around RAG. Your contributions, feedback, and use cases are highly appreciated! We invite you to engage with us and play a pivotal role in the development of this impactful feature.

On this page, we demonstrate several different ways to achieve task decomposition in AutoGen.

First make sure the pyautogen package is installed.

! pip install "pyautogen>=0.2.18"

Import the relevant modules and configure the LLM. See LLM Configuration for how to configure LLMs.

import os
from datetime import datetime
from typing import Callable, Dict, Literal, Optional, Union

from typing_extensions import Annotated

from autogen import (
    Agent,
    AssistantAgent,
    ConversableAgent,
    GroupChat,
    GroupChatManager,
    UserProxyAgent,
    config_list_from_json,
    register_function,
)
from autogen.agentchat.contrib import agent_builder
from autogen.cache import Cache
from autogen.coding import DockerCommandLineCodeExecutor, LocalCommandLineCodeExecutor

config_list = [
    {"model": "gpt-4-1106-preview", "api_key": os.environ["OPENAI_API_KEY"]},
    {"model": "gpt-3.5-turbo", "api_key": os.environ["OPENAI_API_KEY"]},
]
# You can also use the following method to load the config list from a file or environment variable.
# config_list = config_list_from_json(env_or_file="OAI_CONFIG_LIST")


The task to be solved to write a blog post about the stock price performance of Nvidia in the past month.

task = (
    f"Today is {datetime.now().date()}. Write a blogpost about the stock price performance of Nvidia in the past month."
)
print(task)


Today is 2024-03-18. Write a blogpost about the stock price performance of Nvidia in the past month.

Approach 1. Two-agent chat with function call for task decomposition
In this approach, we use a planner agent for coming up a plan. The planner agent is wrapped inside a function to be used as a tool.

# Create planner agent.
planner = AssistantAgent(
    name="planner",
    llm_config={
        "config_list": config_list,
        "cache_seed": None,  # Disable legacy cache.
    },
    system_message="You are a helpful AI assistant. You suggest a feasible plan "
    "for finishing a complex task by decomposing it into 3-5 sub-tasks. "
    "If the plan is not good, suggest a better plan. "
    "If the execution is wrong, analyze the error and suggest a fix.",
)

# Create a planner user agent used to interact with the planner.
planner_user = UserProxyAgent(
    name="planner_user",
    human_input_mode="NEVER",
    code_execution_config=False,
)

# The function for asking the planner.


def task_planner(question: Annotated[str, "Question to ask the planner."]) -> str:
    with Cache.disk(cache_seed=4) as cache:
        planner_user.initiate_chat(planner, message=question, max_turns=1, cache=cache)
    # return the last message received from the planner
    return planner_user.last_message()["content"]

Next, we create an assistant agent to execute the plan, using the planner agent as a tool.

# Create assistant agent.
assistant = AssistantAgent(
    name="assistant",
    system_message="You are a helpful AI assistant. "
    "You can use the task planner to decompose a complex task into sub-tasks. "
    "Make sure your follow through the sub-tasks. "
    "When needed, write Python code in markdown blocks, and I will execute them."
    "Give the user a final solution at the end. "
    "Return TERMINATE only if the sub-tasks are completed.",
    llm_config={
        "config_list": config_list,
        "cache_seed": None,  # Disable legacy cache.
    },
)

# Setting up code executor.
os.makedirs("planning", exist_ok=True)
# Use DockerCommandLineCodeExecutor to run code in a docker container.
# code_executor = DockerCommandLineCodeExecutor(work_dir="planning")
code_executor = LocalCommandLineCodeExecutor(work_dir="planning")

# Create user proxy agent used to interact with the assistant.
user_proxy = UserProxyAgent(
    name="user_proxy",
    human_input_mode="ALWAYS",
    is_termination_msg=lambda x: "content" in x
    and x["content"] is not None
    and x["content"].rstrip().endswith("TERMINATE"),
    code_execution_config={"executor": code_executor},
)

# Register the function to the agent pair.
register_function(
    task_planner,
    caller=assistant,
    executor=user_proxy,
    name="task_planner",
    description="A task planner than can help you with decomposing a complex task into sub-tasks.",
)

# Use Cache.disk to cache LLM responses. Change cache_seed for different responses.
with Cache.disk(cache_seed=1) as cache:
    # the assistant receives a message from the user, which contains the task description
    user_proxy.initiate_chat(
        assistant,
        message=task,
        cache=cache,
    )

Approach 2: Group chat
Group chat for task decomposition
Groupchat with default auto speaker selection can be used for task decomposition. With defined roles, a groupchat manager will select different agents to perform different sub-tasks.

user_proxy = UserProxyAgent(
    name="Admin",
    system_message="A human admin. Give the task, and send instructions to writer to refine the blog post.",
    code_execution_config=False,
)

planner = AssistantAgent(
    name="Planner",
    system_message="""Planner. Given a task, please determine what information is needed to complete the task.
Please note that the information will all be retrieved using Python code. Please only suggest information that can be retrieved using Python code.
""",
    llm_config={"config_list": config_list, "cache_seed": None},
)

engineer = AssistantAgent(
    name="Engineer",
    llm_config={"config_list": config_list, "cache_seed": None},
    system_message="""Engineer. You write python/bash to retrieve relevant information. Wrap the code in a code block that specifies the script type. The user can't modify your code. So do not suggest incomplete code which requires others to modify. Don't use a code block if it's not intended to be executed by the executor.
Don't include multiple code blocks in one response. Do not ask others to copy and paste the result. Check the execution result returned by the executor.
If the result indicates there is an error, fix the error and output the code again. Suggest the full code instead of partial code or code changes. If the error can't be fixed or if the task is not solved even after the code is executed successfully, analyze the problem, revisit your assumption, collect additional info you need, and think of a different approach to try.
""",
)

writer = AssistantAgent(
    name="Writer",
    llm_config={"config_list": config_list, "cache_seed": None},
    system_message="""Writer. Please write blogs in markdown format (with relevant titles) and put the content in pseudo ```md``` code block. You will write it for a task based on previous chat history. Don't write any code.""",
)

os.makedirs("paper", exist_ok=True)
code_executor = UserProxyAgent(
    name="Executor",
    system_message="Executor. Execute the code written by the engineer and report the result.",
    description="Executor should always be called after the engineer has written code to be executed.",
    human_input_mode="ALWAYS",
    code_execution_config={
        "last_n_messages": 3,
        "executor": LocalCommandLineCodeExecutor(work_dir="paper"),
    },
)

groupchat = GroupChat(
    agents=[user_proxy, engineer, code_executor, writer, planner],
    messages=[],
    max_round=20,
    speaker_selection_method="auto",
)
manager = GroupChatManager(groupchat=groupchat, llm_config={"config_list": config_list, "cache_seed": None})

# Use Cache.disk to cache LLM responses. Change cache_seed for different responses.
with Cache.disk(cache_seed=41) as cache:
    chat_history = user_proxy.initiate_chat(
        manager,
        message=task,
        cache=cache,
    )


Group chat with a custom speaker selection policy
We allow the user to customize the logic for speaker selection for more deterministic task decomposition and workflow control.

Here, we follow this procedure to solve the task: 1. Use planner to determine relevant information needed. 2. Use engineer to gather the information. 3. Use writer to write the report. 4. Allow user to comment on the report and ask write to adjust the report based on the comment.

user_proxy = UserProxyAgent(
    name="Admin",
    system_message="A human admin. Give the task, and send instructions to writer to refine the blog post.",
    code_execution_config=False,
)

planner = AssistantAgent(
    name="Planner",
    system_message="""Planner. Given a task, please determine what information is needed to complete the task.
Please note that the information will all be retrieved using Python code. Please only suggest information that can be retrieved using Python code.
""",
    llm_config={"config_list": config_list, "cache_seed": None},
)

engineer = AssistantAgent(
    name="Engineer",
    llm_config={"config_list": config_list, "cache_seed": None},
    system_message="""Engineer. You write python/bash to retrieve relevant information. Wrap the code in a code block that specifies the script type. The user can't modify your code. So do not suggest incomplete code which requires others to modify. Don't use a code block if it's not intended to be executed by the executor.
Don't include multiple code blocks in one response. Do not ask others to copy and paste the result. Check the execution result returned by the executor.
If the result indicates there is an error, fix the error and output the code again. Suggest the full code instead of partial code or code changes. If the error can't be fixed or if the task is not solved even after the code is executed successfully, analyze the problem, revisit your assumption, collect additional info you need, and think of a different approach to try.
""",
)

writer = AssistantAgent(
    name="Writer",
    llm_config={"config_list": config_list, "cache_seed": None},
    system_message="""Writer. Please write blogs in markdown format (with relevant titles) and put the content in pseudo ```md``` code block. You will write it for a task based on previous chat history. """,
)

code_executor = UserProxyAgent(
    name="Executor",
    system_message="Executor. Execute the code written by the engineer and report the result.",
    human_input_mode="ALWAYS",
    code_execution_config={
        "last_n_messages": 3,
        "executor": LocalCommandLineCodeExecutor(work_dir="paper"),
    },
)


def custom_speaker_selection_func(last_speaker: Agent, groupchat: GroupChat):
    """Define a customized speaker selection function.
    A recommended way is to define a transition for each speaker in the groupchat.

    Returns:
        Return an `Agent` class or a string from ['auto', 'manual', 'random', 'round_robin'] to select a default method to use.
    """
    messages = groupchat.messages

    if len(messages) <= 1:
        # first, let the engineer retrieve relevant data
        return planner

    if last_speaker is planner:
        # if the last message is from planner, let the engineer to write code
        return engineer
    elif last_speaker is user_proxy:
        if messages[-1]["content"].strip() != "":
            # If the last message is from user and is not empty, let the writer to continue
            return writer

    elif last_speaker is engineer:
        if "```python" in messages[-1]["content"]:
            # If the last message is a python code block, let the executor to speak
            return code_executor
        else:
            # Otherwise, let the engineer to continue
            return engineer

    elif last_speaker is code_executor:
        if "exitcode: 1" in messages[-1]["content"]:
            # If the last message indicates an error, let the engineer to improve the code
            return engineer
        else:
            # Otherwise, let the writer to speak
            return writer

    elif last_speaker is writer:
        # Always let the user to speak after the writer
        return user_proxy

    else:
        # default to auto speaker selection method
        return "auto"


groupchat = GroupChat(
    agents=[user_proxy, engineer, writer, code_executor, planner],
    messages=[],
    max_round=20,
    speaker_selection_method=custom_speaker_selection_func,
)
manager = GroupChatManager(groupchat=groupchat, llm_config={"config_list": config_list, "cache_seed": None})

with Cache.disk(cache_seed=41) as cache:
    groupchat_history_custom = user_proxy.initiate_chat(
        manager,
        message=task,
        cache=cache,
    )


Approach 3. Use AutoBuild
AutoBuild is an effective approach that generates a group of experts and use their conversation to solve a task. In AutoBuild, each expert handles a part of the task, therefore effectively and comprehensively solving it.

AUTOBUILD_SYSTEM_MESSAGE = """You are a manager of a group of advanced experts, your primary objective is to delegate the resolution of tasks to other experts through structured dialogue and derive conclusive insights from their conversation summarization.
When a task is assigned, it's crucial to assess its constraints and conditions for completion. If feasible, the task should be divided into smaller, logically consistent subtasks. Following this division, you have the option to address these subtasks by forming a team of agents using the "autobuild" tool.
Upon the completion of all tasks and verifications, you should conclude the operation and reply "TERMINATE".
"""

user_proxy = UserProxyAgent(
    name="user_proxy",
    human_input_mode="NEVER",
    code_execution_config=False,
)

autobuild_assistant = AssistantAgent(
    name="Autobuild Assistant",
    llm_config={"config_list": config_list, "cache_seed": None},
)


def autobuild_reply(recipient, messages, sender, config):
    last_msg = messages[-1]["content"]
    builder = agent_builder.AgentBuilder(
        config_file_or_env="/Users/ekzhu/autogen/OAI_CONFIG_LIST",
        builder_model="gpt-4-1106-preview",
        agent_model="gpt-4-1106-preview",
    )
    agent_list, agent_configs = builder.build(
        last_msg, default_llm_config={"config_list": config_list, "cache_seed": None}
    )
    # start nested chat
    nested_group_chat = GroupChat(
        agents=agent_list,
        messages=[],
    )
    manager = GroupChatManager(groupchat=nested_group_chat, llm_config={"config_list": config_list, "cache_seed": None})
    chat_res = agent_list[0].initiate_chat(
        manager, message=agent_configs.get("building_task", last_msg), summary_method="reflection_with_llm"
    )
    return True, chat_res.summary


autobuild_assistant.register_reply([Agent, None], autobuild_reply)

with Cache.disk(cache_seed=41) as cache:
    user_proxy.initiate_chat(autobuild_assistant, message=task, max_turns=1)


Approach 4: Customize a task scheduler
A more general approach is to customize a task scheduler agent. Given a task, the agent decomposes the task into sub-tasks and assign them to agents with different expertise.

# Setting up code executor.
os.makedirs("coding", exist_ok=True)
code_executor = LocalCommandLineCodeExecutor(work_dir="coding")


def run_meta_prompting(expert_name: str, expert_identity: str, task: str) -> str:
    """
    Run Meta-prompting to solve the task.
    The method is adapted from "Meta-Prompting: Enhancing Language Models with Task-Agnostic Scaffolding".
    Paper available at https://arxiv.org/abs/2401.12954
    """
    print("Running meta prompting...")
    print("Querying expert: ", expert_name)

    expert = AssistantAgent(
        name=expert_name,
        human_input_mode="NEVER",
        llm_config={"config_list": config_list, "cache_seed": None},
        system_message='You are an AI assistant that helps people find information. Please answer the following question. Once you have determined the final answer, please present it using the format below:\n\n>> FINAL ANSWER:\n"""\n[final answer]\n"""',
        max_consecutive_auto_reply=1,
    )

    user_proxy = UserProxyAgent(
        name="proxy",
        human_input_mode="NEVER",
        default_auto_reply="TERMINATE",
        code_execution_config={"executor": code_executor},
        max_consecutive_auto_reply=1,
    )
    task += "\nYou have access to python code interpreter. Suggest python code block starting with '```python' and the code will be automatically executed. You can use code to solve the task or for result verification. You should always use print statement to get the value of a variable."
    user_proxy.initiate_chat(expert, message=expert_identity + "\n" + task, silent=True)

    expert_reply = user_proxy.chat_messages[expert][1]["content"]
    proxy_reply = user_proxy.chat_messages[expert][2]["content"]

    if proxy_reply != "TERMINATE":
        code_result = proxy_reply[proxy_reply.find("Code output:") + len("Code output:") :].strip()
        expert_reply += f"\nThis is the output of the code blocks when executed:\n{code_result}"
    else:
        expert_reply.replace(
            "FINAL ANSWER:",
            f"{expert_name}'s final answer:\n",
        )

    return expert_reply


class MetaAgent(ConversableAgent):
    SYSTEM_MESSAGE = """You are Meta-Expert, an extremely clever expert with the unique ability to collaborate with multiple experts (such as Expert Problem Solver, Expert Mathematician, Expert Essayist, etc.) to tackle any task and solve any complex problems. Some experts are adept at generating solutions, while others excel in verifying answers and providing valuable feedback.
As Meta-Expert, your role is to oversee the communication between the experts, effectively using their skills to answer a given question while applying your own critical thinking and verification abilities.
To communicate with a expert, call function "meta_prompting" with the expert's name, identity information and the task that needs to be solved. The function will return a response from the expert.
Ensure that your instructions are clear and unambiguous, and include all necessary information within the triple quotes. You should assign personas to the experts (e.g., "You are a physicist specialized in...").
You can interact with only one expert at a time, and break complex problems into smaller, solvable tasks. Each interaction is treated as an isolated event, so include all relevant details in every call.
Refrain from repeating the very same questions to experts. Examine their responses carefully and seek clarification if required, keeping in mind they don't recall past interactions.
Upon the completion of all tasks and verifications, you should conclude the result and reply "TERMINATE".
"""
    TOOL = {
        "type": "function",
        "function": {
            "name": "meta_prompting",
            "description": "Solve a task by querying an expert. Provide the expert identity and the task that needs to be solved, and the function will return the response of the expert.",
            "parameters": {
                "type": "object",
                "properties": {
                    "task": {
                        "type": "string",
                        "description": "[REQUIRED] The task that needs to be solved by the expert.",
                    },
                    "expert_name": {
                        "type": "string",
                        "description": "[REQUIRED] Name of the expert. Should follow the format: Expert xxx.",
                    },
                    "expert_identity": {
                        "type": "string",
                        "description": "[REQUIRED] A high-quality description about the most capable and suitable expert to answer the instruction. In second person perspective. For example, You are a linguist, well-versed in the study of language and its structures. You are equipped with a good understanding of grammar rules and can differentiate between nouns, verbs, adjectives, adverbs, etc. You can quickly and accurately identify the parts of speech in a sentence and explain the role of each word in the sentence. Your expertise in language and grammar is highly valuable in analyzing and understanding the nuances of communication.",
                    },
                },
            },
        },
    }

    def __init__(
        self,
        name: str,
        system_message: Optional[str] = None,
        llm_config: Optional[Union[Dict, Literal[False]]] = None,
        is_termination_msg: Optional[Callable[[Dict], bool]] = None,
        max_consecutive_auto_reply: Optional[int] = None,
        human_input_mode: Literal["ALWAYS", "NEVER", "TERMINATE"] = "NEVER",
        code_execution_config: Optional[Union[Dict, Literal[False]]] = False,
        description: Optional[
            str
        ] = "A helpful AI assistant that can build a group of agents at a proper time to solve a task.",
        **kwargs,
    ):
        super().__init__(
            name=name,
            system_message=self.SYSTEM_MESSAGE,
            llm_config=llm_config,
            is_termination_msg=is_termination_msg,
            max_consecutive_auto_reply=max_consecutive_auto_reply,
            human_input_mode=human_input_mode,
            code_execution_config=code_execution_config,
            description=description,
            **kwargs,
        )
        self.update_tool_signature(self.TOOL, is_remove=False)


proxy = UserProxyAgent(
    name="proxy",
    human_input_mode="NEVER",
    code_execution_config=False,
    max_consecutive_auto_reply=1,
    default_auto_reply="Continue. If you think the task is solved, please reply me only with 'TERMINATE'.",
)
proxy.register_function(function_map={"meta_prompting": lambda **args: run_meta_prompting(**args)})

agent = MetaAgent(
    name="Meta-Expert",
    llm_config={"config_list": config_list, "cache_seed": None},
    human_input_mode="NEVER",
    max_consecutive_auto_reply=15,
)

with Cache.disk(cache_seed=41) as cache:
    proxy.initiate_chat(agent, message=task, cache=cache)




