import streamlit as st
import asyncio
import json
import time
from datetime import datetime
from typing import Dict, List, Optional, Any, Union

from src.server.self_aware_integration import SelfAwareSystem, CognitivePhase, WorkerType, TaskPriority

# Initialize session state
if "system" not in st.session_state:
    st.session_state.system = SelfAwareSystem()
    
if "tasks" not in st.session_state:
    st.session_state.tasks = []
    
if "knowledge_items" not in st.session_state:
    st.session_state.knowledge_items = {
        "semantic": [],
        "episodic": [],
        "procedural": []
    }
    
if "current_phase" not in st.session_state:
    st.session_state.current_phase = "UNDERSTAND"
    
if "development_context" not in st.session_state:
    st.session_state.development_context = {}

# Self-Modification Engine state
if "code_generation_results" not in st.session_state:
    st.session_state.code_generation_results = None
    
if "validation_results" not in st.session_state:
    st.session_state.validation_results = None
    
if "integration_plans" not in st.session_state:
    st.session_state.integration_plans = []
    
if "development_cycles" not in st.session_state:
    st.session_state.development_cycles = []

# Helper functions
def run_async(func):
    """Run an async function in Streamlit"""
    loop = asyncio.new_event_loop()
    result = loop.run_until_complete(func)
    loop.close()
    return result

def refresh_tasks():
    """Refresh the tasks list"""
    system = st.session_state.system
    phases = ["UNDERSTAND", "PLAN", "EXECUTE", "REFLECT"]
    
    all_tasks = []
    for phase in phases:
        phase_enum = getattr(CognitivePhase, phase)
        phase_tasks = system.get_tasks_by_phase(phase_enum)
        all_tasks.extend(phase_tasks)
    
    st.session_state.tasks = all_tasks
    st.session_state.current_phase = system.get_current_phase().value.upper()

def start_cognitive_cycle():
    """Start a cognitive cycle"""
    system = st.session_state.system
    task_id = run_async(system.start_cognitive_cycle())
    st.success(f"Started cognitive cycle with task ID: {task_id}")
    refresh_tasks()

def start_continuous_operation():
    """Start continuous operation"""
    system = st.session_state.system
    interval = st.session_state.interval
    
    # This is a blocking operation, so we'll run it in a separate thread
    st.info(f"Starting continuous operation with interval {interval} seconds...")
    st.warning("This is a blocking operation. Close the browser tab to stop.")
    
    # We can't use asyncio.run() here because Streamlit doesn't support it well
    # Instead, we'll use a simple loop with sleep
    try:
        while True:
            run_async(system.start_cognitive_cycle())
            refresh_tasks()
            time.sleep(interval)
    except Exception as e:
        st.error(f"Error in continuous operation: {e}")

def add_semantic_knowledge():
    """Add semantic knowledge"""
    system = st.session_state.system
    concept = st.session_state.semantic_concept
    definition = st.session_state.semantic_definition
    related = st.session_state.semantic_related.split(",") if st.session_state.semantic_related else []
    tags = st.session_state.semantic_tags.split(",") if st.session_state.semantic_tags else []
    
    kwargs = {}
    if related:
        kwargs["related_concepts"] = [r.strip() for r in related]
    if tags:
        kwargs["tags"] = [t.strip() for t in tags]
        
    item_id = system.add_semantic_knowledge(concept, definition, **kwargs)
    st.success(f"Added semantic knowledge with ID: {item_id}")

def add_procedural_knowledge():
    """Add procedural knowledge"""
    system = st.session_state.system
    task_name = st.session_state.procedural_task_name
    description = st.session_state.procedural_description
    steps = st.session_state.procedural_steps.split("\n")
    outcome = st.session_state.procedural_outcome
    tags = st.session_state.procedural_tags.split(",") if st.session_state.procedural_tags else []
    
    kwargs = {}
    if tags:
        kwargs["tags"] = [t.strip() for t in tags]
        
    item_id = system.add_procedural_knowledge(task_name, description, steps, outcome, **kwargs)
    st.success(f"Added procedural knowledge with ID: {item_id}")

def add_episodic_knowledge():
    """Add episodic knowledge"""
    system = st.session_state.system
    title = st.session_state.episodic_title
    description = st.session_state.episodic_description
    actors = st.session_state.episodic_actors.split(",") if st.session_state.episodic_actors else []
    tags = st.session_state.episodic_tags.split(",") if st.session_state.episodic_tags else []
    
    kwargs = {}
    if actors:
        kwargs["actors"] = [a.strip() for a in actors]
    if tags:
        kwargs["tags"] = [t.strip() for t in tags]
        
    item_id = system.add_episodic_knowledge(title, description, **kwargs)
    st.success(f"Added episodic knowledge with ID: {item_id}")

def create_task():
    """Create a cognitive task"""
    system = st.session_state.system
    title = st.session_state.task_title
    description = st.session_state.task_description
    phase = st.session_state.task_phase
    worker_type = st.session_state.task_worker
    priority = st.session_state.task_priority
    
    phase_enum = getattr(CognitivePhase, phase)
    
    kwargs = {}
    if worker_type != "None":
        kwargs["worker_type"] = getattr(WorkerType, worker_type)
    
    kwargs["priority"] = getattr(TaskPriority, priority)
    
    task_id = system.create_cognitive_task(title, description, phase_enum, **kwargs)
    st.success(f"Created task with ID: {task_id}")
    refresh_tasks()

def update_context():
    """Update development context"""
    system = st.session_state.system
    key = st.session_state.context_key
    value = st.session_state.context_value
    
    # Try to parse as JSON
    try:
        value = json.loads(value)
    except json.JSONDecodeError:
        # Keep as string if not valid JSON
        pass
        
    system.update_development_context(key, value)
    st.success(f"Updated context key: {key}")
    st.session_state.development_context = system.get_development_context()

def search_knowledge():
    """Search knowledge"""
    system = st.session_state.system
    query = st.session_state.knowledge_query
    max_items = st.session_state.knowledge_max_items
    
    context = system.get_knowledge_context(query, max_items)
    st.session_state.knowledge_items = context

def refresh_development_cycles():
    """Refresh the development cycles list"""
    # In a real implementation, this would fetch cycles from the system
    # For now, we'll just use what's in the session state
    pass

# Main UI
st.title("Self-Aware Cerebrum")
st.subheader("AI Framework with Self-Modification Capabilities")

# Sidebar
st.sidebar.title("Navigation")
page = st.sidebar.selectbox(
    "Navigation",
    ["Cognitive Loop", "Knowledge Management", "Development Context", "Self-Modification"]
)

if page == "Cognitive Loop":
    st.header("Cognitive Loop")
    
    # System status
    st.subheader("System Status")
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Current Phase", st.session_state.current_phase)
    with col2:
        st.metric("Active Tasks", len([t for t in st.session_state.tasks if t.status == "IN_PROGRESS"]))
    
    # Controls
    st.subheader("System Controls")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Start Cognitive Cycle"):
            start_cognitive_cycle()
    
    with col2:
        st.number_input("Interval (seconds)", min_value=1.0, max_value=3600.0, value=60.0, step=1.0, key="interval")
        if st.button("Start Continuous Operation"):
            start_continuous_operation()
    
    # Recent tasks
    st.subheader("Recent Tasks")
    if st.button("Refresh Tasks"):
        refresh_tasks()
    
    if st.session_state.tasks:
        # Sort by created_at, most recent first
        recent_tasks = sorted(st.session_state.tasks, key=lambda x: x.created_at, reverse=True)[:5]
        
        for task in recent_tasks:
            with st.expander(f"{task.title} ({task.status.value})"):
                st.write(f"**Description:** {task.description}")
                st.write(f"**Phase:** {task.phase.value}")
                st.write(f"**Status:** {task.status.value}")
                st.write(f"**Created:** {task.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
                if task.result:
                    st.write(f"**Result:** {task.result}")
                if task.error:
                    st.error(f"**Error:** {task.error}")
    else:
        st.info("No tasks found. Start a cognitive cycle to create tasks.")

elif page == "Knowledge Management":
    st.header("Knowledge Management")
    
    # Knowledge search
    st.subheader("Search Knowledge")
    col1, col2 = st.columns([3, 1])
    with col1:
        st.text_input("Search Query", key="knowledge_query")
    with col2:
        st.number_input("Max Items", min_value=1, max_value=20, value=5, key="knowledge_max_items")
    
    if st.button("Search"):
        search_knowledge()
    
    # Display search results
    if any(st.session_state.knowledge_items.values()):
        st.subheader("Search Results")
        
        tab1, tab2, tab3 = st.tabs(["Semantic", "Episodic", "Procedural"])
        
        with tab1:
            semantic_items = st.session_state.knowledge_items.get("semantic", [])
            if semantic_items:
                for item in semantic_items:
                    with st.expander(f"{item['concept']}"):
                        st.write(f"**Definition:** {item['definition']}")
                        st.write(f"**Confidence:** {item['confidence']}")
                        st.write(f"**ID:** {item['id']}")
            else:
                st.info("No semantic knowledge items found.")
        
        with tab2:
            episodic_items = st.session_state.knowledge_items.get("episodic", [])
            if episodic_items:
                for item in episodic_items:
                    with st.expander(f"{item['title']}"):
                        st.write(f"**Description:** {item['description']}")
                        st.write(f"**Timestamp:** {item['timestamp'].strftime('%Y-%m-%d %H:%M:%S')}")
                        st.write(f"**Confidence:** {item['confidence']}")
                        st.write(f"**ID:** {item['id']}")
            else:
                st.info("No episodic knowledge items found.")
        
        with tab3:
            procedural_items = st.session_state.knowledge_items.get("procedural", [])
            if procedural_items:
                for item in procedural_items:
                    with st.expander(f"{item['task_name']}"):
                        st.write(f"**Description:** {item['description']}")
                        st.write(f"**Steps:**")
                        for i, step in enumerate(item['steps']):
                            st.write(f"{i+1}. {step}")
                        st.write(f"**Expected Outcome:** {item['expected_outcome']}")
                        st.write(f"**Confidence:** {item['confidence']}")
                        st.write(f"**ID:** {item['id']}")
            else:
                st.info("No procedural knowledge items found.")
    
    # Add knowledge
    st.subheader("Add Knowledge")
    
    tab1, tab2, tab3 = st.tabs(["Semantic", "Episodic", "Procedural"])
    
    with tab1:
        st.text_input("Concept", key="semantic_concept")
        st.text_area("Definition", key="semantic_definition")
        st.text_input("Related Concepts (comma-separated)", key="semantic_related")
        st.text_input("Tags (comma-separated)", key="semantic_tags")
        
        if st.button("Add Semantic Knowledge"):
            add_semantic_knowledge()
    
    with tab2:
        st.text_input("Title", key="episodic_title")
        st.text_area("Description", key="episodic_description")
        st.text_input("Actors (comma-separated)", key="episodic_actors")
        st.text_input("Tags (comma-separated)", key="episodic_tags")
        
        if st.button("Add Episodic Knowledge"):
            add_episodic_knowledge()
    
    with tab3:
        st.text_input("Task Name", key="procedural_task_name")
        st.text_area("Description", key="procedural_description")
        st.text_area("Steps (one per line)", key="procedural_steps")
        st.text_input("Expected Outcome", key="procedural_outcome")
        st.text_input("Tags (comma-separated)", key="procedural_tags")
        
        if st.button("Add Procedural Knowledge"):
            add_procedural_knowledge()

elif page == "Development Context":
    st.header("Development Context")
    
    # Update context
    st.subheader("Update Context")
    col1, col2 = st.columns(2)
    with col1:
        st.text_input("Key", key="context_key")
    with col2:
        st.text_area("Value (string or JSON)", key="context_value")
    
    if st.button("Update Context"):
        update_context()
    
    # View context
    st.subheader("Current Context")
    
    # Get current context
    context = st.session_state.system.get_development_context()
    st.session_state.development_context = context
    
    if context:
        # Display as JSON with formatting
        st.json(context)
    else:
        st.info("No context values found.")

elif page == "Self-Modification":
    st.header("Self-Modification Engine")
    
    # Create tabs for different self-modification features
    tabs = st.tabs(["Code Generation", "Code Validation", "Integration Management", "Development Cycles"])
    
    # Code Generation tab
    with tabs[0]:
        st.subheader("Generate Code")
        
        # Input form for code generation
        st.text_input("Component Name", key="component_name")
        st.text_area("Description", key="component_description")
        st.text_input("Target File Path", key="target_file_path")
        
        # Optional context selection
        context_keys = list(st.session_state.development_context.keys()) if st.session_state.development_context else []
        context_key = st.selectbox("Context (Optional)", ["None"] + context_keys, key="context_key_select")
        
        # Optional existing code
        st.text_area("Existing Code (Optional)", key="existing_code")
        
        if st.button("Generate Code"):
            with st.spinner("Generating code..."):
                # Prepare specification
                specification = {
                    "name": st.session_state.component_name,
                    "description": st.session_state.component_description,
                    "file_path": st.session_state.target_file_path
                }
                
                # Get context if selected
                context = None
                if context_key != "None":
                    context = st.session_state.development_context.get(context_key)
                
                # Get existing code if provided
                existing_code = None
                if st.session_state.existing_code:
                    existing_code = st.session_state.existing_code
                
                # Generate code
                result = run_async(lambda: st.session_state.system.generate_code(
                    specification, context, existing_code
                ))
                
                # Store result in session state
                st.session_state.code_generation_results = result
        
        # Display generation results if available
        if st.session_state.code_generation_results:
            st.subheader("Generated Code")
            
            # Display code in a code block
            if "code" in st.session_state.code_generation_results:
                st.code(st.session_state.code_generation_results["code"], language="python")
            
            # Option to validate the generated code
            if st.button("Validate Generated Code"):
                with st.spinner("Validating code..."):
                    # Get the code and file path
                    code = st.session_state.code_generation_results["code"]
                    file_path = st.session_state.target_file_path
                    
                    # Validate code
                    validation_result = run_async(lambda: st.session_state.system.validate_code(
                        code, file_path
                    ))
                    
                    # Store validation result
                    st.session_state.validation_results = validation_result
                    
                    # Switch to validation tab
                    tabs[1].active = True
    
    # Code Validation tab
    with tabs[1]:
        st.subheader("Validate Code")
        
        # Input form for code validation
        st.text_area("Code to Validate", key="validation_code")
        st.text_input("Target File Path", key="validation_file_path")
        
        # Validation level selection
        validation_level = st.selectbox(
            "Validation Level", 
            ["high", "medium", "low"],
            key="validation_level"
        )
        
        if st.button("Validate Code"):
            with st.spinner("Validating code..."):
                # Validate code
                validation_result = run_async(lambda: st.session_state.system.validate_code(
                    st.session_state.validation_code,
                    st.session_state.validation_file_path,
                    validation_level
                ))
                
                # Store validation result
                st.session_state.validation_results = validation_result
        
        # Display validation results if available
        if st.session_state.validation_results:
            st.subheader("Validation Results")
            
            # Display overall result
            passed = st.session_state.validation_results.get("passed", False)
            if passed:
                st.success("Validation Passed")
            else:
                st.error("Validation Failed")
            
            # Display detailed results
            with st.expander("Detailed Results"):
                st.json(st.session_state.validation_results)
    
    # Integration Management tab
    with tabs[2]:
        st.subheader("Integration Management")
        
        # Create integration plan
        st.subheader("Create Integration Plan")
        
        # File path and content inputs
        col1, col2 = st.columns(2)
        with col1:
            st.text_input("File Path", key="integration_file_path")
        with col2:
            st.text_area("File Content", key="integration_file_content")
        
        st.text_input("Description", key="integration_description")
        
        if st.button("Create Integration Plan"):
            with st.spinner("Creating integration plan..."):
                # Create changes dictionary
                changes = {
                    st.session_state.integration_file_path: {
                        "content": st.session_state.integration_file_content,
                        "description": st.session_state.integration_description
                    }
                }
                
                # Create integration plan
                plan = run_async(lambda: st.session_state.system.integrate_changes(changes))
                
                # Add to integration plans
                st.session_state.integration_plans.append(plan)
                
                # Show success message
                st.success(f"Integration plan created with ID: {plan['id']}")
        
        # List existing integration plans
        st.subheader("Integration Plans")
        
        if not st.session_state.integration_plans:
            st.info("No integration plans created yet.")
        else:
            for i, plan in enumerate(st.session_state.integration_plans):
                with st.expander(f"Plan {i+1}: {plan['id']}"):
                    st.write(f"Status: {plan['status']}")
                    st.write(f"Created: {plan['creation_time']}")
                    
                    # Display changes
                    st.subheader("Changes")
                    for file_path, change in plan['changes'].items():
                        st.write(f"File: {file_path}")
                        st.write(f"Description: {change.get('description', 'No description')}")
                    
                    # Action buttons
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        if st.button(f"Stage Changes {i}", key=f"stage_{i}"):
                            with st.spinner("Staging changes..."):
                                result = run_async(lambda: st.session_state.system.integration_manager.stage_changes(plan['id']))
                                st.session_state.integration_plans[i] = run_async(lambda: st.session_state.system.integration_manager.get_integration_status(plan['id']))
                                st.success("Changes staged successfully")
                    
                    with col2:
                        if st.button(f"Test Integration {i}", key=f"test_{i}"):
                            with st.spinner("Testing integration..."):
                                result = run_async(lambda: st.session_state.system.integration_manager.test_integration(plan['id']))
                                st.session_state.integration_plans[i] = run_async(lambda: st.session_state.system.integration_manager.get_integration_status(plan['id']))
                                if result.get("status") == "completed":
                                    st.success("Integration tests passed")
                                else:
                                    st.error("Integration tests failed")
                    
                    with col3:
                        if st.button(f"Apply Changes {i}", key=f"apply_{i}"):
                            with st.spinner("Applying changes..."):
                                result = run_async(lambda: st.session_state.system.integration_manager.apply_changes(plan['id']))
                                st.session_state.integration_plans[i] = run_async(lambda: st.session_state.system.integration_manager.get_integration_status(plan['id']))
                                if result.get("status") == "completed":
                                    st.success("Changes applied successfully")
                                else:
                                    st.error(f"Failed to apply changes: {result.get('error', 'Unknown error')}")
    
    # Development Cycles tab
    with tabs[3]:
        st.subheader("Development Cycles")
        
        # Start new development cycle
        st.subheader("Start New Development Cycle")
        
        # Requirements input
        st.text_input("Cycle Name", key="cycle_name")
        st.text_area("Requirements", key="cycle_requirements")
        
        if st.button("Start Development Cycle"):
            with st.spinner("Starting development cycle..."):
                # Create requirements dictionary
                requirements = {
                    "name": st.session_state.cycle_name,
                    "description": st.session_state.cycle_requirements,
                    "timestamp": datetime.now().isoformat()
                }
                
                # Start development cycle
                cycle_id = run_async(lambda: st.session_state.system.start_development_cycle(requirements))
                
                # Get cycle status
                cycle_status = run_async(lambda: st.session_state.system.get_development_cycle_status(cycle_id))
                
                # Add to development cycles
                st.session_state.development_cycles.append(cycle_status)
                
                # Show success message
                st.success(f"Development cycle started with ID: {cycle_id}")
        
        # List existing development cycles
        st.subheader("Development Cycles")
        
        if not st.session_state.development_cycles:
            st.info("No development cycles started yet.")
        else:
            for i, cycle in enumerate(st.session_state.development_cycles):
                with st.expander(f"Cycle {i+1}: {cycle['id']}"):
                    st.write(f"Status: {cycle['status']}")
                    st.write(f"Created: {cycle['creation_time']}")
                    
                    # Display phases
                    st.subheader("Phases")
                    for phase_name, phase_data in cycle['phases'].items():
                        st.write(f"{phase_name.capitalize()}: {phase_data['status']}")
                    
                    # Display tasks
                    st.subheader("Tasks")
                    if not cycle['tasks']:
                        st.write("No tasks created yet.")
                    else:
                        st.write(f"Number of tasks: {len(cycle['tasks'])}")
                    
                    # Refresh button
                    if st.button(f"Refresh Status {i}", key=f"refresh_{i}"):
                        with st.spinner("Refreshing cycle status..."):
                            updated_cycle = run_async(lambda: st.session_state.system.get_development_cycle_status(cycle['id']))
                            st.session_state.development_cycles[i] = updated_cycle
                            st.success("Cycle status refreshed")

# Initialize by refreshing tasks
if st.session_state.tasks == []:
    refresh_tasks() 