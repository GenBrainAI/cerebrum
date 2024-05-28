from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import os
import subprocess
from ..models.coder import SaveFileRequest, RunFileRequest
from glob import glob
from langchain_chroma import Chroma
from langchain_community.document_loaders import TextLoader
from langchain_community.embeddings.openai import OpenAIEmbeddings
from langchain_text_splitters import CharacterTextSplitter
import openai
from getpass import getpass

app = FastAPI()

openai.api_key = os.environ.get("OPENAI_API_KEY")


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


class ChromaSingleton:
    _instance = None
    _db = None
    _persist_directory = "./chroma_db"

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ChromaSingleton, cls).__new__(cls)
            cls._instance._init_db()
        return cls._instance

    def _init_db(self):
        embedding_function = OpenAIEmbeddings(api_key=OPENAI_API_KEY)
        if os.path.exists(self._persist_directory):
            self._db = Chroma(persist_directory=self._persist_directory, embedding_function=embedding_function)
        else:
            self._db = None

    def get_db(self):
        return self._db

    def set_db(self, db):
        self._db = db


@app.get("/vector/load_self_code")
async def load_cerebrum_code():
    try:
        # Ensure singleton instance
        chroma_singleton = ChromaSingleton()

        # Find all relevant files in the project root
        project_root = "."
        file_extensions = ['*.py', '*.yml', '*.yaml', '*.md', 'requirements.txt', 'Dockerfile', '.env']
        project_files = []
        for ext in file_extensions:
            project_files.extend([y for x in os.walk(project_root) for y in glob(os.path.join(x[0], ext))])

        # Load the content of all files
        documents = []
        for file_path in project_files:
            loader = TextLoader(file_path)
            documents.extend(loader.load())

        # Split documents into chunks
        text_splitter = CharacterTextSplitter(chunk_size=1000, chunk_overlap=0)
        docs = text_splitter.split_documents(documents)

        # Create the embedding function
        embedding_function = OpenAIEmbeddings(api_key=OPENAI_API_KEY)

        # Load documents into Chroma
        db = Chroma.from_documents(docs, embedding_function, persist_directory=chroma_singleton._persist_directory)

        # Update the singleton instance
        chroma_singleton.set_db(db)

        return {"message": "Successfully loaded code into Chroma database"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
