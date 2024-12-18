import streamlit as st
import asyncio
from server.views.controllers.agentic_view_controller import AgenticViewController
from server.persistence.persistence_model_factory import PersistenceModelFactory
from server.views.components.tree_component import TreeComponent
from server.views.components.header import render_header
from server.views.components.sidebar.agentic_config_sidebar import render_agentic_config_sidebar

async def render_agentic_config_view():
    """Render the agentic configuration view."""
    try:
        # Initialize controller if needed
        if 'agentic_controller' not in st.session_state:
            print("📦 Creating new agentic controller...")
            persistence_model = PersistenceModelFactory.persistence_model("inmemory")
            controller = AgenticViewController(persistence_model)
            await controller.initialize()  # Initialize here
            st.session_state.agentic_controller = controller
            print("✅ Agentic controller initialized")
        
        # Render header
        render_header(
            "Agentic Framework Configuration",
            "Configure AI agent frameworks for the current task context."
        )
        
        # Render sidebar showing state context and frameworks
        await render_agentic_config_sidebar()
        
        # Main content - Chat interface
        st.subheader("Framework Configuration Chat")
        
        # Display chat history
        for msg in st.session_state.agentic_controller.view_state.chat_history:
            with st.chat_message(msg["role"]):
                st.write(msg["content"])
        
        # Chat input
        if prompt := st.chat_input("Type your message..."):
            with st.chat_message("user"):
                st.write(prompt)
            
            await st.session_state.agentic_controller.handle_chat(prompt)
            st.rerun()

    except Exception as e:
        print(f"Error in render_agentic_config_view: {str(e)}")
        st.error("Error initializing view. Check console for details.")

def main():
    try:
        asyncio.run(render_agentic_config_view())
    except Exception as e:
        print(f"Error in main: {str(e)}")
        st.error("Application error. Check console for details.")

if __name__ == "__main__":
    main()
