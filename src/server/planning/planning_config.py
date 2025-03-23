"""
Planning Engine Configuration Manager.

This module provides configuration management for the Planning Engine,
including default settings, configuration loading, and validation.
"""

from typing import Dict, List, Optional, Any
import os
import json
import logging
from dataclasses import dataclass, field, asdict
from enum import Enum, auto

logger = logging.getLogger(__name__)

class OptimizationGoal(Enum):
    """Goals for planning optimization."""
    SPEED = auto()        # Optimize for faster planning
    QUALITY = auto()      # Optimize for higher quality plans
    EFFICIENCY = auto()   # Optimize for resource efficiency
    ADAPTABILITY = auto() # Optimize for plan flexibility
    BALANCED = auto()     # Balance all factors

@dataclass
class PlanningConfig:
    """Configuration for the Planning Engine."""
    
    # General settings
    default_storage_path: str = os.path.join(os.path.expanduser("~"), ".cerebrum", "planning_engine")
    optimization_goal: OptimizationGoal = OptimizationGoal.BALANCED
    max_plan_versions: int = 10
    
    # Goal Decomposition settings
    default_decomposition_strategy: str = "TOP_DOWN"
    max_decomposition_depth: int = 5
    min_subgoal_size: int = 2
    
    # Research Planning settings
    enable_auto_research: bool = True
    min_confidence_threshold: float = 0.6
    max_research_tasks: int = 20
    
    # Implementation Planning settings
    enable_auto_implementation: bool = True
    default_architecture_pattern: str = "MODULAR_MONOLITH"
    component_complexity_threshold: int = 7
    
    # Resource Allocation settings
    enable_auto_allocation: bool = True
    default_allocation_strategy: str = "PRIORITY_BASED"
    resource_buffer_percentage: float = 0.2
    
    # Performance settings
    enable_caching: bool = True
    cache_ttl_seconds: int = 3600
    parallel_planning: bool = True
    
    # Integration settings
    auto_integrate_plans: bool = True
    default_metrics_collection: bool = True
    
    # Custom settings
    custom_settings: Dict[str, Any] = field(default_factory=dict)

class PlanningConfigManager:
    """Manages configuration for the Planning Engine."""
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize the configuration manager.
        
        Args:
            config_path: Path to the configuration file
        """
        self.config_path = config_path or os.path.join(
            os.path.expanduser("~"), 
            ".cerebrum", 
            "config", 
            "planning_engine.json"
        )
        self.config = PlanningConfig()
        
        # Ensure the directory structure exists
        config_dir = os.path.dirname(self.config_path)
        try:
            os.makedirs(config_dir, exist_ok=True)
        except FileExistsError:
            # If there's a file with the same name as one of our directories
            # Try to create directory structure one level at a time
            parts = config_dir.split(os.sep)
            current_path = ""
            for part in parts:
                if not part:  # Skip empty parts (like leading slash)
                    continue
                if current_path:
                    current_path = os.path.join(current_path, part)
                else:
                    current_path = part
                
                if os.path.exists(current_path) and not os.path.isdir(current_path):
                    # If path exists but is not a directory, rename it
                    backup_path = f"{current_path}.bak"
                    os.rename(current_path, backup_path)
                    os.makedirs(current_path, exist_ok=True)
                else:
                    os.makedirs(current_path, exist_ok=True)
        
        # Load existing configuration if available
        if os.path.exists(self.config_path):
            self.load_config()
        else:
            # Save default configuration
            self.save_config()
    
    def load_config(self) -> PlanningConfig:
        """
        Load configuration from file.
        
        Returns:
            The loaded configuration
        """
        try:
            with open(self.config_path, "r") as f:
                config_dict = json.load(f)
            
            # Convert enum strings to enum values
            if "optimization_goal" in config_dict:
                config_dict["optimization_goal"] = OptimizationGoal[config_dict["optimization_goal"]]
            
            # Update configuration
            for key, value in config_dict.items():
                if hasattr(self.config, key):
                    setattr(self.config, key, value)
            
            logger.info(f"Loaded planning configuration from {self.config_path}")
            return self.config
        except Exception as e:
            logger.error(f"Error loading planning configuration: {e}")
            return self.config
    
    def save_config(self) -> bool:
        """
        Save configuration to file.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            # Convert to dictionary
            config_dict = asdict(self.config)
            
            # Convert enums to strings
            if "optimization_goal" in config_dict:
                config_dict["optimization_goal"] = self.config.optimization_goal.name
            
            with open(self.config_path, "w") as f:
                json.dump(config_dict, f, indent=4)
            
            logger.info(f"Saved planning configuration to {self.config_path}")
            return True
        except Exception as e:
            logger.error(f"Error saving planning configuration: {e}")
            return False
    
    def update_config(self, updates: Dict[str, Any]) -> PlanningConfig:
        """
        Update configuration with new values.
        
        Args:
            updates: Dictionary of updates to apply
            
        Returns:
            The updated configuration
        """
        try:
            # Handle enum conversions
            if "optimization_goal" in updates and isinstance(updates["optimization_goal"], str):
                updates["optimization_goal"] = OptimizationGoal[updates["optimization_goal"]]
            
            # Update configuration
            for key, value in updates.items():
                if hasattr(self.config, key):
                    setattr(self.config, key, value)
                else:
                    self.config.custom_settings[key] = value
            
            # Save updated configuration
            self.save_config()
            
            return self.config
        except Exception as e:
            logger.error(f"Error updating planning configuration: {e}")
            return self.config
    
    def get_component_config(self, component: str) -> Dict[str, Any]:
        """
        Get configuration specific to a component.
        
        Args:
            component: Component name (goal_decomposition, research, implementation, resource)
            
        Returns:
            Dictionary of component-specific configuration
        """
        config_dict = asdict(self.config)
        result = {}
        
        # Extract component-specific settings
        for key, value in config_dict.items():
            if key.startswith(component):
                result[key] = value
        
        # Include any custom settings
        for key, value in self.config.custom_settings.items():
            if key.startswith(component):
                result[key] = value
        
        return result 