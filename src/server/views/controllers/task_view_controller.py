from typing import Dict, Any, Optional
import streamlit as st
import logging
from datetime import datetime
from ...controllers.tasks_tree_controller import TaskTreeManager, ExecutionStrategy
from ...controllers.task_tree_state_manager import TaskTreeStateManager
from ..components.task_tree_visualizer import TaskTreeVisualizer

class TaskHierarchyController:
    """Enhanced controller with visualization and state management."""
    
    def __init__(self, persistence_model):
        self.global_persistence = persistence_model
        self.logger = logging.getLogger(__name__)
        self.tree_visualizer = TaskTreeVisualizer()
        self.tree_state_manager = TaskTreeStateManager()
        self.task_tree_manager = TaskTreeManager()
        self._task_tree_loaded = False

    async def initialize(self):
        """Initialize the controller and load task tree."""
        try:
            # Initialize task tree from existing tasks
            tasks = self.global_persistence.tasks.list()
            for task in tasks:
                node = self.task_tree_manager.create_node(task)
                if not task.parent_id:
                    self.task_tree_manager.set_as_root(task.id)

            # Try to load saved state
            if not self._task_tree_loaded:
                saved_state = await self.tree_state_manager.load_tree_state(
                    self.task_tree_manager.root_nodes[0].task.id if self.task_tree_manager.root_nodes else None
                )
                if saved_state:
                    self.task_tree_manager.restore_state(saved_state)
                self._task_tree_loaded = True

        except Exception as e:
            self.logger.error(f"Error initializing task hierarchy: {str(e)}")
            raise

    async def render_task_tree(self):
        """Render the task tree visualization and controls."""
        try:
            # Ensure initialization
            if not self._task_tree_loaded:
                await self.initialize()

            # Main content area
            st.title("Task Tree Management")
            
            # Render tree visualization
            self.tree_visualizer.render_tree(self.task_tree_manager)
            
            # Sidebar controls
            st.sidebar.title("Task Tree Controls")
            
            # State management section
            st.sidebar.subheader("State Management")
            
            if st.sidebar.button("Save Current State"):
                tree_id = self.task_tree_manager.root_nodes[0].task.id if self.task_tree_manager.root_nodes else "default"
                if await self.tree_state_manager.save_tree_state(tree_id, self.task_tree_manager):
                    st.sidebar.success("Tree state saved successfully")
                else:
                    st.sidebar.error("Failed to save tree state")
            
            # List and load saved states
            saved_trees = await self.tree_state_manager.list_saved_trees()
            if saved_trees:
                selected_tree = st.sidebar.selectbox(
                    "Load Saved State",
                    options=[tree['tree_id'] for tree in saved_trees],
                    format_func=lambda x: f"{x} (Saved: {next(t['saved_at'] for t in saved_trees if t['tree_id'] == x)})"
                )
                
                if st.sidebar.button("Load Selected State"):
                    state_data = await self.tree_state_manager.load_tree_state(selected_tree)
                    if state_data:
                        self.task_tree_manager.restore_state(state_data)
                        st.sidebar.success("Tree state loaded successfully")
                        st.rerun()
                    else:
                        st.sidebar.error("Failed to load tree state")

                if st.sidebar.button("Delete Selected State"):
                    if await self.tree_state_manager.delete_tree_state(selected_tree):
                        st.sidebar.success("State deleted successfully")
                        st.rerun()
                    else:
                        st.sidebar.error("Failed to delete state")

            # Execution controls
            st.sidebar.subheader("Execution Controls")
            self.tree_visualizer.render_tree_controls(self.task_tree_manager)

            # Task details section
            st.subheader("Task Details")
            selected_task = st.selectbox(
                "Select Task",
                options=[node.task.id for node in self.task_tree_manager.nodes.values()],
                format_func=lambda x: self.task_tree_manager.nodes[x].task.name
            )
            
            if selected_task:
                self.tree_visualizer.render_task_details(self.task_tree_manager.nodes[selected_task])

        except Exception as e:
            self.logger.error(f"Error rendering task tree: {str(e)}")
            st.error(f"Error rendering task tree: {str(e)}")

    async def handle_task_execution(self, task_id: str):
        """Handle task execution with progress tracking."""
        try:
            node = self.task_tree_manager.nodes.get(task_id)
            if not node:
                st.error(f"Task {task_id} not found")
                return

            # Create progress bar
            progress_bar = st.progress(0)
            status_text = st.empty()

            # Execute task with progress updates
            async def progress_callback(current: int, total: int, message: str):
                progress = float(current) / total if total > 0 else 0
                progress_bar.progress(progress)
                status_text.text(message)

            result = await self.task_tree_manager.execute_group(
                "execution",
                [task_id],
                context={"progress_callback": progress_callback}
            )

            # Update progress bar and status
            progress_bar.progress(1.0)
            if result["errors"]:
                status_text.error("Execution completed with errors")
            else:
                status_text.success("Execution completed successfully")

            # Save state after execution
            await self.tree_state_manager.save_tree_state(
                self.task_tree_manager.root_nodes[0].task.id,
                self.task_tree_manager
            )

            return result

        except Exception as e:
            self.logger.error(f"Error executing task: {str(e)}")
            st.error(f"Error executing task: {str(e)}")
            return None

    async def cleanup_old_states(self):
        """Clean up old state files."""
        try:
            days = st.sidebar.number_input(
                "Delete states older than (days)",
                min_value=1,
                max_value=365,
                value=30
            )
            
            if st.sidebar.button("Clean Up Old States"):
                deleted_count = await self.tree_state_manager.cleanup_old_states(days)
                if deleted_count > 0:
                    st.sidebar.success(f"Deleted {deleted_count} old state files")
                else:
                    st.sidebar.info("No old states to clean up")

        except Exception as e:
            self.logger.error(f"Error cleaning up states: {str(e)}")
            st.sidebar.error(f"Error cleaning up states: {str(e)}")
