# src/server/views/components/chat_panel.py
import streamlit as st
from typing import List, Dict, Any, Optional
from ..models.view_state import ViewState

class ChatPanel:
    """Reusable chat interface component."""
    
    def __init__(self, view_state: ViewState):
        self.view_state = view_state
        
    def render(self):
        """Render chat interface with messages."""
        st.subheader("Chat")
        
        # Display chat history
        for msg in self.view_state.chat_history:
            with st.chat_message(msg["role"]):
                st.write(msg["content"])
                
        # Chat input
        if prompt := st.chat_input("Type your message..."):
            return prompt