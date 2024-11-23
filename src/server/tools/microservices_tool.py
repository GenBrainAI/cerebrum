# src/server/tools/microservices_tool.py

from typing import Dict, Optional, List
import os
import yaml
from pathlib import Path

class MicroservicesTool:
    """
    Tool for managing microservices configuration and information.
    """
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize the Microservices Tool.
        
        :param config_path: Optional path to the microservices configuration file
        """
        self.config_path = config_path or os.getenv('MICROSERVICES_CONFIG', 'config/microservices.yaml')
        self._load_config()

    def _load_config(self):
        """
        Load microservices configuration from YAML file.
        If the configuration file doesn't exist, creates a default one.
        
        :return: None
        """
        if not os.path.exists(self.config_path):
            self._create_default_config()
        
        with open(self.config_path, 'r') as f:
            self.config = yaml.safe_load(f)

    def _create_default_config(self):
        """
        Create default configuration file if it doesn't exist.
        Initializes with basic microservices setup.
        
        :return: None
        """
        default_config = {
            'microservices': {
                'auth-service': {
                    'repository': 'GenBrainAI/auth-service',
                    'terraform_path': 'terraform/network-policies.tf'
                },
                'user-service': {
                    'repository': 'GenBrainAI/user-service',
                    'terraform_path': 'terraform/network-policies.tf'
                },
                'payment-service': {
                    'repository': 'GenBrainAI/payment-service',
                    'terraform_path': 'terraform/network-policies.tf'
                }
            }
        }
        
        os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
        with open(self.config_path, 'w') as f:
            yaml.dump(default_config, f)
        
        self.config = default_config

    def get_repository(self, microservice_name: str) -> str:
        """
        Get the GitHub repository for a microservice.
        
        :param microservice_name: Name of the microservice to look up
        :return: String containing the repository path
        :raises ValueError: If the microservice name is not found in configuration
        """
        if microservice_name not in self.config['microservices']:
            raise ValueError(f"Unknown microservice: {microservice_name}")
        return self.config['microservices'][microservice_name]['repository']

    def get_terraform_path(self, microservice_name: str) -> str:
        """
        Get the terraform configuration path for a microservice.
        
        :param microservice_name: Name of the microservice to look up
        :return: String containing the terraform configuration path
        :raises ValueError: If the microservice name is not found in configuration
        """
        if microservice_name not in self.config['microservices']:
            raise ValueError(f"Unknown microservice: {microservice_name}")
        return self.config['microservices'][microservice_name]['terraform_path']

    def list_microservices(self) -> List[str]:
        """
        List all available microservices.
        
        :return: List of strings containing all microservice names
        """
        return list(self.config['microservices'].keys())

    def add_microservice(self, name: str, repository: str, terraform_path: str) -> None:
        """
        Add a new microservice to the configuration.
        
        :param name: Name of the new microservice
        :param repository: GitHub repository path for the microservice
        :param terraform_path: Path to the terraform configuration file
        :return: None
        """
        self.config['microservices'][name] = {
            'repository': repository,
            'terraform_path': terraform_path
        }
        with open(self.config_path, 'w') as f:
            yaml.dump(self.config, f)
