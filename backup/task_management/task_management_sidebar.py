# src/server/views/components/sidebar/task_management_sidebar.py
import streamlit as st
import asyncio
from typing import Optional, List, Dict, Any, Callable
from uuid import UUID

from ...controllers.task_management_controller import TaskManagementController
from ....models.task import Task
from ....models.tasks_manager import TasksManager

class TaskManagementSidebar:
    """Sidebar component for task management view."""
    
    def __init__(self, controller=None):
        """Initialize the sidebar component."""
        self.controller = controller
        
    async def render(self):
        """Render the sidebar component."""
        st.sidebar.title("Task Management")
        
        # Add navigation links
        st.sidebar.markdown("## Navigation")
        st.sidebar.markdown("[Home](/) | [Task Hierarchy](/task_hierarchy) | [Tools Catalog](/tools_catalog)")
        
        # Add task managers section
        st.sidebar.markdown("## Task Managers")
        
        # Get task managers
        task_managers = []
        if self.controller:
            task_managers = self.controller.get_task_managers()
            
        # Display task managers
        if task_managers:
            for tm in task_managers:
                with st.sidebar.expander(f"📁 {tm.name}", expanded=False):
                    st.markdown(f"**ID:** `{tm.id}`")
                    st.markdown(f"**Model:** {tm.model or 'Not specified'}")
                    st.markdown(f"**Description:** {tm.description or 'No description'}")
                    
                    # Get tasks for this manager
                    tasks = self.controller.get_tasks(tm.id)
                    if tasks:
                        st.markdown("**Tasks:**")
                        for task in tasks:
                            st.markdown(f"- {task.name}")
                    else:
                        st.info("No tasks for this manager.")
        else:
            st.sidebar.info("No task managers found.")
            
        # Add quick actions
        st.sidebar.markdown("## Quick Actions")
        
        # Create new task manager button
        if st.sidebar.button("➕ New Task Manager"):
            st.session_state.task_manager_select = "new"
            st.rerun()
            
        # Create new task button (only if task managers exist)
        if task_managers:
            if st.sidebar.button("➕ New Task"):
                st.session_state.task_select = "new"
                st.rerun()
                
        # Add help section
        with st.sidebar.expander("ℹ️ Help", expanded=False):
            st.markdown("""
            **Task Management View**
            
            This view allows you to manage task managers and tasks:
            
            - **Table View**: View all task managers and tasks in table format
            - **Graph View**: Visualize the relationship between task managers and tasks
            - **Manage Tasks**: Create, edit, and delete task managers and tasks
            
            Task managers define the context for tasks, including model and system message.
            Tasks can inherit context from their manager or define their own.
            """)

async def render_task_management_sidebar():
    """Render the task management sidebar."""
    # Get controller from session state
    controller = None
    if 'task_controller' in st.session_state:
        controller = st.session_state.task_controller
        
    # Create and render sidebar
    sidebar = TaskManagementSidebar(controller)
    await sidebar.render() 