def remove_proxy_from_task(self, task_id: str) -> bool:
    """Remove the CurriedProxy association from a task."""
    try:
        active_persistence = self.get_active_persistence()
        task = active_persistence.tasks.read(task_id)
        if not task:
            self.logger.error(f"Task not found: {task_id}")
            return False
            
        # Check if the task has a CurriedProxy
        if not task.curried_proxy_id:
            self.logger.warning(f"Task {task_id} has no associated CurriedProxy")
            return False
            
        # Remove the CurriedProxy association
        old_proxy_id = task.curried_proxy_id
        task.curried_proxy_id = None
        
        # Use update instead of save for TaskCrud
        try:
            active_persistence.tasks.update(task_id, task)
            self.logger.info(f"Removed CurriedProxy {old_proxy_id} from task {task_id}")
            return True
        except AttributeError:
            # If update doesn't exist, try other methods
            try:
                active_persistence.tasks.create(task)
                self.logger.info(f"Updated task {task_id} to remove CurriedProxy")
                return True
            except Exception as e:
                self.logger.error(f"Failed to update task: {str(e)}")
                return False
    except Exception as e:
        self.logger.error(f"Error removing proxy from task: {str(e)}")
        import traceback
        self.logger.error(traceback.format_exc())
        return False 