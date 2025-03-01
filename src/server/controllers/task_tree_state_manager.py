from typing import Dict, Any, Optional, List
from datetime import datetime
from pathlib import Path
import json
import asyncio
import logging
from ..models.task import Task
from ..controllers.task_tree_flow import TaskTreeFlowManager, TaskNode
from ..models.task_tree_flow import TaskNodeState, TaskStatus

class TaskTreeStateManager:
    """Manages persistence and restoration of task tree state."""
    
    def __init__(self, base_path: str = "state/task_trees"):
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)
        self.logger = logging.getLogger(__name__)

    async def save_tree_state(self, tree_id: str, manager: TaskTreeFlowManager) -> bool:
        """Save task tree state to persistent storage."""
        try:
            state_file = self.base_path / f"{tree_id}.json"
            snapshot = manager.get_state_snapshot()
            
            # Add metadata
            snapshot['metadata'] = {
                'saved_at': datetime.now().isoformat(),
                'tree_id': tree_id,
                'version': '1.0',
                'stats': manager.get_execution_stats()
            }
            
            # Save atomically using temporary file
            temp_file = state_file.with_suffix('.tmp')
            with open(temp_file, 'w') as f:
                json.dump(snapshot, f, indent=2)
            temp_file.replace(state_file)
            
            self.logger.info(f"Saved tree state to {state_file}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error saving tree state: {str(e)}")
            return False

    async def load_tree_state(self, tree_id: str) -> Optional[Dict[str, Any]]:
        """Load task tree state from persistent storage."""
        try:
            state_file = self.base_path / f"{tree_id}.json"
            if not state_file.exists():
                return None
                
            with open(state_file, 'r') as f:
                state_data = json.load(f)
                
            return state_data
            
        except Exception as e:
            self.logger.error(f"Error loading tree state: {str(e)}")
            return None

    async def list_saved_trees(self) -> List[Dict[str, Any]]:
        """List all saved task trees with metadata."""
        try:
            trees = []
            for state_file in self.base_path.glob("*.json"):
                try:
                    with open(state_file, 'r') as f:
                        state_data = json.load(f)
                        trees.append({
                            'tree_id': state_data['metadata']['tree_id'],
                            'saved_at': state_data['metadata']['saved_at'],
                            'version': state_data['metadata']['version'],
                            'stats': state_data['metadata'].get('stats', {})
                        })
                except Exception as e:
                    self.logger.error(f"Error reading state file {state_file}: {str(e)}")
                    continue
            return sorted(trees, key=lambda x: x['saved_at'], reverse=True)
            
        except Exception as e:
            self.logger.error(f"Error listing saved trees: {str(e)}")
            return []

    async def delete_tree_state(self, tree_id: str) -> bool:
        """Delete a saved tree state."""
        try:
            state_file = self.base_path / f"{tree_id}.json"
            if state_file.exists():
                state_file.unlink()
                self.logger.info(f"Deleted tree state {tree_id}")
                return True
            return False
            
        except Exception as e:
            self.logger.error(f"Error deleting tree state: {str(e)}")
            return False

    async def cleanup_old_states(self, max_age_days: int = 30) -> int:
        """Clean up old state files."""
        try:
            now = datetime.now()
            deleted_count = 0
            
            for state_file in self.base_path.glob("*.json"):
                try:
                    # Check file age
                    file_time = datetime.fromtimestamp(state_file.stat().st_mtime)
                    age_days = (now - file_time).days
                    
                    if age_days > max_age_days:
                        state_file.unlink()
                        deleted_count += 1
                        
                except Exception as e:
                    self.logger.error(f"Error processing file {state_file}: {str(e)}")
                    continue
                    
            return deleted_count
            
        except Exception as e:
            self.logger.error(f"Error cleaning up old states: {str(e)}")
            return 0 