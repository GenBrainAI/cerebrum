import streamlit as st
from typing import List, Dict, Any, Optional
import asyncio
import time
from datetime import datetime
from ..utils.async_utils import run_async_sync

class TaskSequenceComponent:
    """Component for managing task sequences."""
    
    def __init__(self, controller):
        """Initialize the component."""
        self.controller = controller
    
    def render(self, tasksmanager_id: str):
        """Render the task sequence management component."""
        st.subheader("Task Sequences")
        
        # Get all tasks for this task manager
        tasks = self.controller.get_tasks_for_tasksmanager(tasksmanager_id)
        if not tasks:
            st.info("No tasks available for creating sequences.")
            return
        
        # Get existing sequences
        try:
            # Use the synchronous wrapper to get sequences
            sequences = run_async_sync(self.controller.get_task_sequences(tasksmanager_id))
        except Exception as e:
            st.error(f"Error loading sequences: {str(e)}")
            sequences = []
        
        # Two tabs: View Sequences and Create Sequence
        view_tab, create_tab = st.tabs(["View Sequences", "Create Sequence"])
        
        with view_tab:
            self._render_sequences_list(tasksmanager_id, sequences, tasks)
        
        with create_tab:
            self._render_create_sequence_form(tasksmanager_id, tasks)
    
    def _render_sequences_list(self, tasksmanager_id: str, sequences: List[Dict[str, Any]], tasks: List[Any]):
        """Render the list of existing sequences."""
        if not sequences:
            st.info("No sequences defined yet. Create one using the 'Create Sequence' tab.")
            return
        
        # Create a task ID to name mapping for display
        task_id_to_name = {task.id: task.name for task in tasks}
        
        # Display each sequence
        for seq in sequences:
            with st.expander(f"{seq['name']} ({seq['task_count']} tasks)", expanded=False):
                st.write(f"**Description:** {seq['description']}")
                
                # Show tasks in sequence
                st.write("**Tasks (in order):**")
                for i, task_id in enumerate(seq['task_ids']):
                    task_name = task_id_to_name.get(task_id, f"Unknown Task ({task_id})")
                    st.write(f"{i+1}. {task_name}")
                
                # Action buttons
                col1, col2, col3 = st.columns([1, 1, 1])
                
                with col1:
                    if st.button("Run Sequence", key=f"run_seq_{seq['id']}"):
                        with st.spinner("Running sequence..."):
                            try:
                                # Check if we have messages in session_state to pass as context
                                initial_context = None
                                if hasattr(st, "session_state") and hasattr(st.session_state, "messages"):
                                    initial_context = {
                                        'messages': st.session_state.messages
                                    }
                                    
                                # Run the sequence using the synchronous wrapper
                                result = run_async_sync(
                                    self.controller.run_task_sequence_by_id(
                                        tasksmanager_id, 
                                        seq['id'],
                                        initial_context=initial_context
                                    )
                                )
                                
                                # Show results
                                st.success("Sequence executed successfully!")
                                
                                # Show execution status
                                status = result.get("execution_status", {})
                                if status:
                                    st.json(status)
                            except Exception as e:
                                st.error(f"Error running sequence: {str(e)}")
                
                with col2:
                    if st.button("Edit", key=f"edit_seq_{seq['id']}"):
                        # Set session state for editing
                        st.session_state[f"edit_sequence_{seq['id']}"] = True
                
                with col3:
                    if st.button("Delete", key=f"delete_seq_{seq['id']}"):
                        try:
                            # Delete the sequence using the synchronous wrapper
                            success = run_async_sync(
                                self.controller.delete_task_sequence(tasksmanager_id, seq['id'])
                            )
                            
                            if success:
                                st.success("Sequence deleted!")
                                time.sleep(1)
                                st.rerun()
                            else:
                                st.error("Failed to delete sequence.")
                        except Exception as e:
                            st.error(f"Error deleting sequence: {str(e)}")
                
                # Edit form (shown when edit button is clicked)
                if st.session_state.get(f"edit_sequence_{seq['id']}", False):
                    st.write("### Edit Sequence")
                    
                    # Edit form
                    name = st.text_input("Name", value=seq['name'], key=f"edit_name_{seq['id']}")
                    description = st.text_area("Description", value=seq['description'], key=f"edit_desc_{seq['id']}")
                    
                    # Task selection
                    selected_tasks = st.multiselect(
                        "Select Tasks (in execution order)",
                        options=[task.id for task in tasks],
                        default=seq['task_ids'],
                        format_func=lambda x: task_id_to_name.get(x, f"Unknown ({x})"),
                        key=f"edit_tasks_{seq['id']}"
                    )
                    
                    # Action buttons
                    save_col, cancel_col = st.columns(2)
                    
                    with save_col:
                        if st.button("Save Changes", key=f"save_edit_{seq['id']}"):
                            try:
                                # Update sequence using the synchronous wrapper
                                success = run_async_sync(
                                    self.controller.update_task_sequence(
                                        tasksmanager_id=tasksmanager_id,
                                        sequence_id=seq['id'],
                                        name=name,
                                        description=description,
                                        task_ids=selected_tasks
                                    )
                                )
                                
                                if success:
                                    st.success("Sequence updated!")
                                    # Clear edit state
                                    st.session_state[f"edit_sequence_{seq['id']}"] = False
                                    time.sleep(1)
                                    st.rerun()
                                else:
                                    st.error("Failed to update sequence.")
                            except Exception as e:
                                st.error(f"Error updating sequence: {str(e)}")
                    
                    with cancel_col:
                        if st.button("Cancel", key=f"cancel_edit_{seq['id']}"):
                            # Clear edit state
                            st.session_state[f"edit_sequence_{seq['id']}"] = False
                            st.rerun()
    
    def _render_create_sequence_form(self, tasksmanager_id: str, tasks: List[Any]):
        """Render the form for creating a new sequence."""
        st.write("### Create New Sequence")
        
        # Create form
        with st.form("create_sequence_form"):
            name = st.text_input("Sequence Name")
            description = st.text_area("Description")
            
            # Create task name mapping for display
            task_options = {task.id: f"{task.name}" for task in tasks}
            
            # Task selection
            selected_tasks = st.multiselect(
                "Select Tasks (in execution order)",
                options=list(task_options.keys()),
                format_func=lambda x: task_options[x]
            )
            
            # Submit button
            submitted = st.form_submit_button("Create Sequence")
            
            if submitted:
                if not name:
                    st.error("Sequence name is required.")
                elif not selected_tasks:
                    st.error("At least one task must be selected.")
                else:
                    try:
                        # Create sequence using the synchronous wrapper
                        sequence_id = run_async_sync(
                            self.controller.create_task_sequence(
                                tasksmanager_id=tasksmanager_id,
                                name=name,
                                description=description,
                                task_ids=selected_tasks
                            )
                        )
                        
                        st.success(f"Sequence '{name}' created successfully!")
                        time.sleep(1)
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error creating sequence: {str(e)}") 