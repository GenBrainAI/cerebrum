import streamlit as st
import logging
from typing import Dict, Any, Optional, List
import asyncio
from ...tools.human_tools import human_input_tool
from ...controllers.task_runner import TaskRunner
import time

logger = logging.getLogger(__name__)

class HumanInputComponent:
    """Component for handling human-in-the-loop interactions with CrewAI tasks."""
    
    def __init__(self, task_runner: Optional[TaskRunner] = None):
        """Initialize the component."""
        self.task_runner = task_runner
        self.is_polling = False
        self._poll_task = None
    
    def render(self):
        """Render the human input component."""
        st.subheader("Human-in-the-Loop")
        
        with st.expander("About Human-in-the-Loop", expanded=False):
            st.markdown("""
            **Human-in-the-Loop** allows CrewAI agents to request input from the user during task execution.
            
            When an agent needs clarification or additional information, it will pause execution and wait for your
            response. This enables a collaborative workflow between humans and AI agents.
            
            **How it works:**
            1. An agent encounters a question it needs your help with
            2. The agent's request appears in the panel below
            3. You provide your response and submit it
            4. The agent continues execution with your input
            
            This feature is especially useful for:
            - Clarifying ambiguous requirements
            - Providing domain expertise
            - Making critical decisions
            - Reviewing generated content
            """)
        
        # Display pending requests section
        if "human_input_pending_requests" not in st.session_state:
            st.session_state.human_input_pending_requests = {}
        
        if "human_input_responses" not in st.session_state:
            st.session_state.human_input_responses = {}
        
        # Button to start/stop polling
        if not self.is_polling:
            if st.button("Start Monitoring for Human Input Requests"):
                self.is_polling = True
                self._start_polling()
                st.experimental_rerun()
        else:
            if st.button("Stop Monitoring for Human Input Requests"):
                self.is_polling = False
                self._stop_polling()
                st.experimental_rerun()
        
        # Display status
        if self.is_polling:
            st.success("Monitoring for human input requests... ✅")
        else:
            st.warning("Not currently monitoring for human input requests. Start monitoring to respond to agent questions.")
        
        # Display pending requests
        pending_requests = human_input_tool.get_pending_requests()
        
        if pending_requests:
            st.subheader("Pending Human Input Requests")
            
            for request_id, request_data in pending_requests.items():
                with st.container():
                    st.text_area(
                        f"Request {request_id[:8]}...",
                        value=request_data["query"],
                        height=100,
                        disabled=True,
                        key=f"request_{request_id}"
                    )
                    
                    # Input for user response
                    user_response = st.text_area(
                        "Your response",
                        key=f"response_{request_id}",
                        height=100
                    )
                    
                    # Submit button
                    if st.button("Submit Response", key=f"submit_{request_id}"):
                        success = human_input_tool.respond_to_request(request_id, user_response)
                        if success:
                            st.session_state.human_input_responses[request_id] = user_response
                            st.session_state.human_input_pending_requests.pop(request_id, None)
                            st.success("Response submitted successfully!")
                            st.experimental_rerun()
                        else:
                            st.error("Failed to submit response. Request may have expired.")
                    
                    st.divider()
        else:
            if self.is_polling:
                st.info("No pending human input requests. Agents will appear here when they need your input.")
            else:
                st.info("No pending human input requests. Start monitoring to check for new requests.")
    
    def _start_polling(self):
        """Start polling for human input requests."""
        logger.info("Starting to poll for human input requests")
        
        # In a real implementation, you'd start an async task here
        # For Streamlit, we'll rely on the periodic page refresh
        
    def _stop_polling(self):
        """Stop polling for human input requests."""
        logger.info("Stopping polling for human input requests")
        
    async def _poll_for_requests(self):
        """Poll for human input requests in the background."""
        logger.info("Starting background polling for human input requests")
        
        try:
            while self.is_polling:
                # Check for new requests
                pending_requests = human_input_tool.get_pending_requests()
                
                # Update session state with new requests
                for request_id, request_data in pending_requests.items():
                    if request_id not in st.session_state.human_input_pending_requests:
                        st.session_state.human_input_pending_requests[request_id] = request_data
                
                # Remove completed requests
                for request_id in list(st.session_state.human_input_pending_requests.keys()):
                    if request_id not in pending_requests:
                        st.session_state.human_input_pending_requests.pop(request_id, None)
                
                # Sleep for a short time
                await asyncio.sleep(1)
        except Exception as e:
            logger.error(f"Error in polling task: {str(e)}")
        finally:
            logger.info("Background polling task stopped")
    
    def get_response_history(self) -> List[Dict[str, Any]]:
        """Get the history of human input responses."""
        history = []
        
        for request_id, response in st.session_state.human_input_responses.items():
            if request_id in human_input_tool._pending_requests:
                history.append({
                    "request_id": request_id,
                    "query": human_input_tool._pending_requests[request_id]["query"],
                    "response": response,
                    "timestamp": human_input_tool._pending_requests[request_id]["timestamp"]
                })
        
        return history 