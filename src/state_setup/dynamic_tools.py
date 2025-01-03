import logging
import sys
from pathlib import Path

# Add project root to Python path
project_root = str(Path(__file__).parents[2])  # Go up two levels to reach project root
sys.path.append(project_root)

import asyncio
import os
import json
from typing import Dict, Any
import aiohttp
import uuid
from datetime import datetime

from src.server.persistence.in_memory_persistence import InMemoryPersistenceModel
from src.server.tools.tools_catalog import tools_catalog
from src.server.tools.internal_file_tools import InternalFileTools
from src.server.tools.internal_credentials_tools import InternalCredentialsTools
from src.server.tools.internal_testing_tools import InternalTestingTools
from src.server.tools.internal_proxy_tools import InternalProxyTools
from src.server.tools.url_tools import URLTools
from src.server.controllers.curried_proxy import CurriedProxy
from src.server.models.agent import CrewAIConfig
from src.server.models.tasks_manager import TasksManager
from src.server.models.task import Task
from src.server.models.task_context_model import ContextReference
from src.server.context.context_database import ContextDatabase
from src.server.context.context_provider import ContextProvider
from src.server.context.knowledge_base import KnowledgeBase
from src.server.controllers.agents_controller import CreateCrewRequest, AgentModel, TaskModel
from src.server.models.agent import ToolsProxyCollection, ObjectToolSpec, ToolModel
from src.server.controllers.agents_controller import create_crew
from src.server.models.persistence_models import StorageLocation, StorageType
from src.server.controllers.persistence_controller import save_to_storage
from src.server.persistence.persistence_model_factory import PersistenceModelFactory
from src.server.tools.github_tool import GitHubTool

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Disable Streamlit warnings
logging.getLogger('streamlit').setLevel(logging.ERROR)

async def add_langchain_tools_docs_to_knowledge_base(persistence_model: InMemoryPersistenceModel) -> None:
    """Add Langchain tools documentation to the knowledge base."""
    # Load documentation from file
    docs_path = Path("docs/langchain_tools/langchain_tools.md")
    if not docs_path.exists():
        print(f"🔴 Langchain tools documentation not found at {docs_path}")
        return

    with open(docs_path, 'r', encoding='utf-8') as f:
        langchain_docs = f.read()
    print(f"📚 Loaded Langchain tools documentation from {docs_path}")

    # Add to knowledge base
    knowledge_id = "knowledge_53_4863043375099098577"  # Fixed ID for testing
    print("🔍 Found existing Langchain tools documentation in knowledge base")

    # Add knowledge base context
    context = ContextReference(
        type="knowledge",
        source_id=f"knowledge_{knowledge_id}",
        metadata={
            "name": "langchain_tools_docs",
            "description": "Official Langchain tools documentation",
            "tags_str": "langchain,tools,documentation",
            "source": "docs/langchain_tools/langchain_tools.md"
        },
        priority=100
    )
    task = persistence_model.tasks.get(task_id)
    task.contexts = [context]
    persistence_model.tasks.update(task)
    print("🔗 Added knowledge base context to task")

async def add_tool_creation_guide_context(persistence_model: InMemoryPersistenceModel, task_id: str) -> None:
    """Add tool creation guide context to the task."""
    # Add context reference
    context_id = str(uuid.uuid4())
    source_id = "knowledge_53_4863043375099098577"
    metadata = {
        'name': 'langchain_tools_docs',
        'description': 'Official Langchain tools documentation',
        'tags_str': 'langchain,tools,documentation',
        'source': 'docs/langchain_tools/langchain_tools.md'
    }
    print(f"Debug - Adding context to task {task_id}:")
    print(f"Type: knowledge")
    print(f"Source ID: {source_id}")
    print(f"Priority: 100")
    print(f"Metadata: {metadata}")

    # Get the task
    task = persistence_model.tasks.read(task_id)
    if task is None:
        raise ValueError(f"Task {task_id} not found")

    # Create context reference
    context_ref = {
        'id': context_id,
        'type': 'knowledge',
        'source_id': source_id,
        'metadata': metadata,
        'priority': 100,
        'created_at': datetime.now()
    }

    # Add context to task
    if task.contexts is None:
        task.contexts = []
    task.contexts.append(context_ref)

    # Update task in persistence model
    persistence_model.tasks.update(task_id, task)

    print("Debug - Creating new task context for", task_id)
    print("Debug - Added context reference:", context_ref)

async def setup_dynamic_tools_state(persistence_model: InMemoryPersistenceModel) -> Dict[str, Any]:
    """Set up the dynamic tools state."""
    try:
        # Register tools in catalog
        tools_catalog.register_class("internal_file_tools", InternalFileTools)
        tools_catalog.register_class("internal_credentials_tools", InternalCredentialsTools)
        tools_catalog.register_class("internal_testing_tools", InternalTestingTools)
        tools_catalog.register_class("internal_proxy_tools", InternalProxyTools)
        tools_catalog.register_class("url_tools", URLTools)
        tools_catalog.register_class("GitHubTool", GitHubTool)  # Register GitHubTool class directly
        print("🛠️ Registered tools in catalog")

        # Initialize context database with proper configuration
        context_db = ContextDatabase(
            persist_directory="persistent_state/context/context_db",
            batch_size=100
        )
        
        # Initialize context provider with context database
        context_provider = ContextProvider()
        context_provider.context_db = context_db
        knowledge_base = KnowledgeBase()
        
        # Create documentation links for navigation
        langchain_docs = {
            "Tool Creation Guide": "https://python.langchain.com/docs/modules/agents/tools/custom_tools",
            "Tool Concepts": "https://python.langchain.com/docs/modules/agents/tools/",
            "Tool Examples": "https://python.langchain.com/docs/integrations/tools",
            "Agent Tools": "https://python.langchain.com/docs/modules/agents/tools/",
            "Structured Tools": "https://python.langchain.com/docs/modules/agents/tools/structured"
        }
        
        # Add documentation links to knowledge base
        docs_content = "# Langchain Tools Documentation Links\n\n"
        for title, url in langchain_docs.items():
            docs_content += f"- [{title}]({url})\n"
            
        knowledge_id = await knowledge_base.add_knowledge(
            content=docs_content,
            domain="langchain",
            metadata={
                "type": "documentation_links",
                "category": "tools",
                "tags": ["tools", "documentation", "navigation"]
            }
        )
        print(f"📚 Added Langchain documentation links to knowledge base: {knowledge_id}")
        

        # Create curried proxy
        curried_proxy = CurriedProxy()
        
        # Register tools with the proxy
        for tool_name in tools_catalog.list_tools():
            print(f"\nDebug - Processing tool: {tool_name}")
            tool_instance = tools_catalog.get_tool_instance(tool_name)
            if tool_instance:
                print(f"Debug - Tool instance type: {type(tool_instance)}")
                tool_metadata = tools_catalog.get_tool(tool_name)
                if tool_metadata:
                    print(f"Debug - Tool metadata:")
                    print(f"  - Type: {tool_metadata.tool_type}")
                    print(f"  - Original obj: {type(tool_metadata.original_obj)}")
                    print(f"  - Has __name__: {hasattr(tool_metadata.original_obj, '__name__')}")
                curried_proxy.add_tool(tool_name, tool_instance)
        
        curried_proxy_id = persistence_model.curried_proxies.create(curried_proxy).id
        print(f"🔧 Created curried proxy with ID: {curried_proxy_id}")

        # Create CrewAI configuration
        crew_request = CreateCrewRequest(
            description="Dynamic Langchain Tools Generator",
            agents=[
                AgentModel(
                    role="Security Manager",
                    goal="Manage and validate project credentials securely",
                    backstory="Security expert responsible for handling sensitive credentials and ensuring secure access patterns.",
                    tools=[
                        ToolModel(
                            name="CredentialsTools.load_credentials",
                            description="Load credentials from .env file"
                        ),
                        ToolModel(
                            name="CredentialsTools.validate_credentials",
                            description="Validate required credentials"
                        )
                    ]
                ),
                AgentModel(
                    role="LangChain Tool Architect",
                    goal="Design and specify new Langchain tools based on documentation analysis",
                    backstory="Expert system architect specializing in Langchain integration and tool design. Starts by analyzing relevant documentation before creating specifications.",
                    tools=[
                        ToolModel(
                            name="URLTools.get_data_from_url",
                            description="Fetch Langchain documentation content from URL"
                        ),
                        ToolModel(
                            name="FileTools.read_documentation",
                            description="Read tool documentation from file"
                        )
                    ]
                ),
                AgentModel(
                    role="Tool Implementation Engineer",
                    goal="Implement Langchain tools following specifications and best practices",
                    backstory="Senior developer with expertise in Langchain tool implementation.",
                    tools=[
                        ToolModel(
                            name="FileTools.save_implementation",
                            description="Save generated tool implementation to file"
                        ),
                        ToolModel(
                            name="ProxyTools.register_tool",
                            description="Register tool with global CurriedProxy"
                        )
                    ]
                ),
                AgentModel(
                    role="Test Engineer",
                    goal="Create comprehensive test suites for tools",
                    backstory="Testing specialist who writes thorough unit tests.",
                    tools=[
                        ToolModel(
                            name="FileTools.save_tests",
                            description="Save test code to file"
                        )
                    ]
                ),
                AgentModel(
                    role="QA Automation Engineer",
                    goal="Automate and execute tests, ensure quality",
                    backstory="Quality assurance expert who automates testing processes and validates results.",
                    tools=[
                        ToolModel(
                            name="TestingTools.run_unit_tests",
                            description="Run unit tests and get results"
                        ),
                        ToolModel(
                            name="TestingTools.validate_test_coverage",
                            description="Calculate test coverage"
                        )
                    ]
                )
            ],
            tasks=[
                TaskModel(
                    description="Load and validate project credentials",
                    expected_output="Credentials loaded and validated successfully",
                    agent_role="Security Manager"
                ),
                TaskModel(
                    description="Analyze Langchain documentation and create tool specification",
                    expected_output="""
                    1. List of relevant documentation pages visited
                    2. Key patterns and requirements identified
                    3. Tool specification document created
                    """,
                    agent_role="LangChain Tool Architect",
                    depends_on=["Load and validate project credentials"]
                ),
                TaskModel(
                    description="Implement the tool following Langchain patterns",
                    expected_output="Tool implementation code generated and saved",
                    agent_role="Tool Implementation Engineer",
                    depends_on=["Analyze Langchain documentation and create tool specification"]
                ),
                TaskModel(
                    description="Create comprehensive unit tests",
                    expected_output="Test suite created and saved",
                    agent_role="Test Engineer",
                    depends_on=["Implement the tool following Langchain patterns"]
                ),
                TaskModel(
                    description="Execute tests and validate coverage",
                    expected_output="Test execution report with coverage metrics",
                    agent_role="QA Automation Engineer",
                    depends_on=["Create comprehensive unit tests"]
                )
            ],
            tools_proxy_collection=ToolsProxyCollection(
                toolsets=[],
                functions=[],
                objects=[
                    ObjectToolSpec(
                        name="FileTools",
                        object_type="FileTools",
                        methods=[
                            "FileTools.read_documentation",
                            "FileTools.save_implementation",
                            "FileTools.save_tests"
                        ]
                    ),
                    ObjectToolSpec(
                        name="CredentialsTools",
                        object_type="CredentialsTools",
                        methods=[
                            "CredentialsTools.load_credentials",
                            "CredentialsTools.validate_credentials"
                        ]
                    ),
                    ObjectToolSpec(
                        name="TestingTools",
                        object_type="TestingTools",
                        methods=[
                            "TestingTools.run_unit_tests",
                            "TestingTools.validate_test_coverage"
                        ]
                    ),
                    ObjectToolSpec(
                        name="ProxyTools",
                        object_type="ProxyTools",
                        methods=[
                            "ProxyTools.register_tool"
                        ]
                    )
                ]
            )
        )
        
        # Create crew and store configuration
        crew = await create_crew(crew_request, curried_proxy)
        crewai_config = persistence_model.crewai_config.create(CrewAIConfig(create_crew=crew_request))
        print(f"👥 Created CrewAI configuration with ID: {crewai_config.id}")
        
        # Create TasksManager for dynamic tools
        tasksmanager = TasksManager(
            name="Dynamic Langchain Tools Generator",
            model="gpt-4",
            description="Manages the generation and integration of Langchain tools",
            messages=[
                {
                    "role": "system",
                    "content": """You are a specialized AI assistant coordinating the creation of Langchain tools.
                    Your team consists of specialized agents:
                    
                    1. Security Manager
                    - Handles project credentials securely
                    - Validates required credentials
                    - Ensures secure access patterns
                    
                    2. LangChain Tool Architect
                    - Analyzes tool documentation and requirements
                    - Creates detailed specifications for implementation
                    - Ensures alignment with Langchain patterns
                    
                    3. Tool Implementation Engineer
                    - Implements tools based on specifications
                    - Follows Langchain's tool interface requirements
                    - Ensures proper error handling and type hints
                    - Registers tools with global CurriedProxy
                    
                    4. Test Engineer
                    - Creates comprehensive unit tests
                    - Ensures test coverage of all functionality
                    - Follows testing best practices
                    
                    5. QA Automation Engineer
                    - Executes automated tests
                    - Validates test coverage
                    - Ensures quality standards are met
                    
                    The tools must be compatible with Langchain's patterns:
                    - Implement required methods (_run, _arun)
                    - Include proper type hints and documentation
                    - Handle errors appropriately
                    - Support async operations when needed
                    
                    Tools will be integrated with our DynamicToolsLoader system,
                    so ensure they support:
                    - Dynamic registration with global CurriedProxy
                    - Runtime loading
                    - Proper state management
                    - Tool discovery mechanisms
                    
                    The process follows these steps:
                    1. Validate credentials and security
                    2. Analyze requirements and create specifications
                    3. Implement tool following specifications
                    4. Create comprehensive tests
                    5. Execute tests and validate quality"""
                }
            ]
        )
        tasksmanager = persistence_model.tasksmanagers.create(tasksmanager)
        print(f"📋 Created tasks manager with ID: {tasksmanager.id}")
        
        # Create Task
        task = Task(
            name="Generate Dynamic Langchain Tool",
            description="Generate and integrate a new Langchain tool",
            tasksmanager_id=tasksmanager.id,
            crewai_config_id=crewai_config.id,
            curried_proxy_id=curried_proxy_id,
            use_context=True,
            inherit_manager_context=True
        )
        task = persistence_model.tasks.create(task)
        print(f"✨ Created task with ID: {task.id}")
        
        # Now handle the Langchain tools documentation
        docs_path = Path("docs/langchain_tools/langchain_tools.md")
        if not docs_path.exists():
            print(f"🔴 Langchain tools documentation not found at {docs_path}")
            return
            
        with open(docs_path, 'r', encoding='utf-8') as f:
            langchain_docs = f.read()
            
        print(f"📚 Loaded Langchain tools documentation from {docs_path}")
        
        # Check if documentation already exists in knowledge base
        existing_entries = knowledge_base.get_knowledge(
            domain="langchain",
            tags=["tools", "documentation"]
        )
        
        if existing_entries:
            print("🔍 Found existing Langchain tools documentation in knowledge base")
            knowledge_id = existing_entries[0]["id"]  # Use existing entry
        else:
            # Create new knowledge base entry for Langchain tools documentation
            knowledge_id = await knowledge_base.add_knowledge(
                content=langchain_docs,
                domain="langchain",
                metadata={
                    "source": "docs/langchain_tools/langchain_tools.md",
                    "type": "documentation",
                    "category": "tools",
                    "tags": ["tools", "documentation"]
                }
            )
            print(f"📝 Created new knowledge base entry: {knowledge_id}")
        
        # Now that we have the task and knowledge base entry, add contexts
        existing_contexts = await context_provider.get_task_contexts(task.id)
        has_langchain_docs = any(
            ctx.get('type') == 'knowledge' and 
            ctx.get('source_id') == str(knowledge_id)
            for ctx in existing_contexts
        )
        
        if not has_langchain_docs:
            # Add knowledge base context to task
            await context_provider.add_context_to_task(
                task_id=task.id,
                type="knowledge",
                source_id=str(knowledge_id),
                priority=100,  # High priority as this is essential documentation
                metadata={
                    "name": "langchain_tools_docs",
                    "description": "Official Langchain tools documentation",
                    "tags_str": ",".join(["langchain", "tools", "documentation"]),
                    "source": "docs/langchain_tools/langchain_tools.md"
                }
            )
            print(f"🔗 Added knowledge base context to task")
        else:
            print("✅ Task already has Langchain tools documentation context")
        
        # Add system context with tool creation guide
        await context_provider.add_system_context(
            task_id=task.id,
            name="langchain_tools_guide",
            content="""# Langchain Tool Creation Guide
            # ... (keep existing guide content)
            """,
            description="Guide for creating Langchain tools",
            tags=["langchain", "tools", "guide"],
            priority=90  # Slightly lower priority than the official docs
        )
        print("🔧 Added tool creation guide context")
        
        # Save state
        state_location = StorageLocation(
            type=StorageType.file,
            location="state/specialized",
            state_name="dynamic_tools_state.json"
        )
        
        # Ensure the state directory exists
        os.makedirs("state/specialized", exist_ok=True)
        
        # Save persistence state
        result = save_to_storage(persistence_model, state_location)
        print(f"💾 Dynamic tools state saved: {result}")
        
        # Return state info
        return {
            "tasksmanager_id": tasksmanager.id,
            "task_id": task.id,
            "curried_proxy_id": curried_proxy_id,
            "crewai_config_id": crewai_config.id
        }
    except Exception as e:
        print(f"❌ Error setting up dynamic tools state: {e}")
        raise


if __name__ == "__main__":
        # Initialize persistence model without Streamlit context
    os.environ['STREAMLIT_RUN_MODE'] = 'script'
    persistence_model = PersistenceModelFactory.persistence_model("inmemory")
    asyncio.run(setup_dynamic_tools_state(persistence_model)) 