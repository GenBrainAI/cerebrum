from typing import Dict, Any, Optional, Union
import logging
from crewai.tools import BaseTool
from datetime import datetime
import json
import asyncio
import uuid

logger = logging.getLogger(__name__)

class HumanInputTool(BaseTool):
    """A tool that allows agents to request input from a human user."""
    
    # Class-level variables for mock responses
    _is_test_mode = False
    _mock_responses = []
    _default_mock_response = "This is an automated test response. I'd like to continue."
    
    @classmethod
    def configure_test_mode(cls, enable: bool = True, mock_responses: list = None):
        """
        Configure the tool for testing with mock responses.
        
        Args:
            enable: Whether to enable test mode
            mock_responses: Optional list of responses to use in sequence.
                           If not provided, will use a default response.
        """
        cls._is_test_mode = enable
        if mock_responses:
            cls._mock_responses = list(mock_responses)  # Create a copy
        else:
            cls._mock_responses = []
        logger.info(f"HumanInputTool test mode {'enabled' if enable else 'disabled'}")
        if enable:
            logger.info(f"Mock responses: {cls._mock_responses or [cls._default_mock_response]}")
    
    def __init__(self):
        """Initialize the HumanInputTool."""
        super().__init__(
            name="human_input",
            description="Ask the human for information or feedback. Use this when you need clarification or additional details from the user."
        )
        self._pending_requests = {}
        self._responses = {}
    
    def _run(self, query: str) -> str:
        """
        Request input from a human user.
        
        This is a blocking implementation that uses the input() function.
        In production, you might want to replace this with a more sophisticated
        method that integrates with your UI.
        
        Args:
            query: The question or prompt to show to the human user
            
        Returns:
            The human's response as a string
        """
        print(f"\n🧠 Agent is requesting human input: {query}")
        
        # If in test mode, return a mock response
        if self.__class__._is_test_mode:
            response = self.__class__._mock_responses.pop(0) if self.__class__._mock_responses else self.__class__._default_mock_response
            print(f"🤖 Using mock response in test mode: {response}")
            return response
            
        try:
            human_response = input(f"{query}\nYour response: ")
            print(f"✅ Human response received: {human_response}")
            return human_response
        except Exception as e:
            error_msg = f"Error getting human input: {str(e)}"
            logger.error(error_msg)
            return f"Error: {error_msg}"

    async def _arun(self, query: str) -> str:
        """
        Request input from a human user asynchronously.
        
        This implementation creates a pending request that can be fulfilled
        through the respond_to_request method, which would typically be called
        from a UI controller.
        
        Args:
            query: The question or prompt to show to the human user
            
        Returns:
            The human's response as a string
        """
        # If in test mode, return a mock response immediately
        if self.__class__._is_test_mode:
            response = self.__class__._mock_responses.pop(0) if self.__class__._mock_responses else self.__class__._default_mock_response
            print(f"🤖 Using mock response in test mode (async): {response}")
            return response
            
        request_id = str(uuid.uuid4())
        self._pending_requests[request_id] = {
            "query": query,
            "timestamp": datetime.now().isoformat(),
            "status": "pending"
        }
        
        logger.info(f"Created human input request {request_id}: {query}")
        
        # Wait for response with timeout
        timeout_seconds = 300  # 5 minutes timeout
        start_time = datetime.now()
        
        while request_id not in self._responses:
            await asyncio.sleep(0.5)
            elapsed = (datetime.now() - start_time).total_seconds()
            if elapsed > timeout_seconds:
                logger.warning(f"Request {request_id} timed out after {timeout_seconds} seconds")
                return "Error: Request timed out waiting for human response"
        
        # Get and clear the response
        response = self._responses.pop(request_id)
        self._pending_requests[request_id]["status"] = "completed"
        
        logger.info(f"Human input received for request {request_id}: {response}")
        return response
    
    def respond_to_request(self, request_id: str, response: str) -> bool:
        """
        Provide a response to a pending human input request.
        
        This method would typically be called from a UI controller when
        the human user submits their response.
        
        Args:
            request_id: The ID of the pending request
            response: The human's response
            
        Returns:
            True if the response was successfully recorded, False otherwise
        """
        if request_id not in self._pending_requests:
            logger.warning(f"Request {request_id} not found")
            return False
        
        self._responses[request_id] = response
        logger.info(f"Response recorded for request {request_id}")
        return True
    
    def get_pending_requests(self) -> Dict[str, Dict[str, Any]]:
        """
        Get all pending human input requests.
        
        Returns:
            Dictionary of pending requests, keyed by request ID
        """
        return {k: v for k, v in self._pending_requests.items() if v["status"] == "pending"}

# Global instance for easy access
human_input_tool = HumanInputTool() 