from typing import Dict, Any, Optional
from ..persistence.persistence_model_factory import PersistenceModelFactory
from ..controllers.curried_proxy import CurriedProxy

async def run_crew_task(task_id: str, task_input: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Execute a CrewAI task."""
    try:
        persistence_model = PersistenceModelFactory.persistence_model()
        
        # Get the task and its CrewAI configuration
        task = persistence_model.tasks.read(task_id)
        if not task or not task.crewai_info_id:
            raise ValueError(f"Task {task_id} not found or is not a CrewAI task")
            
        crewai_config = persistence_model.crewai_config.read(task.crewai_info_id)
        if not crewai_config:
            raise ValueError(f"CrewAI configuration {task.crewai_info_id} not found")
        
        # Create or get the curried proxy
        curried_proxy = None
        if task.curried_proxy_id:
            curried_proxy = persistence_model.curried_proxies.read(task.curried_proxy_id)
        else:
            curried_proxy = CurriedProxy()
        
        # Create and execute the crew
        from .agents_controller import create_crew
        crew = await create_crew(crewai_config.create_crew, curried_proxy)
        
        # Execute the crew with the provided input
        await crew.kickoff(task_input)
        
        return {"response": "run_crew_task kicked off successfully"}
    except Exception as e:
        return {"response": f"run_crew_task failed with error: {str(e)}"}