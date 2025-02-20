# src/server/views/components/sidebar/task_hierarchy_sidebar.py
import streamlit as st
from ...models.view_state import ViewState
from ...models.view_types import ViewType
from .utils import truncate_tree_node_names

class TaskHierarchySidebar:
    """Sidebar component for task hierarchy view."""
    
    def __init__(self, controller=None):
        self.controller = controller
    
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
            
            # Add quick actions at the top
            # if st.button("➕ Add New Task"):
            #     st.info("Task creation coming soon")
                
            # if st.button("🔄 Refresh Tasks"):
            #     st.rerun()
            
            # Render task hierarchy as main sidebar content
            st.subheader("Task Structure")
            if self.controller:
                print("\n🌳 Getting task tree for sidebar...")
                tree_data = await self.controller.get_task_tree()
                
                if tree_data:
                    print(f"Tree data received: {len(tree_data.children)} root children")
                    try:
                        # Apply smart name truncation
                        truncate_tree_node_names(tree_data)
                        
                        result = self.controller.tree_component.render(
                            tree_data,
                            key="task_tree_sidebar"
                        )
                        if result is None:
                            print("❌ Tree render returned None")
                            st.warning("Failed to load task tree")
                        else:
                            print("✅ Tree rendered successfully")
                    except Exception as e:
                        print(f"❌ Error rendering tree: {str(e)}")
                        st.error(f"Error rendering tree: {str(e)}")
                else:
                    print("❌ No tree data received")
                    st.info("No tasks available")

# Legacy function for backward compatibility
async def render_task_hierarchy_sidebar():
    """Legacy function to render the task hierarchy sidebar."""
    if 'task_controller' in st.session_state:
        sidebar = TaskHierarchySidebar(st.session_state.task_controller)
        await sidebar.render()
    else:
        with st.sidebar:
            st.warning("Task controller not initialized")