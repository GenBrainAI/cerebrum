from abc import ABC, abstractmethod
from typing import Dict, Any
from pydantic import BaseModel
from ..persistence.in_memory_crud import InMemoryCrud

from .crud_interface import CrudInterface
from ..models.tasks_manager import TasksManager
from ..models.toolset import Tool, Toolset
from ..models.task import Task
from ..models.message import Message
from ..models.agent import CrewAIConfig
from ..controllers.curried_proxy import CurriedProxy
from ..models.specialized_state import (
    SpecializedState, 
    TaskGenerationState, 
    ToolManagementState, 
    AgentFrameworkState
)

class PersistenceModelBase(ABC):

     # New method to access collections more dynamically
    def collection(self, collection_name: str) -> CrudInterface:
        if hasattr(self, f'_{collection_name}'):
            return getattr(self, f'_{collection_name}')
        elif collection_name in self.collections:
            return self.collections[collection_name]
        else:
            # Create a general InMemoryCrud instance with BaseModel as a placeholder
            # and store it in the collections dictionary
            # NOTE: collections are NOT serializable !!!
            self.collections[collection_name] = InMemoryCrud(BaseModel)
            return self.collections[collection_name]

    @abstractmethod
    def to_json(self) -> str:
        pass

    @abstractmethod
    def from_json(self, json_str: str):
        pass

    @property
    @abstractmethod
    def tools(self) -> CrudInterface[Tool]:
        pass

    @property
    @abstractmethod
    def toolsets(self) -> CrudInterface[Toolset]:
        pass

    @property
    @abstractmethod
    def tasksmanagers(self) -> CrudInterface[TasksManager]:
        pass

    @property
    @abstractmethod
    def tasks(self) -> CrudInterface[Task]:
        pass

    @property
    @abstractmethod
    def messages(self) -> CrudInterface[Message]:
        pass

    @property
    @abstractmethod
    def crewai_config(self) -> CrudInterface[CrewAIConfig]:
        pass

    @property
    @abstractmethod
    def curried_proxies(self) -> CrudInterface[CurriedProxy]:
        pass

    def initialize_from_state(self, state: SpecializedState):
        """Initialize model from specialized state."""
        if isinstance(state, TaskGenerationState):
            self._initialize_tasks(state)
        elif isinstance(state, ToolManagementState):
            self._initialize_tools(state)
        elif isinstance(state, AgentFrameworkState):
            self._initialize_agents(state)

    def _initialize_tasks(self, state: TaskGenerationState):
        """Initialize tasks and managers from state."""
        for manager in state.tasksmanagers:
            self.tasksmanagers.create(manager)
        for task in state.tasks:
            self.tasks.create(task)

    def _initialize_tools(self, state: ToolManagementState):
        """Initialize tools from state."""
        for tool in state.tools:
            self.tools.create(tool)

    def _initialize_agents(self, state: AgentFrameworkState):
        """Initialize agents from state."""
        for agent in state.agents:
            self.agents.create(agent)
