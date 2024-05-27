from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import os
import subprocess
from ..models.coder import SaveFileRequest, RunFileRequest

app = FastAPI()

@app.post("/write_code")
async def write_code(request: SaveFileRequest):
    try:
        save_string_to_file(request.filename, request.content)
        return {"message": "File saved successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/run_code")
async def run_code(request: RunFileRequest):
    try:
        output = run_file(request.filename, request.language)
        return {"output": output}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

def save_string_to_file(filename: str, content: str, base_path: str = "."):
    # Ensure the directory exists
    os.makedirs(base_path, exist_ok=True)
    
    # Construct the full path
    file_path = os.path.join(base_path, filename)
    
    # Write the content to the file
    with open(file_path, "w") as file:
        file.write(content)

def run_file(filename: str, language: str, base_path: str = "."):
    # Construct the full path
    file_path = os.path.join(base_path, filename)
    
    # Determine the command based on the language
    if language == "python":
        command = ["python", file_path]
    elif language == "nodejs":
        command = ["node", file_path]
    else:
        raise ValueError("Unsupported language")

    # Run the command and capture the output
    result = subprocess.run(command, capture_output=True, text=True)
    
    # Check if the command was successful
    if result.returncode != 0:
        raise RuntimeError(result.stderr)
    
    return result.stdout
