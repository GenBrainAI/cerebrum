"""
Planning Engine Factory.

This module provides factory methods for creating Planning Engine instances
with various configurations and component combinations.
"""

from typing import Dict, List, Optional, Any
import os
import logging

from src.server.planning.planning_engine import PlanningEngine
from src.server.planning.planning_config import PlanningConfigManager, PlanningConfig
from src.server.planning.goal_decomposition import GoalDecompositionEngine
from src.server.planning.research_planner import ResearchPlanner
from src.server.planning.implementation_planner import ImplementationPlanner, SolutionDesignSystem
from src.server.planning.resource_allocation import ResourceAllocationManager
from src.server.context.knowledge_integration import KnowledgeIntegrationSystem
from src.server.observability.resource_monitor import ResourceMonitor
from src.server.system.codebase_vector_store import CodebaseVectorStore, VectorStoreConfig

logger = logging.getLogger(__name__)

class PlanningEngineFactory:
    """Factory for creating Planning Engine instances."""
    
    @staticmethod
    async def create_planning_engine(
        config_path: Optional[str] = None,
        knowledge_system: Optional[KnowledgeIntegrationSystem] = None,
        include_components: Optional[List[str]] = None,
        storage_path: Optional[str] = None
    ) -> PlanningEngine:
        """
        Create a Planning Engine with the specified components.
        
        Args:
            config_path: Path to configuration file
            knowledge_system: Knowledge Integration System instance
            include_components: List of components to include (all by default)
            storage_path: Path for storing planning data
            
        Returns:
            A configured Planning Engine instance
        """
        # Load configuration
        config_manager = PlanningConfigManager(config_path)
        config = config_manager.config
        
        # Determine which components to include
        include_all = include_components is None
        components = set(include_components or [])
        
        # Determine storage path
        storage_path = storage_path or config.default_storage_path
        
        # Create component instances
        goal_decomposition_engine = None
        research_planner = None
        implementation_planner = None
        solution_design_system = None
        resource_allocation_manager = None
        
        # Create Knowledge System if not provided
        if knowledge_system is None:
            knowledge_path = os.path.join(storage_path, "knowledge")
            knowledge_system = KnowledgeIntegrationSystem(storage_path=knowledge_path)
            await knowledge_system.initialize()
        
        # Create Goal Decomposition Engine
        if include_all or "goal_decomposition" in components:
            logger.info("Creating Goal Decomposition Engine")
            templates_dir = os.path.join(storage_path, "goal_decomposition", "templates")
            goal_decomposition_engine = GoalDecompositionEngine(
                knowledge_system=knowledge_system,
                templates_dir=templates_dir
            )
        
        # Create Research Planner
        if include_all or "research" in components:
            logger.info("Creating Research Planner")
            research_planner = ResearchPlanner(
                knowledge_system=knowledge_system,
                storage_dir=os.path.join(storage_path, "research")
            )
        
        # Create Solution Design System and Implementation Planner
        if include_all or "implementation" in components:
            logger.info("Creating CodebaseVectorStore and Implementation Planning components")
            
            # Create Vector Store Config
            codebase_root = os.path.join(storage_path, "codebase")
            codebase_store_dir = os.path.join(storage_path, "codebase_vectors")
            
            vector_store_config = VectorStoreConfig(
                root_dir=codebase_root,
                store_dir=codebase_store_dir
            )
            
            # Create Codebase Vector Store
            codebase_store = CodebaseVectorStore(config=vector_store_config)
            
            # Create Solution Design System
            solution_design_system = SolutionDesignSystem(
                knowledge_system=knowledge_system,
                codebase_store=codebase_store,
                storage_path=os.path.join(storage_path, "solution_designs")
            )
            
            # Create Implementation Planner
            implementation_planner = ImplementationPlanner(
                solution_design_system=solution_design_system,
                storage_path=os.path.join(storage_path, "implementation")
            )
        
        # Create Resource Allocation Manager
        if include_all or "resource" in components:
            logger.info("Creating Resource Allocation Manager")
            
            # Create Resource Monitor
            resource_monitor = ResourceMonitor()
            
            # Create Resource Allocation Manager
            resource_allocation_manager = ResourceAllocationManager(
                resource_monitor=resource_monitor,
                storage_path=os.path.join(storage_path, "resources")
            )
        
        # Create Planning Engine
        planning_engine = PlanningEngine(
            goal_decomposition_engine=goal_decomposition_engine,
            research_planner=research_planner,
            implementation_planner=implementation_planner,
            solution_design_system=solution_design_system,
            resource_allocation_manager=resource_allocation_manager,
            knowledge_system=knowledge_system,
            storage_path=storage_path
        )
        
        logger.info("Planning Engine created successfully")
        return planning_engine 