import os
import sys
import logging
from typing import Optional, Dict, Any, Callable, List
from pathlib import Path
import uuid
import threading
import queue
import time
import asyncio # Added for Future
import streamlit as st

class HumanInputTool:
    """Tool for getting input from a human user.
    
    This tool allows AI agents to request information from a human user,
    pausing execution until the human responds.
    """
    
    _pending_futures: Dict[str, asyncio.Future] = {}

    def __init__(self):
        """Initialize the HumanInputTool."""
        self.name = "human_input"
        self.description = "Ask the human user for input when you need more information or clarification."
        self.required_args = {"question": "str"}
        self.response_queue = queue.Queue() # May become obsolete for Streamlit
        self._waiting_for_input = False # Potentially re-evaluate usage with futures
        self._current_question = None # Potentially re-evaluate usage with futures
        self._current_session_id = None # Potentially re-evaluate usage with futures
        self._pending_futures = HumanInputTool._pending_futures # Ensure instance has access to class-level dict
        
        # For Pydantic schema compatibility
        from pydantic import BaseModel, Field
        
        class HumanInputSchema(BaseModel):
            """Input schema for human input tool."""
            question: str = Field(..., description="The question to ask the human user")
        
        self.args_schema = HumanInputSchema
    
    async def _run(self, question: str, **kwargs) -> str:
        """Run the tool to get human input.
        
        Args:
            question: The question to ask the human
            
        Returns:
            The human's response
        """
        if 'streamlit' in sys.modules and hasattr(st, 'session_state'):
            # Pass session_id if available in kwargs, otherwise it's None
            session_id = kwargs.get('session_id')
            return await self.streamlit_run(question, session_id=session_id, **kwargs)
        else:
            # console_run can remain synchronous and be called from an async context
            # If it needed to be truly async, one might use asyncio.to_thread
            return self.console_run(question, **kwargs)
    
    async def _arun(self, question: str, **kwargs) -> str:
        """Run the tool asynchronously.
        
        Args:
            question: The question to ask the human
            
        Returns:
            The human's response
        """
        return await self._run(question, **kwargs)
    
    def __call__(self, question: str, **kwargs) -> str:
        """Call the tool directly.
        
        Args:
            question: The question to ask the human
            
        Returns:
            The human's response
        """
        # This synchronous call needs careful handling if _run is async.
        # For CrewAI, _arun or _run (if wrapped) is typically used.
        # If called directly in a sync context, this would error.
        # For now, let's assume it's called from an async context that can handle it
        # or that CrewAI's mechanisms manage the async transition.
        # A more robust solution might involve asyncio.run() if it's certain
        # this can be a blocking call, but that's usually not desired in async code.
        # Consider raising NotImplementedError or making __call__ async as well.
        # For this refactor, focusing on _run and streamlit_run.
        if asyncio.get_event_loop().is_running():
             # This is a temporary workaround and might not be ideal.
             # It's better if the caller uses await tool.arun() or await tool.run()
            return asyncio.get_event_loop().run_until_complete(self._run(question, **kwargs))
        else:
            # Fallback for pure synchronous environments, less ideal.
            return self.console_run(question, **kwargs) # Fallback to console if no loop

    async def streamlit_run(self, question: str, session_id: Optional[str] = None, **kwargs) -> str:
        """Streamlit-specific implementation to get input from a human via the UI.
        
        Args:
            question: The question to ask the human
            session_id: Optional session ID (not directly used by future mechanism but good for context)
            
        Returns:
            The human's response when provided
        """
        request_id = str(uuid.uuid4())
        
        # Store question and active request_id in session state for the UI to pick up
        st.session_state[f"human_input_question_{request_id}"] = question
        st.session_state["human_input_active_request_id"] = request_id # UI uses this to know which request to respond to
        
        future = asyncio.Future()
        # Add a session state key to indicate UI should show input for this request_id
        st.session_state[f'human_input_waiting_{request_id}'] = True

        self._pending_futures[request_id] = future
        
        logging.info(f"Human input requested (streamlit): ID {request_id}, Question: {question}")

        try:
            response = await future
            return response
        except Exception as e:
            # Log the error with traceback
            logging.error(f"Error in HumanInputTool.streamlit_run (request_id: {request_id}): {str(e)}", exc_info=True)
            # Attempt to set exception on future to unblock awaiter if not already done
            if request_id and request_id in self._pending_futures:
                current_future = self._pending_futures[request_id]
                if current_future and not current_future.done():
                    current_future.set_exception(e)
                # Remove from pending futures as it's now handled
                del self._pending_futures[request_id]
            
            # Clean up session state associated with this failed request
            if request_id:
                if f"human_input_question_{request_id}" in st.session_state:
                    del st.session_state[f"human_input_question_{request_id}"]
                if f"human_input_waiting_{request_id}" in st.session_state:
                    del st.session_state[f"human_input_waiting_{request_id}"]
                # If this was the active request, try to clear it,
                # but be mindful not to clear a newer active request.
                if st.session_state.get("human_input_active_request_id") == request_id:
                    del st.session_state["human_input_active_request_id"]
            return f"ERROR: Human input failed due to: {str(e)}"
        finally:
            # Final cleanup for this request_id from _pending_futures if it's done
            if request_id and request_id in self._pending_futures and self._pending_futures[request_id].done():
                del self._pending_futures[request_id]
            # Session state for 'waiting' should ideally be cleared by submit_response 
            # or the error handler. If still present, it might indicate an issue.
            # The 'human_input_question_{request_id}' is also cleared by submit_response.

    def console_run(self, question: str, **kwargs) -> str:
        """Console-based implementation to get input from a human via the terminal.
        
        Args:
            question: The question to ask the human
            
        Returns:
            The human's response
        """
        try:
            print(f"\n🧠 AI is asking: {question}")
            print("Please provide your response:")
            user_input = input(">> ")
            # Logging the response might be excessive, consider if needed for debugging.
            # logger.info(f"Human response (console) for '{question}': {user_input}")
            return user_input
        except Exception as e:
            logger.error(f"Error in HumanInputTool.console_run: {str(e)}", exc_info=True)
            return f"ERROR: Human input (console) failed due to: {str(e)}"
    
    @property
    def is_waiting_for_input(self) -> bool:
        """Check if the tool is waiting for human input (legacy, less relevant with futures)."""
        # This might be true if there's an active_request_id in session_state
        return "human_input_active_request_id" in st.session_state and \
               st.session_state["human_input_active_request_id"] in self._pending_futures
    
    @property
    def current_question(self) -> Optional[str]:
        """Get the current question being asked (legacy, use active_request_id)."""
        active_request_id = st.session_state.get("human_input_active_request_id")
        if active_request_id:
            return st.session_state.get(f"human_input_question_{active_request_id}")
        return None
    
    @property
    def current_session_id(self) -> Optional[str]:
        """Get the current session ID (legacy, less relevant)."""
        # This property was tied to the old blocking mechanism.
        # It's less relevant now. Could be removed or adapted if session_id is used with futures.
        return self._current_session_id 
    
    def submit_response(self, request_id: str, response: str) -> None:
        """Submit a response to the waiting question identified by request_id.
        
        Args:
            request_id: The ID of the input request this response is for.
            response: The human's response to the question.
        """
        try:
            future = self._pending_futures.pop(request_id, None)
            
            if future and not future.done():
                future.set_result(response)
                logging.info(f"Human response submitted for ID {request_id}: {response}")
            elif future and future.done():
                # This case means the future was already completed, possibly by an error handler
                # or a timeout (if implemented). Logging is good.
                logging.warning(f"Attempted to set response for already completed future ID {request_id}.")
            else:
                logging.warning(f"No pending future found for ID {request_id} when submitting response. It might have timed out or errored.")

            # Clean up session state related to this specific request
            if f"human_input_question_{request_id}" in st.session_state:
                del st.session_state[f"human_input_question_{request_id}"]
            if f"human_input_waiting_{request_id}" in st.session_state: # Also clear the waiting flag
                del st.session_state[f"human_input_waiting_{request_id}"]
            
            # If this was the active request, clear it.
            if st.session_state.get("human_input_active_request_id") == request_id:
                del st.session_state["human_input_active_request_id"]
        except Exception as e:
            logger.error(f"Error in HumanInputTool.submit_response (request_id: {request_id}): {str(e)}", exc_info=True)
            # If the future was retrieved but set_result failed, or pop failed,
            # ensure it's removed from _pending_futures if it's still there and an error occurred.
            if request_id and request_id in self._pending_futures:
                current_future = self._pending_futures.pop(request_id) # remove it
                if current_future and not current_future.done():
                    current_future.set_exception(e) # Propagate error if possible
            # No return value here, but logging is critical.

        # The response_queue is not used by the future-based streamlit_run.
        # If console_run were also async and future-based, it could use it.
        # For now, this line has no effect on streamlit_run.
        # self.response_queue.put(response) 

# Create a singleton instance of the tool
human_input_tool = HumanInputTool()

# Updated helper to reflect new submit_response signature
def get_human_input(question: str, session_id: Optional[str] = None, **kwargs) -> str:
    """Get input from a human user.
    
    This function provides a convenient wrapper around the human_input_tool
    for use in various contexts. This wrapper is synchronous.
    If you are in an async context, you should call `await human_input_tool.run(question, ...)`
    or `await human_input_tool.arun(question, ...)`.
    
    Args:
        question: The question to ask the human
        session_id: Optional session ID to track which conversation this is part of
        
    Returns:
        The human's response
    """
    # This global helper function is synchronous.
    # It can only reliably call the synchronous console_run or a blocking version.
    # For the new async streamlit_run, this helper is not suitable if called from a sync context
    # without proper async-to-sync bridging.
    if 'streamlit' in sys.modules and hasattr(st, 'session_state') and not asyncio.get_event_loop().is_running():
        # This is problematic. Calling an async method from a sync one.
        # This indicates a mismatch in how this helper is intended to be used.
        # For now, let it fall through to console or error if loop is running.
        logging.warning("get_human_input (sync helper) called in Streamlit context. This may not work as expected with async streamlit_run.")
        # Attempting to run streamlit_run synchronously - THIS IS NOT RECOMMENDED
        # and likely to cause issues. The UI should trigger submit_response,
        # and the agent should `await streamlit_run`.
        # This helper function is less useful with the async refactor.
        # return human_input_tool.console_run(question, **kwargs) # Safer fallback
        raise RuntimeError("The synchronous get_human_input helper cannot be used with async streamlit_run. Await human_input_tool.run() instead.")


    if 'streamlit' in sys.modules and hasattr(st, 'session_state') and asyncio.get_event_loop().is_running():
        # If an event loop is running, it implies this is part of an async flow.
        # However, this function itself is sync. This is a conflict.
        logging.error("Synchronous get_human_input called from an async context in Streamlit. This is not supported.")
        raise RuntimeError("Synchronous get_human_input called from an async Streamlit context.")
    else:
        # Default to console if not in Streamlit or if issues with async context
        return human_input_tool.console_run(question, **kwargs)

# Helper function to check if human input is waiting
def is_waiting_for_input() -> bool:
    """Check if the human input tool is waiting for a response."""
    # This should reflect the new mechanism, e.g., check active_request_id
    if 'streamlit' in sys.modules and hasattr(st, 'session_state'):
        return "human_input_active_request_id" in st.session_state and \
               st.session_state["human_input_active_request_id"] in human_input_tool._pending_futures
    return False # Default for non-streamlit context

# Helper function to get the current question
def get_current_question() -> Optional[str]:
    """Get the current question being asked by the human input tool."""
    if 'streamlit' in sys.modules and hasattr(st, 'session_state'):
        active_request_id = st.session_state.get("human_input_active_request_id")
        if active_request_id:
            return st.session_state.get(f"human_input_question_{active_request_id}")
    return None

# Helper function to submit a response - needs request_id
def submit_response(request_id: str, response: str) -> None:
    """Submit a response to the waiting human input tool.
    
    Args:
        request_id: The ID of the input request this response is for.
        response: The human's response to the question.
    """
    human_input_tool.submit_response(request_id, response)