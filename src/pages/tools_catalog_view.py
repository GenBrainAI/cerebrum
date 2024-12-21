import streamlit as st
import asyncio
from server.views.controllers.tools_view_controller import ToolsCatalogController
from server.persistence.persistence_model_factory import PersistenceModelFactory
from server.views.components.header import render_header
from server.views.components.sidebar.tools_catalog_sidebar import render_tools_catalog_sidebar
from server.views.base_view import BaseView
from server.views.models.view_types import ViewType
from typing import Dict, Any
from server.models.message import Message

class ToolsCatalogView(BaseView):
    def __init__(self):
        super().__init__(ViewType.TOOLS_CATALOG)
    
    def get_session_data(self) -> Dict[str, Any]:
        """Get tools catalog specific session data."""
        data = super().get_session_data()
        
        if 'tools_controller' in st.session_state:
            chat_history = st.session_state.tools_controller.view_state.chat_history
            print(f"\n📝 Saving chat history:")
            print(f"  Length: {len(chat_history)}")
            print(f"  Content: {chat_history}")
        
        data.update({
            'chat_history': st.session_state.tools_controller.view_state.chat_history
            if 'tools_controller' in st.session_state else []
        })
        return data
        
    def restore_session_state(self, session_data: Dict[str, Any]):
        """Restore tools catalog specific session state."""
        super().restore_session_state(session_data)
        
        chat_history = session_data.get('chat_history', [])
        print(f"\n📖 Restoring chat history:")
        print(f"  Length: {len(chat_history)}")
        
        if 'tools_controller' in st.session_state:
            st.session_state.tools_controller.view_state.chat_history = chat_history
            
    def clear_session(self):
        """Clear the tools catalog session data."""
        if 'tools_controller' in st.session_state:
            # Clear chat history
            st.session_state.tools_controller.view_state.chat_history = []
            
            # Save empty session
            self.save_session()
            
            print("\n🗑️ Cleared tools catalog session")

async def render_tools_catalog_view():
    """Render the tools catalog view."""
    view = ToolsCatalogView()
    view.load_session()
    
    try:
        # Initialize controller if needed
        if 'tools_controller' not in st.session_state:
            print("Initializing tools controller...")
            persistence_model = PersistenceModelFactory.persistence_model("inmemory")
            controller = ToolsCatalogController(persistence_model)
            await controller.initialize()
            st.session_state.tools_controller = controller
            
        # Add clear session icon in sidebar
        with st.sidebar:
            col1, col2 = st.columns([0.1, 0.9])
            with col1:
                if st.empty().button("🔄", help="Clear chat history", key="clear_chat_icon"):
                    view.clear_session()
                    st.rerun()
    
        # Render sidebar
        await render_tools_catalog_sidebar()
        
        # Render header
        render_header(
            "Tools Catalog",
            "Browse and manage available tools with integrated chat interface."
        )
        
        st.subheader("Tools Management Chat")
        
        # Display messages
        for msg in st.session_state.tools_controller.view_state.chat_history:
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
            
            await st.session_state.tools_controller.handle_chat(prompt)
            st.rerun()
        
    except Exception as e:
        print(f"Error in render_tools_catalog_view: {str(e)}")
        st.error("Error initializing view. Check console for details.")

def main():
    """Main entry point for tools catalog view."""
    st.set_page_config(page_title="Tools Catalog", layout="wide")
    asyncio.run(render_tools_catalog_view())

if __name__ == "__main__":
    main()
