import requests
import os
import json

# Use the GROQ_API_KEY from environment
api_key = os.environ.get("GROQ_API_KEY")
url = "https://api.groq.com/openai/v1/models"

headers = {
    "Authorization": f"Bearer {api_key}",
    "Content-Type": "application/json"
}

response = requests.get(url, headers=headers)
models = response.json()

print("Available Groq models:")
for model in models.get("data", []):
    print(f"- {model['id']}") 