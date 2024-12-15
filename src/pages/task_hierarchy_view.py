# src/pages/task_hierarchy_view.py
import streamlit as st
import asyncio
from server.views.controllers.task_view_controller import TaskHierarchyController
from server.persistence.persistence_model_factory import PersistenceModelFactory
from server.views.components.tree_component import TreeComponent
from server.views.components.header import render_header

async def render_task_hierarchy_view():
    """Render the task hierarchy view."""
    # Initialize controller if needed
    if 'task_controller' not in st.session_state:
        persistence_model = PersistenceModelFactory.persistence_model("inmemory")
        st.session_state.task_controller = TaskHierarchyController(persistence_model)
    
    # Initialize tree component if needed
    if 'task_tree' not in st.session_state:
        st.session_state.task_tree = TreeComponent(
            on_node_click=st.session_state.task_controller.handle_node_click
        )
    
    # Sidebar - Tree Component
    with st.sidebar:
        st.subheader("Task Hierarchy")
        tree_data = await st.session_state.task_controller.get_task_tree()
        if tree_data:
            st.session_state.task_tree.render(tree_data)
    
    # Main content - Chat
    render_header(
        "Task Hierarchy Management",
        "Manage and organize tasks in a hierarchical structure with integrated chat interface."
    )
    
    st.subheader("Task Management Chat")
    
    # Display messages
    for msg in st.session_state.task_controller.view_state.chat_history:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])
    
    # Chat input
    if prompt := st.chat_input("Type your message..."):
        # Add user message to display
        with st.chat_message("user"):
            st.write(prompt)
        
        # Process message
        await st.session_state.task_controller.handle_chat(prompt)
        st.rerun()

def main():
    """Main entry point for task hierarchy view."""
    st.set_page_config(page_title="Task Hierarchy", layout="wide")
    asyncio.run(render_task_hierarchy_view())

if __name__ == "__main__":
    main()