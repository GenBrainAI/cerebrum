# src/server/tools/microservices_tool.py

from typing import Dict, Optional, List
import os
import yaml
from pathlib import Path

class MicroservicesTool:
    """Tool for managing microservices information"""
    
    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path or os.getenv('MICROSERVICES_CONFIG', 'config/microservices.yaml')
        self._load_config()

    def _load_config(self):
        """Load microservices configuration from YAML file"""
        if not os.path.exists(self.config_path):
            self._create_default_config()
        
        with open(self.config_path, 'r') as f:
            self.config = yaml.safe_load(f)

    def _create_default_config(self):
        """Create default configuration file if it doesn't exist"""
        default_config = {
            'microservices': {
                'auth-service': {
                    'repository': 'GenBrainAI/auth-service',
                    'terraform_path': 'terraform/network-policies.tf'
                },
                'user-service': {
                    'repository': 'GenBrainAI/user-service',
                    'terraform_path': 'terraform/network-policies.tf'
                }
            }
        }
        
        os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
        with open(self.config_path, 'w') as f:
            yaml.dump(default_config, f)
        
        self.config = default_config

    def get_repository(self, microservice_name: str) -> str:
        """Get the GitHub repository for a microservice"""
        if microservice_name not in self.config['microservices']:
            raise ValueError(f"Unknown microservice: {microservice_name}")
        return self.config['microservices'][microservice_name]['repository']

    def get_terraform_path(self, microservice_name: str) -> str:
        """Get the terraform configuration path for a microservice"""
        if microservice_name not in self.config['microservices']:
            raise ValueError(f"Unknown microservice: {microservice_name}")
        return self.config['microservices'][microservice_name]['terraform_path']

    def list_microservices(self) -> List[str]:
        """List all available microservices"""
        return list(self.config['microservices'].keys())

    def add_microservice(self, name: str, repository: str, terraform_path: str) -> None:
        """Add a new microservice to the configuration"""
        self.config['microservices'][name] = {
            'repository': repository,
            'terraform_path': terraform_path
        }
        with open(self.config_path, 'w') as f:
            yaml.dump(self.config, f)
