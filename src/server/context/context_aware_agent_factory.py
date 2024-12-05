from typing import List, Dict, Any, Optional
from uuid import UUID
from crewai import Agent
from pydantic import BaseModel

from src.server.context.context_provider import ContextProvider
from src.server.models.agent import AgentModel
from src.server.tools.tools_catalog import tools_catalog
from src.server.controllers.curried_proxy import CurriedProxy

class ContextualAgentConfig(BaseModel):
    """Configuration for context-aware agent creation."""
    code_context: bool = True  # Include code understanding context
    domain_context: bool = True  # Include domain knowledge
    system_context: bool = True  # Include system-level context
    context_priority: int = 0  # Priority for context ordering

class ContextAwareAgentFactory:
    """Factory for creating context-aware agents."""
    
    def __init__(self, context_provider: ContextProvider):
        self.context_provider = context_provider
        self.tools_catalog = tools_catalog
    
    async def create_agent(
        self,
        agent_model: AgentModel,
        config: ContextualAgentConfig,
        task_id: Optional[str] = None
    ) -> Agent:
        """Create a context-aware agent with relevant tools and knowledge."""
        try:
            # Gather context based on configuration
            contexts = []
            
            if config.code_context and task_id:
                code_contexts = await self.context_provider.get_task_contexts(
                    task_id=task_id,
                    context_type="vector",
                    limit=5
                )
                contexts.extend(code_contexts)
            
            if config.domain_context and task_id:
                domain_contexts = await self.context_provider.get_task_contexts(
                    task_id=task_id,
                    context_type="knowledge",
                    limit=5
                )
                contexts.extend(domain_contexts)
            
            if config.system_context and task_id:
                system_contexts = await self.context_provider.get_task_contexts(
                    task_id=task_id,
                    context_type="system",
                    limit=5
                )
                contexts.extend(system_contexts)
            
            # Create context-enhanced backstory
            enhanced_backstory = self._enhance_backstory(
                agent_model.backstory,
                contexts
            )
            
            # Get relevant tools based on context
            tools = await self._get_context_aware_tools(
                agent_model,
                contexts
            )
            
            # Create the agent with enhanced context
            agent = Agent(
                role=agent_model.role,
                goal=agent_model.goal,
                backstory=enhanced_backstory,
                tools=tools,
                verbose=True
            )
            
            return agent
            
        except Exception as e:
            raise ValueError(f"Error creating context-aware agent: {str(e)}")
    
    def _enhance_backstory(self, original_backstory: str, contexts: List[Dict[str, Any]]) -> str:
        """Enhance agent backstory with relevant context."""
        context_summaries = []
        
        for context in contexts:
            if context.get("relevance", 0) > 0.7:  # Only use highly relevant context
                summary = f"- {context['content'][:200]}..."  # Summarize long content
                context_summaries.append(summary)
        
        if context_summaries:
            enhanced = f"{original_backstory}\n\nAdditional Context:\n"
            enhanced += "\n".join(context_summaries)
            return enhanced
        
        return original_backstory
    
    async def _get_context_aware_tools(
        self,
        agent_model: AgentModel,
        contexts: List[Dict[str, Any]]
    ) -> List[Any]:
        """Get tools that are relevant to the agent's context."""
        tools = []
        
        # Get explicitly requested tools
        if agent_model.tools:
            for tool_model in agent_model.tools:
                tool_metadata = self.tools_catalog.get_tool(tool_model.name)
                if tool_metadata:
                    tool_instance = self.tools_catalog.get_tool_instance(tool_model.name)
                    if tool_instance:
                        tools.append(tool_instance)
        
        # Add additional tools based on context
        context_tools = set()
        for context in contexts:
            if "tool_references" in context.get("metadata", {}):
                tool_refs = context["metadata"]["tool_references"]
                context_tools.update(tool_refs)
        
        # Get instances of context-suggested tools
        for tool_name in context_tools:
            if tool_name not in [t.name for t in tools]:  # Avoid duplicates
                tool_metadata = self.tools_catalog.get_tool(tool_name)
                if tool_metadata:
                    tool_instance = self.tools_catalog.get_tool_instance(tool_name)
                    if tool_instance:
                        tools.append(tool_instance)
        
        return tools