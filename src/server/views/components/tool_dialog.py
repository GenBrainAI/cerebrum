from ..models.view_state import ViewState
from typing import Optional, Dict, Any

class ToolDialog:
    def __init__(self, view_state: ViewState, persistence_model):
        self.view_state = view_state
        self.persistence_model = persistence_model
        self._has_streamlit = False
        try:
            import streamlit as st
            self._has_streamlit = True
            self._st = st
        except ImportError:
            pass

    def render(self) -> Optional[Dict[str, Any]]:
        """Render the tool configuration dialog."""
        if not self._has_streamlit:
            return None
            
        with self._st.form("tool_config_form"):
            name = self._st.text_input("Tool Name")
            description = self._st.text_area("Description")
            tool_type = self._st.selectbox("Tool Type", ["API", "Function", "LangChain", "Utility", "Custom"])
            
            if self._st.form_submit_button("Save"):
                return {
                    "name": name,
                    "description": description,
                    "tool_type": tool_type
                }
        return None 