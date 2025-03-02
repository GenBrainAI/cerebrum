from typing import Dict, List, Optional, Any, Union, Tuple
from pydantic import BaseModel
import json
import os
import time
from datetime import datetime
import random

class ParameterSet(BaseModel):
    """Configuration parameters for an AI model"""
    model_name: str
    temperature: float = 0.7
    top_p: float = 1.0
    max_tokens: int = 1000
    presence_penalty: float = 0.0
    frequency_penalty: float = 0.0
    stop_sequences: List[str] = []
    additional_params: Dict[str, Any] = {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API calls"""
        result = {
            "model": self.model_name,
            "temperature": self.temperature,
            "top_p": self.top_p,
            "max_tokens": self.max_tokens,
            "presence_penalty": self.presence_penalty,
            "frequency_penalty": self.frequency_penalty
        }
        
        if self.stop_sequences:
            result["stop"] = self.stop_sequences
            
        result.update(self.additional_params)
        return result

class TaskPerformance(BaseModel):
    """Performance metrics for a task execution"""
    task_id: str
    parameter_set_id: str
    execution_time: float
    token_count: int
    success: bool
    quality_score: Optional[float] = None
    error_message: Optional[str] = None
    created_at: datetime = datetime.now()

class TaskType(BaseModel):
    """Type of task with optimal parameter ranges"""
    name: str
    description: str
    optimal_parameter_ranges: Dict[str, Dict[str, Union[float, int, List[str]]]] = {}
    
    def get_parameter_bounds(self, param_name: str) -> Tuple[float, float]:
        """Get the min/max bounds for a numeric parameter"""
        if param_name not in self.optimal_parameter_ranges:
            # Default bounds
            if param_name == "temperature":
                return (0.0, 1.0)
            elif param_name == "top_p":
                return (0.0, 1.0)
            elif param_name == "max_tokens":
                return (50, 4000)
            elif param_name in ["presence_penalty", "frequency_penalty"]:
                return (-2.0, 2.0)
            else:
                return (0.0, 1.0)
                
        bounds = self.optimal_parameter_ranges[param_name]
        return (bounds.get("min", 0.0), bounds.get("max", 1.0))

class AIParameterManager:
    """Manages and optimizes AI model parameters"""
    
    def __init__(self, storage_path: Optional[str] = None):
        self.storage_path = storage_path or os.path.join(os.path.expanduser("~"), ".cerebrum", "parameters")
        os.makedirs(self.storage_path, exist_ok=True)
        
        self.parameter_sets: Dict[str, ParameterSet] = {}
        self.task_types: Dict[str, TaskType] = {}
        self.performance_history: List[TaskPerformance] = []
        
        self._load_data()
        self._register_default_task_types()
    
    def _load_data(self) -> None:
        """Load saved parameter sets and task types"""
        param_sets_path = os.path.join(self.storage_path, "parameter_sets.json")
        task_types_path = os.path.join(self.storage_path, "task_types.json")
        performance_path = os.path.join(self.storage_path, "performance_history.json")
        
        if os.path.exists(param_sets_path):
            with open(param_sets_path, 'r') as f:
                data = json.load(f)
                for param_id, param_data in data.items():
                    self.parameter_sets[param_id] = ParameterSet(**param_data)
                    
        if os.path.exists(task_types_path):
            with open(task_types_path, 'r') as f:
                data = json.load(f)
                for type_name, type_data in data.items():
                    self.task_types[type_name] = TaskType(**type_data)
                    
        if os.path.exists(performance_path):
            with open(performance_path, 'r') as f:
                data = json.load(f)
                for perf_data in data:
                    # Convert string datetime back to datetime object
                    if "created_at" in perf_data and isinstance(perf_data["created_at"], str):
                        perf_data["created_at"] = datetime.fromisoformat(perf_data["created_at"])
                    self.performance_history.append(TaskPerformance(**perf_data))
    
    def _save_data(self) -> None:
        """Save parameter sets, task types, and performance history to disk"""
        os.makedirs(self.storage_path, exist_ok=True)
        
        param_sets_path = os.path.join(self.storage_path, "parameter_sets.json")
        task_types_path = os.path.join(self.storage_path, "task_types.json")
        performance_path = os.path.join(self.storage_path, "performance_history.json")
        
        with open(param_sets_path, 'w') as f:
            data = {param_id: param_set.model_dump() for param_id, param_set in self.parameter_sets.items()}
            json.dump(data, f, indent=2)
            
        with open(task_types_path, 'w') as f:
            data = {type_name: task_type.model_dump() for type_name, task_type in self.task_types.items()}
            json.dump(data, f, indent=2)
            
        with open(performance_path, 'w') as f:
            # Convert datetime objects to ISO format strings for JSON serialization
            data = []
            for perf in self.performance_history:
                perf_dict = perf.model_dump()
                # Convert datetime objects to ISO format strings
                if isinstance(perf_dict["created_at"], datetime):
                    perf_dict["created_at"] = perf_dict["created_at"].isoformat()
                data.append(perf_dict)
            json.dump(data, f, indent=2)
    
    def _register_default_task_types(self) -> None:
        """Register default task types with optimal parameter ranges"""
        if "code_generation" not in self.task_types:
            self.task_types["code_generation"] = TaskType(
                name="code_generation",
                description="Generate code based on requirements",
                optimal_parameter_ranges={
                    "temperature": {"min": 0.1, "max": 0.7},
                    "top_p": {"min": 0.9, "max": 1.0},
                    "presence_penalty": {"min": 0.0, "max": 0.5},
                    "frequency_penalty": {"min": 0.0, "max": 0.5}
                }
            )
            
        if "creative_writing" not in self.task_types:
            self.task_types["creative_writing"] = TaskType(
                name="creative_writing",
                description="Generate creative text content",
                optimal_parameter_ranges={
                    "temperature": {"min": 0.7, "max": 1.0},
                    "top_p": {"min": 0.9, "max": 1.0},
                    "presence_penalty": {"min": 0.5, "max": 1.0},
                    "frequency_penalty": {"min": 0.5, "max": 1.0}
                }
            )
            
        if "factual_qa" not in self.task_types:
            self.task_types["factual_qa"] = TaskType(
                name="factual_qa",
                description="Answer factual questions accurately",
                optimal_parameter_ranges={
                    "temperature": {"min": 0.0, "max": 0.3},
                    "top_p": {"min": 0.9, "max": 1.0},
                    "presence_penalty": {"min": 0.0, "max": 0.3},
                    "frequency_penalty": {"min": 0.0, "max": 0.3}
                }
            )
            
        self._save_data()
    
    def create_parameter_set(self, model_name: str, **kwargs) -> str:
        """Create a new parameter set and return its ID"""
        param_set = ParameterSet(model_name=model_name, **kwargs)
        param_id = f"{model_name}_{int(time.time())}"
        self.parameter_sets[param_id] = param_set
        self._save_data()
        return param_id
    
    def get_parameter_set(self, param_id: str) -> Optional[ParameterSet]:
        """Get a parameter set by ID"""
        return self.parameter_sets.get(param_id)
    
    def update_parameter_set(self, param_id: str, **kwargs) -> bool:
        """Update a parameter set"""
        if param_id not in self.parameter_sets:
            return False
            
        current_params = self.parameter_sets[param_id].dict()
        current_params.update(kwargs)
        self.parameter_sets[param_id] = ParameterSet(**current_params)
        self._save_data()
        return True
    
    def delete_parameter_set(self, param_id: str) -> bool:
        """Delete a parameter set"""
        if param_id not in self.parameter_sets:
            return False
            
        del self.parameter_sets[param_id]
        self._save_data()
        return True
    
    def record_performance(self, task_id: str, parameter_set_id: str, 
                          execution_time: float, token_count: int, 
                          success: bool, quality_score: Optional[float] = None,
                          error_message: Optional[str] = None) -> None:
        """Record performance metrics for a task execution"""
        performance = TaskPerformance(
            task_id=task_id,
            parameter_set_id=parameter_set_id,
            execution_time=execution_time,
            token_count=token_count,
            success=success,
            quality_score=quality_score,
            error_message=error_message
        )
        
        self.performance_history.append(performance)
        self._save_data()
    
    def get_optimal_parameters(self, task_type: str, model_name: str) -> ParameterSet:
        """Get optimal parameters for a task type and model"""
        # Check if we have performance history for this task type
        task_performances = [p for p in self.performance_history 
                            if p.task_id.startswith(f"{task_type}_") and p.success]
        
        if not task_performances or task_type not in self.task_types:
            # No history, use defaults or create new
            if model_name in [p.model_name for p in self.parameter_sets.values()]:
                # Use existing parameter set for this model
                for param_id, param_set in self.parameter_sets.items():
                    if param_set.model_name == model_name:
                        return param_set
            
            # Create new parameter set with defaults for this task type
            task_type_obj = self.task_types.get(task_type)
            if task_type_obj:
                params = {
                    "model_name": model_name,
                    "temperature": random.uniform(*task_type_obj.get_parameter_bounds("temperature")),
                    "top_p": random.uniform(*task_type_obj.get_parameter_bounds("top_p")),
                    "presence_penalty": random.uniform(*task_type_obj.get_parameter_bounds("presence_penalty")),
                    "frequency_penalty": random.uniform(*task_type_obj.get_parameter_bounds("frequency_penalty"))
                }
                param_id = self.create_parameter_set(**params)
                return self.parameter_sets[param_id]
            else:
                # No task type info, use generic defaults
                param_id = self.create_parameter_set(model_name=model_name)
                return self.parameter_sets[param_id]
        
        # We have performance history, find the best performing parameters
        # Sort by quality score if available, otherwise by success rate
        if any(p.quality_score is not None for p in task_performances):
            # Use quality score
            best_performances = sorted(
                [p for p in task_performances if p.quality_score is not None],
                key=lambda x: x.quality_score,
                reverse=True
            )
        else:
            # Use execution time as a proxy for quality
            best_performances = sorted(
                task_performances,
                key=lambda x: x.execution_time
            )
        
        # Get the parameter set from the best performance
        if best_performances:
            best_param_id = best_performances[0].parameter_set_id
            if best_param_id in self.parameter_sets:
                return self.parameter_sets[best_param_id]
        
        # Fallback to defaults
        param_id = self.create_parameter_set(model_name=model_name)
        return self.parameter_sets[param_id]
    
    def evolve_parameters(self, task_type: str, model_name: str, 
                         exploration_rate: float = 0.2) -> ParameterSet:
        """Evolve parameters for a task type based on performance history"""
        # Get the current best parameters
        current_best = self.get_optimal_parameters(task_type, model_name)
        
        # Decide whether to explore or exploit
        if random.random() < exploration_rate:
            # Exploration: create a new parameter set with some randomness
            task_type_obj = self.task_types.get(task_type)
            if not task_type_obj:
                # No task type info, use generic exploration
                params = {
                    "model_name": model_name,
                    "temperature": max(0, min(1, current_best.temperature + random.uniform(-0.2, 0.2))),
                    "top_p": max(0, min(1, current_best.top_p + random.uniform(-0.1, 0.1))),
                    "presence_penalty": max(-2, min(2, current_best.presence_penalty + random.uniform(-0.5, 0.5))),
                    "frequency_penalty": max(-2, min(2, current_best.frequency_penalty + random.uniform(-0.5, 0.5)))
                }
            else:
                # Use task type bounds for exploration
                temp_bounds = task_type_obj.get_parameter_bounds("temperature")
                top_p_bounds = task_type_obj.get_parameter_bounds("top_p")
                presence_bounds = task_type_obj.get_parameter_bounds("presence_penalty")
                frequency_bounds = task_type_obj.get_parameter_bounds("frequency_penalty")
                
                params = {
                    "model_name": model_name,
                    "temperature": random.uniform(*temp_bounds),
                    "top_p": random.uniform(*top_p_bounds),
                    "presence_penalty": random.uniform(*presence_bounds),
                    "frequency_penalty": random.uniform(*frequency_bounds)
                }
            
            param_id = self.create_parameter_set(**params)
            return self.parameter_sets[param_id]
        else:
            # Exploitation: use the current best
            return current_best
    
    def analyze_parameter_impact(self, task_type: str) -> Dict[str, Dict[str, float]]:
        """Analyze the impact of different parameters on task performance"""
        task_performances = [p for p in self.performance_history 
                            if p.task_id.startswith(f"{task_type}_") and p.success]
        
        if not task_performances:
            return {}
            
        # Analyze impact of each parameter
        results = {}
        
        # Temperature analysis
        temp_ranges = [(0.0, 0.3), (0.3, 0.7), (0.7, 1.0)]
        temp_results = {}
        
        for temp_min, temp_max in temp_ranges:
            range_perfs = []
            for perf in task_performances:
                param_set = self.parameter_sets.get(perf.parameter_set_id)
                if param_set and temp_min <= param_set.temperature < temp_max:
                    range_perfs.append(perf)
            
            if range_perfs:
                avg_quality = sum(p.quality_score or 0 for p in range_perfs) / len(range_perfs)
                temp_results[f"{temp_min}-{temp_max}"] = avg_quality
        
        results["temperature"] = temp_results
        
        # Similar analysis could be implemented for other parameters
        # This is a simplified version focusing on temperature
        
        return results 