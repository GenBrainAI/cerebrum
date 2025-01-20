"""
Base plugin system for agent frameworks.
Provides the foundation for integrating different agent frameworks like CrewAI.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Union
from enum import Enum
from pydantic import BaseModel, Field

class AgentRole(str, Enum):
    """Standard roles for agents across frameworks."""
    ASSISTANT = "assistant"
    USER_PROXY = "user_proxy"
    CODE_AGENT = "code_agent"
    TOOL_AGENT = "tool_agent"

class AgentOutput(BaseModel):
    """Standardized output format for agent executions."""
    content: str = Field(description="The main output content from the agent")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata about the execution")
    artifacts: List[Dict[str, Any]] = Field(default_factory=list, description="Any artifacts produced (code, files, etc)")
    status: str = Field(description="Status of the execution (success, error, etc)")
    error: Optional[str] = Field(default=None, description="Error message if execution failed")
    format: str = Field(default="text", description="Output format (text, json, code, etc)")
    
class AgentConfig(BaseModel):
    """Common configuration for all agent frameworks."""
    role: AgentRole = Field(description="The role of the agent")
    model: str = Field(description="The model to use")
    instructions: str = Field(description="Instructions/system prompt for the agent")
    tools: List[Dict[str, Any]] = Field(default_factory=list, description="Tools available to the agent")
    temperature: float = Field(default=0.7, description="Temperature for model responses")
    max_tokens: int = Field(default=4000, description="Maximum tokens for responses")
    additional_config: Dict[str, Any] = Field(default_factory=dict, description="Framework-specific configuration")

class AgentFrameworkPlugin(ABC):
    """Base class for agent framework plugins."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self._is_initialized = False
    
    @abstractmethod
    async def initialize(self) -> bool:
        """Initialize the plugin."""
        pass
    
    @abstractmethod
    async def shutdown(self) -> bool:
        """Shutdown the plugin."""
        pass
    
    @abstractmethod
    async def create_agent(self, config: AgentConfig) -> Any:
        """Create an agent with the given configuration."""
        pass
    
    @abstractmethod
    async def execute_task(
        self,
        agent: Any,
        task: Dict[str, Any],
        stream: bool = False,
        context: Optional[Dict[str, Any]] = None
    ) -> AgentOutput:
        """Execute a task using the agent.
        
        Args:
            agent: The agent instance to use
            task: Task configuration and inputs
            stream: Whether to stream the output
            context: Additional context for the execution
            
        Returns:
            Standardized output containing the execution results
        """
        pass
    
    @abstractmethod
    def get_capabilities(self) -> List[str]:
        """Get list of plugin capabilities."""
        pass
    
    @property
    def is_initialized(self) -> bool:
        """Check if plugin is initialized."""
        return self._is_initialized
    
    @property
    def version(self) -> str:
        """Get plugin version."""
        return "1.0.0" 