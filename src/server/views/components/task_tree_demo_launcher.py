import streamlit as st
from pathlib import Path

class TaskTreeDemoLauncher:
    """Component for launching the task tree demo."""
    
    def __init__(self, task_controller):
        """Initialize the launcher."""
        self.controller = task_controller
    
    def render(self):
        """Render the task tree demo launcher."""
        st.write("## Task Tree Demonstration")
        
        demo_state_path = Path("state/task_tree_demo.json")
        demo_state_exists = demo_state_path.exists()
        
        if demo_state_exists:
            st.info(
                "This demo showcases a multi-plugin task tree with handover between " +
                "different AI frameworks (CrewAI, AutoGen, SmolAgents)."
            )
            
            if st.button("Load Task Tree Demo"):
                result = self.controller.load_state(str(demo_state_path))
                if result and "success" in result.lower():
                    st.success("Demo state loaded successfully!")
                    st.rerun()
                else:
                    st.error(f"Failed to load demo state: {result}")
        else:
            st.warning("Task tree demo state file not found. Generate it first.")
            
            if st.button("Generate Task Tree Demo"):
                from src.server.demos.task_tree_demo import save_task_tree_demo_state
                try:
                    state_file = save_task_tree_demo_state()
                    st.success(f"Demo state generated successfully: {state_file}")
                    st.rerun()
                except Exception as e:
                    st.error(f"Failed to generate demo state: {str(e)}")
