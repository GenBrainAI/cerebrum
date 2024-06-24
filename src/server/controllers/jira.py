from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel
import requests
from requests.auth import HTTPBasicAuth
import json
import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from typing import List, Optional

app = FastAPI(
    title="Jira Ticket Fetcher API",
    description="API for configuring and fetching Jira tickets",
    version="1.0.0",
    openapi_version="3.1.0"
)

scheduler = BackgroundScheduler()
scheduler.start()

# Persistence layer (mock implementation)
class JiraConfig(BaseModel):
    project_key: str
    tag: str
    team: str
    jira_url: str
    jira_username: str
    jira_api_token: str
    task_id: str
    schedule_interval: int  # in minutes


class JiraTicketHandler:
    def __init__(self, config: JiraConfig):
        self.config = config

    def fetch_new_tickets(self):
        jql_query = f'project = {self.config.project_key} AND labels = {self.config.tag} ORDER BY created DESC'

        headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        }

        payload = {
            'jql': jql_query,
            'maxResults': 50,
            'fields': ['summary', 'status', 'assignee', 'created', 'updated']
        }

        response = requests.post(
            f'{self.config.jira_url}/rest/api/2/search',
            headers=headers,
            auth=HTTPBasicAuth(self.config.jira_username, self.config.jira_api_token),
            data=json.dumps(payload)
        )

        if response.status_code == 200:
            issues = response.json().get('issues', [])
            for issue in issues:
                self.process_ticket(issue)
        else:
            print(f"Failed to fetch issues. Status Code: {response.status_code}")
            print(f"Response: {response.text}")

    def process_ticket(self, ticket):
        ticket_id = ticket['id']
        ticket_key = ticket['key']

        # Set ticket status to 'In Progress'
        self.update_ticket_status(ticket_id, 'In Progress')

        # Send ticket to task endpoint
        response = requests.post(f'http://localhost:8000/task/{self.config.task_id}/run', json=ticket)

        if response.status_code == 200:
            # Set ticket status to 'Done' if processing is successful
            self.update_ticket_status(ticket_id, 'Done')
        else:
            print(f"Failed to process ticket {ticket_key}. Status Code: {response.status_code}")

    def update_ticket_status(self, ticket_id, status):
        url = f'{self.config.jira_url}/rest/api/2/issue/{ticket_id}/transitions'
        headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        }

        # Fetch available transitions
        transitions_response = requests.get(url, headers=headers, auth=HTTPBasicAuth(self.config.jira_username, self.config.jira_api_token))
        if transitions_response.status_code == 200:
            transitions = transitions_response.json()['transitions']
            for transition in transitions:
                if transition['to']['name'].lower() == status.lower():
                    transition_id = transition['id']
                    break
            else:
                print(f"No transition found for status '{status}'")
                return

            # Execute the transition
            payload = {
                'transition': {
                    'id': transition_id
                }
            }
            response = requests.post(url, headers=headers, auth=HTTPBasicAuth(self.config.jira_username, self.config.jira_api_token), data=json.dumps(payload))
            if response.status_code == 204:
                print(f"Ticket {ticket_id} status updated to {status}")
            else:
                print(f"Failed to update ticket {ticket_id} status to {status}. Status Code: {response.status_code}")
                print(f"Response: {response.text}")
        else:
            print(f"Failed to fetch transitions for ticket {ticket_id}. Status Code: {transitions_response.status_code}")
            print(f"Response: {transitions_response.text}")

# FastAPI endpoints
@app.post("/jira/configure", tags=["Configuration"], summary="Configure Jira Settings")
def configure_jira(config: JiraConfig):
    handler = JiraTicketHandler(config=config)
    handler_id = persistence_model.jira_ticket_handler.create(handler)
    scheduler.add_job(handler.fetch_new_tickets, 'interval', minutes=config.schedule_interval, id=handler_id)
    return {"message": "Jira configuration created successfully", "handler_id": handler_id}

@app.put("/jira/configure/{handler_id}", tags=["Configuration"], summary="Update Jira Settings")
def update_jira_config(handler_id: str, config: JiraConfig):
    handler = persistence_model.jira_ticket_handler.read(handler_id)
    if not handler:
        raise HTTPException(status_code=404, detail="Jira handler not found")
    handler.config = config
    persistence_model.jira_ticket_handler.update(handler_id, handler)
    scheduler.remove_job(handler_id)
    scheduler.add_job(handler.fetch_new_tickets, 'interval', minutes=config.schedule_interval, id=handler_id)
    return {"message": "Jira configuration updated successfully"}

@app.delete("/jira/configure/{handler_id}", tags=["Configuration"], summary="Delete Jira Configuration")
def delete_jira_config(handler_id: str):
    handler = persistence_model.jira_ticket_handler.read(handler_id)
    if not handler:
        raise HTTPException(status_code=404, detail="Jira handler not found")
    persistence_model.jira_ticket_handler.delete(handler_id)
    scheduler.remove_job(handler_id)
    return {"message": "Jira configuration deleted successfully"}

@app.get("/jira/configurations", tags=["Configuration"], summary="Get All Jira Configurations")
def get_jira_configurations():
    return persistence_model.jira_ticket_handler.read_all()

# if __name__ == "__main__":
#     # Load all saved Jira configurations and start their schedulers
    
#     import uvicorn
#     uvicorn.run(app, host="0.0.0.0", port=8000)