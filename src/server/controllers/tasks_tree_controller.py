from typing import List, Dict, Callable, Optional
from abc import ABC, abstractmethod
from pydantic import BaseModel

class Task(BaseModel):
    name: str
    input_data: Optional[Dict] = None

    def run(self, input_data: Optional[Dict] = None) -> str:
        # Simulating a task execution that generates text
        return f"Task {self.name} output: {input_data}"

class TaskAggregator(ABC):
    @abstractmethod
    def aggregate(self, responses: List[str]) -> str:
        pass

class AllAggregator(TaskAggregator):
    def aggregate(self, responses: List[str]) -> str:
        return "\n".join(responses)

class CombineAggregator(TaskAggregator):
    def aggregate(self, responses: List[str]) -> str:
        return " ".join(responses)

class SummarizeAllAggregator(TaskAggregator):
    def aggregate(self, responses: List[str]) -> str:
        # Simulating summarization logic
        return f"Summary: {', '.join(responses)}"

class ChooseFunctionAggregator(TaskAggregator):
    def __init__(self, choose_function: Callable[[List[str]], str]):
        self.choose_function = choose_function

    def aggregate(self, responses: List[str]) -> str:
        return self.choose_function(responses)

class TaskNode:
    def __init__(self, task: Task, aggregator: TaskAggregator = AllAggregator()):
        self.task = task
        self.aggregator = aggregator
        self.children: List[TaskNode] = []

    def add_child(self, child: 'TaskNode'):
        self.children.append(child)

    def run(self, input_data: Optional[Dict] = None) -> str:
        responses = []
        for child in self.children:
            response = child.run(input_data)
            responses.append(response)

        aggregated_response = self.aggregator.aggregate(responses)
        return self.task.run({"input_data": aggregated_response})

class TasksManager:
    def __init__(self, root: TaskNode):
        self.root = root

    def run(self, input_data: Optional[Dict] = None) -> str:
        return self.root.run(input_data)

# Unit tests
def test_tasks_manager():
    # Create tasks
    task1 = Task(name="Task 1")
    task2 = Task(name="Task 2")
    task3 = Task(name="Task 3")
    task4 = Task(name="Task 4")

    # Create task nodes
    node1 = TaskNode(task1)
    node2 = TaskNode(task2, CombineAggregator())
    node3 = TaskNode(task3, SummarizeAllAggregator())
    node4 = TaskNode(task4, ChooseFunctionAggregator(lambda responses: responses[0]))

    # Build the task hierarchy
    node1.add_child(node2)
    node1.add_child(node3)
    node2.add_child(node4)

    # Create the tasks manager
    tasks_manager = TasksManager(node1)

    # Run the tasks
    result = tasks_manager.run()
    expected_result = "Task Task 1 output: {'input_data': 'Summary: Task Task 2 output: {'input_data': 'Task Task 4 output: None'}, Task Task 3 output: None'}"
    assert result == expected_result

    print("All tests passed!")

# Run the unit tests
test_tasks_manager()
