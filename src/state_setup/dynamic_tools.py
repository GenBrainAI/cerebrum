import logging
import sys
from pathlib import Path

# Add project root to Python path
project_root = str(Path(__file__).parents[2])  # Go up two levels to reach project root
sys.path.append(project_root)

from typing import Dict, Any
import uuid
from datetime import datetime
import os

from src.server.context import knowledge_base
from src.server.persistence.in_memory_persistence import InMemoryPersistenceModel
from src.server.models.tools_catalog import ToolsCatalog
from src.server.tools.internal_file_tools import InternalFileTools
from src.server.tools.internal_credentials_tools import InternalCredentialsTools
from src.server.tools.internal_testing_tools import InternalTestingTools
from src.server.tools.internal_proxy_tools import InternalProxyTools
from src.server.tools.url_tools import URLTools
from src.server.controllers.curried_proxy import CurriedProxy
from src.server.models.agent import CrewAIConfig, CreateCrewRequest, AgentModel, ToolModel
from src.server.models.process import Process
from src.server.models.tasks_manager import TasksManager
from src.server.models.task import Task
from src.server.controllers.agents_controller import CreateCrewRequest, AgentModel
from src.server.models.agent import ToolModel
from src.server.models.persistence_models import StorageLocation, StorageType
from src.server.controllers.persistence_controller import save_to_storage
from src.server.persistence.persistence_model_factory import PersistenceModelFactory
from src.server.context.context_provider import ContextProvider
from src.server.context.crew_context_enhancer import CrewContextEnhancer, CrewContextConfig
from src.server.context.unified_context_manager import UnifiedContextManager

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Disable Streamlit warnings
logging.getLogger('streamlit').setLevel(logging.ERROR)

# Get the global instance
tools_catalog = ToolsCatalog()

# Create and register internal tools
def register_internal_tools():
    """Create and register all internal tools with proper docstrings."""
    print("\n🔄 Registering internal tools...")
    
    # Create tool instances
    internal_file_tools = InternalFileTools()
    internal_credentials_tools = InternalCredentialsTools()
    internal_testing_tools = InternalTestingTools()
    internal_proxy_tools = InternalProxyTools()
    url_tools = URLTools()
    
    # Register tools with catalog using register_instance
    tools_catalog.register_instance(internal_file_tools, "internal_file_tools")
    tools_catalog.register_instance(internal_credentials_tools, "internal_credentials_tools")
    tools_catalog.register_instance(internal_testing_tools, "internal_testing_tools")
    tools_catalog.register_instance(internal_proxy_tools, "internal_proxy_tools")
    tools_catalog.register_instance(url_tools, "url_tools")
    
    # Log registered tools and their methods
    print("\n📦 Registered tools and methods:")
    for tool_name in tools_catalog.list_tools():
        try:
            metadata = tools_catalog.get_tool(tool_name)
            print(f"\n🔧 {tool_name}:")
            if metadata:
                if metadata.description:
                    desc_lines = metadata.description.split('\n')
                    print(f"  Description: {desc_lines[0] if desc_lines else ''}")
                print(f"  Type: {metadata.tool_type}")
                if metadata.parameters:
                    print(f"  Parameters: {[p.name for p in metadata.parameters]}")
                if '.' not in tool_name:  # Base tool
                    print("  Methods:")
                    tool_instance = tools_catalog.get_tool_instance(tool_name)
                    if tool_instance:
                        for method_name in dir(tool_instance):
                            if not method_name.startswith('_'):
                                method = getattr(tool_instance, method_name)
                                if callable(method):
                                    method_metadata = tools_catalog.get_tool(f"{tool_name}.{method_name}")
                                    if method_metadata and method_metadata.description:
                                        desc_lines = method_metadata.description.split('\n')
                                        print(f"    - {method_name}: {desc_lines[0] if desc_lines else ''}")
        except Exception as e:
            print(f"  ❌ Error getting metadata for {tool_name}: {str(e)}")

def save_persistence_state(persistence_model: InMemoryPersistenceModel, file_path: str) -> None:
    """Save the persistence model state to a JSON file."""
    try:
        # Create storage location for the state
        state_location = StorageLocation(
            type=StorageType.file,
            location="state/specialized",
            state_name="dynamic_tools_state.json"
        )

        # Ensure the directory exists
        os.makedirs(state_location.location, exist_ok=True)
        
        # Save the state using the persistence controller
        message = save_to_storage(persistence_model, state_location)
        logger.info(message)
    except Exception as e:
        logger.error(f"❌ Failed to save persistence state: {str(e)}")

def load_persistence_state(persistence_model: InMemoryPersistenceModel, file_path: str) -> None:
    """Load the persistence model state from a JSON file."""
    try:
        state_location = StorageLocation(
            type=StorageType.file,
            location="persistent_state",
            state_name="dynamic_tools_state.json"
        )
        
        if not Path(f"{state_location.location}/{state_location.state_name}").exists():
            logger.info(f"No existing state file found at {state_location.location}/{state_location.state_name}")
            return
            
        # State will be loaded automatically by the persistence model
        logger.info(f"✅ Loaded persistence state from {state_location.location}/{state_location.state_name}")
    except Exception as e:
        logger.error(f"❌ Failed to load persistence state: {str(e)}")

async def add_tool_development_context(task_id: str, persistence_model: InMemoryPersistenceModel) -> None:
    """Add tool development specific context to the task."""
    try:
        context_provider = ContextProvider()
        
        # Add system context for tool development guidelines
        await context_provider.add_system_context(
            task_id=task_id,
            name="Tool Development Guidelines",
            content="""When developing tools, follow these guidelines:
            1. Use concrete types instead of Any where possible
            2. Include comprehensive docstrings with parameters and returns
            3. Implement proper error handling and logging
            4. Add unit tests for all functionality
            5. Follow Python best practices and PEP standards""",
            category="development",
            priority=90
        )
        
        # Add knowledge base context for tool patterns
        await context_provider.add_context_to_task(
            task_id=task_id,
            type="knowledge",
            source_id="tool_patterns",
            priority=80,
            metadata={
                "name": "Tool Development Patterns",
                "content": """Common tool development patterns:
                1. Use async/await for I/O operations
                2. Implement proper parameter validation
                3. Return structured responses
                4. Include progress tracking for long operations
                5. Support cancellation where appropriate""",
                "category": "patterns"
            }
        )
        
        # Add vector store context for code examples
        await context_provider.add_context_to_task(
            task_id=task_id,
            type="vector",
            source_id="tool_examples",
            priority=70,
            metadata={
                "name": "Tool Implementation Examples",
                "description": "Example implementations of various tools",
                "category": "examples"
            }
        )
        
        # Add testing context
        await context_provider.add_context_to_task(
            task_id=task_id,
            type="knowledge",
            source_id="testing_guidelines",
            priority=85,
            metadata={
                "name": "Testing Guidelines",
                "content": """Testing requirements for tools:
                1. Unit tests for all public methods
                2. Integration tests for external dependencies
                3. Test edge cases and error conditions
                4. Use pytest fixtures for setup
                5. Mock external services appropriately""",
                "category": "testing"
            }
        )
        
        logger.info(f"Added tool development context to task {task_id}")
        
    except Exception as e:
        logger.error(f"Error adding tool development context: {str(e)}")
        raise

async def add_test_analysis_context(task_id: str, persistence_model: InMemoryPersistenceModel) -> None:
    """Add test analysis specific context to the task."""
    try:
        context_provider = ContextProvider()
        
        # Add test analysis guidelines
        await context_provider.add_system_context(
            task_id=task_id,
            name="Test Analysis Guidelines",
            content="""When analyzing test failures, follow these steps:
            1. Identify the type of failure (assertion, error, timeout)
            2. Analyze test output and stack traces
            3. Check test coverage and edge cases
            4. Review test data and fixtures
            5. Validate test environment setup
            
            Common Test Issues:
            1. Incorrect assertions or expectations
            2. Missing edge case coverage
            3. Improper test isolation
            4. Race conditions in async tests
            5. Resource cleanup issues""",
            category="testing",
            priority=95
        )
        
        # Add test-driven development context
        await context_provider.add_context_to_task(
            task_id=task_id,
            type="knowledge",
            source_id="tdd_workflow",
            priority=90,
            metadata={
                "name": "Test-Driven Development Workflow",
                "content": """TDD Workflow Steps:
                1. Write failing test first
                2. Implement minimum code to pass
                3. Refactor while maintaining tests
                4. Iterate for each feature
                5. Maintain test suite quality
                
                Best Practices:
                1. Keep tests focused and atomic
                2. Use descriptive test names
                3. Follow Arrange-Act-Assert pattern
                4. Mock external dependencies
                5. Maintain test data fixtures""",
                "category": "testing"
            }
        )
        
        # Add test improvement patterns
        await context_provider.add_context_to_task(
            task_id=task_id,
            type="knowledge",
            source_id="test_improvement",
            priority=85,
            metadata={
                "name": "Test Improvement Patterns",
                "content": """Test Improvement Strategies:
                1. Analyze test coverage gaps
                2. Add property-based testing
                3. Implement stress testing
                4. Add performance benchmarks
                5. Enhance error messages
                
                Continuous Improvement:
                1. Regular test suite review
                2. Performance optimization
                3. Maintenance of test data
                4. Documentation updates
                5. CI/CD integration""",
                "category": "testing"
            }
        )
        
        logger.info(f"Added test analysis context to task {task_id}")
        
    except Exception as e:
        logger.error(f"Error adding test analysis context: {str(e)}")
        raise

# Update the Technical Lead's backstory in setup_dynamic_tools_state
async def create_technical_lead_agent() -> AgentModel:
    """Create an enhanced Technical Lead agent with test analysis capabilities."""
    return AgentModel(
        name="Technical Lead",
        role="Technical Lead",
        goal="Oversee the tool development process, ensure high quality implementation, and manage test-driven development",
        backstory="""Expert technical lead with deep knowledge of software architecture, development practices, and test-driven development.
        Specializes in:
        1. Code quality and architecture
        2. Test suite design and analysis
        3. Development process optimization
        4. Technical mentorship
        5. Quality assurance
        
        Experienced in:
        - Managing complex development workflows
        - Analyzing and resolving test failures
        - Implementing test-driven development
        - Coordinating between development and testing teams
        - Maintaining high code quality standards""",
        tools=[ToolModel(name=tool_name, description="Tool for operations") 
               for tool_name in tools_catalog.list_tools()]
    )

async def setup_dynamic_tools_state(persistence_model: InMemoryPersistenceModel, state_file: str = "persistent_state/dynamic_tools_state.json") -> Dict[str, Any]:
    """Set up the dynamic tools state with in-memory persistence and JSON serialization."""
    try:
        print("\n🔄 Setting up dynamic tools state...")
        
        # Initialize unified context manager
        context_manager = UnifiedContextManager()
        
        # Register tools if not already registered
        if not tools_catalog.list_tools():
            register_internal_tools()
        
        # Log available tools
        available_tools = tools_catalog.list_tools()
        print(f"📦 Available tools in catalog: {available_tools}")

        # Then try to load existing state
        print("\n🔄 Loading existing state...")
        load_persistence_state(persistence_model, state_file)

        # Create curried proxy if not exists
        existing_proxies = persistence_model.curried_proxies.list()
        if not existing_proxies:
            print("\n🆕 Creating new curried proxy...")
            curried_proxy = CurriedProxy()
            
            # Register tools with the proxy
            print("🔧 Registering tools with proxy...")
            for tool_name in tools_catalog.list_tools():
                print(f"  ➕ Adding tool: {tool_name}")
                tool_instance = tools_catalog.get_tool_instance(tool_name)
                if tool_instance:
                    curried_proxy.add_tool(tool_name, tool_instance)
                    print(f"  ✅ Added tool: {tool_name}")
                else:
                    print(f"  ❌ Could not get instance for tool: {tool_name}")
            
            curried_proxy_id = persistence_model.curried_proxies.create(curried_proxy).id
            print(f"✨ Created curried proxy with ID: {curried_proxy_id}")
            
            # Log registered tools
            proxy_tools = curried_proxy.list_tools()
            print(f"🔧 Tools registered in proxy: {proxy_tools}")
        else:
            curried_proxy = existing_proxies[0]
            curried_proxy_id = curried_proxy.id
            print(f"\n🔄 Using existing curried proxy with ID: {curried_proxy_id}")
            
            # Re-register tools with the proxy
            print("🔄 Re-registering tools with existing proxy...")
            for tool_name in tools_catalog.list_tools():
                print(f"  ➕ Adding tool: {tool_name}")
                tool_instance = tools_catalog.get_tool_instance(tool_name)
                if tool_instance:
                    curried_proxy.add_tool(tool_name, tool_instance)
                    print(f"  ✅ Added tool: {tool_name}")
                else:
                    print(f"  ❌ Could not get instance for tool: {tool_name}")
            
            # Update proxy in persistence model
            persistence_model.curried_proxies.update(str(curried_proxy_id), curried_proxy)
            print(f"✅ Updated tools in proxy: {curried_proxy.list_tools()}")

        # Create TasksManager if not exists
        existing_managers = persistence_model.tasksmanagers.list()
        if not existing_managers:
            tasksmanager = TasksManager(
                name="Dynamic Langchain Tools Generator",
                model="gpt-4o-mini",
                description="Manages the generation and integration of Langchain tools",
                messages=[{
                    "role": "system",
                    "content": """You are a specialized AI assistant coordinating the creation of Langchain tools.
                    Your team consists of specialized agents for security, architecture, implementation, testing, and QA.
                    Tools must be compatible with Langchain's patterns and support dynamic registration."""
                }]
            )
            tasksmanager = persistence_model.tasksmanagers.create(tasksmanager)
            logger.info(f"📋 Created tasks manager with ID: {tasksmanager.id}")
        else:
            tasksmanager = existing_managers[0]
            logger.info(f"📋 Using existing tasks manager with ID: {tasksmanager.id}")

        # Create CrewAI config if not exists
        existing_configs = persistence_model.crewai_config.list()
        if not existing_configs:
            # Create enhanced Technical Lead
            technical_lead = await create_technical_lead_agent()
            
            crewai_config = CrewAIConfig(
                id=str(uuid.uuid4()),
                create_crew=CreateCrewRequest(
                    description="Configuration for the dynamic tools generation crew",
                    process=Process.hierarchical,
                    agents=[
                        technical_lead,  # Use enhanced Technical Lead
                        AgentModel(
                            name="Tools Architect",
                            role="Lead Tools Architect",
                            goal="Design robust and reusable tools with clear interfaces",
                            backstory="Expert in designing modular and maintainable tools",
                            tools=[
                                ToolModel(name="internal_file_tools", description="Tool for file operations"),
                                ToolModel(name="internal_testing_tools", description="Tool for testing operations")
                            ]
                        ),
                        AgentModel(
                            name="Implementation Engineer",
                            role="Tools Developer",
                            goal="Implement tools following the design specifications and save them to the dist directory",
                            backstory="Skilled in writing clean, efficient, and well-tested code",
                            tools=[
                                ToolModel(name="internal_file_tools", description="Tool for file operations"),
                                ToolModel(name="internal_testing_tools", description="Tool for testing operations")
                            ]
                        ),
                        AgentModel(
                            name="Test Engineer",
                            role="Test Engineer",
                            goal="Create and execute comprehensive tests for the implemented tools",
                            backstory="Expert in test-driven development and quality assurance",
                            tools=[
                                ToolModel(name="internal_testing_tools", description="Tool for testing operations"),
                                ToolModel(name="internal_file_tools", description="Tool for file operations")
                            ]
                        ),
                        AgentModel(
                            name="Code Saver",
                            role="Code Extractor",
                            goal="Extract and save clean code from markdown-formatted implementations",
                            backstory="Expert in parsing and extracting code from documentation and saving it to the correct location",
                            tools=[ToolModel(name="internal_file_tools", description="Tool for file operations")]
                        )
                    ],
                    tasks=[
                        {
                            "name": "Design Complex Fibonacci Tool",
                            "description": "Design a tool that calculates Fibonacci sequence for complex numbers, starting with i+i and i+2i. The tool should handle complex number arithmetic and provide clear interfaces for sequence generation.",
                            "agent_role": "Lead Tools Architect",
                            "expected_output": "Tool design specification for complex number Fibonacci calculator",
                            "tools": [ToolModel(name="internal_file_tools", description="Tool for file operations")],
                            "next": "Implement Complex Fibonacci Tool"
                        },
                        {
                            "name": "Implement Complex Fibonacci Tool",
                            "description": "Implement the complex number Fibonacci calculator following the design specifications. Provide the implementation in markdown format with explanations.",
                            "agent_role": "Tools Developer",
                            "expected_output": "Implemented complex number Fibonacci tool code with explanations in markdown",
                            "tools": [ToolModel(name="internal_file_tools", description="Tool for file operations")],
                            "depends_on": ["Design Complex Fibonacci Tool"],
                            "next": "Create Tests"
                        },
                        {
                            "name": "Create Tests",
                            "description": "Create comprehensive unit tests for the complex Fibonacci tool, including edge cases and error handling",
                            "agent_role": "Test Engineer",
                            "expected_output": "Complete test suite for the complex Fibonacci tool",
                            "tools": [ToolModel(name="internal_testing_tools", description="Tool for testing operations")],
                            "depends_on": ["Implement Complex Fibonacci Tool"],
                            "next": "Save Code to Dist"
                        },
                        {
                            "name": "Save Code to Dist",
                            "description": "Extract the Python code from the markdown-formatted implementation and save it using internal_file_tools.save_implementation. Steps: 1) Extract only the actual Python code from the markdown, ignoring explanations and formatting. 2) Call internal_file_tools.save_implementation(code=extracted_code, tool_name='complex_fibonacci_tool'). The function will automatically save the file as 'complex_fibonacci_tool.py' in the dist directory.",
                            "agent_role": "Code Extractor",
                            "expected_output": "Clean Python code saved to dist directory",
                            "tools": [ToolModel(name="internal_file_tools", description="Tool for file operations")],
                            "depends_on": ["Create Tests"]
                        }
                    ]
                ),
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            crewai_config = persistence_model.crewai_config.create(crewai_config)
            logger.info(f"⚙️ Created CrewAI config with ID: {crewai_config.id}")
        else:
            crewai_config = existing_configs[0]
            logger.info(f"⚙️ Using existing CrewAI config with ID: {crewai_config.id}")

        # Create Task if not exists
        existing_tasks = persistence_model.tasks.list()
        if not existing_tasks:
            task = Task(
                name="Generate Dynamic Langchain Tool",
                description="Generate and integrate a new Langchain tool",
                tasksmanager_id=tasksmanager.id,
                curried_proxy_id=str(curried_proxy_id),
                crewai_config_id=str(crewai_config.id),
                use_context=True,
                inherit_manager_context=True,
                framework="crewai"
            )
            task = persistence_model.tasks.create(task)
            logger.info(f"✨ Created task with ID: {task.id}")
            
            # Add tool development context using unified manager
            await context_manager.add_context_to_task(
                task_id=task.id,
                content="""Tool Development Context:
                1. Follow tool development guide in docs/
                2. Use type hints and proper documentation
                3. Implement error handling and testing
                4. Integrate with context system""",
                context_type="system",
                metadata={
                    "name": "Tool Development Guidelines",
                    "category": "development",
                    "priority": 90
                }
            )
            logger.info("📚 Added tool development context")
            
            # Add documentation context
            await context_manager.add_context_to_task(
                task_id=task.id,
                content="""Documentation Requirements:
                1. Comprehensive docstrings
                2. Usage examples
                3. Error handling documentation
                4. Test cases documentation""",
                context_type="knowledge",
                metadata={
                    "name": "Documentation Guidelines",
                    "domain": "documentation",
                    "category": "guidelines",
                    "priority": 85
                }
            )
            logger.info("📝 Added documentation context")
            
            # Add test context
            await context_manager.add_context_to_task(
                task_id=task.id,
                content="""Testing Requirements:
                1. Unit tests for all functionality
                2. Integration tests for external dependencies
                3. Edge case testing
                4. Performance testing""",
                context_type="knowledge",
                metadata={
                    "name": "Testing Guidelines",
                    "domain": "testing",
                    "category": "guidelines",
                    "priority": 80
                }
            )
            logger.info("🧪 Added testing context")
        else:
            task = existing_tasks[0]
            # Update existing task with CrewAI config if not set
            if not task.crewai_config_id:
                task.crewai_config_id = str(crewai_config.id)
                persistence_model.tasks.update(str(task.id), task)
                logger.info(f"✨ Updated existing task with CrewAI config ID: {crewai_config.id}")
            logger.info(f"✨ Using existing task with ID: {task.id}")

        # Save updated state
        save_persistence_state(persistence_model, state_file)
        logger.info("💾 Saved state to file")
        
        return {
            'curried_proxy_id': curried_proxy_id,
            'tasksmanager_id': tasksmanager.id,
            'task_id': task.id
        }
        
    except Exception as e:
        logger.error(f"❌ Failed to setup dynamic tools state: {str(e)}")
        raise

async def add_langchain_tools_docs_to_knowledge_base(persistence_model: InMemoryPersistenceModel) -> None:
    """Add Langchain tools documentation to the knowledge base."""
    # Get URL tools instance
    url_tools = tools_catalog.get_tool_instance("url_tools")
    if not url_tools:
        print("🔴 URL tools not available")
        return
        
    # Load local documentation from file
    docs_path = Path("docs/langchain_tools/langchain_tools.md")
    if not docs_path.exists():
        print(f"🔴 Langchain tools documentation not found at {docs_path}")
        return
        
    with open(docs_path, 'r', encoding='utf-8') as f:
        local_docs = f.read()
    print(f"📚 Loaded local Langchain tools documentation from {docs_path}")
    
    # Create documentation links for navigation
    langchain_docs = {
        "Tool Creation Guide": "https://python.langchain.com/docs/modules/agents/tools/custom_tools",
        "Tool Concepts": "https://python.langchain.com/docs/modules/agents/tools/",
        "Tool Examples": "https://python.langchain.com/docs/integrations/tools",
        "Agent Tools": "https://python.langchain.com/docs/modules/agents/tools/",
        "Structured Tools": "https://python.langchain.com/docs/modules/agents/tools/structured"
    }
    
    # Fetch documentation from URLs
    print("🌐 Fetching documentation from URLs...")
    docs_content = []
    
    for title, url in langchain_docs.items():
        try:
            print(f"  📥 Fetching {title} from {url}")
            doc_result = await url_tools.get_documentation(url)
            docs_content.append({
                'title': title,
                'url': url,
                'content': doc_result['content'],
                'code_blocks': doc_result['code_blocks']
            })
            print(f"  ✅ Successfully fetched {title}")
        except Exception as e:
            print(f"  ❌ Error fetching {title}: {str(e)}")
            
    # Combine all documentation
    combined_docs = f"{local_docs}\n\n"
    for doc in docs_content:
        combined_docs += f"\n# {doc['title']}\n"
        combined_docs += f"Source: {doc['url']}\n\n"
        combined_docs += doc['content']
        
        if doc['code_blocks']:
            combined_docs += "\n\n## Code Examples\n"
            for block in doc['code_blocks']:
                combined_docs += f"\n```{block['language']}\n{block['code']}\n```\n"
    
    # Add to knowledge base
    knowledge_id = await knowledge_base.add_knowledge(
        content=combined_docs,
        domain="langchain",
        metadata={
            "type": "documentation",
            "category": "tools",
            "tags": ["tools", "documentation", "langchain"],
            "sources": list(langchain_docs.values())
        }
    )
    print(f"📚 Added combined Langchain documentation to knowledge base: {knowledge_id}")
    
    # Add documentation links to knowledge base
    docs_links = "# Langchain Tools Documentation Links\n\n"
    for title, url in langchain_docs.items():
        docs_links += f"- [{title}]({url})\n"
        
    await knowledge_base.add_knowledge(
        content=docs_links,
        domain="langchain",
        metadata={
            "type": "documentation_links",
            "category": "tools",
            "tags": ["tools", "documentation", "navigation"]
        }
    )
    print("🔗 Added documentation links to knowledge base")

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

if __name__ == "__main__":
    # Initialize persistence model without Streamlit context
    os.environ['STREAMLIT_RUN_MODE'] = 'script'
    persistence_model = PersistenceModelFactory.persistence_model("inmemory")
    
    try:
        import asyncio
        result = asyncio.run(setup_dynamic_tools_state(persistence_model))
        logger.info("✅ Dynamic tools state setup completed successfully")
        logger.info(f"📊 Result: {result}")
    except Exception as e:
        logger.error(f"❌ Failed to setup dynamic tools state: {str(e)}")
        sys.exit(1) 