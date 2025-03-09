# src/server/views/components/sidebar/task_hierarchy_sidebar.py
import streamlit as st
import logging
from ...models.view_state import ViewState
from ...models.view_types import ViewType
from .utils import truncate_tree_node_names

class TaskHierarchySidebar:
    """Sidebar component for task hierarchy view."""
    
    def __init__(self, controller=None):
        self.controller = controller
        self.logger = logging.getLogger(__name__)
    
    async def render(self):
        """Render the task hierarchy sidebar."""
        with st.sidebar:
            st.header("Task Hierarchy")
            
            # Get state status from controller
            if self.controller and self.controller.view_state:
                status = self.controller.view_state.task_status
                if status["loaded"]:
                    st.markdown(f"🟢 **Active Task:** {status['tasksmanager_name']}-{status['task_name']}")
                    st.markdown("**State:** Task Management loaded")
                else:
                    st.markdown("🔴 State loaded but no task context found")
            else:
                st.markdown("🔴 No task state loaded")
            
            st.markdown("---")
            
            # Render task hierarchy as main sidebar content
            st.subheader("Task Structure")
            if self.controller:
                try:
                    # Get task tree data
                    tree_data = await self.controller.get_task_tree()
                    
                    if tree_data and tree_data.children:
                        # Apply smart name truncation
                        truncate_tree_node_names(tree_data)
                        
                        # Set up the tree component's internal state
                        if self.controller.view_state.expanded_nodes:
                            self.controller.tree_component._expanded_nodes = self.controller.view_state.expanded_nodes
                            
                        if self.controller.view_state.selected_node:
                            self.controller.tree_component._selected_nodes = [str(self.controller.view_state.selected_node)]
                        
                        # Render the tree
                        result = self.controller.tree_component.render(
                            tree_data, 
                            key="task_tree_sidebar"
                        )
                        
                        # Process result
                        if result and 'selected' in result:
                            # Update selected and expanded nodes in view state
                            self.controller.view_state.selected_node = result.get("selected")
                            self.controller.view_state.expanded_nodes = result.get("expanded", [])
                            
                            # Handle the node click
                            if result.get("selected"):
                                self.controller.handle_node_click(result.get("selected"))
                    else:
                        st.info("No tasks found. Use the Task Management tab to create task managers and tasks.")
                except Exception as e:
                    self.logger.error(f"Error rendering task tree: {str(e)}")
                    st.error(f"Error rendering tree: {str(e)}")
            else:
                st.info("Controller not initialized")
                
            # Add navigation buttons
            st.markdown("---")
            
            # Quick action buttons
            st.subheader("Quick Actions")
            
            # Create new task manager button
            if st.button("➕ New Task Manager", help="Create a new task manager"):
                st.session_state.active_tab = 2  # Switch to task management tab
                st.session_state.task_manager_select = "new"
                st.rerun()
                
            # Create new task button
            if st.button("➕ New Task", help="Create a new task"):
                st.session_state.active_tab = 2  # Switch to task management tab
                st.session_state.task_select = "new"
                st.rerun()
                
            # Refresh button
            if st.button("🔄 Refresh Tree", help="Refresh task tree"):
                st.rerun()

async def render_task_hierarchy_sidebar():
    """Render the task hierarchy sidebar."""
    # Get controller from session state
    controller = None
    if 'task_controller' in st.session_state:
        controller = st.session_state.task_controller
        
    # Create and render sidebar
    sidebar = TaskHierarchySidebar(controller)
    await sidebar.render()