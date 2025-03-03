import streamlit as st
import asyncio
import json
import time
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime
from typing import Dict, List, Optional, Any, Union

from src.server.self_aware_integration import SelfAwareSystem, CognitivePhase, WorkerType, TaskPriority
from src.server.planning.goal_decomposition import GoalType, DecompositionStrategy

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
    ["Cognitive Loop", "Knowledge Management", "Development Context", "Self-Modification", "Goal Decomposition"]
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

elif page == "Goal Decomposition":
    # Goal Decomposition page
    st.header("Goal Decomposition")
    
    # Create tabs for different operations
    tab1, tab2, tab3, tab4 = st.tabs(["Decompose Goal", "View Subgoals", "Prioritize Subgoals", "Validate Decomposition"])
    
    with tab1:
        st.header("Decompose a New Goal")
        
        # Goal input form
        with st.form("decompose_goal_form"):
            goal_name = st.text_input("Goal Name", "")
            goal_description = st.text_area("Goal Description", "")
            
            # Goal type selection
            goal_type_options = [t.name for t in GoalType]
            goal_type = st.selectbox("Goal Type", goal_type_options, index=0)
            
            # Strategy selection
            strategy_options = [s.name for s in DecompositionStrategy]
            strategy = st.selectbox("Decomposition Strategy", strategy_options, index=0)
            
            # Advanced options
            with st.expander("Advanced Options"):
                # Context keywords
                context_keywords = st.text_input("Context Keywords (comma-separated)", "")
                
                # Custom template selection
                use_custom_template = st.checkbox("Use Custom Template", False)
                custom_template = None
                if use_custom_template:
                    template_options = ["Research Project", "Software Development", "Content Creation", "Custom"]
                    selected_template = st.selectbox("Template", template_options)
                    
                    if selected_template == "Custom":
                        custom_template = st.text_area("Custom Template (JSON)", "{}")
            
            submitted = st.form_submit_button("Decompose Goal")
            
            if submitted:
                with st.spinner("Decomposing goal..."):
                    # Prepare goal dictionary
                    goal = {
                        "name": goal_name,
                        "description": goal_description,
                        "type": goal_type
                    }
                    
                    # Prepare context
                    context = None
                    if context_keywords:
                        context = {
                            "keywords": [k.strip() for k in context_keywords.split(",")]
                        }
                    
                    # Add template if selected
                    if use_custom_template and custom_template:
                        try:
                            template_data = json.loads(custom_template)
                            if context:
                                context["template"] = template_data
                            else:
                                context = {"template": template_data}
                        except json.JSONDecodeError:
                            st.error("Invalid JSON in custom template")
                            st.stop()
                    
                    # Call the decompose_goal method
                    try:
                        result = run_async(lambda: st.session_state.system.decompose_goal(
                            goal=goal,
                            strategy=strategy,
                            context=context
                        ))
                        
                        # Store the result in session state
                        if "decomposed_goals" not in st.session_state:
                            st.session_state.decomposed_goals = {}
                        
                        st.session_state.decomposed_goals[result["id"]] = result
                        st.session_state.current_goal_id = result["id"]
                        
                        # Display success message
                        st.success(f"Goal decomposed successfully! ID: {result['id']}")
                        
                        # Display summary
                        st.subheader("Decomposition Summary")
                        st.json({
                            "id": result["id"],
                            "name": result["name"],
                            "subgoals_count": result["subgoals_count"],
                            "total_time_hours": result["total_time_hours"],
                            "max_complexity": result["max_complexity"],
                            "risk_level": result["risk_level"]
                        })
                    
                    except Exception as e:
                        st.error(f"Error decomposing goal: {str(e)}")
    
    with tab2:
        st.header("View Subgoals")
        
        # Goal selection
        if "decomposed_goals" in st.session_state and st.session_state.decomposed_goals:
            goal_options = {g["id"]: f"{g['name']} ({g['id']})" for g in st.session_state.decomposed_goals.values()}
            
            selected_goal_id = st.selectbox(
                "Select Goal", 
                list(goal_options.keys()),
                format_func=lambda x: goal_options[x],
                index=list(goal_options.keys()).index(st.session_state.current_goal_id) if "current_goal_id" in st.session_state else 0
            )
            
            if st.button("View Subgoals"):
                with st.spinner("Loading subgoals..."):
                    try:
                        subgoals = run_async(lambda: st.session_state.system.get_subgoals(selected_goal_id))
                        
                        if not subgoals:
                            st.info("No subgoals found for this goal.")
                        else:
                            # Display subgoals in a table
                            st.subheader(f"Subgoals for {goal_options[selected_goal_id]}")
                            
                            # Create a DataFrame for better display
                            subgoals_data = []
                            for sg in subgoals:
                                subgoals_data.append({
                                    "ID": sg["id"],
                                    "Name": sg["name"],
                                    "Priority": sg["priority"],
                                    "Time (hours)": sg["time_hours"],
                                    "Complexity": sg["complexity"],
                                    "Risk Level": sg["risk_level"],
                                    "Status": sg["status"]
                                })
                            
                            df = pd.DataFrame(subgoals_data)
                            st.dataframe(df)
                            
                            # Display subgoal details
                            st.subheader("Subgoal Details")
                            for sg in subgoals:
                                with st.expander(f"{sg['name']} ({sg['id']})"):
                                    st.write(f"**Description:** {sg['description']}")
                                    st.write(f"**Priority:** {sg['priority']}")
                                    st.write(f"**Time Estimate:** {sg['time_hours']} hours")
                                    st.write(f"**Complexity:** {sg['complexity']}/10")
                                    st.write(f"**Risk Level:** {sg['risk_level']}/10")
                                    st.write(f"**Knowledge Requirements:** {', '.join(sg['knowledge_requirements'])}")
                                    st.write(f"**Parent ID:** {sg['parent_id'] or 'None'}")
                                    st.write(f"**Children IDs:** {', '.join(sg['children_ids']) if sg['children_ids'] else 'None'}")
                                    st.write(f"**Status:** {sg['status']}")
                    
                    except Exception as e:
                        st.error(f"Error loading subgoals: {str(e)}")
        else:
            st.info("No decomposed goals available. Please decompose a goal first.")
    
    with tab3:
        st.header("Prioritize Subgoals")
        
        # Goal selection
        if "decomposed_goals" in st.session_state and st.session_state.decomposed_goals:
            goal_options = {g["id"]: f"{g['name']} ({g['id']})" for g in st.session_state.decomposed_goals.values()}
            
            selected_goal_id = st.selectbox(
                "Select Goal for Prioritization", 
                list(goal_options.keys()),
                format_func=lambda x: goal_options[x],
                index=list(goal_options.keys()).index(st.session_state.current_goal_id) if "current_goal_id" in st.session_state else 0,
                key="prioritize_goal_select"
            )
            
            if st.button("Prioritize Subgoals"):
                with st.spinner("Prioritizing subgoals..."):
                    try:
                        prioritized = run_async(lambda: st.session_state.system.prioritize_subgoals(selected_goal_id))
                        
                        if not prioritized:
                            st.info("No subgoals found for this goal.")
                        else:
                            # Display prioritized subgoals
                            st.subheader(f"Prioritized Subgoals for {goal_options[selected_goal_id]}")
                            
                            # Create a DataFrame for better display
                            priority_data = []
                            for i, sg in enumerate(prioritized):
                                priority_data.append({
                                    "Priority Rank": i + 1,
                                    "ID": sg["id"],
                                    "Name": sg["name"],
                                    "Base Priority": sg["priority"],
                                    "Time (hours)": sg["time_hours"],
                                    "Complexity": sg["complexity"],
                                    "Risk Level": sg["risk_level"],
                                    "Status": sg["status"]
                                })
                            
                            df = pd.DataFrame(priority_data)
                            st.dataframe(df)
                            
                            # Visualization
                            st.subheader("Priority Visualization")
                            
                            # Bar chart of time estimates by priority
                            fig, ax = plt.subplots(figsize=(10, 6))
                            
                            names = [f"{i+1}. {sg['name']}" for i, sg in enumerate(prioritized)]
                            times = [sg["time_hours"] for sg in prioritized]
                            
                            bars = ax.barh(names, times, color='skyblue')
                            
                            # Add risk level as color intensity
                            for i, bar in enumerate(bars):
                                risk = prioritized[i]["risk_level"] / 10
                                bar.set_color(plt.cm.Reds(risk))
                            
                            ax.set_xlabel('Time Estimate (hours)')
                            ax.set_title('Subgoal Time Estimates by Priority')
                            
                            # Add a colorbar for risk level
                            sm = plt.cm.ScalarMappable(cmap=plt.cm.Reds, norm=plt.Normalize(0, 10))
                            sm.set_array([])
                            cbar = plt.colorbar(sm, ax=ax)
                            cbar.set_label('Risk Level')
                            
                            st.pyplot(fig)
                    
                    except Exception as e:
                        st.error(f"Error prioritizing subgoals: {str(e)}")
        else:
            st.info("No decomposed goals available. Please decompose a goal first.")
    
    with tab4:
        st.header("Validate Decomposition")
        
        # Goal selection
        if "decomposed_goals" in st.session_state and st.session_state.decomposed_goals:
            goal_options = {g["id"]: f"{g['name']} ({g['id']})" for g in st.session_state.decomposed_goals.values()}
            
            selected_goal_id = st.selectbox(
                "Select Goal for Validation", 
                list(goal_options.keys()),
                format_func=lambda x: goal_options[x],
                index=list(goal_options.keys()).index(st.session_state.current_goal_id) if "current_goal_id" in st.session_state else 0,
                key="validate_goal_select"
            )
            
            if st.button("Validate Decomposition"):
                with st.spinner("Validating decomposition..."):
                    try:
                        validation = run_async(lambda: st.session_state.system.validate_decomposition(selected_goal_id))
                        
                        # Display validation results
                        st.subheader(f"Validation Results for {goal_options[selected_goal_id]}")
                        
                        if validation["valid"]:
                            st.success("✅ Decomposition is valid!")
                        else:
                            st.error("❌ Decomposition has errors!")
                        
                        # Display errors
                        if validation["errors"]:
                            st.subheader("Errors")
                            for error in validation["errors"]:
                                st.error(error)
                        
                        # Display warnings
                        if validation["warnings"]:
                            st.subheader("Warnings")
                            for warning in validation["warnings"]:
                                st.warning(warning)
                        
                        # If no errors or warnings
                        if not validation["errors"] and not validation["warnings"]:
                            st.info("No issues found in the decomposition.")
                    
                    except Exception as e:
                        st.error(f"Error validating decomposition: {str(e)}")
        else:
            st.info("No decomposed goals available. Please decompose a goal first.")

# Initialize by refreshing tasks
if st.session_state.tasks == []:
    refresh_tasks() 