"""
Self-Modification Engine for the Self-Aware Cerebrum system.

This package contains components that enable the system to understand, modify, and extend its own code.
"""

from src.server.self_modification.code_generator import CodeGenerator
from src.server.self_modification.safety_validator import SafetyValidator
from src.server.self_modification.integration_manager import IntegrationManager
from src.server.self_modification.agentic_framework import AgenticDevelopmentController

__all__ = [
    'CodeGenerator',
    'SafetyValidator',
    'IntegrationManager',
    'AgenticDevelopmentController'
] 