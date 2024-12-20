import streamlit as st
import asyncio
from server.views.base_view import BaseView
from server.views.models.view_types import ViewType
from server.views.components.header import render_header
from server.views.components.sidebar.tools_catalog_sidebar import render_tools_catalog_sidebar
from server.views.controllers.tools_view_controller import ToolsCatalogController
from server.persistence.persistence_model_factory import PersistenceModelFactory
from typing import Dict, Any

class ToolsCatalogView(BaseView):
    def __init__(self):
        super().__init__(ViewType.TOOLS_CATALOG)
    
    def get_session_data(self) -> Dict[str, Any]:
        """Get tools catalog specific session data."""
        data = super().get_session_data()
        # Add view-specific data
        data.update({
            'selected_tool': st.session_state.get('selected_tool'),
            'tool_filters': st.session_state.get('tool_filters', {}),
            'search_query': st.session_state.get('search_query', ''),
            'category_filters': st.session_state.get('category_filters', [])
        })
        return data
        
    def restore_session_state(self, session_data: Dict[str, Any]):
        """Restore tools catalog specific session state."""
        super().restore_session_state(session_data)
        st.session_state.selected_tool = session_data.get('selected_tool')
        st.session_state.tool_filters = session_data.get('tool_filters', {})
        st.session_state.search_query = session_data.get('search_query', '')
        st.session_state.category_filters = session_data.get('category_filters', [])

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
    
        # Render sidebar first, outside of columns
        await render_tools_catalog_sidebar()
        
        # Render header
        render_header(
            "Tools Catalog",
            "Browse and manage available tools and their configurations."
        )
        
        # Main content - Chat interface
        st.subheader("Tools Management Chat")
        
        # Display chat history
        for msg in st.session_state.tools_controller.view_state.chat_history:
            with st.chat_message(msg["role"]):
                st.write(msg["content"])
        
        # Chat input
        if prompt := st.chat_input("Type your message..."):
            with st.chat_message("user"):
                st.write(prompt)
            
            await st.session_state.tools_controller.handle_chat(prompt)
            st.rerun()
        
        # Save session at appropriate points
        view.save_session()
        
    except Exception as e:
        print(f"Error in render_tools_catalog_view: {str(e)}")
        st.error("Error initializing view. Check console for details.")

def main():
    """Main entry point for tools catalog view."""
    st.set_page_config(page_title="Tools Catalog", layout="wide")
    asyncio.run(render_tools_catalog_view())

if __name__ == "__main__":
    main()
