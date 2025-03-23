"""
Mock main application module for testing.
"""
from fastapi import FastAPI
from .apis.agents_api import router as AgentsApiRouter

# Create a mock FastAPI application
app = FastAPI(
    title="Cerebrum API",
    description="Mock Cerebrum API for testing",
    version="0.1.0"
)

# Include mock routers
app.include_router(AgentsApiRouter) 