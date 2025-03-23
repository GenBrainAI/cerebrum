"""
Mock agents controller for testing.
"""
from typing import Dict, Any, List, Optional
from unittest.mock import MagicMock, AsyncMock

# Create mock classes
GitHubTool = MagicMock()

# Create mock functions
async def create_crew(crew_name: str, **kwargs) -> Dict[str, Any]:
    """Create a mock crew."""
    return {
        "id": "mock-crew-id",
        "name": crew_name,
        "agents": [],
        "created_at": "2023-01-01T00:00:00Z"
    }

async def enhance_crew_with_context(crew_id: str, context: str) -> Dict[str, Any]:
    """Enhance a mock crew with context."""
    return {
        "id": crew_id,
        "context": context,
        "updated_at": "2023-01-02T00:00:00Z"
    } 