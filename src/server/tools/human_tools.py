import os
import sys
import logging
from typing import Optional, Dict, Any, Callable, List
from pathlib import Path
import uuid
import threading
import queue
import time
import streamlit as st

class HumanInputTool:
    """Tool for getting input from a human user.
    
    This tool allows AI agents to request information from a human user,
    pausing execution until the human responds.
    """
    
    def __init__(self):
        """Initialize the HumanInputTool."""
        self.name = "human_input"
        self.description = "Ask the human user for input when you need more information or clarification."
        self.required_args = {"question": "str"}
        self.response_queue = queue.Queue()
        self._waiting_for_input = False
        self._current_question = None
        self._current_session_id = None
        
        # For Pydantic schema compatibility
        from pydantic import BaseModel, Field
        
        class HumanInputSchema(BaseModel):
            """Input schema for human input tool."""
            question: str = Field(..., description="The question to ask the human user")
        
        self.args_schema = HumanInputSchema
    
    def _run(self, question: str, **kwargs) -> str:
        """Run the tool to get human input.
        
        Args:
            question: The question to ask the human
            
        Returns:
            The human's response
        """
        # This is the default implementation that will be replaced 
        # with a Streamlit or console version
        return f"PLACEHOLDER RESPONSE TO: {question}"
    
    async def _arun(self, question: str, **kwargs) -> str:
        """Run the tool asynchronously.
        
        Args:
            question: The question to ask the human
            
        Returns:
            The human's response
        """
        return self._run(question, **kwargs)
    
    def __call__(self, question: str, **kwargs) -> str:
        """Call the tool directly.
        
        Args:
            question: The question to ask the human
            
        Returns:
            The human's response
        """
        return self._run(question, **kwargs)
    
    def streamlit_run(self, question: str, session_id: Optional[str] = None, **kwargs) -> str:
        """Streamlit-specific implementation to get input from a human via the UI.
        
        Args:
            question: The question to ask the human
            session_id: Optional session ID to track which conversation this is part of
            
        Returns:
            The human's response when provided
        """
        # Set the current question and mark that we're waiting for input
        self._current_question = question
        self._current_session_id = session_id or str(uuid.uuid4())
        self._waiting_for_input = True
        
        # Store in session state to persist across Streamlit reruns
        key_prefix = f"human_input_{self._current_session_id}"
        question_key = f"{key_prefix}_question"
        waiting_key = f"{key_prefix}_waiting"
        response_key = f"{key_prefix}_response"
        
        # Store the question and waiting state in session state
        st.session_state[question_key] = question
        st.session_state[waiting_key] = True
        
        # Wait for the response (this will block until the user provides input)
        try:
            # In the Streamlit context, we need to yield control back to the UI thread
            # so we'll put the question in session state and wait for a response
            while st.session_state.get(waiting_key, True):
                # Check if we have a response
                if response_key in st.session_state:
                    response = st.session_state[response_key]
                    # Clear the response from session state
                    del st.session_state[response_key]
                    # Mark that we're no longer waiting
                    st.session_state[waiting_key] = False
                    self._waiting_for_input = False
                    return response
                
                # Wait a bit before checking again
                time.sleep(0.1)
                
            # If we get here, something went wrong
            return "ERROR: No response received"
            
        except Exception as e:
            logging.error(f"Error in human_input_tool: {str(e)}")
            self._waiting_for_input = False
            return f"ERROR: {str(e)}"
    
    def console_run(self, question: str, **kwargs) -> str:
        """Console-based implementation to get input from a human via the terminal.
        
        Args:
            question: The question to ask the human
            
        Returns:
            The human's response
        """
        print(f"\n🧠 AI is asking: {question}")
        print("Please provide your response:")
        user_input = input(">> ")
        print(f"Thank you! Your response: {user_input}")
        return user_input
    
    @property
    def is_waiting_for_input(self) -> bool:
        """Check if the tool is waiting for human input."""
        return self._waiting_for_input
    
    @property
    def current_question(self) -> Optional[str]:
        """Get the current question being asked."""
        return self._current_question
    
    @property
    def current_session_id(self) -> Optional[str]:
        """Get the current session ID."""
        return self._current_session_id
    
    def submit_response(self, response: str) -> None:
        """Submit a response to the waiting question.
        
        Args:
            response: The human's response to the question
        """
        if self._waiting_for_input:
            # Put the response in session state
            if self._current_session_id:
                key = f"human_input_{self._current_session_id}_response"
                st.session_state[key] = response
                
            # Also put it in the queue for non-Streamlit contexts
            self.response_queue.put(response)
            
            # Reset the waiting state
            self._waiting_for_input = False

# Create a singleton instance of the tool
human_input_tool = HumanInputTool()

def get_human_input(question: str, session_id: Optional[str] = None) -> str:
    """Get input from a human user.
    
    This function provides a convenient wrapper around the human_input_tool
    for use in various contexts.
    
    Args:
        question: The question to ask the human
        session_id: Optional session ID to track which conversation this is part of
        
    Returns:
        The human's response
    """
    # Check if we're in a Streamlit context
    if 'streamlit' in sys.modules and hasattr(st, 'session_state'):
        # Use the Streamlit implementation
        return human_input_tool.streamlit_run(question, session_id)
    else:
        # Use the console implementation
        return human_input_tool.console_run(question)

# Helper function to check if human input is waiting
def is_waiting_for_input() -> bool:
    """Check if the human input tool is waiting for a response."""
    return human_input_tool.is_waiting_for_input

# Helper function to get the current question
def get_current_question() -> Optional[str]:
    """Get the current question being asked by the human input tool."""
    return human_input_tool.current_question

# Helper function to submit a response
def submit_response(response: str) -> None:
    """Submit a response to the waiting human input tool.
    
    Args:
        response: The human's response to the question
    """
    human_input_tool.submit_response(response) 