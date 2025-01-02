import aiohttp
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)

class URLTools:
    """Tool for URL operations."""
    
    def __init__(self):
        """Initialize URLTools with an aiohttp session."""
        self.session = aiohttp.ClientSession()
        
    async def fetch_documentation(self, url: str) -> dict:
        """Fetch documentation from URL.
        
        Args:
            url: The URL to fetch documentation from.
            
        Returns:
            A dictionary containing the status, message, and content.
        """
        try:
            async with self.session.get(url) as response:
                if response.status != 200:
                    return {
                        "status": "error",
                        "message": f"Failed to fetch documentation: HTTP {response.status}",
                        "content": None
                    }
                    
                content = await response.text()
                return {
                    "status": "success",
                    "message": f"Documentation fetched from {url}",
                    "content": content
                }
        except Exception as e:
            logger.error(f"Error fetching documentation: {str(e)}")
            return {
                "status": "error",
                "message": f"Failed to fetch documentation: {str(e)}",
                "content": None
            }
            
    async def close(self):
        """Close the aiohttp session."""
        if self.session and not self.session.closed:
            await self.session.close() 