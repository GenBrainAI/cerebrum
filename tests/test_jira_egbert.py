# # import requests
# # from fastapi.testclient import TestClient

# from src.server.controllers.jira import JiraTicketHandler, JiraConfig
# from src.server.models.message import Message

# request_data = {
#     "description": "File creator",
#     "agents": [
#         {
#             "role": "File maker",
#             "verbose": True,
#             "goal": "create new files and save them",
#             "backstory": "You are a 40 year old administrator that creates files and stores them",
#             "class_tools": [],
#             "tools": [
#                 {"name": "save_file", "description": "Tool for storing files"},
#                 {"name": "GitHubTool", "description": "Tool for storing files"},
#             ],
#         }
#     ],
#     "tasks": [
#         {
#             "description": "Make files",
#             "expected_output": "Create a .txt file that says hello world and write it to /home/egbert/hello_world.txt",
#             "agent_role": "File maker"
#         },
#         {
#             "description": "change and commit file to github repo",
#             "expected_output": "Change the file hello.txt to say hello world and commit it to the github repo GenBrainAI/cerebrum",
#             "agent_role": "File maker file"
#         },
#         {
#             "description": "get the readme from the repository and output its contents",
#             "expected_output": "Get the readme file from the github repo and output its contents",
#             "agent_role": "File maker"
#         }
#     ]
# }

# base_url = "http://localhost:8080"

# def test_jira(client: TestClient):
#     response = requests.post(f"{base_url}/agent/crewai", json=request_data)
#     assert response.status_code == 200
#     data = response.json()
#     print(data)

#     tasksmanager_data = {
#         "name": "File expert",
#         "model": "gpt-4o",
#         "description": "make files",
#     }

#     tasksmanager_response = requests.post(f"{base_url}/tasksmanager", json=tasksmanager_data)
#     assert tasksmanager_response.status_code == 201
#     tasksmanager_id = tasksmanager_response.json()["id"]

#     # Create task
#     system_message = Message(
#         role="system",
#         content="You create new files based on input"
#     )

#     task_data = {
#         "name": "file maker",
#         "description": "Makes new files",
#         "tasksmanager_id": tasksmanager_id,
#         "messages": [system_message.dict()],
#         "crewai_info_id": data['crew_id']['id'],
#         "curried_proxy_id": data['curried_proxy_id'],
#     }

#     task_response = requests.post(f"{base_url}/task", json=task_data)
#     assert task_response.status_code == 201
#     task_id = task_response.json()["id"]

#     # Run task with user message
#     user_message = Message(
#         role="user",
#         content="write a file to /home/egbert/hello.txt that says hello world and commit it to github"
#     )

#     run_task = {
#         'caller_id': "UnitTestCaller",
#         'messages': [user_message.dict()]
#     }

#     run_task_response = requests.post(f"{base_url}/task/{tasksmanager_id}/{task_id}/run", json=run_task)
#     print(run_task_response)
