from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import requests
from requests.auth import HTTPBasicAuth
import json
import datetime
import os
from apscheduler.schedulers.background import BackgroundScheduler

app = FastAPI(
    title="Jira Ticket Fetcher API",
    description="API for configuring and fetching Jira tickets",
    version="1.0.0",
    openapi_version="3.1.0"
)

scheduler = BackgroundScheduler()

# Jira configuration variables
JIRA_URL = 'https://your-domain.atlassian.net'
JIRA_USERNAME = 'user@example.com'
JIRA_API_TOKEN = 'your-generated-api-token'

# File to store the last fetch time
LAST_FETCH_FILE = 'last_fetch_time.txt'

class JiraConfig(BaseModel):
    project_key: str
    tag: str
    team: str

class SchedulerConfig(BaseModel):
    last_fetch_time: datetime.datetime

class JIRATaskFetcher:
    def __init__(self, project_key, tag, team):
        self.project_key = project_key
        self.tag = tag
        self.team = team

jira_fetcher = None

def get_last_fetch_time():
    if os.path.exists(LAST_FETCH_FILE):
        with open(LAST_FETCH_FILE, 'r') as file:
            return file.read().strip()
    else:
        return None

def update_last_fetch_time(fetch_time):
    with open(LAST_FETCH_FILE, 'w') as file:
        file.write(fetch_time)

def fetch_new_tickets():
    global jira_fetcher

    if not jira_fetcher:
        return

    last_fetch_time = get_last_fetch_time()

    jql_query = f'project = {jira_fetcher.project_key} AND labels = {jira_fetcher.tag}'
    if last_fetch_time:
        jql_query += f' AND updated >= "{last_fetch_time}"'
    jql_query += ' ORDER BY created DESC'

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
        f'{JIRA_URL}/rest/api/2/search',
        headers=headers,
        auth=HTTPBasicAuth(JIRA_USERNAME, JIRA_API_TOKEN),
        data=json.dumps(payload)
    )

    if response.status_code == 200:
        issues = response.json().get('issues', [])
        for issue in issues:
            process_ticket(issue)
        current_fetch_time = datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S.%f%z')
        update_last_fetch_time(current_fetch_time)
    else:
        print(f"Failed to fetch issues. Status Code: {response.status_code}")
        print(f"Response: {response.text}")

def process_ticket(ticket):
    ticket_id = ticket['id']
    ticket_key = ticket['key']

    # Set ticket status to 'In Progress'
    update_ticket_status(ticket_id, 'In Progress')

    # Send ticket to localhost endpoint
    response = requests.post('http://localhost:8000/ticket', json=ticket)

    if response.status_code == 200:
        # Set ticket status to 'Done' if processing is successful
        update_ticket_status(ticket_id, 'Done')
    else:
        print(f"Failed to process ticket {ticket_key}. Status Code: {response.status_code}")

def update_ticket_status(ticket_id, status):
    url = f'{JIRA_URL}/rest/api/2/issue/{ticket_id}/transitions'
    headers = {
        'Accept': 'application/json',
        'Content-Type': 'application/json'
    }

    # Fetch available transitions
    transitions_response = requests.get(url, headers=headers, auth=HTTPBasicAuth(JIRA_USERNAME, JIRA_API_TOKEN))
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
        response = requests.post(url, headers=headers, auth=HTTPBasicAuth(JIRA_USERNAME, JIRA_API_TOKEN), data=json.dumps(payload))
        if response.status_code == 204:
            print(f"Ticket {ticket_id} status updated to {status}")
        else:
            print(f"Failed to update ticket {ticket_id} status to {status}. Status Code: {response.status_code}")
            print(f"Response: {response.text}")
    else:
        print(f"Failed to fetch transitions for ticket {ticket_id}. Status Code: {transitions_response.status_code}")
        print(f"Response: {transitions_response.text}")

@app.post("/configure", tags=["Configuration"], summary="Configure Jira Settings")
def configure_jira(config: JiraConfig):
    global jira_fetcher
    jira_fetcher = JIRATaskFetcher(config.project_key, config.tag, config.team)
    return {"message": "Jira configuration updated successfully"}

@app.post("/scheduler", tags=["Scheduler"], summary="Configure Scheduler Settings")
def configure_scheduler(config: SchedulerConfig):
    update_last_fetch_time(config.last_fetch_time.strftime('%Y-%m-%dT%H:%M:%S.%f%z'))
    return {"message": "Scheduler configuration updated successfully"}

# Schedule the ticket fetch job to run every minute
scheduler.add_job(fetch_new_tickets, 'interval', minutes=1)
scheduler.start()

# if __name__ == "__main__":
#     import uvicorn
#     uvicorn.run(app, host="0.0.0.0", port=8000)
