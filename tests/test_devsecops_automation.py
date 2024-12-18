import pytest
from unittest.mock import Mock, AsyncMock, patch, create_autospec
from fastapi import HTTPException
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
from src.server.controllers.jira_controller import JiraController
from src.server.models.jira_config import JiraConfig
from src.server.models.task import Task
from src.server.models.agent import CreateCrewRequest, AgentModel, TaskModel, ToolModel, CrewAIConfig
from src.server.persistence.persistence_model_factory import PersistenceModelFactory
from src.server.controllers.task_runner import TaskRunner

class MockTaskOutput:
    def __init__(self, content: str):
        self.content = content
        
    def __str__(self) -> str:
        return self.content

class MockCrewOutput:
    def __init__(
        self,
        raw: str,
        json_dict: Optional[Dict[str, Any]] = None,
        pydantic_model: Optional[BaseModel] = None,
        tasks_output: Optional[List[MockTaskOutput]] = None,
        token_usage: Optional[Dict[str, int]] = None
    ):
        self.raw = raw
        self.json_dict = json_dict
        self.pydantic = pydantic_model
        self.tasks_output = tasks_output or []
        self.token_usage = token_usage or {}
    
    def __str__(self) -> str:
        if self.pydantic:
            return str(self.pydantic)
        elif self.json_dict:
            return str(self.json_dict)
        return self.raw

@pytest.fixture
def mock_task_runner():
    runner = AsyncMock(spec=TaskRunner)
    # Explicitly set up the run_task method to be an AsyncMock
    runner.run_task = AsyncMock()
    runner.mock_task = Mock(
        id="test-task-id",
        tasksmanager_id="test-tasksmanager-id",
        crewai_config_id="test-crew-id",
        curried_proxy_id=None
    )
    return runner

@pytest.fixture
def mock_jira_service():
    service = AsyncMock()
    service.update_ticket_status = AsyncMock()
    service.add_comment = AsyncMock()
    service.fetch_tickets = AsyncMock()
    return service

@pytest.fixture
def jira_config():
    return JiraConfig(
        project_key="DSO",
        jira_url="https://example.atlassian.net",
        jira_username="test",
        jira_api_token="test-token",
        task_id="test-task-id",
        schedule_interval=5
    )

@pytest.fixture
def mock_persistence_model(mock_task_runner):
    persistence = Mock()
    persistence.tasks = Mock()
    persistence.tasks.read = Mock(return_value=mock_task_runner.mock_task)
    return persistence

@pytest.fixture
def jira_controller(jira_config, mock_jira_service, mock_persistence_model):
    with patch('src.server.controllers.jira_controller.PersistenceModelFactory') as mock_factory:
        mock_factory._instance = mock_persistence_model
        mock_factory.persistence_model.return_value = mock_persistence_model
        return JiraController(jira_config, mock_jira_service)

@pytest.mark.asyncio
async def test_process_devsecops_ticket_successful(jira_controller, mock_task_runner):
    """Test successful processing of a DevSecOps ticket."""
    ticket = {
        'id': 'DSO-1',
        'key': 'DSO-1',
        'fields': {
            'summary': 'Add ingress call from payment-service to user-service',
            'description': 'Need to access user-service from payment-service',
            'labels': ['DevSecOps']
        }
    }

    # Set up the mock response for run_task
    mock_task_runner.run_task.return_value = {
        "response": "run_crew_task kicked off successfully"
    }

    # Patch TaskRunner to return our mock
    with patch('src.server.controllers.jira_controller.TaskRunner', return_value=mock_task_runner):
        # Process the ticket
        await jira_controller.process_devsecops_ticket(ticket)

        # Verify Jira status updates
        jira_controller.jira_service.update_ticket_status.assert_any_call('DSO-1', 'In Progress')
        jira_controller.jira_service.update_ticket_status.assert_any_call('DSO-1', 'In Review')

        # Verify TaskRunner was called correctly
        assert mock_task_runner.run_task.called
        call_args = mock_task_runner.run_task.call_args
        assert call_args is not None
        args, kwargs = call_args
        
        assert kwargs['tasksmanager_id'] == 'test-tasksmanager-id'
        assert kwargs['task_id'] == 'test-task-id'
        assert kwargs['running_extra_params'] == {
            'source_service': 'payment-service',
            'target_service': 'user-service',
            'communication_type': 'ingress',
            'ticket_id': 'DSO-1'
        }

@pytest.mark.asyncio
async def test_process_devsecops_ticket_with_error(jira_controller, mock_task_runner):
    """Test error handling in DevSecOps ticket processing."""
    ticket = {
        'id': 'DSO-1',
        'key': 'DSO-1',
        'fields': {
            'summary': 'Add ingress call from payment-service to user-service',
            'description': 'Need to access user-service from payment-service',
            'labels': ['DevSecOps']
        }
    }

    # Configure mock to return error response
    error_message = "Failed to create PR"
    mock_task_runner.run_task.return_value = {
        "response": f"run_crew_task failed with error: {error_message}"
    }

    with patch('src.server.controllers.jira_controller.TaskRunner', return_value=mock_task_runner):
        try:
            # Process the ticket (should raise exception)
            await jira_controller.process_devsecops_ticket(ticket)
            pytest.fail("Expected an exception but none was raised")
        except Exception as e:
            # Verify the exception is what we expect
            assert str(e) == f"run_crew_task failed with error: {error_message}"
            
            # Verify error handling
            jira_controller.jira_service.update_ticket_status.assert_any_call('DSO-1', 'In Progress')
            jira_controller.jira_service.update_ticket_status.assert_any_call('DSO-1', 'Failed')
            
            # Verify error comment was added
            jira_controller.jira_service.add_comment.assert_called_once_with(
                'DSO-1',
                f'Error processing ticket: run_crew_task failed with error: {error_message}'
            )

@pytest.mark.asyncio
async def test_extract_service_names(jira_controller):
    """Test the extraction of source and target service names from ticket content."""
    ticket = {
        'fields': {
            'summary': 'Add ingress call from payment-service to user-service',
            'description': 'Need to access user-service from payment-service for payment processing'
        }
    }
    
    source_service = jira_controller.extract_source_service(ticket)
    target_service = jira_controller.extract_target_service(ticket)
    
    assert source_service == 'payment-service'
    assert target_service == 'user-service'