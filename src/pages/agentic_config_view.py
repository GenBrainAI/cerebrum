import streamlit as st
import asyncio
from server.views.base_view import BaseView
from server.views.models.view_types import ViewType
from server.views.components.header import render_header
from server.views.components.sidebar.agentic_config_sidebar import render_agentic_config_sidebar
from server.views.controllers.agentic_view_controller import AgenticViewController
from server.persistence.persistence_model_factory import PersistenceModelFactory
from typing import Dict, Any

class AgenticConfigView(BaseView):
    def __init__(self):
        super().__init__(ViewType.AGENTIC_CONFIG)
    
    def get_session_data(self) -> Dict[str, Any]:
        """Get agentic config specific session data."""
        data = super().get_session_data()
        # Add view-specific data
        data.update({
            'selected_config': st.session_state.get('selected_config'),
            'config_params': st.session_state.get('config_params', {}),
            'active_tab': st.session_state.get('active_tab')
        })
        return data
        
    def restore_session_state(self, session_data: Dict[str, Any]):
        """Restore agentic config specific session state."""
        super().restore_session_state(session_data)
        st.session_state.selected_config = session_data.get('selected_config')
        st.session_state.config_params = session_data.get('config_params', {})
        st.session_state.active_tab = session_data.get('active_tab')

async def render_agentic_config_view():
    """Render the agentic configuration view."""
    view = AgenticConfigView()
    view.load_session()
    
    try:
        # Initialize controller if needed
        if 'agentic_controller' not in st.session_state:
            print("📦 Creating new agentic controller...")
            persistence_model = PersistenceModelFactory.persistence_model("inmemory")
            controller = AgenticViewController(persistence_model)
            await controller.initialize()
            st.session_state.agentic_controller = controller
            print("✅ Agentic controller initialized")
    
        # Render sidebar first, outside of columns
        await render_agentic_config_sidebar()
        
        # Render header
        render_header(
            "Agentic Configuration",
            "Configure and manage AI agent behaviors and parameters."
        )
        
        # Main content - Chat interface
        st.subheader("Framework Configuration Chat")
        
        # Display chat history
        for msg in st.session_state.agentic_controller.view_state.chat_history:
            with st.chat_message(msg["role"]):
                st.write(msg["content"])
        
        # Chat input
        if prompt := st.chat_input("Type your message..."):
            with st.chat_message("user"):
                st.write(prompt)
            
            await st.session_state.agentic_controller.handle_chat(prompt)
            st.rerun()
        
        # Save session at appropriate points
        view.save_session()
        
    except Exception as e:
        print(f"Error in render_agentic_config_view: {str(e)}")
        st.error("Error initializing view. Check console for details.")

def main():
    """Main entry point for agentic config view."""
    st.set_page_config(page_title="Agentic Configuration", layout="wide")
    asyncio.run(render_agentic_config_view())

if __name__ == "__main__":
    main()
