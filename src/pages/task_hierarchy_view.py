# src/pages/task_hierarchy_view.py
import streamlit as st
import asyncio
from server.views.controllers.task_view_controller import TaskHierarchyController
from server.persistence.persistence_model_factory import PersistenceModelFactory
from server.views.components.tree_component import TreeComponent
from server.views.components.header import render_header
from server.views.components.sidebar.task_hierarchy_sidebar import render_task_hierarchy_sidebar
from server.views.base_view import BaseView
from server.views.models.view_types import ViewType
from typing import Dict, Any
from server.models.message import Message

class TaskHierarchyView(BaseView):
    def __init__(self):
        super().__init__(ViewType.TASK_HIERARCHY)
    
    def get_session_data(self) -> Dict[str, Any]:
        """Get task hierarchy specific session data."""
        data = super().get_session_data()
        
        # Debug chat history
        if 'task_controller' in st.session_state:
            chat_history = st.session_state.task_controller.view_state.chat_history
            print(f"\n📝 Saving chat history:")
            print(f"  Length: {len(chat_history)}")
            print(f"  Content: {chat_history}")
        else:
            print("\n⚠️ No task controller in session state")
        
        # Add view-specific data
        data.update({
            'selected_task': st.session_state.get('selected_task'),
            'expanded_nodes': st.session_state.get('expanded_nodes', []),
            'chat_history': st.session_state.task_controller.view_state.chat_history
        })
        return data
        
    def restore_session_state(self, session_data: Dict[str, Any]):
        """Restore task hierarchy specific session state."""
        super().restore_session_state(session_data)
        st.session_state.selected_task = session_data.get('selected_task')
        st.session_state.expanded_nodes = session_data.get('expanded_nodes', [])
        
        # Debug restored chat history
        chat_history = session_data.get('chat_history', [])
        print(f"\n📖 Restoring chat history:")
        print(f"  Length: {len(chat_history)}")
        print(f"  Content: {chat_history}")
        
        if 'task_controller' in st.session_state:
            st.session_state.task_controller.view_state.chat_history = chat_history

async def render_task_hierarchy_view():
    """Render the task hierarchy view."""
    view = TaskHierarchyView()
    view.load_session()
    
    try:
        # Initialize controller if needed
        if 'task_controller' not in st.session_state:
            print("Initializing task controller...")
            persistence_model = PersistenceModelFactory.persistence_model("inmemory")
            controller = TaskHierarchyController(persistence_model)
            await controller.initialize()
            st.session_state.task_controller = controller
    
        # Render sidebar first, outside of columns
        await render_task_hierarchy_sidebar()
        
        # Render header
        render_header(
            "Task Hierarchy Management",
            "Manage and organize tasks in a hierarchical structure with integrated chat interface."
        )
        
        st.subheader("Task Management Chat")
        
        # Display messages - handle both Message objects and dicts
        for msg in st.session_state.task_controller.view_state.chat_history:
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
            
            await st.session_state.task_controller.handle_chat(prompt)
            st.rerun()
        
    except Exception as e:
        print(f"Error in render_task_hierarchy_view: {str(e)}")
        st.error("Error initializing view. Check console for details.")

def main():
    """Main entry point for task hierarchy view."""
    st.set_page_config(page_title="Task Hierarchy", layout="wide")
    asyncio.run(render_task_hierarchy_view())

if __name__ == "__main__":
    main()