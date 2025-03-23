"""
Mock agents API for testing.
"""
from fastapi import APIRouter, Depends, HTTPException
from typing import Dict, Any

# Create a mock router
router = APIRouter(prefix="/agents", tags=["agents"])

@router.post("/crews")
async def create_crew(crew_data: Dict[str, Any]) -> Dict[str, Any]:
    """Create a mock crew endpoint."""
    return {
        "id": "mock-crew-id",
        "name": crew_data.get("name", "Mock Crew"),
        "created_at": "2023-01-01T00:00:00Z"
    }

@router.post("/crews/{crew_id}/context")
async def add_context_to_crew(crew_id: str, context_data: Dict[str, Any]) -> Dict[str, Any]:
    """Add context to a mock crew endpoint."""
    return {
        "id": crew_id,
        "context": context_data.get("context", ""),
        "updated_at": "2023-01-02T00:00:00Z"
    } 