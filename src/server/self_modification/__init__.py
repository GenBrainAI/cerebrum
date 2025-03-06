"""
Self-Modification Engine for the Self-Aware Cerebrum system.

This package contains components that enable the system to understand, modify, and extend its own code.
"""

from src.server.self_modification.code_generator import CodeGenerator
from src.server.self_modification.safety_validator import SafetyValidator
from src.server.self_modification.integration_manager import IntegrationManager
from src.server.self_modification.agentic_framework import AgenticDevelopmentController
from src.server.self_modification.code_modification_engine import CodeModification, CodeModificationEngine
from src.server.self_modification.modification_validator import ModificationValidator, StaticAnalyzer, TestRunner
from src.server.self_modification.modification_version_control import ModificationVersionControl

__all__ = [
    'CodeGenerator',
    'SafetyValidator',
    'IntegrationManager',
    'AgenticDevelopmentController',
    'CodeModification',
    'CodeModificationEngine',
    'ModificationValidator',
    'StaticAnalyzer',
    'TestRunner',
    'ModificationVersionControl'
] 