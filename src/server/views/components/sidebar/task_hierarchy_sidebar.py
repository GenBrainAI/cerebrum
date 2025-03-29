# src/server/views/components/sidebar/task_hierarchy_sidebar.py
import streamlit as st
import logging
import time
from ...models.view_state import ViewState
from ...models.view_types import ViewType
from .utils import truncate_tree_node_names

class TaskHierarchySidebar:
    """Sidebar component for task hierarchy view."""
    
    def __init__(self, controller=None):
        self.controller = controller
        self.logger = logging.getLogger(__name__)
        
        # Log controller initialization
        if controller:
            print(f"🔧 TaskHierarchySidebar initialized with controller")
            if hasattr(controller, 'view_state'):
                print(f"🔧 Controller has view_state with task_status: {controller.view_state.task_status}")
            else:
                print(f"🔧 Controller does not have view_state")
        else:
            print(f"🔧 TaskHierarchySidebar initialized without controller")
        
        # Initialize save status if not set
        if 'save_status' not in st.session_state:
            st.session_state.save_status = None
            self.logger.info("Initialized save_status to None")
        if 'last_save_time' not in st.session_state:
            st.session_state.last_save_time = None
            self.logger.info("Initialized last_save_time to None")
        
        # Log current save status for debugging
        if hasattr(st.session_state, 'save_status'):
            self.logger.info(f"Current save_status: {st.session_state.save_status}")
        if hasattr(st.session_state, 'last_save_time'):
            self.logger.info(f"Current last_save_time: {st.session_state.last_save_time}")
    
    async def render(self):
        """Render the task hierarchy sidebar."""
        with st.sidebar:
            st.header("Task Hierarchy")
            
            # Add reset button for chat history
            col1, col2 = st.columns([0.1, 0.9])
            with col1:
                if st.button("🔄", help="Reset chat history", key="reset_task_chat_history"):
                    # Get the view and clear session
                    from src.pages.task_hierarchy_view import TaskHierarchyView
                    view = TaskHierarchyView()
                    view.clear_session()
                    st.rerun()
            
            # Get state status from controller
            if self.controller and self.controller.view_state:
                # Ensure controller is using the correct persistence model based on active tab
                if hasattr(self.controller, 'global_persistence') and hasattr(self.controller, 'persistence_model'):
                    # For non-chat views (task tree, management), always use global persistence
                    active_tab = st.session_state.get('active_tab', 0)
                    if active_tab != 0:  # Not in chat view
                        if self.controller.persistence_model is not self.controller.global_persistence:
                            print("🔧 Switching controller to global persistence in sidebar for non-chat view")
                            self.controller.persistence_model = self.controller.global_persistence
                
                status = self.controller.view_state.task_status
                
                # Fix: Ensure task_status is properly set if it's not already
                if not status.get("loaded", False):
                    # For chat view (tab 0), prefer specialized state task if available
                    active_tab = st.session_state.get('active_tab', 0)
                    if active_tab == 0 and hasattr(self.controller, 'local_persistence') and self.controller.local_persistence:
                        print(f"🔧 Setting active task from specialized state in sidebar for chat view")
                        # Get tasks from specialized state
                        local_task_managers = self.controller.local_persistence.tasksmanagers.list()
                        if local_task_managers:
                            local_task_manager = next(
                                (m for m in local_task_managers if "Task Management" in m.name),
                                local_task_managers[0]
                            )
                            local_tasks = self.controller.local_persistence.tasks.list()
                            local_task = next(
                                (t for t in local_tasks if t.tasksmanager_id == local_task_manager.id),
                                None
                            )
                            if local_task:
                                print(f"🔧 Found specialized task in sidebar: {local_task.name} for chat functionality")
                                self.controller.view_state.set_active_task(
                                    task_id=local_task.id,
                                    task_name=local_task.name,
                                    manager_id=local_task_manager.id,
                                    manager_name=local_task_manager.name
                                )
                                # Update status with the new values
                                status = self.controller.view_state.task_status
                                print(f"🔧 Updated task status in sidebar with specialized task: {status}")
                    else:
                        # For non-chat views, always use global state tasks
                        task_managers = self.controller.get_task_managers()
                        if task_managers:
                            tasks = self.controller.get_tasks(task_managers[0].id)
                            if tasks:
                                print(f"🔧 Setting active task from global state in sidebar")
                                self.controller.view_state.set_active_task(
                                    task_id=tasks[0].id,
                                    task_name=tasks[0].name,
                                    manager_id=task_managers[0].id,
                                    manager_name=task_managers[0].name
                                )
                                # Update status with the new values
                                status = self.controller.view_state.task_status
                                print(f"🔧 Updated task status in sidebar with global task: {status}")
                
                # Log task status for debugging
                print(f"🔍 Task status in sidebar: {status}")
                self.logger.info(f"Task status in sidebar: {status}")
                
                # Show state status with save indicator
                col1, col2 = st.columns([3, 1])
                with col1:
                    print(f"🔍 Checking loaded status: {status.get('loaded', False)}")
                    if status.get("loaded", False):
                        tasksmanager_name = status.get("tasksmanager_name", "Unknown")
                        task_name = status.get("task_name", "Unknown")
                        print(f"🔍 Displaying active task: {tasksmanager_name}-{task_name}")
                        
                        # Indicate if this is a specialized state task (for chat) or global state task
                        active_tab = st.session_state.get('active_tab', 0)
                        if active_tab == 0 and hasattr(self.controller, 'local_persistence') and self.controller.local_persistence:
                            # Check if this task is from specialized state
                            task_id = status.get("task_id")
                            try:
                                # Try to find this task in specialized state
                                specialized_task = self.controller.local_persistence.tasks.read(task_id)
                                if specialized_task:
                                    st.markdown(f"🟢 **Active Task:** {tasksmanager_name}-{task_name}")
                                    st.markdown("**State:** Specialized Task Management")
                                else:
                                    st.markdown(f"🟢 **Active Task:** {tasksmanager_name}-{task_name}")
                                    st.markdown("**State:** Global Task Management")
                            except:
                                st.markdown(f"🟢 **Active Task:** {tasksmanager_name}-{task_name}")
                                st.markdown("**State:** Global Task Management")
                        else:
                            st.markdown(f"🟢 **Active Task:** {tasksmanager_name}-{task_name}")
                            st.markdown("**State:** Global Task Management")
                    else:
                        print("🔍 No task context found, displaying error message")
                        st.markdown("🔴 State loaded but no task context found")
                with col2:
                    # Log save status for debugging
                    print(f"🔍 Save status: {st.session_state.save_status}")
                    self.logger.info(f"Rendering save status: {st.session_state.save_status}")
                    
                    if st.session_state.save_status == "pending":
                        st.markdown("💾 *Saving...*")
                        self.logger.info("Displaying 'Saving...' indicator")
                    elif st.session_state.save_status == "saved" and st.session_state.last_save_time:
                        time_diff = time.time() - st.session_state.last_save_time
                        if time_diff < 5:  # Show saved status for 5 seconds
                            st.markdown("✅ *Saved*")
                            self.logger.info(f"Displaying 'Saved' indicator (time diff: {time_diff}s)")
                        else:
                            st.session_state.save_status = None
                            self.logger.info(f"Cleared save status after {time_diff}s")
            else:
                print("🔍 No controller or view state available")
                st.markdown("🔴 No task state loaded")
            
            st.markdown("---")
            
            # Render task hierarchy as main sidebar content
            st.subheader("Task Structure")
            if self.controller:
                try:
                    # Always use global persistence for task tree
                    if hasattr(self.controller, 'global_persistence') and hasattr(self.controller, 'persistence_model'):
                        original_persistence = self.controller.persistence_model
                        self.controller.persistence_model = self.controller.global_persistence
                    
                    # Get task tree data
                    tree_data = await self.controller.get_task_tree()
                    
                    # Restore original persistence if needed
                    if hasattr(self.controller, 'global_persistence') and 'original_persistence' in locals():
                        self.controller.persistence_model = original_persistence
                    
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
                # Ensure we're using global persistence for task management
                if hasattr(self.controller, 'global_persistence'):
                    self.controller.persistence_model = self.controller.global_persistence
                
                st.session_state.active_tab = 2  # Switch to task management tab
                st.session_state.task_manager_select = "new"
                st.rerun()
                
            # Create new task button
            if st.button("➕ New Task", help="Create a new task"):
                # Ensure we're using global persistence for task management
                if hasattr(self.controller, 'global_persistence'):
                    self.controller.persistence_model = self.controller.global_persistence
                
                st.session_state.active_tab = 2  # Switch to task management tab
                st.session_state.task_select = "new"
                st.rerun()

async def render_task_hierarchy_sidebar():
    """Render the task hierarchy sidebar."""
    # Get controller from session state
    controller = None
    if 'task_controller' in st.session_state:
        controller = st.session_state.task_controller
        print(f"🔧 Got controller from session state")
        if hasattr(controller, 'view_state'):
            print(f"🔧 Controller has view_state with task_status: {controller.view_state.task_status}")
        else:
            print(f"🔧 Controller does not have view_state")
    else:
        print(f"🔧 No controller in session state")
        
    # Create and render sidebar
    sidebar = TaskHierarchySidebar(controller)
    await sidebar.render()