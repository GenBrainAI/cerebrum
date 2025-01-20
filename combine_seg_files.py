import os

def combine_files(core_files):
    """Combines specific files into a single output file.

    Args:
        core_files: A set of file paths to include
    """
    with open("combined_code.txt", "w") as outfile:
        for file_path in sorted(core_files):  # Sort for consistent output
            try:
                if os.path.exists(file_path):
                    print(f"Processing: {file_path}")
                    outfile.write(f"<{file_path}>\n\n")
                    with open(file_path, "r") as infile:
                        outfile.write(infile.read())
                    outfile.write("\n\n")
                else:
                    print(f"Warning: File not found - {file_path}")
            except Exception as e:
                print(f"Error processing {file_path}: {str(e)}")

if __name__ == "__main__":
    core_files = {
        # Core Agentic and Context Layer
        "./src/server/controllers/cerebrum_agent_controller.py",
        "./src/server/context/context_aware_agent_factory.py",
        "./src/server/context/crew_context_enhancer.py",
        "./src/server/context/context_provider.py",
        "./src/server/context/vector_store.py",
        "./src/server/context/knowledge_base.py",
        "./src/server/context/system_context.py",
        "./src/server/context/task_context.py",
        "./src/server/context/crewai_context.py",
        "./src/server/context/context_database.py",
        "./src/server/context/context_analytics.py",
        "./src/server/context/code_catalog.py",
        
        # Core Controllers Layer
        "./src/server/controllers/task_runner.py",
        "./src/server/controllers/agents_controller.py",
        "./src/server/controllers/curried_proxy.py",
        "./src/server/controllers/crew_runner.py",
        "./src/server/controllers/task_tree_controller.py",
        "./src/server/controllers/tasks_tree_controller.py",
        "./src/server/controllers/operator.py",
        "./src/server/controllers/config_loader.py",
        "./src/server/controllers/context_state_controller.py",
        "./src/server/controllers/github_controller.py",
        "./src/server/controllers/jira_controller.py",
        "./src/server/controllers/rest_proxy_controller.py",
        
        # Tools and Tools Management
        "./src/server/tools/tools_catalog.py",
        "./src/server/tools/tool_factory.py",
        "./src/server/tools/microservices_tool.py",
        "./src/server/tools/terraform_tool.py",
        "./src/server/tools/github_tool.py",
        "./src/server/tools/jira_tool.py",
        "./src/server/tools/context_tool.py",
        "./src/server/tools/file_tool.py",
        "./src/server/tools/docstring_parser.py",
        
        # Core Models Layer
        "./src/server/models/agent.py",
        "./src/server/models/specialized_state.py",
        "./src/server/models/task.py",
        "./src/server/models/task_context_model.py",
        "./src/server/models/function.py",
        "./src/server/models/message.py",
        "./src/server/models/tools_descriptors.py",
        "./src/server/models/toolset.py",
        "./src/server/models/curried_proxy_info.py",
        "./src/server/models/exceptions.py",
        
        # Persistence and State Management
        "./src/server/persistence/persistence_model.py",
        "./src/server/persistence/in_memory_persistence.py",
        "./src/server/persistence/persistence_model_factory.py",
        "./src/server/persistence/crud_interface.py",
        "./src/server/persistence/in_memory_crud.py",
        "./src/server/controllers/persistence_controller.py",
        
        # View Controllers and Components
        "./src/server/views/controllers/agentic_view_controller.py",
        "./src/server/views/controllers/task_view_controller.py",
        "./src/server/views/controllers/tools_view_controller.py",
        "./src/server/views/components/tree_component.py",
        "./src/server/views/components/tree_select_component.py",
        "./src/server/views/components/chat_panel.py",
        "./src/server/views/base_view.py",
        "./src/server/views/state/state_manager.py",
        "./src/server/views/state/view_serializer.py",
        
        # API Layer
        "./src/server/apis/agents_api.py",
        "./src/server/apis/task_api.py",
        "./src/server/apis/context_api.py",
        "./src/server/apis/default_api.py",
        
        # Data Providers
        "./src/server/views/data/task_tree_provider.py",
        "./src/server/views/data/agent_tree_provider.py",
        "./src/server/views/data/tools_tree_provider.py",
        
        # Main Entry Points and Core UI
        "./run_chat.py",
        "./src/chat.py",
        "./src/pages/task_hierarchy_view.py",
        "./src/pages/tools_catalog_view.py",
        "./src/pages/agentic_config_view.py",
        
        # State Setup and Services
        "./src/server/services/state_manager.py",
        "./generators/terrafom_devsec_ops_generator.py",
        
        # Utils
        "./src/server/utils/task_utils.py",
        "./src/server/utils/state_loader.py",
        "./src/server/utils/context.py"
    }
    
    combine_files(core_files)
    print("Files combined successfully into 'combined_code.txt'")
