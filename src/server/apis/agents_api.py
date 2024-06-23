import os
from fastapi import FastAPI, HTTPException, APIRouter
from dotenv import load_dotenv
from ..models.agent import CreateCrewRequest, AutogenConfig
router = APIRouter()
from ..persistence.persistence_model_factory import PersistenceModelFactory
persistence_model = PersistenceModelFactory.persistence_model("inmemory")


@router.post("/agents/crewai")
async def create_crewai(request: CreateCrewRequest):
    try:
        crewai_config(create_crewai=request)
        persistence_model.crewai_config.create(crewai_config)
        return {"message": "Crew created", "crewai_config": crewai_config}   
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/agent/autogen")
async def autogen_agent(config: AutogenConfig):
    try:
        return {"message": "Not Implemented", "config": config}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
