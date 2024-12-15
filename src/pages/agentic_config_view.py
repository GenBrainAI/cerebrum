import streamlit as st
import asyncio
from server.views.controllers.agentic_view_controller import AgenticViewController
from server.persistence.persistence_model_factory import PersistenceModelFactory
from server.views.components.tree_component import TreeComponent
from server.views.components.header import render_header

async def render_agentic_config_view():
    """Render the agentic configuration view."""
    # Initialize controller if needed
    if 'agentic_controller' not in st.session_state:
        persistence_model = PersistenceModelFactory.persistence_model("inmemory")
        st.session_state.agentic_controller = AgenticViewController(persistence_model)
    
    # Initialize tree component if needed
    if 'agent_tree' not in st.session_state:
        st.session_state.agent_tree = TreeComponent(
            on_node_click=st.session_state.agentic_controller.handle_node_click
        )
    
    # Sidebar - Tree Component
    with st.sidebar:
        st.subheader("Agent Configurations")
        tree_data = await st.session_state.agentic_controller.get_agent_tree()
        if tree_data:
            st.session_state.agent_tree.render(tree_data)
    
    # Main content - Chat
    render_header(
        "Agent Configuration",
        "Configure and manage AI agents and their workflows in a centralized interface."
    )
    
    st.subheader("Agent Configuration Chat")
    
    # Display messages
    for msg in st.session_state.agentic_controller.view_state.chat_history:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])
    
    # Chat input
    if prompt := st.chat_input("Type your message..."):
        # Add user message to display
        with st.chat_message("user"):
            st.write(prompt)
        
        # Process message
        await st.session_state.agentic_controller.handle_chat(prompt)
        st.rerun()

def main():
    """Main entry point for agentic configuration view."""
    st.set_page_config(page_title="Agent Configuration", layout="wide")
    asyncio.run(render_agentic_config_view())

if __name__ == "__main__":
    main()
