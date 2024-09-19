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
        for agent in request.agents:
            for tool in agent.class_tools:
                factory = ToolFactory(tool.name, curried_proxy)
                factory.set_curried_proxy()
            for tool in agent.tools:
                curried_proxy.add_tool(tool.name, tool)

        await create_crew(request, curried_proxy)
        crewai_config = CrewAIConfig(create_crew=request)
        config_id = persistence_model.crewai_config.create(crewai_config)
        curried_proxy_id = persistence_model.curried_proxies.create(curried_proxy).id

        return {"message": "Crew created", "crew_id": config_id, "curried_proxy_id": curried_proxy_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# @router.post("/agent/autogen")
# async def autogen_agent(config: AutogenConfig):
#     try:
#         return {"message": "Not Implemented", "config": config}
#     except Exception as e:
#         raise HTTPException(status_code=400, detail=str(e))
