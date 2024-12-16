import streamlit as st
from ..components.dialogs.agentic_dialog import AgenticDialog
from ..components.tree_component import TreeComponent

async def render_agentic_view(controller):
    """Render the agentic configuration view."""
    
    # Create and render tree component in sidebar
    tree = TreeComponent(on_node_click=controller.handle_node_click)
    root_node = await controller.get_agent_tree()
    tree.render(root_node, title="Agent Hierarchy", in_sidebar=True)
    
    # Main content area
    if controller.view_state.selected_agentic:
        # Render agentic dialog in main area
        AgenticDialog(
            on_save=controller.handle_agent_save,
            on_cancel=controller.handle_agent_cancel
        ).render(controller.view_state, controller.view_state.selected_agentic)
    else:
        # Show placeholder message when no agent is selected
        st.write("Select an agent from the sidebar to view or edit its configuration.") 