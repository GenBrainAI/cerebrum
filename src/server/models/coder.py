from pydantic import BaseModel

class SaveFileRequest(BaseModel):
    filename: str
    content: str

class RunFileRequest(BaseModel):
    filename: str
    language: str  # "python" or "nodejs"
