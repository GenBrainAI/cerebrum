import sys
from pathlib import Path
import asyncio
import os
import json
import dotenv
from typing import Any, Dict
import logging
import aiohttp

project_root = str(Path(__file__).parents[1])
sys.path.append(project_root)

# Setup logging
logger = logging.getLogger(__name__)

# Disable Streamlit warnings
logging.getLogger('streamlit').setLevel(logging.ERROR)

from server.tools.tools_catalog import tools_catalog
from server.persistence.persistence_model_factory import PersistenceModelFactory
from server.models.tasks_manager import TasksManager
from server.models.task import Task
from server.models.agent import (
    CreateCrewRequest, 
    AgentModel, 
    TaskModel, 
    ToolModel,
    ToolsProxyCollection,
    ObjectToolSpec,
    CrewAIConfig
)
from server.models.persistence_models import StorageLocation, StorageType
from server.controllers.curried_proxy import CurriedProxy
from server.controllers.agents_controller import create_crew
from server.controllers.persistence_controller import save_to_storage
from server.models.curried_proxy_info import CurriedProxyInfo, ToolInfo
from server.context.context_provider import ContextProvider
from server.context.knowledge_base import KnowledgeBase
from server.context.context_database import ContextDatabase

class FileTools:
    """Tool for handling file operations related to documentation and code."""
    
    def __init__(self, base_dir: str = "tools"):
        self.base_dir = base_dir
        os.makedirs(base_dir, exist_ok=True)

    async def read_documentation(self, file_path: str) -> str:
        """
        Read documentation from a file.
        
        :param file_path: Path to the documentation file
        :return: Content of the documentation file
        """
        try:
            with open(file_path, 'r') as f:
                return f.read()
        except Exception as e:
            logger.error(f"Error reading documentation: {str(e)}")
            return f"Error: {str(e)}"

    async def save_implementation(self, code: str, file_path: str) -> Dict[str, Any]:
        """
        Save generated code to a file.
        
        :param code: The code content to save
        :param file_path: Path where to save the code
        :return: Dictionary containing save status
        """
        try:
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            with open(file_path, 'w') as f:
                f.write(code)
            return {"status": "success", "message": f"Code saved to {file_path}"}
        except Exception as e:
            logger.error(f"Error saving implementation: {str(e)}")
            return {"status": "error", "message": str(e)}

    async def save_tests(self, test_code: str, file_path: str) -> Dict[str, Any]:
        """
        Save test code to a file.
        
        :param test_code: The test code content to save
        :param file_path: Path where to save the tests
        :return: Dictionary containing save status
        """
        try:
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            with open(file_path, 'w') as f:
                f.write(test_code)
            return {"status": "success", "message": f"Tests saved to {file_path}"}
        except Exception as e:
            logger.error(f"Error saving tests: {str(e)}")
            return {"status": "error", "message": str(e)}

class CredentialsTools:
    """Tool for managing project credentials."""
    
    def __init__(self, env_path: str = None):
        self.env_path = env_path or os.path.join(project_root, '.env')

    async def load_credentials(self) -> Dict[str, Any]:
        """
        Load credentials from .env file.
        
        :return: Dictionary containing credentials or error message
        """
        try:
            creds = dotenv.dotenv_values(self.env_path)
            return {"status": "success", "credentials": creds}
        except Exception as e:
            logger.error(f"Error loading credentials: {str(e)}")
            return {"status": "error", "message": str(e)}

    async def validate_credentials(self, credentials: Dict[str, str]) -> Dict[str, Any]:
        """
        Validate that required credentials are present.
        
        :param credentials: Dictionary of credentials to validate
        :return: Dictionary containing validation status
        """
        required_keys = ['API_KEY', 'DATABASE_URL']
        missing = [key for key in required_keys if key not in credentials]
        if missing:
            return {
                "status": "error",
                "message": f"Missing required credentials: {', '.join(missing)}"
            }
        return {"status": "success", "message": "All required credentials present"}

class TestingTools:
    """Tool for running tests and validating coverage."""
    
    def __init__(self, test_dir: str = "tests"):
        self.test_dir = test_dir

    async def run_unit_tests(self, test_file: str) -> Dict[str, Any]:
        """
        Run unit tests and return results.
        
        :param test_file: Path to the test file to run
        :return: Dictionary containing test results
        """
        try:
            import unittest
            loader = unittest.TestLoader()
            suite = loader.discover(os.path.dirname(test_file))
            runner = unittest.TextTestRunner(verbosity=2)
            result = runner.run(suite)
            return {
                "status": "success",
                "results": {
                    "tests_run": result.testsRun,
                    "errors": len(result.errors),
                    "failures": len(result.failures),
                    "skipped": len(result.skipped)
                }
            }
        except Exception as e:
            logger.error(f"Error running tests: {str(e)}")
            return {"status": "error", "message": str(e)}

    async def validate_test_coverage(self, test_file: str) -> Dict[str, Any]:
        """
        Calculate test coverage percentage.
        
        :param test_file: Path to the test file to analyze
        :return: Dictionary containing coverage results
        """
        try:
            import coverage
            cov = coverage.Coverage()
            cov.start()
            await self.run_unit_tests(test_file)
            cov.stop()
            coverage_result = cov.report()
            return {
                "status": "success",
                "coverage_percentage": coverage_result
            }
        except ImportError:
            return {
                "status": "error",
                "message": "Coverage package not installed"
            }
        except Exception as e:
            logger.error(f"Error calculating coverage: {str(e)}")
            return {"status": "error", "message": str(e)}

class ProxyTools:
    """Tool for managing dynamic tool registration."""
    
    def __init__(self):
        self.registered_tools = set()

    async def register_tool(self, tool_name: str, tool_instance: Any) -> Dict[str, Any]:
        """
        Register a tool with the global CurriedProxy.
        
        :param tool_name: Name to register the tool under
        :param tool_instance: The tool instance to register
        :return: Dictionary containing registration status
        """
        try:
            from server.controllers.curried_proxy import global_proxy
            global_proxy.add_tool(tool_name, tool_instance)
            self.registered_tools.add(tool_name)
            return {
                "status": "success",
                "message": f"Tool {tool_name} registered successfully"
            }
        except Exception as e:
            logger.error(f"Error registering tool: {str(e)}")
            return {"status": "error", "message": str(e)}

class URLTools:
    """Tool for fetching data from URLs."""
    
    async def get_data_from_url(self, url: str) -> str:
        """
        Fetch content from a URL using aiohttp.
        
        :param url: The URL to fetch content from
        :return: The content fetched from the URL
        """
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    return await response.text()
        except Exception as e:
            logger.error(f"Error fetching URL: {str(e)}")
            return f"Error: {str(e)}"

async def setup_dynamic_tools_state():
    """Setup CrewAI configuration for dynamic Langchain tools generation."""
    try:
        # Initialize persistence model without Streamlit context
        os.environ['STREAMLIT_RUN_MODE'] = 'script'
        persistence_model = PersistenceModelFactory.persistence_model("inmemory")
        
        # Create curried proxy and add tools with proper module info
        curried_proxy = CurriedProxy()
        
        # Add tools with proper module information for serialization
        tool_infos = [
            ToolInfo(
                name="FetchURL",
                type="function",
                tool_data={
                    "name": "fetch_url",
                    "description": "Fetch content from a URL using HTTP GET request",
                    "function_module": "aiohttp",
                    "class_name": "ClientSession",
                    "is_method": True,
                    "parameters": {
                        "url": {
                            "type": "string",
                            "description": "The URL to fetch content from",
                            "required": True
                        },
                        "headers": {
                            "type": "object",
                            "description": "Optional HTTP headers to include in the request",
                            "required": False
                        }
                    },
                    "returns": {
                        "type": "string",
                        "description": "The content fetched from the URL"
                    }
                }
            ),
            ToolInfo(
                name="FileTools",
                type="function",
                tool_data={
                    "name": "FileTools",
                    "description": "File operations for tool management",
                    "function_module": "src.state_setup.dynamic_tools",
                    "class_name": "FileTools",
                    "is_method": True,
                    "parameters": {
                        "base_dir": {
                            "type": "string",
                            "description": "Base directory for file operations",
                            "required": False,
                            "default": "tools"
                        }
                    }
                }
            ),
            ToolInfo(
                name="CredentialsTools",
                type="function",
                tool_data={
                    "name": "CredentialsTools",
                    "description": "Credentials management tools",
                    "function_module": "src.state_setup.dynamic_tools",
                    "class_name": "CredentialsTools",
                    "is_method": True,
                    "parameters": {
                        "env_path": {
                            "type": "string",
                            "description": "Path to the .env file",
                            "required": False
                        }
                    }
                }
            ),
            ToolInfo(
                name="TestingTools",
                type="function",
                tool_data={
                    "name": "TestingTools",
                    "description": "Testing and validation tools",
                    "function_module": "src.state_setup.dynamic_tools",
                    "class_name": "TestingTools",
                    "is_method": True,
                    "parameters": {
                        "test_dir": {
                            "type": "string",
                            "description": "Directory containing test files",
                            "required": False,
                            "default": "tests"
                        }
                    }
                }
            ),
            ToolInfo(
                name="ProxyTools",
                type="function",
                tool_data={
                    "name": "ProxyTools",
                    "description": "Dynamic tool registration",
                    "function_module": "src.state_setup.dynamic_tools",
                    "class_name": "ProxyTools",
                    "is_method": True,
                    "parameters": {
                        "tool_name": {
                            "type": "string",
                            "description": "Name to register the tool under",
                            "required": True
                        },
                        "tool_instance": {
                            "type": "object",
                            "description": "The tool instance to register",
                            "required": True
                        }
                    },
                    "returns": {
                        "type": "object",
                        "description": "Dictionary containing registration status and message"
                    }
                }
            ),
            ToolInfo(
                name="URLTools",
                type="function",
                tool_data={
                    "name": "get_data_from_url",
                    "description": "Fetch content from a URL using HTTP GET request",
                    "function_module": "src.state_setup.dynamic_tools",
                    "class_name": "URLTools",
                    "is_method": True,
                    "parameters": {
                        "url": {
                            "type": "string",
                            "description": "The URL to fetch content from",
                            "required": True
                        }
                    },
                    "returns": {
                        "type": "string",
                        "description": "The content fetched from the URL"
                    }
                }
            )
        ]
        
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
        
        # Create proxy info and reconstruct proxy
        proxy_info = CurriedProxyInfo(tools=tool_infos)
        curried_proxy = CurriedProxy.from_info(proxy_info)
        
        # Register tools in the catalog
        file_tools = FileTools()
        credentials_tools = CredentialsTools()
        testing_tools = TestingTools()
        proxy_tools = ProxyTools()
        url_tools = URLTools()
        
        tools_catalog.register_tool(file_tools, "FileTools")
        tools_catalog.register_tool(credentials_tools, "CredentialsTools")
        tools_catalog.register_tool(testing_tools, "TestingTools")
        tools_catalog.register_tool(proxy_tools, "ProxyTools")
        tools_catalog.register_tool(url_tools, "URLTools")
        
        print("🛠️ Registered tools in catalog")
        
        # Store curried proxy in persistence model
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
            model="gpt-4o",
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
        result = save_to_storage(state_location)
        print(f"💾 Dynamic tools state saved: {result}")
        
        # Return state info
        return {
            "tasksmanager_id": tasksmanager.id,
            "task_id": task.id,
            "curried_proxy_id": curried_proxy_id,
            "crewai_config_id": crewai_config.id
        }
        
    except Exception as e:
        print(f"Error setting up dynamic tools state: {str(e)}")
        raise

if __name__ == "__main__":
    asyncio.run(setup_dynamic_tools_state()) 