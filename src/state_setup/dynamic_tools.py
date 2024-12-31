import sys
from pathlib import Path
import asyncio
import os
import json
import dotenv
from typing import Any, Dict
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

class FileTools:
    """Tool for file operations."""
    
    def __init__(self, base_dir="src/tools"):
        self.base_dir = base_dir
        os.makedirs(base_dir, exist_ok=True)
        
    def save_implementation(self, code: str, tool_name: str) -> dict:
        """Save generated tool implementation to file."""
        try:
            # Create a valid filename from the tool name
            filename = f"{tool_name.lower().replace(' ', '_')}.py"
            file_path = os.path.join(self.base_dir, filename)
            
            # Create the directory if it doesn't exist
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            # Save the code
            with open(file_path, 'w') as f:
                f.write(code)
                
            return {
                "status": "success",
                "message": f"Code saved to {file_path}",
                "path": file_path
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to save implementation: {str(e)}",
                "path": None
            }
            
    def save_tests(self, test_code: str, tool_name: str) -> dict:
        """Save test code to file."""
        try:
            # Create a valid filename from the tool name
            filename = f"test_{tool_name.lower().replace(' ', '_')}.py"
            test_dir = os.path.join(self.base_dir, "tests")
            file_path = os.path.join(test_dir, filename)
            
            # Create the test directory if it doesn't exist
            os.makedirs(test_dir, exist_ok=True)
            
            # Save the test code
            with open(file_path, 'w') as f:
                f.write(test_code)
                
            return {
                "status": "success",
                "message": f"Tests saved to {file_path}",
                "path": file_path
            }
        except Exception as e:
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
        
    def register_tool(self, tool_path: str, tool_name: str) -> dict:
        """Register tool with global CurriedProxy."""
        try:
            # Import the tool module
            spec = importlib.util.spec_from_file_location(tool_name, tool_path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            # Get the tool class
            tool_class = getattr(module, tool_name)
            
            # Register the tool
            self.proxy.register_tool(tool_class)
            
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

async def setup_dynamic_tools_state():
    """Initialize and configure the dynamic tools environment."""
    url_tools = None  # Initialize outside try block for cleanup
    try:
        # Initialize tools
        file_tools = FileTools()
        testing_tools = TestingTools()
        proxy_tools = ProxyTools()
        url_tools = URLTools()  # Store reference for cleanup
        
        # Create necessary directories
        os.makedirs("src/tools", exist_ok=True)
        os.makedirs("src/tools/tests", exist_ok=True)
        
        # Initialize logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        logger = logging.getLogger(__name__)
        
        # Set up CrewAI configuration
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
                    ]
                ),
                AgentModel(
                    role="LangChain Tool Architect",
                    goal="Design and specify Langchain tools",
                    backstory="Expert in Langchain architecture who creates tool specifications",
                    tools=[
                        ToolModel(
                            name="URLTools.fetch_documentation",
                            description="Fetch Langchain documentation from URL to understand patterns and requirements"
                        ),
                        ToolModel(
                            name="FileTools.read_documentation",
                            description="Read local documentation files for additional context"
                        )
                    ]
                ),
                AgentModel(
                    role="Tool Implementation Engineer",
                    goal="Implement Langchain tools following specifications and best practices",
                    backstory="Senior developer with expertise in Langchain tool implementation. Ensures code is saved in the correct location and follows project structure.",
                    tools=[
                        ToolModel(
                            name="FileTools.save_implementation",
                            description="Save generated tool implementation to file. Returns a dictionary with status, message, and path."
                        ),
                        ToolModel(
                            name="ProxyTools.register_tool",
                            description="Register tool with global CurriedProxy for dynamic loading"
                        )
                    ]
                ),
                AgentModel(
                    role="Test Engineer",
                    goal="Create comprehensive test suites for tools",
                    backstory="Testing specialist who writes thorough unit tests and ensures they are saved in the correct location.",
                    tools=[
                        ToolModel(
                            name="FileTools.save_tests",
                            description="Save test code to file. Returns a dictionary with status, message, and path."
                        )
                    ]
                ),
                AgentModel(
                    role="QA Automation Engineer",
                    goal="Automate and execute tests, ensure quality",
                    backstory="Quality assurance expert who automates testing processes and validates results. Verifies that tests are properly saved and executable.",
                    tools=[
                        ToolModel(
                            name="TestingTools.run_unit_tests",
                            description="Run unit tests and get results. Expects test file path from FileTools.save_tests response."
                        ),
                        ToolModel(
                            name="TestingTools.validate_test_coverage",
                            description="Calculate test coverage and ensure it meets quality standards. Expects test file path from FileTools.save_tests response."
                        )
                    ]
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
                    agent_role="Security Manager"
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
                    depends_on=["Load and validate project credentials"]
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
                    depends_on=["Analyze Langchain documentation and create tool specification"]
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
                    depends_on=["Implement the tool following Langchain patterns"]
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
                    depends_on=["Create comprehensive unit tests"]
                )
            ],
        )
        
        # Return initialized state
        return {
            "file_tools": file_tools,
            "testing_tools": testing_tools,
            "proxy_tools": proxy_tools,
            "url_tools": url_tools,
            "crew_config": crew_config,
            "logger": logger
        }
        
    except Exception as e:
        logger.error(f"Failed to set up dynamic tools state: {str(e)}")
        raise
    finally:
        # Clean up aiohttp session if it was created
        if url_tools is not None:
            await url_tools.close()

if __name__ == "__main__":
    asyncio.run(setup_dynamic_tools_state()) 