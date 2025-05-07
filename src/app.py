import os
import sys
import logging
from pathlib import Path

# Set parent directory in sys.path for imports
parent_dir = os.path.dirname(os.path.abspath(__file__))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

import streamlit as st
import asyncio
from src.chat import main as chat_main
from src.server.tools.human_tools import is_waiting_for_input, get_current_question
from src.server.views.components.human_input_component import render_human_input_component

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

def main():
    """Run the Cerebrum application."""
    try:
        
        # Add CSS for styling
        st.markdown("""
        <style>
        .stApp {
            max-width: 1200px;
            margin: 0 auto;
        }
        .human-input-alert {
            border: 2px solid #ff4b4b;
            border-radius: 5px;
            padding: 10px;
            background-color: #ffe6e6;
            margin-bottom: 10px;
        }
        </style>
        """, unsafe_allow_html=True)
        
        # Check if we have a human input request pending
        if is_waiting_for_input():
            # Display an alert in the sidebar
            with st.sidebar:
                st.markdown(
                    f"""
                    <div class="human-input-alert">
                    <h3>⚠️ Human Input Requested</h3>
                    <p>An AI agent is waiting for your input!</p>
                    </div>
                    """, 
                    unsafe_allow_html=True
                )
                
                # Add a separate human input component in the sidebar
                st.subheader("Respond to AI Request")
                question = get_current_question()
                if question:
                    st.info(f"Question: {question}")
                    render_human_input_component()
        
        # Run the main chat application
        chat_main()
        
    except Exception as e:
        logger.exception(f"Error in main app: {str(e)}")
        st.error(f"An error occurred: {str(e)}")

if __name__ == "__main__":
    main()  