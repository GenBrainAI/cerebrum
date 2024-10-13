import pytest
from unittest.mock import patch, Mock, call
from src.server.controllers.jira_controller import JiraController
from src.server.models.jira_config import JiraConfig
from src.server.tools.jira_service import JiraService

@pytest.fixture
def jira_config():
    return JiraConfig(
        project_key="TEST",
        jira_url="https://example.atlassian.net",
        jira_username="username",
        jira_api_token="api_token",
        task_id="task-123"
    )

@pytest.fixture
def jira_service():
    return Mock(spec=JiraService)

@pytest.fixture
def jira_controller(jira_config, jira_service):
    return JiraController(jira_config, jira_service)

def test_fetch_new_tickets(jira_controller, jira_service):
    jira_service.fetch_tickets.return_value = [{'id': '1', 'key': 'TEST-1'}]
    tickets = jira_controller.fetch_new_tickets()
    assert len(tickets) == 1
    assert tickets[0]['id'] == '1'
    assert tickets[0]['key'] == 'TEST-1'
    jira_service.fetch_tickets.assert_called_once_with(jira_controller.config.project_key)

def test_process_ticket(jira_controller, jira_service):
    with patch('requests.post') as mock_post:
        mock_post.return_value = Mock(status_code=200)
        ticket = {'id': '1', 'key': 'TEST-1'}
        jira_controller.process_ticket(ticket)

        # Check that update_ticket_status was called twice, first with 'In Progress', then with 'Done'
        assert jira_service.update_ticket_status.call_count == 2
        jira_service.update_ticket_status.assert_has_calls([
            call('1', 'In Progress'),
            call('1', 'Done')
        ])
        mock_post.assert_called_once()


def test_process_ticket_failure(jira_controller, jira_service):
    with patch('requests.post') as mock_post:
        mock_post.return_value = Mock(status_code=500)
        ticket = {'id': '1', 'key': 'TEST-1'}
        jira_controller.process_ticket(ticket)

        # Check that update_ticket_status was called only once with 'In Progress'
        jira_service.update_ticket_status.assert_called_once_with('1', 'In Progress')
        mock_post.assert_called_once()

def test_update_config(jira_controller, jira_config, jira_service):
    new_config = JiraConfig(
        project_key="NEW",
        jira_url="https://new.atlassian.net",
        jira_username="new_username",
        jira_api_token="new_api_token",
        task_id="new-task-123"
    )
    new_service = Mock(spec=JiraService)

    jira_controller.update_config(new_config, new_service)

    assert jira_controller.config == new_config
    assert jira_controller.jira_service == new_service