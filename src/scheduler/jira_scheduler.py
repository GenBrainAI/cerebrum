from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.job import Job

scheduler = BackgroundScheduler()
scheduler.start()

def add_jira_job(job_id: str, func, interval: int) -> None:
    """Add a new Jira job to the scheduler."""
    scheduler.add_job(func, 'interval', minutes=interval, id=job_id)

def remove_jira_job(job_id: str) -> None:
    """Remove a Jira job from the scheduler."""
    scheduler.remove_job(job_id)

def get_all_jira_jobs() -> list:
    """Get all scheduled Jira jobs."""
    return [
        {
            "id": job.id,
            "next_run_time": job.next_run_time.isoformat() if job.next_run_time else None,
            "interval": job.trigger.interval.total_seconds() // 60
        }
        for job in scheduler.get_jobs()
    ]