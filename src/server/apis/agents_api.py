from fastapi import APIRouter, HTTPException
from ..models.agent import CreateCrewRequest, CrewAIConfig
from ..persistence.persistence_model_factory import PersistenceModelFactory
from ..controllers.agents_controller import create_crew, run_crewai
from ..controllers.curried_proxy import CurriedProxy
from ..tools.tool_factory import ToolFactory

router = APIRouter()
persistence_model = PersistenceModelFactory.persistence_model("inmemory")


@router.post("/agent/crewai")
async def create_crewai(request: CreateCrewRequest):
    try:
        curried_proxy = CurriedProxy()
        for tool in request.agent.tools:
            factory = ToolFactory(tool["name"], curried_proxy)
            factory.set_curried_proxy()
            
        curried_proxy.add_tool(tool.name, tool)
        crew = await create_crew(request, curried_proxy)
        crewai_config = CrewAIConfig(create_crew=request)
        config_id = persistence_model.crewai_config.create(crewai_config)
        return {"message": "Crew created", "crew_id": config_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# @router.post("/agent/autogen")
# async def autogen_agent(config: AutogenConfig):
#     try:
#         return {"message": "Not Implemented", "config": config}
#     except Exception as e:
#         raise HTTPException(status_code=400, detail=str(e))
