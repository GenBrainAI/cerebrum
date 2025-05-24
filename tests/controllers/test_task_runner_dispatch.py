import asyncio
import unittest
from unittest.mock import patch, AsyncMock, MagicMock
import uuid

from src.server.models.task import Task
from src.server.models.tasks_manager import TasksManager
from src.server.models.crewai_config import CrewAIConfig # For mocking return
from src.server.controllers.task_runner import TaskRunner
from src.server.persistence.persistence_model_factory import PersistenceModelFactory

class TestTaskRunnerDispatch(unittest.IsolatedAsyncioTestCase):

    async def asyncSetUp(self):
        self.persistence_model_factory = PersistenceModelFactory()
        self.persistence_model = self.persistence_model_factory.get_model(use_in_memory=True)
        
        self.task_runner = TaskRunner(persistence_model=self.persistence_model)
        # Mock essential methods not under test to avoid side-effects
        self.task_runner._initialize_observability = MagicMock()
        # Mock sequence checking to isolate run_task logic
        self.task_runner._check_if_task_starts_sequence = MagicMock(return_value=None)
        
        # Ensure plugin manager is initialized if task_runner.initialize() is called
        # or mock relevant parts if initialize() is complex/has external dependencies
        # For dispatch logic, full initialization might not be strictly needed if internal calls are mocked.
        # await self.task_runner.initialize() # If this is light enough

        self.tasks_manager_id = str(uuid.uuid4())
        tasks_manager = TasksManager(
            id=self.tasks_manager_id,
            name="TestManager",
            model="gpt-4o-mini"
        )
        self.persistence_model.tasksmanagers.create(tasks_manager)

    @patch('src.server.controllers.task_runner.TaskRunner._run_crewai_task', new_callable=AsyncMock)
    @patch('src.server.controllers.task_runner.TaskRunner._run_standard_task', new_callable=AsyncMock)
    async def test_scenario1_simple_task_no_crewai(self, mock_run_standard_task, mock_run_crewai_task):
        """Test dispatch to _run_standard_task for a simple task."""
        mock_run_standard_task.return_value = {"status": "completed", "response": "Standard task done"}

        task_id = str(uuid.uuid4())
        simple_task = Task(
            id=task_id,
            name="SimpleTask",
            tasksmanager_id=self.tasks_manager_id,
            crewai_config_id=None,
            framework=None 
        )
        self.persistence_model.tasks.create(simple_task)
        
        await self.task_runner.run_task(self.tasks_manager_id, task_id)

        mock_run_standard_task.assert_called_once()
        mock_run_crewai_task.assert_not_called()
        # Verify that it's called with the correct task object
        called_task_arg = mock_run_standard_task.call_args[0][0]
        self.assertEqual(called_task_arg.id, task_id)

    @patch('src.server.controllers.task_runner.TaskRunner._run_crewai_task', new_callable=AsyncMock)
    @patch('src.server.controllers.task_runner.TaskRunner._run_standard_task', new_callable=AsyncMock)
    async def test_scenario1_simple_task_framework_standard(self, mock_run_standard_task, mock_run_crewai_task):
        """Test dispatch to _run_standard_task for task.framework='standard'."""
        mock_run_standard_task.return_value = {"status": "completed", "response": "Standard task framework done"}

        task_id = str(uuid.uuid4())
        standard_framework_task = Task(
            id=task_id,
            name="StandardFrameworkTask",
            tasksmanager_id=self.tasks_manager_id,
            crewai_config_id=None,
            framework="standard" # Explicitly standard
        )
        self.persistence_model.tasks.create(standard_framework_task)
        
        await self.task_runner.run_task(self.tasks_manager_id, task_id)

        mock_run_standard_task.assert_called_once()
        mock_run_crewai_task.assert_not_called()
        called_task_arg = mock_run_standard_task.call_args[0][0]
        self.assertEqual(called_task_arg.id, task_id)

    @patch('src.server.controllers.task_runner.TaskRunner._run_standard_task', new_callable=AsyncMock)
    @patch('src.server.controllers.task_runner.TaskRunner._run_crewai_task', new_callable=AsyncMock)
    async def test_scenario2_crewai_task_via_config_id(self, mock_run_crewai_task, mock_run_standard_task):
        """Test dispatch to _run_crewai_task when crewai_config_id is set."""
        mock_run_crewai_task.return_value = {"status": "completed", "response": "CrewAI task done (config_id)"}
        
        # Mock for persistence_model.crewai_config.read()
        # This mock is inside TaskRunner, so we patch it there.
        # Or, if persistence_model is passed, mock on the instance.
        self.task_runner.persistence_model.crewai_config.read = MagicMock(
            return_value=CrewAIConfig(id="dummy_crew_config_id", name="DummyConfig", create_crew={})
        )

        task_id = str(uuid.uuid4())
        crewai_task_by_id = Task(
            id=task_id,
            name="CrewAIByIdTask",
            tasksmanager_id=self.tasks_manager_id,
            crewai_config_id="dummy_crew_config_id", # Valid ID
            framework=None 
        )
        self.persistence_model.tasks.create(crewai_task_by_id)
        
        await self.task_runner.run_task(self.tasks_manager_id, task_id)

        mock_run_crewai_task.assert_called_once()
        mock_run_standard_task.assert_not_called()
        # Verify that it's called with the correct task object
        called_task_arg = mock_run_crewai_task.call_args[0][0]
        self.assertEqual(called_task_arg.id, task_id)
        self.task_runner.persistence_model.crewai_config.read.assert_called_with("dummy_crew_config_id")


    @patch('src.server.controllers.task_runner.TaskRunner._run_standard_task', new_callable=AsyncMock)
    @patch('src.server.controllers.task_runner.TaskRunner._run_crewai_task', new_callable=AsyncMock)
    async def test_scenario3_crewai_task_via_framework_crewai(self, mock_run_crewai_task, mock_run_standard_task):
        """Test dispatch to _run_crewai_task when framework is 'crewai'."""
        mock_run_crewai_task.return_value = {"status": "completed", "response": "CrewAI task done (framework)"}

        # _run_crewai_task might try to read a crewai_config even if id is None.
        # So, ensure the mock can handle that or is configured appropriately.
        self.task_runner.persistence_model.crewai_config.read = MagicMock(
            return_value=None # Or a default CrewAIConfig if _run_crewai_task expects one
        )
        # If _run_crewai_task requires a config object even if task.crewai_config_id is None
        # (e.g. for default settings), then return a mock CrewAIConfig:
        # self.task_runner.persistence_model.crewai_config.read = MagicMock(
        #     return_value=CrewAIConfig(id="default_cfg", name="DefaultConfig", create_crew={})
        # )


        task_id = str(uuid.uuid4())
        crewai_task_by_framework = Task(
            id=task_id,
            name="CrewAIByFrameworkTask",
            tasksmanager_id=self.tasks_manager_id,
            crewai_config_id=None, # Explicitly None
            framework="crewai"      # Explicitly "crewai"
        )
        self.persistence_model.tasks.create(crewai_task_by_framework)
        
        await self.task_runner.run_task(self.tasks_manager_id, task_id)

        mock_run_crewai_task.assert_called_once()
        mock_run_standard_task.assert_not_called()
        called_task_arg = mock_run_crewai_task.call_args[0][0]
        self.assertEqual(called_task_arg.id, task_id)
        # Check if read was called, e.g. with None if that's the case.
        # The exact call depends on _run_crewai_task's internal logic when task.crewai_config_id is None.
        # For this dispatch test, confirming _run_crewai_task was called is primary.
        # self.task_runner.persistence_model.crewai_config.read.assert_called_with(None)


    @patch('src.server.controllers.task_runner.TaskRunner._run_standard_task', new_callable=AsyncMock)
    @patch('src.server.controllers.task_runner.TaskRunner._run_crewai_task', new_callable=AsyncMock)
    @patch('src.server.controllers.task_runner.TaskRunner._run_tree_flow_task', new_callable=AsyncMock) # Added tree_flow mock
    async def test_scenario_tree_flow_task(self, mock_run_tree_flow_task, mock_run_crewai_task, mock_run_standard_task):
        """Test dispatch to _run_tree_flow_task when tree_flow_id is set."""
        mock_run_tree_flow_task.return_value = {"status": "completed", "response": "Tree flow task done"}
        
        # Mock persistence_model.task_tree_flows.read for _run_tree_flow_task
        # This mock is on the persistence_model instance used by the task_runner.
        self.task_runner.persistence_model.task_tree_flows.read = MagicMock(
            return_value=MagicMock() # Return a mock tree flow object
        )

        task_id = str(uuid.uuid4())
        tree_flow_task = Task(
            id=task_id,
            name="TreeFlowTask",
            tasksmanager_id=self.tasks_manager_id,
            tree_flow_id="dummy_tree_flow_id" # Valid tree_flow_id
        )
        self.persistence_model.tasks.create(tree_flow_task)
        
        await self.task_runner.run_task(self.tasks_manager_id, task_id)

        mock_run_tree_flow_task.assert_called_once()
        mock_run_crewai_task.assert_not_called()
        mock_run_standard_task.assert_not_called()
        
        called_task_arg = mock_run_tree_flow_task.call_args[0][0]
        self.assertEqual(called_task_arg.id, task_id)
        # self.task_runner.persistence_model.task_tree_flows.read.assert_called_with("dummy_tree_flow_id")


if __name__ == '__main__':
    unittest.main()
