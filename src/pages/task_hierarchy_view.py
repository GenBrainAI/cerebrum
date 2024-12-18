# src/pages/task_hierarchy_view.py
import streamlit as st
import asyncio
from server.views.controllers.task_view_controller import TaskHierarchyController
from server.persistence.persistence_model_factory import PersistenceModelFactory
from server.views.components.tree_component import TreeComponent
from server.views.components.header import render_header
from server.views.components.sidebar.task_hierarchy_sidebar import render_task_hierarchy_sidebar

async def render_task_hierarchy_view():
    """Render the task hierarchy view."""
    # Initialize controller if needed
    if 'task_controller' not in st.session_state:
        print("Initializing task controller...")
        persistence_model = PersistenceModelFactory.persistence_model("inmemory")
        controller = TaskHierarchyController(persistence_model)
        await controller.initialize()
        st.session_state.task_controller = controller
    
    # Render sidebar showing state context and tasks
    await render_task_hierarchy_sidebar()
    
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
        with st.chat_message("user"):
            st.write(prompt)
        
        await st.session_state.task_controller.handle_chat(prompt)
        st.rerun()

def main():
    """Main entry point for task hierarchy view."""
    st.set_page_config(page_title="Task Hierarchy", layout="wide")
    asyncio.run(render_task_hierarchy_view())

if __name__ == "__main__":
    main()