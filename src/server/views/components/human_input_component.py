"""
Human Input Component for Streamlit UI

This component displays a UI for humans to interact with AI agents by 
responding to questions asked via the human_input_tool.
"""

import streamlit as st
import logging
from typing import Dict, Any, Optional, List
import asyncio
from ...tools.human_tools import human_input_tool, is_waiting_for_input, get_current_question, submit_response
from ...controllers.task_runner import TaskRunner
import time

logger = logging.getLogger(__name__)

class HumanInputComponent:
    """Streamlit component for handling human input requests from AI agents."""
    
    def __init__(self, session_id: Optional[str] = None):
        """Initialize the HumanInputComponent.
        
        Args:
            session_id: Optional session ID to track which conversation this is part of
        """
        self.session_id = session_id
        self._initialize_session_state()
    
    def _initialize_session_state(self) -> None:
        """Initialize session state variables for this component."""
        if "human_input_history" not in st.session_state:
            st.session_state.human_input_history = []
        if "human_input_expanding" not in st.session_state:
            st.session_state.human_input_expanding = False
        if "human_input_show_history" not in st.session_state:
            st.session_state.human_input_show_history = False
    
    def handle_input_callback(self) -> None:
        """Handle user input submissions."""
        # Get the input value from session state
        response = st.session_state.human_input_response
        
        if response:
            # Get the current question
            question = get_current_question()
            
            # Add to history
            if question:
                st.session_state.human_input_history.append({
                    "question": question,
                    "response": response,
                    "timestamp": time.time()
                })
            
            # Submit the response
            submit_response(response)
            
            # Clear the input field
            st.session_state.human_input_response = ""
    
    def toggle_history(self) -> None:
        """Toggle display of input history."""
        st.session_state.human_input_show_history = not st.session_state.human_input_show_history
    
    def render(self) -> None:
        """Render the human input component."""
        # Check if there's a pending question
        waiting = is_waiting_for_input()
        question = get_current_question()
        
        if waiting and question:
            with st.container():
                st.info("🧠 **AI is asking for your input:**")
                st.markdown(f"**{question}**")
                
                # Input field for response
                st.text_input(
                    "Your response:",
                    key="human_input_response",
                    on_change=self.handle_input_callback
                )
                
                # Add a submit button for clarity
                if st.button("Submit Response", key="human_input_submit"):
                    self.handle_input_callback()
        
        # Option to show interaction history
        if st.session_state.human_input_history:
            if st.button(
                "Show Interaction History" if not st.session_state.human_input_show_history else "Hide Interaction History", 
                key="toggle_history"
            ):
                self.toggle_history()
            
            if st.session_state.human_input_show_history:
                with st.expander("Human-AI Interaction History", expanded=True):
                    for i, interaction in enumerate(st.session_state.human_input_history):
                        st.markdown(f"### Interaction {i+1}")
                        st.markdown(f"**AI asked:** {interaction['question']}")
                        st.markdown(f"**You responded:** {interaction['response']}")
                        st.divider()

def render_human_input_component(session_id: Optional[str] = None) -> None:
    """Render the human input component in the current Streamlit app.
    
    Args:
        session_id: Optional session ID to track which conversation this is part of
    """
    component = HumanInputComponent(session_id)
    component.render() 