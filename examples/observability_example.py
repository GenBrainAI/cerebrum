#!/usr/bin/env python3
"""
Example demonstrating the use of Cerebrum's Observability Layer components:
- Progress Tracker: For monitoring and visualizing system progress
- Intervention Interface: For human intervention in system operations
"""

import asyncio
import os
import logging
import tempfile
from datetime import datetime
import json
import base64

from src.server.observability.progress_tracker import (
    ProgressTracker, ProgressState, ProgressMetric, TrackingLevel
)
from src.server.observability.intervention_interface import (
    InterventionInterface, InterventionLevel, InterventionStatus,
    ResponseAction, InterventionContext, InterventionRequest, InterventionResponse
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Example task data
tasks = [
    {
        "id": "task1",
        "name": "Data Collection",
        "description": "Collect data from various sources",
        "type": "task",
        "expected_duration": 300,  # 5 minutes
        "metrics": {
            "sources_processed": {
                "name": "Sources Processed",
                "description": "Number of data sources processed",
                "current_value": 0,
                "target_value": 10,
                "unit": "sources"
            },
            "data_collected": {
                "name": "Data Collected",
                "description": "Amount of data collected",
                "current_value": 0,
                "target_value": 1000,
                "unit": "MB"
            }
        }
    },
    {
        "id": "task2",
        "name": "Data Processing",
        "description": "Process and clean collected data",
        "type": "task",
        "parent_id": "project1",
        "expected_duration": 600,  # 10 minutes
        "metrics": {
            "records_processed": {
                "name": "Records Processed",
                "description": "Number of records processed",
                "current_value": 0,
                "target_value": 5000,
                "unit": "records"
            }
        }
    },
    {
        "id": "task3",
        "name": "Model Training",
        "description": "Train machine learning model",
        "type": "task",
        "parent_id": "project1",
        "expected_duration": 1800,  # 30 minutes
        "metrics": {
            "epochs_completed": {
                "name": "Epochs Completed",
                "description": "Number of training epochs completed",
                "current_value": 0,
                "target_value": 100,
                "unit": "epochs"
            },
            "accuracy": {
                "name": "Model Accuracy",
                "description": "Current model accuracy",
                "current_value": 0,
                "target_value": 95,
                "unit": "%"
            }
        }
    },
    {
        "id": "project1",
        "name": "ML Pipeline Project",
        "description": "End-to-end ML pipeline implementation",
        "type": "project",
        "expected_duration": 3600,  # 60 minutes
    },
    {
        "id": "milestone1",
        "name": "Initial Data Collection Complete",
        "description": "First milestone: data collection finished",
        "type": "milestone",
        "parent_id": "project1",
    }
]

# Example of simulated work function
async def simulate_task_progress(progress_tracker, task_id, steps=10, delay=1.0):
    """Simulate progress for a task."""
    # Get task details
    task = next((t for t in tasks if t["id"] == task_id), None)
    if not task:
        return
    
    # Start task
    await progress_tracker.update_progress(
        task_id,
        state=ProgressState.IN_PROGRESS,
        message=f"Starting {task['name']}"
    )
    
    # Update metrics
    metrics = task.get("metrics", {})
    
    # Simulate progress
    for step in range(1, steps + 1):
        # Calculate completion percentage
        completion = (step / steps) * 100
        
        # Update metrics if present
        metric_updates = {}
        for metric_name, metric in metrics.items():
            target = metric["target_value"]
            current = (metric["target_value"] * step) / steps
            metric_updates[metric_name] = current
        
        # Update progress
        await progress_tracker.update_progress(
            task_id,
            completion_percentage=completion,
            message=f"Progress: {completion:.1f}%",
            metrics_updates=metric_updates
        )
        
        # Generate an intervention request at 50% progress
        if step == steps // 2 and task_id == "task3":
            yield "intervention_needed"
        
        # Simulate work
        await asyncio.sleep(delay)
    
    # Complete task
    await progress_tracker.update_progress(
        task_id,
        state=ProgressState.COMPLETED,
        completion_percentage=100.0,
        message=f"Completed {task['name']}"
    )
    
    # Mark milestone complete when data collection is done
    if task_id == "task1":
        await progress_tracker.update_progress(
            "milestone1",
            state=ProgressState.COMPLETED,
            completion_percentage=100.0,
            message="Milestone reached: Data collection complete"
        )

async def intervention_handler(intervention_interface, intervention_id):
    """Handle the intervention response."""
    print("\nIntervention requested. Waiting for response...")
    
    # Wait for response (in a real system, this would be a UI or API endpoint)
    # For this example, we'll auto-respond after a delay to simulate user action
    await asyncio.sleep(5)
    
    # Create a response
    response = InterventionResponse(
        action=ResponseAction.MODIFY,
        notes="Adjusted hyperparameters for better convergence",
        modifications={"learning_rate": 0.01, "batch_size": 64},
        responder="example_user"
    )
    
    # Submit response
    result = await intervention_interface.respond_to_intervention(
        intervention_id,
        response
    )
    
    print(f"Intervention response submitted: {result['status']}")
    return result

async def main():
    """Run the example."""
    # Create temporary directory for storing data
    data_dir = tempfile.mkdtemp()
    
    # Initialize Progress Tracker
    progress_tracker = ProgressTracker(config={
        "tracking_level": TrackingLevel.DETAILED,
        "snapshot_interval": 5,
        "storage_path": os.path.join(data_dir, "progress")
    })
    
    # Initialize Intervention Interface
    intervention_interface = InterventionInterface(config={
        "auto_approve_level": InterventionLevel.INFORMATION,
        "default_timeout": 60,
        "notification_channels": ["console"],
        "storage_path": os.path.join(data_dir, "interventions")
    })
    
    print(f"Data will be stored in: {data_dir}")
    
    # Register tasks with Progress Tracker
    print("\nRegistering tasks...")
    for task in tasks:
        # Convert metrics format
        metrics = {}
        for name, metric_data in task.get("metrics", {}).items():
            metrics[name] = ProgressMetric(
                name=metric_data["name"],
                description=metric_data["description"],
                current_value=metric_data["current_value"],
                target_value=metric_data["target_value"],
                unit=metric_data["unit"]
            )
        
        # Register task
        await progress_tracker.register_item(
            item_id=task["id"],
            item_type=task["type"],
            name=task["name"],
            description=task["description"],
            parent_id=task.get("parent_id"),
            expected_duration=task.get("expected_duration"),
            metrics=metrics
        )
    
    # Run the simulation
    print("\nStarting simulation...")
    intervention_id = None
    intervention_task = None
    
    # First run data collection
    async for event in simulate_task_progress(progress_tracker, "task1", steps=5, delay=0.5):
        if event == "intervention_needed":
            # This doesn't happen in task1
            pass
    
    # Generate a progress report and visualization
    print("\nProgress report after data collection:")
    report = await progress_tracker.get_progress_report()
    print(json.dumps(report["summary"], indent=2))
    
    # Now run data processing and model training in parallel
    task2 = simulate_task_progress(progress_tracker, "task2", steps=8, delay=0.7)
    task3 = simulate_task_progress(progress_tracker, "task3", steps=10, delay=1.0)
    
    # Process events from tasks
    task2_iter = task2.__aiter__()
    task3_iter = task3.__aiter__()
    task2_done = False
    task3_done = False
    
    while not (task2_done and task3_done):
        # Handle task2
        if not task2_done:
            try:
                event2 = await task2_iter.__anext__()
                if event2 == "intervention_needed":
                    # This doesn't happen in task2
                    pass
            except StopAsyncIteration:
                task2_done = True
        
        # Handle task3
        if not task3_done:
            try:
                event3 = await task3_iter.__anext__()
                if event3 == "intervention_needed":
                    # Request intervention
                    context = InterventionContext(
                        component="model_training",
                        operation="hyperparameter_tuning",
                        related_items=["task3"],
                        metrics={"accuracy": 45.5, "loss": 0.75},
                        system_state={"gpu_memory": "4.2GB", "cpu_usage": "78%"},
                        decision_factors={"convergence": "slow", "overfitting": "possible"}
                    )
                    
                    request = InterventionRequest(
                        title="Model Training Convergence Issue",
                        description="The model is converging slowly. Hyperparameter adjustments may be needed.",
                        level=InterventionLevel.WARNING,
                        context=context,
                        options=[
                            ResponseAction.CONTINUE,
                            ResponseAction.MODIFY,
                            ResponseAction.CANCEL
                        ],
                        timeout=60,
                        required_role="data_scientist"
                    )
                    
                    # Submit request
                    result = await intervention_interface.request_intervention(request)
                    intervention_id = result["intervention_id"]
                    
                    # Start handler
                    intervention_task = asyncio.create_task(
                        intervention_handler(intervention_interface, intervention_id)
                    )
            except StopAsyncIteration:
                task3_done = True
        
        # Slight delay to avoid tight loop
        await asyncio.sleep(0.1)
    
    # Wait for intervention to complete if it's still pending
    if intervention_task:
        await intervention_task
    
    # Create visualizations
    print("\nGenerating visualizations...")
    timeline = await progress_tracker.create_visualization(
        visualization_type="progress_timeline"
    )
    
    milestones = await progress_tracker.create_visualization(
        visualization_type="milestone_status"
    )
    
    dependencies = await progress_tracker.create_visualization(
        visualization_type="dependency_network"
    )
    
    # Save visualizations
    vis_dir = os.path.join(data_dir, "visualizations")
    os.makedirs(vis_dir, exist_ok=True)
    
    # Extract and save images
    for vis_name, vis_data in [
        ("timeline", timeline),
        ("milestones", milestones),
        ("dependencies", dependencies)
    ]:
        if "image" in vis_data and vis_data["image"].startswith("data:image/png;base64,"):
            # Extract base64 data
            img_data = vis_data["image"].split(",")[1]
            img_bytes = base64.b64decode(img_data)
            
            # Save to file
            with open(os.path.join(vis_dir, f"{vis_name}.png"), "wb") as f:
                f.write(img_bytes)
    
    # Final progress report
    print("\nFinal progress report:")
    report = await progress_tracker.get_progress_report()
    print(json.dumps(report["summary"], indent=2))
    
    # Save tracking data
    await progress_tracker.save_tracking_data(os.path.join(data_dir, "tracking_data.json"))
    
    # Show intervention results if any
    if intervention_id:
        print("\nIntervention details:")
        details = await intervention_interface.get_intervention(intervention_id)
        print(f"ID: {details['id']}")
        print(f"Status: {details['status']}")
        if details['response']:
            print(f"Action: {details['response']['action']}")
            print(f"Notes: {details['response']['notes']}")
            if details['response'].get('modifications'):
                print("Modifications:")
                for k, v in details['response']['modifications'].items():
                    print(f"  {k}: {v}")
    
    print(f"\nExperiment data saved to: {data_dir}")
    print("Example completed successfully.")

if __name__ == "__main__":
    asyncio.run(main()) 