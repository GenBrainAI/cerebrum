# # Save as: tests/test_application_state.py

# import pytest
# import os
# from pathlib import Path
# from fastapi.testclient import TestClient
# from src.server.main import app
# from src.server.models.message import Message
# from src.server.models.persistence_models import StorageLocation, StorageType

# @pytest.fixture
# def client():
#     return TestClient(app)

# def test_load_and_use_application_state(client):
#     # First verify the state file exists
#     state_path = Path("state/application_handler_state.json")
#     assert state_path.exists(), "State file not found"
    
#     # Load the state
#     state_location = StorageLocation(
#         type=StorageType.file,
#         location="state",
#         state_name="application_handler_state.json"
#     )
    
#     response = client.post("/state/load", json=state_location.dict())
#     assert response.status_code == 201
    
#     # Create a test email response
#     test_email = """
#     Dear John,
    
#     Thank you for your application for the Senior Developer position at TechCorp Inc.
    
#     We are pleased to inform you that we would like to move forward with your application.
#     Your experience aligns perfectly with what we're looking for.
    
#     Jane Smith will be your point of contact for the next steps.
    
#     Best regards,
#     Hiring Team
#     TechCorp Inc.
#     """
    
#     # Create a message using the email
#     user_message = Message(
#         role="user",
#         content=test_email
#     )
    
#     # Run the task
#     run_task = {
#         'caller_id': "TestEmailProcessor",
#         'messages': [user_message.dict()],
#         'running_extra_params': {
#             'phone_number': '+1234567890'  # Test phone number
#         }
#     }
    
#     # Get a tasksmanager (should be the first one since we just loaded the state)
#     tasksmanagers_response = client.get("/tasksmanager")
#     assert tasksmanagers_response.status_code == 200
#     tasksmanagers = tasksmanagers_response.json()["tasksmanagers"]
#     assert len(tasksmanagers) > 0
    
#     tasksmanager_id = tasksmanagers[0]["id"]
    
#     # Get the associated task
#     tasks_response = client.get(f"/task/{tasksmanager_id}")
#     assert tasks_response.status_code == 200
#     task = tasks_response.json()
    
#     # Run the task
#     run_response = client.post(
#         f"/task/{tasksmanager_id}/{task['id']}/run",
#         json=run_task
#     )
#     assert run_response.status_code == 200
    
#     # Verify SMS file was created
#     sms_logs_dir = Path("sms_logs")
#     assert sms_logs_dir.exists(), "SMS logs directory not created"
    
#     # There should be at least one SMS log file
#     sms_files = list(sms_logs_dir.glob("sms_*.txt"))
#     assert len(sms_files) > 0, "No SMS log files found"
    
#     # Read the latest SMS file
#     latest_sms = max(sms_files, key=lambda x: x.stat().st_mtime)
#     with latest_sms.open() as f:
#         sms_content = f.read()
        
#     # Verify SMS content contains key information
#     assert "TechCorp Inc" in sms_content, "Company name not found in SMS"
#     assert "Senior Developer" in sms_content, "Position not found in SMS"
#     assert "+1234567890" in sms_content, "Phone number not found in SMS"

# if __name__ == "__main__":
#     pytest.main([__file__])
