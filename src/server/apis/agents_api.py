from fastapi import APIRouter, HTTPException
from ..models.agent import CreateCrewRequest, CrewAIConfig
from ..persistence.persistence_model_factory import PersistenceModelFactory
from ..controllers.agents_controller import create_crew
from ..controllers.curried_proxy import CurriedProxy
from ..tools.tool_factory import ToolFactory

from ..models.agent import CreateCrewRequest, AgentModel, CrewAIConfig
from ..controllers.curried_proxy import CurriedProxy
from ..tools.tools_catalog import tools_catalog
from ..tools.tool_factory import ToolFactory

router = APIRouter()
persistence_model = PersistenceModelFactory.persistence_model("inmemory")

async def initialize_agent_tools(agent: AgentModel, curried_proxy: CurriedProxy) -> None:
    """Initialize tools for an agent using the ToolsCatalog.
    
    Args:
        agent: The agent model containing tool configurations
        curried_proxy: The curried proxy to add tools to
    """
    if agent.class_tools:
        for tool_model in agent.class_tools:
            # Use ToolFactory for class-based tools
            factory = ToolFactory(tool_model.name, curried_proxy)
            factory.set_curried_proxy()
    
    if agent.tools:
        for tool_model in agent.tools:
            # Get the actual tool implementation from the catalog
            tool_metadata = tools_catalog.get_tool(tool_model.name)
            if tool_metadata is None:
                raise HTTPException(
                    status_code=400,
                    detail=f"Tool '{tool_model.name}' not found in the catalog"
                )
            
            # Get the tool instance from the catalog
            tool_instance = tools_catalog.get_tool_instance(tool_model.name)
            if tool_instance is None:
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to instantiate tool '{tool_model.name}'"
                )
            
            # Add the tool to the curried proxy with proper configuration
            curried_proxy.add_tool(
                name=tool_model.name,
                tool=tool_instance
            )

@router.post("/agent/crewai")
async def create_crewai(request: CreateCrewRequest):
    """Create a CrewAI crew with properly initialized tools."""
    try:
        # Create a new curried proxy for this crew
        curried_proxy = CurriedProxy()

        # Initialize tools for each agent
        for agent in request.agents:
            await initialize_agent_tools(agent, curried_proxy)

        # Create the crew using the configured tools
        await create_crew(request, curried_proxy)
        
        # Store the configuration and curried proxy
        crewai_config = CrewAIConfig(create_crew=request)
        config = persistence_model.crewai_config.create(crewai_config)
        proxy = persistence_model.curried_proxies.create(curried_proxy)

        return {
            "message": "Crew created",
            "crew_id": config.id,
            "curried_proxy_id": proxy.id
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# @router.post("/agent/autogen")
# async def autogen_agent(config: AutogenConfig):
#     try:
#         return {"message": "Not Implemented", "config": config}
#     except Exception as e:
#         raise HTTPException(status_code=400, detail=str(e))
