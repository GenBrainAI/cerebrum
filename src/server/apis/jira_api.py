from fastapi import APIRouter, HTTPException
from ..models.jira_config import JiraConfig
from ..controllers.jira_controller import JiraController
from ..tools.jira_service import JiraService
from ...scheduler.jira_scheduler import add_jira_job, remove_jira_job, get_all_jira_jobs
from ..persistence.persistence_model_factory import PersistenceModelFactory

router = APIRouter()
persistence_model = PersistenceModelFactory.persistence_model("inmemory")

@router.post("/jira/configure", tags=["Configuration"], summary="Configure Jira Settings")
async def configure_jira(config: JiraConfig):
    jira_service = JiraService(config.jira_url, config.jira_username, config.jira_api_token)
    controller = JiraController(config, jira_service)
    controller_id = persistence_model.jira_controller.create(controller)
    add_jira_job(controller_id, controller.fetch_new_tickets, config.schedule_interval)
    return {"message": "Jira configuration created successfully", "controller_id": controller_id}

@router.put("/jira/configure/{controller_id}", tags=["Configuration"], summary="Update Jira Settings")
async def update_jira_config(controller_id: str, config: JiraConfig):
    controller = persistence_model.jira_controller.read(controller_id)
    if not controller:
        raise HTTPException(status_code=404, detail="Jira controller not found")
    jira_service = JiraService(config.jira_url, config.jira_username, config.jira_api_token)
    controller.update_config(config, jira_service)
    persistence_model.jira_controller.update(controller_id, controller)
    remove_jira_job(controller_id)
    add_jira_job(controller_id, controller.fetch_new_tickets, config.schedule_interval)
    return {"message": "Jira configuration updated successfully"}

@router.delete("/jira/configure/{controller_id}", tags=["Configuration"], summary="Delete Jira Configuration")
async def delete_jira_config(controller_id: str):
    controller = persistence_model.jira_controller.read(controller_id)
    if not controller:
        raise HTTPException(status_code=404, detail="Jira controller not found")
    persistence_model.jira_controller.delete(controller_id)
    remove_jira_job(controller_id)
    return {"message": "Jira configuration deleted successfully"}

@router.get("/jira/configurations", tags=["Configuration"], summary="Get All Jira Configurations")
async def get_jira_configurations():
    return get_all_jira_jobs()