import streamlit as st
import asyncio
from server.views.controllers.tools_view_controller import ToolsCatalogController
from server.persistence.persistence_model_factory import PersistenceModelFactory
from server.views.components.tree_component import TreeComponent
from server.views.components.header import render_header
from server.views.components.sidebar.tools_catalog_sidebar import render_tools_catalog_sidebar

async def render_tools_catalog_view():
    """Render the tools catalog view."""
    try:
        # Initialize controller if needed
        if 'tools_controller' not in st.session_state:
            print("Initializing tools controller...")
            persistence_model = PersistenceModelFactory.persistence_model("inmemory")
            controller = ToolsCatalogController(persistence_model)
            await controller.initialize()
            st.session_state.tools_controller = controller
        
        # Render header
        render_header(
            "Tools Catalog Management",
            "Manage and configure tools and integrations with chat-based interface."
        )
        
        # Render sidebar showing state context and tools catalog
        await render_tools_catalog_sidebar()
        
        # Main content - Chat interface only
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
        
    except Exception as e:
        print(f"Error in render_tools_catalog_view: {str(e)}")
        st.error("Error initializing view. Check console for details.")

def main():
    st.set_page_config(page_title="Tools Catalog", layout="wide")
    asyncio.run(render_tools_catalog_view())

if __name__ == "__main__":
    main()
