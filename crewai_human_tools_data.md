# human in the loop with crewAI #258

[New issue](https://github.com/crewAIInc/crewAI/issues/new/choose)

Copy link

[New issue](https://github.com/crewAIInc/crewAI/issues/new/choose)

Copy link

Closed

Closed

[human in the loop with crewAI](https://github.com/crewAIInc/crewAI/issues/258#top)#258

Copy link

[![@ArmandoFranzone](https://avatars.githubusercontent.com/u/113166892?u=e6d45d25e2e5465a0d850e42e00a58215c05087e&v=4&size=80)](https://github.com/ArmandoFranzone)

## Description

[![@ArmandoFranzone](https://avatars.githubusercontent.com/u/113166892?u=e6d45d25e2e5465a0d850e42e00a58215c05087e&v=4&size=48)](https://github.com/ArmandoFranzone)

[ArmandoFranzone](https://github.com/ArmandoFranzone)

opened [on Feb 19, 2024](https://github.com/crewAIInc/crewAI/issues/258#issue-2142813392)

Issue body actions

Is there a way in Crew AI to structure an interview process where one agent asks questions to a human and another agent summarizes the conversation?

## Activity

[![andrewcbecker](https://avatars.githubusercontent.com/u/40001625?u=60c748f27a438d2e696118470cc0a9e65b552579&v=4&size=80)](https://github.com/andrewcbecker)

### andrewcbecker commented on Feb 19, 2024

[![@andrewcbecker](https://avatars.githubusercontent.com/u/40001625?u=60c748f27a438d2e696118470cc0a9e65b552579&v=4&size=48)](https://github.com/andrewcbecker)

[andrewcbecker](https://github.com/andrewcbecker)

[on Feb 19, 2024](https://github.com/crewAIInc/crewAI/issues/258#issuecomment-1952896569) · edited by [andrewcbecker](https://github.com/andrewcbecker)

Edits

I'm sure there's a few ways to go about it. The first one that comes to mind is using human input and structuring the agent tasks to initiate the human tool at the desired time. Once the first agent is complete it can delegate a summarization task to another agent, or you can instruct the first agent to do the summary.

Configuring Agents/Tasks: [https://docs.crewai.com/how-to/Customizing-Agents/](https://docs.crewai.com/how-to/Customizing-Agents/)  
Assigning tools to agents: [https://docs.crewai.com/how-to/Customizing-Agents/#example-assigning-tools-to-an-agent](https://docs.crewai.com/how-to/Customizing-Agents/#example-assigning-tools-to-an-agent)  
Human As a Tool (via LangChain): [https://docs.crewai.com/how-to/Human-Input-on-Execution/](https://docs.crewai.com/how-to/Human-Input-on-Execution/)

Edit: Removed duplicate info.

[![ArmandoFranzone](https://avatars.githubusercontent.com/u/113166892?u=e6d45d25e2e5465a0d850e42e00a58215c05087e&v=4&size=80)](https://github.com/ArmandoFranzone)

### ArmandoFranzone commented on Feb 20, 2024

[![@ArmandoFranzone](https://avatars.githubusercontent.com/u/113166892?u=e6d45d25e2e5465a0d850e42e00a58215c05087e&v=4&size=48)](https://github.com/ArmandoFranzone)

[ArmandoFranzone](https://github.com/ArmandoFranzone)

[on Feb 20, 2024](https://github.com/crewAIInc/crewAI/issues/258#issuecomment-1954313876)

Author

Thanks for your suggestion. Here is a first implementation. Could you help me to improve the interaction between the interviewer agent and the human?

```python
import os
from langchain_openai import ChatOpenAI
from langchain.agents import load_tools
from crewai import Agent, Task, Crew
from crewai.tasks.task_output import TaskOutput

# Set Model
llm = ChatOpenAI(model="gpt-3.5-turbo", temperature=0)

def callback_function(output: TaskOutput):
    # Do something after the task is completed
    print(f"""Task completed! - Items List: {output.result}""")

# Loading Human Tools
human_tools = load_tools(["human"])


# Agents definition
interviewer = Agent(
  role='Interviwer',
  goal='making questions about business to human',
  backstory="""You are an interviewer of business man.""",
  llm=llm,
  verbose=False,
  allow_delegation=False,
  tools=human_tools
)

writer = Agent(
  role='Writer',
  goal=' Summarizing interview',
  backstory="""You are a writer and your expertise lies in summarizing interviews.""",
  llm=llm,
  verbose=False,
  allow_delegation=False,
)


# Tasks definition
interviewer_task = Task(
  description=f"""
Your task is to interview successful entrepreneurs. 
Ask 3 business questions. Ask one question at a time, and at the end of the questions, 
conclude by writing only "finish".
""",
  max_inter=3,
  agent=interviewer,
  callback=callback_function,
  tools=human_tools
)

writer_task = Task(
  description=f"""
Summarize the content of the provided interview
""",
  max_inter=3,
  agent=writer,
  callback=callback_function,
  context=[interviewer_task]
)

items_crew = Crew(
  agents=[interviewer,writer],
  tasks=[interviewer_task, writer_task],
)

# Get your crew to work!
response = items_crew.kickoff()

print("#########")
print(response)
print("#########")
```

[![](https://avatars.githubusercontent.com/u/10519862?s=64&u=9ced463a290afb0b74282d37dddd6e80ff616bf4&v=4)francisjervis](https://github.com/francisjervis)

mentioned this [on Apr 12, 2024](https://github.com/crewAIInc/crewAI/issues/258#event-1377653335)

- [Human Input in Agent Execution documentation: unintelligible and broken example #464](https://github.com/crewAIInc/crewAI/issues/464)
    

[![francisjervis](https://avatars.githubusercontent.com/u/10519862?u=9ced463a290afb0b74282d37dddd6e80ff616bf4&v=4&size=80)](https://github.com/francisjervis)

### francisjervis commented on Apr 13, 2024

[![@francisjervis](https://avatars.githubusercontent.com/u/10519862?u=9ced463a290afb0b74282d37dddd6e80ff616bf4&v=4&size=48)](https://github.com/francisjervis)

[francisjervis](https://github.com/francisjervis)

[on Apr 13, 2024](https://github.com/crewAIInc/crewAI/issues/258#issuecomment-2052725492) · edited by [francisjervis](https://github.com/francisjervis)

Edits

Here is a working version.

Changes:  
1: Refactor your interviewer agent prompt to explicitly tell the LLM to pass the question as the action input.  
2: Add memory to the crew, so that it can keep track of questions/answers.  
3: Remove redundant callback function.  
4: Define the crew process as sequential.  
5: Refactor your interviewer agent prompt to output a list of Q-A pairs followed by "finish" so its output is correctly passed as context to the writer agent.  
6: More aggressive logging.

```
from langchain_openai import ChatOpenAI
from langchain.agents import load_tools
from crewai import Agent, Task, Crew, Process
from crewai.tasks.task_output import TaskOutput

# Set Model
llm = ChatOpenAI(model="gpt-3.5-turbo", temperature=0)

# Loading Human Tools
human_tools = load_tools(["human"])

# Agents definition
interviewer = Agent(
  role='Interviwer',
  goal='making questions about business to human',
  backstory="""You are an interviewer of business man.""",
  llm=llm,
  verbose=True,
  allow_delegation=False,
  tools=human_tools
)

writer = Agent(
  role='Writer',
  goal=' Summarizing interview',
  backstory="""You are a writer and your expertise lies in summarizing interviews.""",
  llm=llm,
  verbose=True,
  allow_delegation=False,
)

# Tasks definition
interviewer_task = Task(
  description=f"""
Your task is to interview successful entrepreneurs. 
Ask three business questions. Ask one question at a time.
When three questions have been answered by the interviewee, conclude by responding with a list of questions and answers, followed by "finish" on a new line.
To ask a question, use the "human" tool and provide the question to be asked as the "Action Input".
""",
  max_inter=3,
  expected_output="a coherent question",
  agent=interviewer,
  tools=human_tools
)

writer_task = Task(
  description=f"""
Summarize the content of the provided interview
""",
  max_inter=3,
  agent=writer,
  expected_output="a coherent summary",
  context=[interviewer_task]
)

items_crew = Crew(
  agents=[interviewer,writer],
  tasks=[interviewer_task, writer_task],
  process=Process.sequential,
  memory=True,
  verbose=True,
  full_output=True,
)

# Get your crew to work!
response = items_crew.kickoff()

print("#########")
print(response)
print("#########")
```

Sample output:

```
/Users/francis/PycharmProjects/crewaitest1/.venv/bin/python /Users/francis/Library/Application Support/JetBrains/PyCharmCE2023.3/scratches/scratch.py 
 [DEBUG]: == Working Agent: Interviwer
 [INFO]: == Starting Task: 
Your task is to interview successful entrepreneurs. 
Ask three business questions. Ask one question at a time.
When three questions have been answered by the interviewee, conclude by responding with a list of questions and answers, followed by "finish" on a new line.
To ask a question, use the "human" tool and provide the question to be asked as the "Action Input".



> Entering new CrewAgentExecutor chain...
I need to ask three business questions to successful entrepreneurs.

Action: human
Action Input: {"question": "What is the most important lesson you have learned in your entrepreneurial journey?"}

What is the most important lesson you have learned in your entrepreneurial journey?
get lots of cats
 

get lots of cats

Thought: 
I need to ask another business question to successful entrepreneurs.

Action: human
Action Input: {"question": "What advice would you give to aspiring entrepreneurs who are just starting out?"}

What advice would you give to aspiring entrepreneurs who are just starting out?
get a cat
 

get a cat

Thought: 
I need to ask one more business question to successful entrepreneurs.

Action: human
Action Input: {"question": "How do you handle failure and setbacks in your business ventures?"}

How do you handle failure and setbacks in your business ventures?
cats
 

cats

Thought: 
I now know the final answer

Final Answer: 
1. What is the most important lesson you have learned in your entrepreneurial journey? - The most important lesson is to get lots of cats.
2. What advice would you give to aspiring entrepreneurs who are just starting out? - The advice is to get a cat.
3. How do you handle failure and setbacks in your business ventures? - The answer is cats.

finish

> Finished chain.
 [DEBUG]: == [Interviwer] Task output: 1. What is the most important lesson you have learned in your entrepreneurial journey? - The most important lesson is to get lots of cats.
2. What advice would you give to aspiring entrepreneurs who are just starting out? - The advice is to get a cat.
3. How do you handle failure and setbacks in your business ventures? - The answer is cats.

finish


 [DEBUG]: == Working Agent: Writer
 [INFO]: == Starting Task: 
Summarize the content of the provided interview



> Entering new CrewAgentExecutor chain...
I now can give a great answer

Current Task: 
Summarize the content of the provided interview

Final Answer: 
The most important lesson learned in the entrepreneurial journey is to get lots of cats. The advice given to aspiring entrepreneurs who are just starting out is to get a cat. When it comes to handling failure and setbacks in business ventures, the answer is cats.

> Finished chain.
 [DEBUG]: == [Writer] Task output: The most important lesson learned in the entrepreneurial journey is to get lots of cats. The advice given to aspiring entrepreneurs who are just starting out is to get a cat. When it comes to handling failure and setbacks in business ventures, the answer is cats.


#########
{'final_output': 'The most important lesson learned in the entrepreneurial journey is to get lots of cats. The advice given to aspiring entrepreneurs who are just starting out is to get a cat. When it comes to handling failure and setbacks in business ventures, the answer is cats.', 'tasks_outputs': [TaskOutput(description='\nYour task is to interview successful entrepreneurs. \nAsk three business questions. Ask one question at a time.\nWhen three questions have been answered by the interviewee, conclude by responding with a list of questions and answers, followed by "finish" on a new line.\nTo ask a question, use the "human" tool and provide the question to be asked as the "Action Input".\n', summary='\nYour task is to interview successful entrepreneurs. \nAsk three business...', exported_output='1. What is the most important lesson you have learned in your entrepreneurial journey? - The most important lesson is to get lots of cats.\n2. What advice would you give to aspiring entrepreneurs who are just starting out? - The advice is to get a cat.\n3. How do you handle failure and setbacks in your business ventures? - The answer is cats.\n\nfinish', raw_output='1. What is the most important lesson you have learned in your entrepreneurial journey? - The most important lesson is to get lots of cats.\n2. What advice would you give to aspiring entrepreneurs who are just starting out? - The advice is to get a cat.\n3. How do you handle failure and setbacks in your business ventures? - The answer is cats.\n\nfinish'), TaskOutput(description='\nSummarize the content of the provided interview\n', summary='\nSummarize the content of the provided interview\n...', exported_output='The most important lesson learned in the entrepreneurial journey is to get lots of cats. The advice given to aspiring entrepreneurs who are just starting out is to get a cat. When it comes to handling failure and setbacks in business ventures, the answer is cats.', raw_output='The most important lesson learned in the entrepreneurial journey is to get lots of cats. The advice given to aspiring entrepreneurs who are just starting out is to get a cat. When it comes to handling failure and setbacks in business ventures, the answer is cats.')]}
#########

Process finished with exit code 0

```

👍4

[![francisjervis](https://avatars.githubusercontent.com/u/10519862?u=9ced463a290afb0b74282d37dddd6e80ff616bf4&v=4&size=80)](https://github.com/francisjervis)

### francisjervis commented on Apr 13, 2024

[![@francisjervis](https://avatars.githubusercontent.com/u/10519862?u=9ced463a290afb0b74282d37dddd6e80ff616bf4&v=4&size=48)](https://github.com/francisjervis)

[francisjervis](https://github.com/francisjervis)

[on Apr 13, 2024](https://github.com/crewAIInc/crewAI/issues/258#issuecomment-2052727845) · edited by [francisjervis](https://github.com/francisjervis)

Edits

Do you want to add this to the docs as an example of how to use the Langchain human input tool with a crew [@joaomdmoura](https://github.com/joaomdmoura)?

👍5

[![beeapu](https://avatars.githubusercontent.com/u/172244139?v=4&size=80)](https://github.com/beeapu)

### beeapu commented on Jun 28, 2024

[![@beeapu](https://avatars.githubusercontent.com/u/172244139?v=4&size=48)](https://github.com/beeapu)

[beeapu](https://github.com/beeapu)

[on Jun 28, 2024](https://github.com/crewAIInc/crewAI/issues/258#issuecomment-2196693786) · edited by [beeapu](https://github.com/beeapu)

Edits

Suppose i want to take the input and on base of that input i want my crewai agent to ether retune something or take input about something. How should I do this? should i create a manager agent which delicate task on base of query?  
say ether i want to list all the appointment or book appointment and for that input name and date. Can i do this with crewai itself?

[![](https://avatars.githubusercontent.com/u/113166892?s=64&u=e6d45d25e2e5465a0d850e42e00a58215c05087e&v=4)ArmandoFranzone](https://github.com/ArmandoFranzone)

closed this as [completed](https://github.com/crewAIInc/crewAI/issues?q=is%3Aissue%20state%3Aclosed%20archived%3Afalse%20reason%3Acompleted)[on Jun 30, 2024](https://github.com/crewAIInc/crewAI/issues/258#event-13340786005)

[![](https://avatars.githubusercontent.com/u/7207877?s=64&u=15d8ab60744a056753bfdc60c7d0b0143c295d8c&v=4)tituslhy](https://github.com/tituslhy)

mentioned this [on Jul 12, 2024](https://github.com/crewAIInc/crewAI/issues/258#event-1406320801)

- [\[Feature Request\] Adding a "Ask Human" Agent class #921](https://github.com/crewAIInc/crewAI/issues/921)
    

[![jakin6](https://avatars.githubusercontent.com/u/70150840?v=4&size=80)](https://github.com/jakin6)

### jakin6 commented on Nov 7, 2024

[![@jakin6](https://avatars.githubusercontent.com/u/70150840?v=4&size=48)](https://github.com/jakin6)

[jakin6](https://github.com/jakin6)

[on Nov 7, 2024](https://github.com/crewAIInc/crewAI/issues/258#issuecomment-2462071956)

please how u can make the human in loop over api, when it asks send to your ui and respond back

[![](https://avatars.githubusercontent.com/u/17240466?s=64&u=f5445d01f1927c9dfe2d747e58bb80fc3f8a3bf6&v=4)olokshyn](https://github.com/olokshyn)

mentioned this [on Feb 7, 2025](https://github.com/crewAIInc/crewAI/issues/258#event-2022359574)

- [\[QUESTION\] How to design asynchronous human-in-the-loop Crews running on the backend? #2051](https://github.com/crewAIInc/crewAI/issues/2051)
    

[](https://github.com/moshebeeri)