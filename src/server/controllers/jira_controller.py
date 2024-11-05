import re
import logging
import requests
from typing import Dict, Optional
from ..models.jira_config import JiraConfig
from ..tools.jira_service import JiraService
from ..controllers.task_runner import TaskRunner
from ..persistence.persistence_model_factory import PersistenceModelFactory

persistence_model = PersistenceModelFactory.persistence_model("inmemory")

class JiraController:
    def __init__(self, config: JiraConfig, jira_service: JiraService):
        self.config = config
        self.jira_service = jira_service
        self.persistence_model = PersistenceModelFactory.persistence_model()

    def update_config(self, new_config: JiraConfig, new_jira_service: JiraService):
        self.config = new_config
        self.jira_service = new_jira_service

    def fetch_new_tickets(self):
        return self.jira_service.fetch_tickets(self.config.project_key)

    def process_ticket(self, ticket):
        ticket_id = ticket['id']
        ticket_key = ticket['key']

        # Set ticket status to 'In Progress'
        self.jira_service.update_ticket_status(ticket_id, 'In Progress')

        # Send ticket to task endpoint
        response = requests.post(f'http://localhost:8000/task/{self.config.task_id}/run', json=ticket)

        if response.status_code == 200:
            # Set ticket status to 'Done' if processing is successful
            self.jira_service.update_ticket_status(ticket_id, 'Done')
        else:
            print(f"Failed to process ticket {ticket_key}. Status Code: {response.status_code}")
            
    async def process_devsecops_ticket(self, ticket: Dict):
        """Process a DevSecOps ticket using CrewAI automation."""
        if 'DevSecOps' not in ticket.get('fields', {}).get('labels', []):
            return
            
        try:
            # Update ticket status to In Progress
            await self.jira_service.update_ticket_status(ticket['id'], 'In Progress')
            
            # Extract source and target services
            source_service = self.extract_source_service(ticket)
            target_service = self.extract_target_service(ticket)
            
            if not source_service or not target_service:
                raise ValueError("Could not determine source and target services")
            
            # Get the task associated with this configuration
            task = self.persistence_model.tasks.read(self.config.task_id)
            if not task:
                raise ValueError(f"Task {self.config.task_id} not found")
            
            # Create task runner and prepare input
            task_runner = TaskRunner(self.persistence_model)
            task_input = {
                'source_service': source_service,
                'target_service': target_service,
                'communication_type': 'ingress',
                'ticket_id': ticket['key']
            }
            
            # Run the task
            result = await task_runner.run_task(
                tasksmanager_id=task.tasksmanager_id,
                task_id=task.id,
                running_extra_params=task_input
            )
            
            if not result or not isinstance(result, dict) or 'response' not in result:
                raise ValueError("Task execution did not return expected response")
                
            response = result['response']
            if 'failed' in response.lower():
                raise ValueError(response)
                
            # Update ticket with success
            await self.jira_service.update_ticket_status(ticket['id'], 'In Review')
            if response:
                await self.jira_service.add_comment(ticket['id'], response)
                
        except Exception as e:
            error_message = f"Error processing ticket: {str(e)}"
            logging.error(error_message, exc_info=True)
            await self.jira_service.add_comment(ticket['id'], error_message)
            await self.jira_service.update_ticket_status(ticket['id'], 'Failed')
            raise

    def extract_source_service(self, ticket: Dict) -> Optional[str]:
        """Extract source service from ticket content."""
        summary = ticket.get('fields', {}).get('summary', '').lower()
        description = ticket.get('fields', {}).get('description', '').lower()
        
        patterns = [
            r'from\s+(\w+)-service',
            r'(\w+)-service\s+needs?\s+to',
            r'(\w+)-service\s+(?:should|must|will|can)',
            r'access.*?from\s+(\w+)-service',
        ]
        
        for pattern in patterns:
            for text in [summary, description]:
                match = re.search(pattern, text)
                if match:
                    return f"{match.group(1)}-service"
        return None

    def extract_target_service(self, ticket: Dict) -> Optional[str]:
        """Extract target service from ticket content."""
        summary = ticket.get('fields', {}).get('summary', '').lower()
        description = ticket.get('fields', {}).get('description', '').lower()
        
        patterns = [
            r'to\s+(\w+)-service',
            r'access\s+(\w+)-service',
            r'call\s+(?:to\s+)?(\w+)-service',
            r'communicate\s+(?:with\s+)?(\w+)-service',
        ]
        
        for pattern in patterns:
            for text in [summary, description]:
                match = re.search(pattern, text)
                if match:
                    return f"{match.group(1)}-service"
        return None