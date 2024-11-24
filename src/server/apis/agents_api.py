from fastapi import APIRouter, HTTPException
from ..models.agent import CreateCrewRequest, AgentModel, CrewAIConfig
from ..persistence.persistence_model_factory import PersistenceModelFactory
from ..controllers.agents_controller import create_crew
from ..controllers.curried_proxy import CurriedProxy
from ..tools.tools_catalog import tools_catalog

router = APIRouter()
persistence_model = PersistenceModelFactory.persistence_model("inmemory")

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
        crew = await create_crew(request, curried_proxy)
        
        # Get persistence model
        persistence_model = PersistenceModelFactory.persistence_model()
        
        # Store the configuration and curried proxy
        config = persistence_model.crewai_config.create(CrewAIConfig(create_crew=request))
        proxy = persistence_model.curried_proxies.create(curried_proxy)

        return {
            "message": "Crew created",
            "crew_id": config.id,
            "curried_proxy_id": proxy.id
        }

    except HTTPException:
        # Re-raise HTTP exceptions to maintain their status codes
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

def levenshtein_distance(s1: str, s2: str) -> int:
    """Calculate the Levenshtein distance between two strings."""
    if len(s1) < len(s2):
        return levenshtein_distance(s2, s1)

    if len(s2) == 0:
        return len(s1)

    previous_row = range(len(s2) + 1)
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row

    return previous_row[-1]

def find_similar_tools(target: str, available_tools: set[str], max_distance: int = 3) -> list[str]:
    """Find similar tool names using Levenshtein distance.
    
    Args:
        target: The tool name to find similarities for
        available_tools: Set of available tool names
        max_distance: Maximum Levenshtein distance to consider (default: 3)
        
    Returns:
        List of similar tool names, sorted by similarity
    """
    # Normalize names for comparison
    target_lower = target.lower()
    
    # Calculate distances and find similar tools
    similarities = []
    for tool in available_tools:
        # Check both full name and parts (for compound names)
        tool_lower = tool.lower()
        parts = tool_lower.split('.')
        
        # Calculate minimum distance considering both full name and last part
        distances = [levenshtein_distance(target_lower, tool_lower)]
        if len(parts) > 1:
            distances.append(levenshtein_distance(target_lower, parts[-1]))
        
        min_distance = min(distances)
        if min_distance <= max_distance:
            similarities.append((min_distance, tool))
    
    # Sort by distance (most similar first) and return tool names
    return [tool for _, tool in sorted(similarities)]

async def initialize_agent_tools(agent: AgentModel, curried_proxy: CurriedProxy) -> None:
    """Initialize tools for an agent using the ToolsCatalog."""
    # Get list of available tools for validation
    available_tools = set(tools_catalog.list_tools())
    
    # Handle class tools if present
    if agent.class_tools:
        from ..tools.tool_factory import ToolFactory
        for tool_model in agent.class_tools:
            if tool_model.name not in ToolFactory.TOOLS:
                similar_tools = find_similar_tools(tool_model.name, set(ToolFactory.TOOLS.keys()))
                error_msg = f"Tool '{tool_model.name}' not found in available factory tools."
                if similar_tools:
                    error_msg += f" Did you mean: {', '.join(similar_tools)}?"
                else:
                    error_msg += f" Available tools: {', '.join(ToolFactory.TOOLS.keys())}"
                
                raise HTTPException(status_code=400, detail=error_msg)
            
            try:
                factory = ToolFactory(tool_model.name, curried_proxy)
                factory.set_curried_proxy()
            except Exception as e:
                raise HTTPException(
                    status_code=400,
                    detail=f"Failed to initialize factory tool '{tool_model.name}': {str(e)}"
                )
    
    # Handle regular tools
    if agent.tools:
        for tool_model in agent.tools:
            # Check if the tool exists in catalog
            if not any(tool_name.startswith(tool_model.name) for tool_name in available_tools):
                # Find similar tool names using Levenshtein distance
                similar_tools = find_similar_tools(tool_model.name, available_tools)
                
                error_msg = f"Tool '{tool_model.name}' not found in the catalog."
                if similar_tools:
                    error_msg += f" Did you mean: {', '.join(similar_tools)}?"
                else:
                    error_msg += f" Available tools: {', '.join(sorted(available_tools))}"
                
                raise HTTPException(status_code=400, detail=error_msg)
            
            try:
                # Get tool metadata from catalog
                tool_metadata = tools_catalog.get_tool(tool_model.name)
                if tool_metadata is None:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Tool '{tool_model.name}' metadata not found in catalog"
                    )
                
                # Get tool instance from catalog and add to proxy
                tool_instance = tools_catalog.get_tool_instance(tool_model.name)
                curried_proxy.add_tool(tool_model.name, tool_instance)
                
            except HTTPException:
                raise
            except Exception as e:
                raise HTTPException(
                    status_code=400,
                    detail=f"Failed to initialize tool '{tool_model.name}': {str(e)}"
                )