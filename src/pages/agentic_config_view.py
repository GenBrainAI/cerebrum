import streamlit as st
import asyncio
from server.views.controllers.agentic_view_controller import AgenticViewController
from server.persistence.persistence_model_factory import PersistenceModelFactory
from server.views.components.header import render_header
from server.views.components.sidebar.agentic_config_sidebar import render_agentic_config_sidebar
from server.views.base_view import BaseView
from server.views.models.view_types import ViewType
from typing import Dict, Any
from server.models.message import Message

class AgenticConfigView(BaseView):
    def __init__(self):
        super().__init__(ViewType.AGENTIC_CONFIG)
    
    def get_session_data(self) -> Dict[str, Any]:
        """Get agentic config specific session data."""
        data = super().get_session_data()
        
        if 'agentic_controller' in st.session_state:
            chat_history = st.session_state.agentic_controller.view_state.chat_history
            print(f"\n📝 Saving chat history:")
            print(f"  Length: {len(chat_history)}")
            print(f"  Content: {chat_history}")
        
        data.update({
            'chat_history': st.session_state.agentic_controller.view_state.chat_history
            if 'agentic_controller' in st.session_state else []
        })
        return data
        
    def restore_session_state(self, session_data: Dict[str, Any]):
        """Restore agentic config specific session state."""
        super().restore_session_state(session_data)
        
        chat_history = session_data.get('chat_history', [])
        print(f"\n📖 Restoring chat history:")
        print(f"  Length: {len(chat_history)}")
        
        if 'agentic_controller' in st.session_state:
            st.session_state.agentic_controller.view_state.chat_history = chat_history
            
    def clear_session(self):
        """Clear the agentic config session data."""
        if 'agentic_controller' in st.session_state:
            # Clear chat history
            st.session_state.agentic_controller.view_state.chat_history = []
            
            # Save empty session
            self.save_session()
            
            print("\n🗑️ Cleared agentic config session")

async def render_agentic_config_view():
    """Render the agentic configuration view."""
    view = AgenticConfigView()
    view.load_session()
    
    try:
        # Initialize controller if needed
        if 'agentic_controller' not in st.session_state:
            print("Initializing agentic controller...")
            persistence_model = PersistenceModelFactory.persistence_model("inmemory")
            controller = AgenticViewController(persistence_model)
            await controller.initialize()
            st.session_state.agentic_controller = controller
            
        # Add clear session icon in sidebar
        with st.sidebar:
            col1, col2 = st.columns([0.1, 0.9])
            with col1:
                if st.empty().button("🔄", help="Clear chat history", key="clear_chat_icon"):
                    view.clear_session()
                    st.rerun()
    
        # Render sidebar
        await render_agentic_config_sidebar()
        
        # Render header
        render_header(
            "Agentic Framework Configuration",
            "Configure and manage agentic frameworks with integrated chat interface."
        )
        
        st.subheader("Agentic Configuration Chat")
        
        # Display messages
        for msg in st.session_state.agentic_controller.view_state.chat_history:
            if isinstance(msg, Message):
                role = msg.role
                content = msg.content
            elif isinstance(msg, dict):
                role = msg["role"]
                content = msg["content"]
            else:
                role = getattr(msg, 'role', 'user')
                content = str(msg)
            
            with st.chat_message(role):
                st.write(content)
        
        # Chat input
        if prompt := st.chat_input("Type your message..."):
            with st.chat_message("user"):
                st.write(prompt)
            
            await st.session_state.agentic_controller.handle_chat(prompt)
            st.rerun()
        
    except Exception as e:
        print(f"Error in render_agentic_config_view: {str(e)}")
        st.error("Error initializing view. Check console for details.")

def main():
    """Main entry point for agentic config view."""
    st.set_page_config(page_title="Agentic Configuration", layout="wide")
    asyncio.run(render_agentic_config_view())

if __name__ == "__main__":
    main()
