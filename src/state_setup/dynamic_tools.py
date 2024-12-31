import sys
from pathlib import Path
import asyncio
import os
import json
import dotenv
from typing import Any, Dict, List, Optional
import logging
import aiohttp
import unittest
import importlib.util
import coverage
from io import StringIO

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
    CrewAIConfig,
    CrewConfiguration
)
from server.models.persistence_models import StorageLocation, StorageType
from server.controllers.curried_proxy import CurriedProxy
from server.controllers.agents_controller import create_crew
from server.controllers.persistence_controller import save_to_storage
from server.models.curried_proxy_info import CurriedProxyInfo, ToolInfo
from server.context.context_provider import ContextProvider
from server.context.knowledge_base import KnowledgeBase
from server.context.context_database import ContextDatabase
from server.context.crew_ai_knowledge_bridge import CrewAIKnowledgeBridge
from server.context.context_aware_agent_factory import ContextAwareAgentFactory
from server.context.unified_context import UnifiedContextState, ContextConfig

class FileTools:
    """Tool for file operations."""
    
    def __init__(self, base_dir="src/tools"):
        self.base_dir = base_dir
        os.makedirs(base_dir, exist_ok=True)
        
    def save_implementation(self, code: str, tool_name: str) -> dict:
        """Save generated tool implementation to file."""
        try:
            logger.info(f"Attempting to save implementation for tool: {tool_name}")
            # Create a valid filename from the tool name
            filename = f"{tool_name.lower().replace(' ', '_')}.py"
            file_path = os.path.join(self.base_dir, filename)
            
            logger.info(f"Target file path: {file_path}")
            # Create the directory if it doesn't exist
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            # Save the code
            with open(file_path, 'w') as f:
                f.write(code)
            
            logger.info(f"Successfully saved implementation to: {file_path}")
            return {
                "status": "success",
                "message": f"Code saved to {file_path}",
                "path": file_path
            }
        except Exception as e:
            logger.error(f"Failed to save implementation: {str(e)}", exc_info=True)
            return {
                "status": "error",
                "message": f"Failed to save implementation: {str(e)}",
                "path": None
            }
            
    def save_tests(self, test_code: str, tool_name: str) -> dict:
        """Save test code to file."""
        try:
            logger.info(f"Attempting to save tests for tool: {tool_name}")
            # Create a valid filename from the tool name
            filename = f"test_{tool_name.lower().replace(' ', '_')}.py"
            test_dir = os.path.join(self.base_dir, "tests")
            file_path = os.path.join(test_dir, filename)
            
            logger.info(f"Target test file path: {file_path}")
            # Create the test directory if it doesn't exist
            os.makedirs(test_dir, exist_ok=True)
            
            # Save the test code
            with open(file_path, 'w') as f:
                f.write(test_code)
            
            logger.info(f"Successfully saved tests to: {file_path}")
            return {
                "status": "success",
                "message": f"Tests saved to {file_path}",
                "path": file_path
            }
        except Exception as e:
            logger.error(f"Failed to save tests: {str(e)}", exc_info=True)
            return {
                "status": "error",
                "message": f"Failed to save tests: {str(e)}",
                "path": None
            }

    async def read_documentation(self, file_path: str) -> Dict[str, Any]:
        """
        Read documentation from a file.
        
        :param file_path: Path to the documentation file
        :return: Dictionary containing file content
        """
        print(f"\n📖 Reading documentation from: {file_path}")
        try:
            with open(file_path, 'r') as f:
                content = f.read()
            print(f"✅ Successfully read documentation ({len(content)} chars)")
            return {"status": "success", "content": content}
        except Exception as e:
            error_msg = f"Error reading documentation: {str(e)}"
            logger.error(error_msg)
            print(f"❌ {error_msg}")
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
    
    def __init__(self):
        self.test_runner = unittest.TextTestRunner(verbosity=2)
        
    def run_unit_tests(self, test_file_path: str) -> dict:
        """Run unit tests and get results."""
        try:
            logger.info(f"Attempting to run tests from file: {test_file_path}")
            
            if not os.path.exists(test_file_path):
                logger.error(f"Test file not found: {test_file_path}")
                return {
                    "status": "error",
                    "message": f"Test file not found: {test_file_path}",
                    "results": None
                }
                
            logger.info(f"Loading test module from: {test_file_path}")
            # Load the test module
            spec = importlib.util.spec_from_file_location("test_module", test_file_path)
            if spec is None:
                logger.error(f"Failed to create module spec for: {test_file_path}")
                return {
                    "status": "error",
                    "message": "Failed to create module spec",
                    "results": None
                }
                
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            logger.info(f"Successfully loaded test module: {module.__name__}")
            
            # Find and run tests
            loader = unittest.TestLoader()
            suite = loader.loadTestsFromModule(module)
            logger.info(f"Found {suite.countTestCases()} test cases")
            
            result = self.test_runner.run(suite)
            logger.info(f"Test execution completed: {result.testsRun} tests run")
            
            return {
                "status": "success",
                "message": "Tests executed successfully",
                "results": {
                    "run": result.testsRun,
                    "failures": len(result.failures),
                    "errors": len(result.errors),
                    "skipped": len(result.skipped)
                }
            }
        except Exception as e:
            logger.error(f"Error running tests: {str(e)}", exc_info=True)
            return {
                "status": "error",
                "message": f"Failed to run tests: {str(e)}",
                "results": None
            }
            
    def validate_test_coverage(self, test_file_path: str) -> dict:
        """Calculate test coverage."""
        try:
            if not os.path.exists(test_file_path):
                return {
                    "status": "error",
                    "message": f"Test file not found: {test_file_path}",
                    "coverage": None
                }
                
            # Initialize coverage
            cov = coverage.Coverage()
            cov.start()
            
            # Run the tests
            test_result = self.run_unit_tests(test_file_path)
            
            # Stop coverage
            cov.stop()
            cov.save()
            
            # Get coverage report
            report = StringIO()
            cov.report(file=report)
            coverage_output = report.getvalue()
            
            return {
                "status": "success",
                "message": "Coverage analysis completed",
                "coverage": {
                    "report": coverage_output,
                    "test_results": test_result["results"]
                }
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to analyze coverage: {str(e)}",
                "coverage": None
            }

class ProxyTools:
    def __init__(self):
        self.proxy = CurriedProxy()
        logger.info("Initialized ProxyTools with new CurriedProxy instance")
        
    def register_tool(self, tool_path: str, tool_name: str) -> dict:
        """Register tool with global CurriedProxy."""
        try:
            logger.info(f"Attempting to register tool: {tool_name} from path: {tool_path}")
            # Import the tool module
            spec = importlib.util.spec_from_file_location(tool_name, tool_path)
            if spec is None:
                logger.error(f"Failed to create module spec for: {tool_path}")
                return {
                    "status": "error",
                    "message": "Failed to create module spec",
                    "tool_info": None
                }
            
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            logger.info(f"Successfully loaded module: {module.__name__}")
            
            # Get the tool class
            tool_class = getattr(module, tool_name)
            logger.info(f"Found tool class: {tool_class.__name__}")
            
            # Register the tool
            self.proxy.register_tool(tool_class)
            logger.info(f"Successfully registered tool: {tool_name}")
            
            return {
                "status": "success",
                "message": f"Tool {tool_name} registered successfully",
                "tool_info": {
                    "name": tool_name,
                    "path": tool_path,
                    "class": tool_class.__name__
                }
            }
        except Exception as e:
            logger.error(f"Failed to register tool: {str(e)}", exc_info=True)
            return {
                "status": "error",
                "message": f"Failed to register tool: {str(e)}",
                "tool_info": None
            }

class URLTools:
    def __init__(self):
        self.session = aiohttp.ClientSession()
        
    async def fetch_documentation(self, url: str) -> dict:
        """Fetch documentation from URL."""
        try:
            async with self.session.get(url) as response:
                if response.status != 200:
                    return {
                        "status": "error",
                        "message": f"Failed to fetch documentation: HTTP {response.status}",
                        "content": None
                    }
                    
                content = await response.text()
                return {
                    "status": "success",
                    "message": f"Documentation fetched from {url}",
                    "content": content
                }
        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to fetch documentation: {str(e)}",
                "content": None
            }
            
    async def close(self):
        """Close the aiohttp session."""
        await self.session.close()

class ContextConfig:
    """Configuration for context handling across different frameworks."""
    
    def __init__(self):
        self.vector_config = {
            "batch_size": 100,
            "max_retries": 3,
            "retry_delay": 1,
            "connection_timeout": 30,
            "max_concurrent_requests": 10,
            "chunk_size": 1000,
            "chunk_overlap": 100,
            "embedding_model": "text-embedding-3-small",
            "embeddings_provider": "openai"
        }
        
        self.knowledge_config = {
            "base_path": "persistent_state/context/knowledge_base",
            "domains": ["langchain", "tools", "patterns", "system"],
            "default_tags": ["documentation", "tools", "patterns"]
        }
        
        self.code_config = {
            "analyze_deps": True,
            "parse_docs": True,
            "deep_scan": False,
            "exclude_dirs": ["venv", "__pycache__", ".git", "node_modules"]
        }
        
        self.framework_configs = {
            "cerebrum": {
                "default_context_types": ["vector", "knowledge", "code"],
                "context_weights": {
                    "vector": 1.0,
                    "knowledge": 0.8,
                    "code": 0.6
                }
            },
            "crew_ai": {
                "default_context_types": ["vector", "knowledge"],
                "context_weights": {
                    "vector": 0.8,
                    "knowledge": 1.0
                },
                "min_relevance": 0.7
            }
        }

class UnifiedContextState:
    """Manages different types of contexts and their assignments to various agent frameworks."""
    
    def __init__(self, base_path: str = "persistent_state/context", config: Optional[ContextConfig] = None):
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)
        
        # Use provided config or create default
        self.config = config or ContextConfig()
        
        # Initialize different context stores with config
        self.vector_store = VectorStore(
            config=VectorStoreConfig(**self.config.vector_config),
            base_path=str(self.base_path / "vector_store")
        )
        self.knowledge_base = KnowledgeBase(
            base_path=str(self.base_path / "knowledge_base")
        )
        self.code_catalog = CodeCatalog()
        
        # Initialize context assignments
        self.context_assignments = {
            "cerebrum": {
                "tasks": {},
                "task_managers": {}
            },
            "crew_ai": {
                "agents": {},
                "tasks": {},
                "crews": {}
            }
        }
        
        # Initialize context bridges
        self.crew_bridge = None
        self.context_provider = None
        
    async def initialize(self):
        """Initialize context provider and bridges."""
        self.context_provider = ContextProvider()
        self.crew_bridge = CrewAIKnowledgeBridge(self.context_provider)
        
    async def assign_context_to_cerebrum_task(
        self,
        task_id: str,
        context_types: List[str],
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Assign context to a Cerebrum task."""
        self.context_assignments["cerebrum"]["tasks"][task_id] = {
            "types": context_types,
            "metadata": metadata or {}
        }
        
    async def assign_context_to_crew_agent(
        self,
        agent_id: str,
        context_types: List[str],
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Assign context to a CrewAI agent."""
        self.context_assignments["crew_ai"]["agents"][agent_id] = {
            "types": context_types,
            "metadata": metadata or {}
        }
        
    async def get_context_for_entity(
        self,
        entity_type: str,
        framework: str,
        entity_id: str,
        query: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get assigned context for a specific entity with framework-specific weights."""
        assignments = self.context_assignments.get(framework, {}).get(entity_type, {})
        entity_context = assignments.get(entity_id, {})
        
        if not entity_context:
            # Use default context types from framework config
            framework_config = self.config.framework_configs.get(framework, {})
            context_types = framework_config.get("default_context_types", [])
        else:
            context_types = entity_context["types"]
            
        if not context_types:
            return []
            
        # Get framework-specific weights and minimum relevance
        framework_config = self.config.framework_configs.get(framework, {})
        context_weights = framework_config.get("context_weights", {})
        min_relevance = framework_config.get("min_relevance", 0.0)
        
        contexts = []
        for context_type in context_types:
            weight = context_weights.get(context_type, 1.0)
            
            if context_type == "vector":
                vector_contexts = await self.context_provider._get_vector_contexts(
                    entity_id, query or ""
                )
                for ctx in vector_contexts:
                    ctx["weighted_relevance"] = ctx.get("relevance", 0) * weight
                contexts.extend(vector_contexts)
                
            elif context_type == "knowledge":
                knowledge_contexts = await self.context_provider._get_knowledge_contexts(
                    entity_id
                )
                for ctx in knowledge_contexts:
                    ctx["weighted_relevance"] = ctx.get("relevance", 0) * weight
                contexts.extend(knowledge_contexts)
                
            elif context_type == "code":
                code_contexts = await self.context_provider._get_code_contexts(
                    entity_id
                )
                for ctx in code_contexts:
                    ctx["weighted_relevance"] = ctx.get("relevance", 0) * weight
                contexts.extend(code_contexts)
        
        # Filter by minimum relevance and sort by weighted relevance
        filtered_contexts = [
            ctx for ctx in contexts 
            if ctx.get("weighted_relevance", 0) >= min_relevance
        ]
        filtered_contexts.sort(key=lambda x: x.get("weighted_relevance", 0), reverse=True)
        
        return filtered_contexts
        
    async def create_specialized_state(
        self,
        state_type: str,
        config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create a specialized state for different frameworks."""
        if state_type == "crew_ai":
            return await self._create_crew_ai_state(config)
        elif state_type == "cerebrum":
            return await self._create_cerebrum_state(config)
        else:
            raise ValueError(f"Unsupported state type: {state_type}")
            
    async def _create_crew_ai_state(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Create specialized state for CrewAI."""
        crew_config = CrewConfiguration(**config)
        
        # Enhance agents with context
        for agent in crew_config.agents:
            contexts = await self.get_context_for_entity(
                "agents", "crew_ai", agent.role, None
            )
            agent.backstory = self._enhance_backstory(agent.backstory, contexts)
            
        return {
            "crew_config": crew_config,
            "context_provider": self.context_provider,
            "crew_bridge": self.crew_bridge
        }
        
    async def _create_cerebrum_state(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Create specialized state for Cerebrum."""
        return {
            "context_provider": self.context_provider,
            "vector_store": self.vector_store,
            "knowledge_base": self.knowledge_base,
            "code_catalog": self.code_catalog
        }
        
    def _enhance_backstory(self, original_backstory: str, contexts: List[Dict[str, Any]]) -> str:
        """Enhance agent backstory with context."""
        if not contexts:
            return original_backstory
            
        enhanced = f"{original_backstory}\n\nRelevant Context:\n"
        for context in contexts:
            enhanced += f"\n• [{context['type']}] {context['content']}"
            if 'metadata' in context:
                enhanced += f" (Source: {context['metadata'].get('source', 'unknown')})"
                
        return enhanced

async def setup_dynamic_tools_state():
    """Initialize and configure the dynamic tools environment."""
    try:
        logger.info("Starting dynamic tools state setup")
        
        # Create context configuration
        context_config = ContextConfig()
        
        # Initialize unified context state with config
        unified_state = UnifiedContextState(config=context_config)
        await unified_state.initialize()
        
        # Initialize tools
        file_tools = FileTools()
        testing_tools = TestingTools()
        proxy_tools = ProxyTools()
        url_tools = URLTools()
        
        logger.info("Tools initialized successfully")
        
        # Create necessary directories
        os.makedirs("src/tools", exist_ok=True)
        os.makedirs("src/tools/tests", exist_ok=True)
        logger.info("Created necessary directories")
        
        # Initialize logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        logger.info("Setting up CrewAI configuration")
        # Set up CrewAI configuration with context
        crew_config = CrewConfiguration(
            agents=[
                AgentModel(
                    role="Security Manager",
                    goal="Ensure secure handling of credentials and sensitive data",
                    backstory="Security expert who validates and manages project credentials",
                    tools=[
                        ToolModel(
                            name="CredentialsTools.load_credentials",
                            description="Load credentials from .env file"
                        ),
                        ToolModel(
                            name="CredentialsTools.validate_credentials",
                            description="Validate required credentials are present and properly formatted"
                        )
                    ],
                    context={
                        "domain": "security",
                        "tags": ["credentials", "validation"]
                    }
                ),
                AgentModel(
                    role="LangChain Tool Architect",
                    goal="Design and specify Langchain tools",
                    backstory="""Expert in Langchain architecture who creates tool specifications.
                    Has deep knowledge of LangChain patterns and best practices.
                    Focuses on creating reusable and maintainable tool designs.""",
                    tools=[
                        ToolModel(
                            name="URLTools.fetch_documentation",
                            description="Fetch Langchain documentation from URL to understand patterns and requirements"
                        ),
                        ToolModel(
                            name="FileTools.read_documentation",
                            description="Read local documentation files for additional context"
                        )
                    ],
                    context={
                        "domain": "langchain",
                        "tags": ["architecture", "design", "tools"],
                        "documentation_path": "docs/langchain_tools/langchain_tools.md"
                    }
                ),
                AgentModel(
                    role="Tool Implementation Engineer",
                    goal="Implement Langchain tools following specifications and best practices",
                    backstory="""Senior developer with expertise in Langchain tool implementation.
                    Ensures code is saved in the correct location and follows project structure.
                    Implements tools based on architect's specifications while maintaining code quality.""",
                    tools=[
                        ToolModel(
                            name="FileTools.save_implementation",
                            description="Save generated tool implementation to file. Returns a dictionary with status, message, and path."
                        ),
                        ToolModel(
                            name="ProxyTools.register_tool",
                            description="Register tool with global CurriedProxy for dynamic loading"
                        )
                    ],
                    context={
                        "domain": "implementation",
                        "tags": ["coding", "langchain", "tools"],
                        "project_structure": {
                            "implementation_path": "src/tools",
                            "test_path": "src/tools/tests"
                        }
                    }
                ),
                AgentModel(
                    role="Test Engineer",
                    goal="Create comprehensive test suites for tools",
                    backstory="""Testing specialist who writes thorough unit tests and ensures they are saved in the correct location.
                    Creates tests that verify both functionality and edge cases.
                    Ensures test coverage meets project standards.""",
                    tools=[
                        ToolModel(
                            name="FileTools.save_tests",
                            description="Save test code to file. Returns a dictionary with status, message, and path."
                        )
                    ],
                    context={
                        "domain": "testing",
                        "tags": ["tests", "coverage", "quality"],
                        "test_requirements": {
                            "min_coverage": 80,
                            "required_test_types": ["unit", "integration"],
                            "test_path": "src/tools/tests"
                        }
                    }
                ),
                AgentModel(
                    role="QA Automation Engineer",
                    goal="Automate and execute tests, ensure quality",
                    backstory="""Quality assurance expert who automates testing processes and validates results.
                    Verifies that tests are properly saved and executable.
                    Ensures test coverage meets quality standards.""",
                    tools=[
                        ToolModel(
                            name="TestingTools.run_unit_tests",
                            description="Run unit tests and get results. Expects test file path from FileTools.save_tests response."
                        ),
                        ToolModel(
                            name="TestingTools.validate_test_coverage",
                            description="Calculate test coverage and ensure it meets quality standards. Expects test file path from FileTools.save_tests response."
                        )
                    ],
                    context={
                        "domain": "qa",
                        "tags": ["automation", "coverage", "validation"],
                        "quality_standards": {
                            "min_coverage": 80,
                            "max_complexity": 10
                        }
                    }
                )
            ],
            tasks=[
                TaskModel(
                    description="Load and validate project credentials",
                    expected_output="""Credentials validation report:
                    {
                        "status": "success",
                        "credentials": {
                            "loaded": true,
                            "validated": true,
                            "missing": []
                        }
                    }""",
                    agent_role="Security Manager",
                    context={
                        "required_credentials": ["API_KEY", "DATABASE_URL"]
                    }
                ),
                TaskModel(
                    description="Analyze Langchain documentation and create tool specification",
                    expected_output="""Documentation analysis report:
                    {
                        "status": "success",
                        "documentation": {
                            "pages_visited": ["<url_list>"],
                            "patterns_identified": ["<pattern_list>"],
                            "specification": "<tool_spec_content>"
                        }
                    }""",
                    agent_role="LangChain Tool Architect",
                    depends_on=["Load and validate project credentials"],
                    context={
                        "documentation_sources": [
                            "docs/langchain_tools/langchain_tools.md"
                        ],
                        "tool_type": "graphql",
                        "required_features": [
                            "query execution",
                            "schema validation",
                            "error handling"
                        ]
                    }
                ),
                TaskModel(
                    description="Implement the tool following Langchain patterns",
                    expected_output="""Implementation report:
                    {
                        "status": "success",
                        "implementation": {
                            "code_saved": true,
                            "file_path": "<file_path>",
                            "tool_registered": true
                        }
                    }""",
                    agent_role="Tool Implementation Engineer",
                    depends_on=["Analyze Langchain documentation and create tool specification"],
                    context={
                        "implementation_standards": {
                            "code_style": "pep8",
                            "max_complexity": 10,
                            "required_docstrings": true
                        }
                    }
                ),
                TaskModel(
                    description="Create comprehensive unit tests",
                    expected_output="""Test creation report:
                    {
                        "status": "success",
                        "tests": {
                            "saved": true,
                            "file_path": "<file_path>",
                            "test_cases": ["<test_case_list>"]
                        }
                    }""",
                    agent_role="Test Engineer",
                    depends_on=["Implement the tool following Langchain patterns"],
                    context={
                        "test_requirements": {
                            "coverage_threshold": 80,
                            "required_test_types": [
                                "unit",
                                "integration",
                                "edge_cases"
                            ]
                        }
                    }
                ),
                TaskModel(
                    description="Execute tests and validate coverage",
                    expected_output="""Test execution report:
                    {
                        "status": "success",
                        "execution": {
                            "tests_run": "<number>",
                            "passed": "<number>",
                            "failed": "<number>",
                            "coverage_percentage": "<number>"
                        }
                    }""",
                    agent_role="QA Automation Engineer",
                    depends_on=["Create comprehensive unit tests"],
                    context={
                        "quality_requirements": {
                            "min_coverage": 80,
                            "max_allowed_failures": 0
                        }
                    }
                )
            ],
        )
        
        # Create specialized states
        crew_state = await unified_state.create_specialized_state(
            "crew_ai",
            crew_config.dict()
        )
        
        cerebrum_state = await unified_state.create_specialized_state(
            "cerebrum",
            {}
        )
        
        # Return initialized state
        state = {
            "file_tools": file_tools,
            "testing_tools": testing_tools,
            "proxy_tools": proxy_tools,
            "url_tools": url_tools,
            "unified_state": unified_state,
            "crew_state": crew_state,
            "cerebrum_state": cerebrum_state,
            "logger": logger
        }
        
        logger.info("Dynamic tools state setup completed successfully")
        return state
        
    except Exception as e:
        logger.error(f"Failed to set up dynamic tools state: {str(e)}", exc_info=True)
        raise
    finally:
        if url_tools is not None:
            logger.info("Cleaning up URL tools session")
            await url_tools.close()

if __name__ == "__main__":
    asyncio.run(setup_dynamic_tools_state()) 