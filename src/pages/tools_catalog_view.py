import streamlit as st
import asyncio
from server.views.controllers.tools_view_controller import ToolsCatalogController
from server.persistence.persistence_model_factory import PersistenceModelFactory
from server.views.components.tree_component import TreeComponent
from server.views.components.header import render_header

async def render_tools_catalog_view():
    """Render the tools catalog view."""
    # Initialize controller if needed
    if 'tools_controller' not in st.session_state:
        persistence_model = PersistenceModelFactory.persistence_model("inmemory")
        st.session_state.tools_controller = ToolsCatalogController(persistence_model)
    
    # Initialize tree component if needed
    if 'tools_tree' not in st.session_state:
        st.session_state.tools_tree = TreeComponent(
            on_node_click=st.session_state.tools_controller.handle_node_click
        )
    
    # Sidebar - Tree Component
    with st.sidebar:
        st.subheader("Tools Catalog")
        tree_data = await st.session_state.tools_controller.get_tools_tree()
        if tree_data:
            st.session_state.tools_tree.render(tree_data)
    
    # Main content - Chat
    render_header(
        "Tools Catalog Management",
        "Manage and configure tools and integrations with chat-based interface."
    )
    
    st.subheader("Tools Management Chat")
    
    # Display messages
    for msg in st.session_state.tools_controller.view_state.chat_history:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])
    
    # Chat input
    if prompt := st.chat_input("Type your message..."):
        # Add user message to display
        with st.chat_message("user"):
            st.write(prompt)
        
        # Process message
        await st.session_state.tools_controller.handle_chat(prompt)
        st.rerun()

def main():
    """Main entry point for tools catalog view."""
    st.set_page_config(page_title="Tools Catalog", layout="wide")
    asyncio.run(render_tools_catalog_view())

if __name__ == "__main__":
    main()
