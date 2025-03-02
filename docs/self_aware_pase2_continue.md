Detailed Implementation Instructions for the Next Development Cycle
After analyzing the current state of the Self-Aware Cerebrum system, I believe implementing the entire Phase 3 (Planning Engine) would be too ambitious for a single development cycle. Instead, I recommend focusing on completing the ChromaDB integration and implementing the first component of Phase 3: the Goal Decomposition Engine.
Development Cycle Objectives
Complete the ChromaDB vector store integration
Create a comprehensive self-aware initialization script
Implement the Goal Decomposition Engine (first component of Phase 3)
1. Complete ChromaDB Vector Store Integration
Task 1.1: Update CerebrumSystemCore
File Path: src/server/cerebrum_system_core.py
Changes Required:
Update imports to use the new ChromaVectorStore
Modify the initialization code to use ChromaDB
Update methods that interact with the vector store
Implementation Instructions:

# Update imports
from src.server.context.chroma_vector_store import (
    ChromaVectorStore,
    VectorStoreConfig
)

# In the __init__ method, replace the vector store initialization
vector_store_config = VectorStoreConfig(
    persist_directory=os.path.join(base_path, "vector_store"),
    collection_name="codebase",
    embedding_model="text-embedding-3-small"
)

# Initialize the vector store
self.vector_store = ChromaVectorStore(
    config=vector_store_config,
    base_path=os.path.join(base_path, "vector_store")
)

# Update the index_codebase method to use the new ChromaVectorStore
async def index_codebase(self, incremental: bool = True) -> Dict[str, Any]:
    """Index the codebase using the ChromaVectorStore."""
    logger.info(f"Indexing codebase at {self.codebase_root}")
    
    start_time = datetime.now()
    
    # Use the new ChromaVectorStore indexing method
    result = await self.vector_store.index_directory(
        directory=self.codebase_root,
        incremental=incremental,
        collection_name="codebase",
        file_types=[".py", ".md", ".txt", ".json", ".yaml", ".yml"]
    )
    
    end_time = datetime.now()
    time_taken = (end_time - start_time).total_seconds()
    
    # Add time taken to the result
    result["time_taken"] = time_taken
    
    logger.info(f"Codebase indexing completed in {time_taken:.2f} seconds")
    return result

# Update the search_codebase method
async def search_codebase(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
    """Search the codebase using semantic search."""
    logger.info(f"Searching codebase for: {query}")
    
    results = await self.vector_store.search(
        query=query,
        collection_name="codebase",
        limit=limit
    )
    
    return results


Task 1.2: Update UnifiedContextManager
File Path: src/server/context/unified_context_manager.py
Changes Required:
Update imports to use the new ChromaVectorStore
Modify the initialization code to use ChromaDB
Update methods that interact with the vector store
Implementation Instructions:
# Update imports
from src.server.context.chroma_vector_store import (
    ChromaVectorStore,
    VectorStoreConfig
)

# In the __init__ method, replace the vector store initialization
self.vector_store_dir = self.base_path / "vector_store"
self.vector_store_dir.mkdir(exist_ok=True)

self.vector_store = ChromaVectorStore(
    config=VectorStoreConfig(
        persist_directory=str(self.vector_store_dir),
        collection_name="unified_context",
        embedding_model="text-embedding-3-small"
    ),
    base_path=str(self.vector_store_dir)
)

# Update the initialize_codebase_index method
async def initialize_codebase_index(self, incremental: bool = True) -> Dict[str, Any]:
    """Initialize or update the codebase vector store."""
    logger.info(f"Initializing codebase index (incremental={incremental})")
    
    result = await self.vector_store.index_directory(
        directory=self.codebase_root,
        incremental=incremental,
        collection_name="codebase",
        file_types=[".py", ".md", ".txt", ".json", ".yaml", ".yml"]
    )
    
    return result

# Update the search_codebase method
async def search_codebase(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
    """Search the codebase using semantic search."""
    logger.info(f"Searching codebase for: {query}")
    
    results = await self.vector_store.search(
        query=query,
        collection_name="codebase",
        limit=limit
    )
    
    return results


Task 1.3: Standardize Vector Store Paths
File Path: src/server/context/context_provider.py
Changes Required:
Standardize the paths used for vector store files
Ensure consistent naming conventions
Implementation Instructions:

# Define standard paths for vector store
GLOBAL_VECTOR_STORE_PATH = "persistent_state/global_context/vector_store"
CONTEXT_VECTOR_STORE_PATH = "persistent_state/context/vector_store"
CODEBASE_VECTOR_STORE_PATH = "persistent_state/codebase/vector_store"

# Update the get_vector_store_path method
def get_vector_store_path(context_type: str = "default") -> str:
    """Get the appropriate vector store path based on context type."""
    if context_type == "global":
        return GLOBAL_VECTOR_STORE_PATH
    elif context_type == "codebase":
        return CODEBASE_VECTOR_STORE_PATH
    else:
        return os.path.join(CONTEXT_VECTOR_STORE_PATH, context_type)


2. Create Self-Aware Initialization Script
Task 2.1: Create Initialization Script
File Path: scripts/initialize_self_aware.py
Implementation Instructions:

#!/usr/bin/env python
"""
Initialization script for the Self-Aware Cerebrum system.

This script initializes all components of the Self-Aware Cerebrum system,
including the vector store, parameter manager, knowledge system, and more.
"""

import os
import sys
import asyncio
import argparse
import logging
from pathlib import Path

# Add the parent directory to the path so we can import our modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.server.self_aware_integration import SelfAwareSystem
from scripts.setup_vector_store import setup_vector_store

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('initialize_self_aware.log')
    ]
)

logger = logging.getLogger(__name__)

async def initialize_self_aware(
    codebase_root: str = ".",
    base_path: str = "persistent_state/self_aware",
    setup_vector: bool = True,
    incremental: bool = False
) -> None:
    """
    Initialize the Self-Aware Cerebrum system.
    
    Args:
        codebase_root: Path to the codebase root directory
        base_path: Path to the base directory for persistent state
        setup_vector: Whether to set up the vector store
        incremental: Whether to perform incremental indexing for the vector store
    """
    logger.info(f"Initializing Self-Aware Cerebrum system")
    logger.info(f"Codebase root: {codebase_root}")
    logger.info(f"Base path: {base_path}")
    
    # Create base directory if it doesn't exist
    os.makedirs(base_path, exist_ok=True)
    
    # Set up vector store if requested
    if setup_vector:
        logger.info("Setting up vector store...")
        vector_result = await setup_vector_store(
            codebase_root=codebase_root,
            base_path=os.path.join(base_path, "vector_store"),
            incremental=incremental
        )
        logger.info(f"Vector store setup completed: {vector_result}")
    
    # Initialize the Self-Aware System
    logger.info("Initializing Self-Aware System...")
    system = SelfAwareSystem(storage_path=base_path)
    
    # Initialize AI Parameter Manager
    logger.info("Initializing AI Parameter Manager...")
    await system.parameter_manager.initialize()
    
    # Initialize Knowledge Integration System
    logger.info("Initializing Knowledge Integration System...")
    await system.knowledge_system.initialize()
    
    # Initialize Cognitive Loop Orchestrator
    logger.info("Initializing Cognitive Loop Orchestrator...")
    await system.cognitive_orchestrator.initialize()
    
    # Register specialized workers
    logger.info("Registering specialized workers...")
    await system.register_specialized_workers()
    
    # Initialize Self-Modification components
    logger.info("Initializing Self-Modification components...")
    # No explicit initialization needed as they're initialized in the constructor
    
    logger.info("Self-Aware Cerebrum system initialization completed successfully")
    return system

def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(description="Initialize the Self-Aware Cerebrum system")
    parser.add_argument(
        "--codebase-root",
        type=str,
        default=".",
        help="Path to the codebase root directory"
    )
    parser.add_argument(
        "--base-path",
        type=str,
        default="persistent_state/self_aware",
        help="Path to the base directory for persistent state"
    )
    parser.add_argument(
        "--skip-vector",
        action="store_true",
        help="Skip vector store setup"
    )
    parser.add_argument(
        "--incremental",
        action="store_true",
        help="Perform incremental indexing for the vector store"
    )
    
    args = parser.parse_args()
    
    # Run the initialization
    asyncio.run(initialize_self_aware(
        codebase_root=args.codebase_root,
        base_path=args.base_path,
        setup_vector=not args.skip_vector,
        incremental=args.incremental
    ))

if __name__ == "__main__":
    main()


Task 2.2: Update SelfAwareSystem to Support Initialization
File Path: src/server/self_aware_integration.py
Changes Required:
Add an initialize method to properly set up all components
Ensure proper registration of specialized workers
Implementation Instructions:

# Add to the SelfAwareSystem class
async def initialize(self):
    """Initialize all components of the Self-Aware System."""
    logger.info("Initializing Self-Aware System components")
    
    # Initialize AI Parameter Manager
    await self.parameter_manager.initialize()
    
    # Initialize Knowledge Integration System
    await self.knowledge_system.initialize()
    
    # Initialize Cognitive Loop Orchestrator
    await self.cognitive_orchestrator.initialize()
    
    # Register specialized workers
    await self.register_specialized_workers()
    
    logger.info("Self-Aware System initialization completed")

async def register_specialized_workers(self):
    """Register specialized workers with the cognitive orchestrator."""
    logger.info("Registering specialized workers")
    
    # Create and register Requirements Worker
    requirements_worker = RequirementsWorker(
        knowledge_system=self.knowledge_system,
        parameter_manager=self.parameter_manager
    )
    await self.cognitive_orchestrator.register_worker(
        worker_type=WorkerType.REQUIREMENTS,
        worker=requirements_worker
    )
    
    # Create and register Planning Worker
    planning_worker = PlanningWorker(
        knowledge_system=self.knowledge_system,
        parameter_manager=self.parameter_manager
    )
    await self.cognitive_orchestrator.register_worker(
        worker_type=WorkerType.PLANNING,
        worker=planning_worker
    )
    
    # Create and register Implementation Worker
    implementation_worker = ImplementationWorker(
        knowledge_system=self.knowledge_system,
        parameter_manager=self.parameter_manager,
        code_generator=self.code_generator,
        safety_validator=self.safety_validator
    )
    await self.cognitive_orchestrator.register_worker(
        worker_type=WorkerType.IMPLEMENTATION,
        worker=implementation_worker
    )
    
    # Create and register Evaluation Worker
    evaluation_worker = EvaluationWorker(
        knowledge_system=self.knowledge_system,
        parameter_manager=self.parameter_manager,
        test_runner=self.test_runner
    )
    await self.cognitive_orchestrator.register_worker(
        worker_type=WorkerType.EVALUATION,
        worker=evaluation_worker
    )
    
    logger.info("Specialized workers registered successfully")


3. Implement Goal Decomposition Engine
Task 3.1: Create Goal Decomposition Engine
File Path: src/server/planning/goal_decomposition.py
Implementation Instructions:

"""
Goal Decomposition Engine for the Self-Aware Cerebrum system.

This module provides capabilities for breaking down high-level goals into
manageable subgoals and tasks, with resource estimation and prioritization.
"""

from typing import Dict, List, Optional, Any, Union
import logging
import asyncio
import json
import os
import uuid
from datetime import datetime
from enum import Enum, auto
from dataclasses import dataclass

logger = logging.getLogger(__name__)

class GoalType(Enum):
    """Types of goals that can be decomposed."""
    RESEARCH = auto()
    DEVELOPMENT = auto()
    ANALYSIS = auto()
    INTEGRATION = auto()
    OPTIMIZATION = auto()
    TESTING = auto()
    DOCUMENTATION = auto()
    GENERAL = auto()

class DecompositionStrategy(Enum):
    """Strategies for decomposing goals."""
    TOP_DOWN = auto()
    BOTTOM_UP = auto()
    ITERATIVE = auto()
    DOMAIN_SPECIFIC = auto()

@dataclass
class ResourceEstimate:
    """Resource estimates for a goal or subgoal."""
    time_hours: float
    complexity: int  # 1-10 scale
    knowledge_requirements: List[str]
    dependencies: List[str]
    risk_level: int  # 1-10 scale

@dataclass
class SubGoal:
    """Representation of a subgoal within a decomposed goal."""
    id: str
    name: str
    description: str
    goal_type: GoalType
    priority: int  # 1-10 scale
    resources: ResourceEstimate
    parent_id: Optional[str] = None
    children_ids: List[str] = None
    status: str = "pending"
    
    def __post_init__(self):
        if self.children_ids is None:
            self.children_ids = []

@dataclass
class DecomposedGoal:
    """Representation of a fully decomposed goal."""
    id: str
    name: str
    description: str
    goal_type: GoalType
    strategy: DecompositionStrategy
    subgoals: Dict[str, SubGoal]
    root_subgoal_ids: List[str]
    total_resources: ResourceEstimate
    creation_time: str
    status: str = "pending"

class GoalDecompositionEngine:
    """Engine for decomposing high-level goals into manageable subgoals."""
    
    def __init__(self, knowledge_system=None):
        """Initialize the Goal Decomposition Engine.
        
        Args:
            knowledge_system: Knowledge Integration System for context.
        """
        self.knowledge_system = knowledge_system
        self.decomposed_goals = {}
        self.decomposition_history = []
        
    async def decompose_goal(
        self, 
        goal: Dict[str, Any],
        strategy: DecompositionStrategy = DecompositionStrategy.TOP_DOWN,
        context: Optional[Dict[str, Any]] = None
    ) -> DecomposedGoal:
        """Decompose a high-level goal into subgoals.
        
        Args:
            goal: Dictionary containing goal details.
            strategy: Strategy to use for decomposition.
            context: Additional context for decomposition.
            
        Returns:
            DecomposedGoal object with the decomposition results.
        """
        goal_id = goal.get("id", str(uuid.uuid4()))
        logger.info(f"Decomposing goal with ID: {goal_id}")
        
        # Extract goal information
        goal_name = goal.get("name", "Unnamed Goal")
        goal_description = goal.get("description", "")
        goal_type_str = goal.get("type", "GENERAL")
        goal_type = GoalType[goal_type_str] if goal_type_str in GoalType.__members__ else GoalType.GENERAL
        
        # Apply the appropriate decomposition strategy
        if strategy == DecompositionStrategy.TOP_DOWN:
            subgoals, root_ids = await self._apply_top_down_strategy(goal, context)
        elif strategy == DecompositionStrategy.BOTTOM_UP:
            subgoals, root_ids = await self._apply_bottom_up_strategy(goal, context)
        elif strategy == DecompositionStrategy.ITERATIVE:
            subgoals, root_ids = await self._apply_iterative_strategy(goal, context)
        elif strategy == DecompositionStrategy.DOMAIN_SPECIFIC:
            subgoals, root_ids = await self._apply_domain_specific_strategy(goal, context)
        else:
            # Default to top-down
            subgoals, root_ids = await self._apply_top_down_strategy(goal, context)
        
        # Calculate total resources
        total_resources = await self._calculate_total_resources(subgoals)
        
        # Create the decomposed goal
        decomposed_goal = DecomposedGoal(
            id=goal_id,
            name=goal_name,
            description=goal_description,
            goal_type=goal_type,
            strategy=strategy,
            subgoals=subgoals,
            root_subgoal_ids=root_ids,
            total_resources=total_resources,
            creation_time=datetime.now().isoformat(),
            status="ready"
        )
        
        # Store the decomposed goal
        self.decomposed_goals[goal_id] = decomposed_goal
        
        # Record in history
        self.decomposition_history.append({
            "goal_id": goal_id,
            "strategy": strategy.name,
            "timestamp": datetime.now().isoformat(),
            "subgoal_count": len(subgoals)
        })
        
        logger.info(f"Goal decomposition completed with {len(subgoals)} subgoals")
        return decomposed_goal
    
    async def _apply_top_down_strategy(
        self, 
        goal: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> Tuple[Dict[str, SubGoal], List[str]]:
        """Apply top-down decomposition strategy.
        
        This strategy starts with the high-level goal and breaks it down
        into increasingly specific subgoals.
        
        Args:
            goal: Dictionary containing goal details.
            context: Additional context for decomposition.
            
        Returns:
            Tuple of (subgoals dictionary, root subgoal IDs)
        """
        logger.info(f"Applying top-down decomposition strategy")
        
        subgoals = {}
        root_ids = []
        
        # Create the initial breakdown based on goal type
        goal_type_str = goal.get("type", "GENERAL")
        goal_type = GoalType[goal_type_str] if goal_type_str in GoalType.__members__ else GoalType.GENERAL
        
        # Get knowledge context if available
        knowledge_context = None
        if self.knowledge_system and context:
            knowledge_context = await self._get_knowledge_context(goal, context)
        
        # Create initial breakdown based on goal type and knowledge
        initial_breakdown = await self._create_initial_breakdown(goal, goal_type, knowledge_context)
        
        # Create root subgoals
        for i, subgoal_info in enumerate(initial_breakdown):
            subgoal_id = str(uuid.uuid4())
            
            # Create resource estimate
            resources = ResourceEstimate(
                time_hours=subgoal_info.get("time_hours", 1.0),
                complexity=subgoal_info.get("complexity", 5),
                knowledge_requirements=subgoal_info.get("knowledge_requirements", []),
                dependencies=subgoal_info.get("dependencies", []),
                risk_level=subgoal_info.get("risk_level", 3)
            )
            
            # Create subgoal
            subgoal = SubGoal(
                id=subgoal_id,
                name=subgoal_info.get("name", f"Subgoal {i+1}"),
                description=subgoal_info.get("description", ""),
                goal_type=goal_type,
                priority=subgoal_info.get("priority", 5),
                resources=resources,
                parent_id=None,
                children_ids=[],
                status="pending"
            )
            
            subgoals[subgoal_id] = subgoal
            root_ids.append(subgoal_id)
            
            # Further decompose if needed
            if subgoal_info.get("needs_further_decomposition", False):
                child_subgoals = await self._further_decompose_subgoal(subgoal, goal_type, knowledge_context)
                
                for child_id, child_subgoal in child_subgoals.items():
                    subgoals[child_id] = child_subgoal
                    subgoal.children_ids.append(child_id)
        
        return subgoals, root_ids
    
    async def _apply_bottom_up_strategy(
        self, 
        goal: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> Tuple[Dict[str, SubGoal], List[str]]:
        """Apply bottom-up decomposition strategy.
        
        This strategy identifies atomic tasks first, then groups them
        into higher-level subgoals.
        
        Args:
            goal: Dictionary containing goal details.
            context: Additional context for decomposition.
            
        Returns:
            Tuple of (subgoals dictionary, root subgoal IDs)
        """
        # Implementation for bottom-up strategy
        # This is a placeholder - actual implementation would be more complex
        logger.info(f"Applying bottom-up decomposition strategy")
        
        # For now, delegate to top-down as a fallback
        return await self._apply_top_down_strategy(goal, context)
    
    async def _apply_iterative_strategy(
        self, 
        goal: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> Tuple[Dict[str, SubGoal], List[str]]:
        """Apply iterative decomposition strategy.
        
        This strategy creates an initial set of subgoals, then refines
        them through multiple iterations.
        
        Args:
            goal: Dictionary containing goal details.
            context: Additional context for decomposition.
            
        Returns:
            Tuple of (subgoals dictionary, root subgoal IDs)
        """
        # Implementation for iterative strategy
        # This is a placeholder - actual implementation would be more complex
        logger.info(f"Applying iterative decomposition strategy")
        
        # For now, delegate to top-down as a fallback
        return await self._apply_top_down_strategy(goal, context)
    
    async def _apply_domain_specific_strategy(
        self, 
        goal: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> Tuple[Dict[str, SubGoal], List[str]]:
        """Apply domain-specific decomposition strategy.
        
        This strategy uses domain-specific knowledge to create
        an appropriate decomposition.
        
        Args:
            goal: Dictionary containing goal details.
            context: Additional context for decomposition.
            
        Returns:
            Tuple of (subgoals dictionary, root subgoal IDs)
        """
        # Implementation for domain-specific strategy
        # This is a placeholder - actual implementation would be more complex
        logger.info(f"Applying domain-specific decomposition strategy")
        
        # For now, delegate to top-down as a fallback
        return await self._apply_top_down_strategy(goal, context)
    
    async def _create_initial_breakdown(
        self, 
        goal: Dict[str, Any],
        goal_type: GoalType,
        knowledge_context: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Create initial breakdown of a goal based on its type.
        
        Args:
            goal: Dictionary containing goal details.
            goal_type: Type of the goal.
            knowledge_context: Knowledge context for the goal.
            
        Returns:
            List of dictionaries with subgoal information.
        """
        # This would ideally use AI to create the breakdown
        # For now, use predefined templates based on goal type
        
        if goal_type == GoalType.RESEARCH:
            return [
                {
                    "name": "Background Research",
                    "description": "Gather and analyze existing knowledge on the topic",
                    "priority": 8,
                    "time_hours": 4.0,
                    "complexity": 6,
                    "knowledge_requirements": ["research_methodology"],
                    "dependencies": [],
                    "risk_level": 2,
                    "needs_further_decomposition": True
                },
                {
                    "name": "Gap Analysis",
                    "description": "Identify gaps in current knowledge",
                    "priority": 7,
                    "time_hours": 3.0,
                    "complexity": 7,
                    "knowledge_requirements": ["analytical_thinking"],
                    "dependencies": ["Background Research"],
                    "risk_level": 3,
                    "needs_further_decomposition": False
                },
                {
                    "name": "Research Planning",
                    "description": "Plan specific research activities",
                    "priority": 6,
                    "time_hours": 2.0,
                    "complexity": 5,
                    "knowledge_requirements": ["project_planning"],
                    "dependencies": ["Gap Analysis"],
                    "risk_level": 4,
                    "needs_further_decomposition": True
                },
                {
                    "name": "Research Execution",
                    "description": "Execute the research plan",
                    "priority": 9,
                    "time_hours": 8.0,
                    "complexity": 8,
                    "knowledge_requirements": ["research_methodology"],
                    "dependencies": ["Research Planning"],
                    "risk_level": 6,
                    "needs_further_decomposition": True
                },
                {
                    "name": "Findings Synthesis",
                    "description": "Synthesize research findings",
                    "priority": 7,
                    "time_hours": 4.0,
                    "complexity": 7,
                    "knowledge_requirements": ["analytical_thinking"],
                    "dependencies": ["Research Execution"],
                    "risk_level": 3,
                    "needs_further_decomposition": False
                }
            ]
        elif goal_type == GoalType.DEVELOPMENT:
            return [
                {
                    "name": "Requirements Analysis",
                    "description": "Analyze and document requirements",
                    "priority": 9,
                    "time_hours": 3.0,
                    "complexity": 6,
                    "knowledge_requirements": ["requirements_engineering"],
                    "dependencies": [],
                    "risk_level": 4,
                    "needs_further_decomposition": True
                },
                {
                    "name": "Architecture Design",
                    "description": "Design the system architecture",
                    "priority": 8,
                    "time_hours": 4.0,
                    "complexity": 8,
                    "knowledge_requirements": ["software_architecture"],
                    "dependencies": ["Requirements Analysis"],
                    "risk_level": 7,
                    "needs_further_decomposition": True
                },
                {
                    "name": "Implementation",
                    "description": "Implement the designed solution",
                    "priority": 10,
                    "time_hours": 10.0,
                    "complexity": 7,
                    "knowledge_requirements": ["programming"],
                    "dependencies": ["Architecture Design"],
                    "risk_level": 6,
                    "needs_further_decomposition": True
                },
                {
                    "name": "Testing",
                    "description": "Test the implementation",
                    "priority": 9,
                    "time_hours": 5.0,
                    "complexity": 6,
                    "knowledge_requirements": ["testing_methodology"],
                    "dependencies": ["Implementation"],
                    "risk_level": 5,
                    "needs_further_decomposition": True
                },
                {
                    "name": "Documentation",
                    "description": "Document the solution",
                    "priority": 7,
                    "time_hours": 3.0,
                    "complexity": 4,
                    "knowledge_requirements": ["technical_writing"],
                    "dependencies": ["Implementation"],
                    "risk_level": 2,
                    "needs_further_decomposition": False
                }
            ]
        else:
            # Generic breakdown for other goal types
            return [
                {
                    "name": "Analysis",
                    "description": "Analyze the problem or goal",
                    "priority": 8,
                    "time_hours": 2.0,
                    "complexity": 6,
                    "knowledge_requirements": ["analytical_thinking"],
                    "dependencies": [],
                    "risk_level": 3,
                    "needs_further_decomposition": False
                },
                {
                    "name": "Planning",
                    "description": "Plan the approach",
                    "priority": 7,
                    "time_hours": 2.0,
                    "complexity": 5,
                    "knowledge_requirements": ["project_planning"],
                    "dependencies": ["Analysis"],
                    "risk_level": 4,
                    "needs_further_decomposition": False
                },
                {
                    "name": "Execution",
                    "description": "Execute the plan",
                    "priority": 9,
                    "time_hours": 6.0,
                    "complexity": 7,
                    "knowledge_requirements": [],
                    "dependencies": ["Planning"],
                    "risk_level": 5,
                    "needs_further_decomposition": True
                },
                {
                    "name": "Evaluation",
                    "description": "Evaluate the results",
                    "priority": 6,
                    "time_hours": 2.0,
                    "name": "Evaluation",
                    "description": "Evaluate the results",
                    "priority": 6,
                    "time_hours": 2.0,
                    "complexity": 5,
                    "knowledge_requirements": ["analytical_thinking"],
                    "dependencies": ["Execution"],
                    "risk_level": 3,
                    "needs_further_decomposition": False
                },
                {
                    "name": "Documentation",
                    "description": "Document the process and results",
                    "priority": 5,
                    "time_hours": 2.0,
                    "complexity": 4,
                    "knowledge_requirements": ["technical_writing"],
                    "dependencies": ["Execution"],
                    "risk_level": 2,
                    "needs_further_decomposition": False
                }
            ]
    
    async def _further_decompose_subgoal(
        self, 
        subgoal: SubGoal,
        goal_type: GoalType,
        knowledge_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, SubGoal]:
        """Further decompose a subgoal into smaller subgoals.
        
        Args:
            subgoal: The subgoal to decompose.
            goal_type: Type of the parent goal.
            knowledge_context: Knowledge context for the goal.
            
        Returns:
            Dictionary of child subgoals.
        """
        logger.info(f"Further decomposing subgoal: {subgoal.name}")
        
        child_subgoals = {}
        
        # This would ideally use AI to create the decomposition
        # For now, use simple templates based on subgoal name
        
        if "Research" in subgoal.name:
            children = [
                {
                    "name": f"{subgoal.name} - Literature Review",
                    "description": "Review existing literature on the topic",
                    "priority": subgoal.priority,
                    "time_hours": subgoal.resources.time_hours * 0.4,
                    "complexity": max(subgoal.resources.complexity - 1, 1),
                    "knowledge_requirements": subgoal.resources.knowledge_requirements + ["literature_review"],
                    "dependencies": [],
                    "risk_level": max(subgoal.resources.risk_level - 1, 1)
                },
                {
                    "name": f"{subgoal.name} - Data Collection",
                    "description": "Collect relevant data for analysis",
                    "priority": subgoal.priority,
                    "time_hours": subgoal.resources.time_hours * 0.3,
                    "complexity": subgoal.resources.complexity,
                    "knowledge_requirements": subgoal.resources.knowledge_requirements + ["data_collection"],
                    "dependencies": [f"{subgoal.name} - Literature Review"],
                    "risk_level": subgoal.resources.risk_level
                },
                {
                    "name": f"{subgoal.name} - Analysis",
                    "description": "Analyze collected data and information",
                    "priority": subgoal.priority,
                    "time_hours": subgoal.resources.time_hours * 0.3,
                    "complexity": subgoal.resources.complexity,
                    "knowledge_requirements": subgoal.resources.knowledge_requirements + ["data_analysis"],
                    "dependencies": [f"{subgoal.name} - Data Collection"],
                    "risk_level": subgoal.resources.risk_level
                }
            ]
        elif "Implementation" in subgoal.name:
            children = [
                {
                    "name": f"{subgoal.name} - Core Functionality",
                    "description": "Implement core functionality",
                    "priority": subgoal.priority,
                    "time_hours": subgoal.resources.time_hours * 0.5,
                    "complexity": subgoal.resources.complexity,
                    "knowledge_requirements": subgoal.resources.knowledge_requirements,
                    "dependencies": [],
                    "risk_level": subgoal.resources.risk_level
                },
                {
                    "name": f"{subgoal.name} - Edge Cases",
                    "description": "Handle edge cases and error conditions",
                    "priority": subgoal.priority - 1,
                    "time_hours": subgoal.resources.time_hours * 0.3,
                    "complexity": subgoal.resources.complexity + 1,
                    "knowledge_requirements": subgoal.resources.knowledge_requirements + ["error_handling"],
                    "dependencies": [f"{subgoal.name} - Core Functionality"],
                    "risk_level": subgoal.resources.risk_level + 1
                },
                {
                    "name": f"{subgoal.name} - Optimization",
                    "description": "Optimize the implementation",
                    "priority": subgoal.priority - 2,
                    "time_hours": subgoal.resources.time_hours * 0.2,
                    "complexity": subgoal.resources.complexity + 2,
                    "knowledge_requirements": subgoal.resources.knowledge_requirements + ["optimization_techniques"],
                    "dependencies": [f"{subgoal.name} - Edge Cases"],
                    "risk_level": subgoal.resources.risk_level
                }
            ]
        elif "Testing" in subgoal.name:
            children = [
                {
                    "name": f"{subgoal.name} - Unit Tests",
                    "description": "Create and run unit tests",
                    "priority": subgoal.priority,
                    "time_hours": subgoal.resources.time_hours * 0.4,
                    "complexity": subgoal.resources.complexity - 1,
                    "knowledge_requirements": subgoal.resources.knowledge_requirements + ["unit_testing"],
                    "dependencies": [],
                    "risk_level": max(subgoal.resources.risk_level - 1, 1)
                },
                {
                    "name": f"{subgoal.name} - Integration Tests",
                    "description": "Create and run integration tests",
                    "priority": subgoal.priority,
                    "time_hours": subgoal.resources.time_hours * 0.3,
                    "complexity": subgoal.resources.complexity,
                    "knowledge_requirements": subgoal.resources.knowledge_requirements + ["integration_testing"],
                    "dependencies": [f"{subgoal.name} - Unit Tests"],
                    "risk_level": subgoal.resources.risk_level
                },
                {
                    "name": f"{subgoal.name} - System Tests",
                    "description": "Create and run system tests",
                    "priority": subgoal.priority,
                    "time_hours": subgoal.resources.time_hours * 0.3,
                    "complexity": subgoal.resources.complexity + 1,
                    "knowledge_requirements": subgoal.resources.knowledge_requirements + ["system_testing"],
                    "dependencies": [f"{subgoal.name} - Integration Tests"],
                    "risk_level": subgoal.resources.risk_level + 1
                }
            ]
        else:
            # Generic decomposition for other subgoals
            children = [
                {
                    "name": f"{subgoal.name} - Planning",
                    "description": f"Plan the {subgoal.name} activities",
                    "priority": subgoal.priority,
                    "time_hours": subgoal.resources.time_hours * 0.2,
                    "complexity": max(subgoal.resources.complexity - 1, 1),
                    "knowledge_requirements": subgoal.resources.knowledge_requirements,
                    "dependencies": [],
                    "risk_level": max(subgoal.resources.risk_level - 1, 1)
                },
                {
                    "name": f"{subgoal.name} - Execution",
                    "description": f"Execute the {subgoal.name} activities",
                    "priority": subgoal.priority,
                    "time_hours": subgoal.resources.time_hours * 0.6,
                    "complexity": subgoal.resources.complexity,
                    "knowledge_requirements": subgoal.resources.knowledge_requirements,
                    "dependencies": [f"{subgoal.name} - Planning"],
                    "risk_level": subgoal.resources.risk_level
                },
                {
                    "name": f"{subgoal.name} - Review",
                    "description": f"Review the {subgoal.name} results",
                    "priority": subgoal.priority - 1,
                    "time_hours": subgoal.resources.time_hours * 0.2,
                    "complexity": max(subgoal.resources.complexity - 1, 1),
                    "knowledge_requirements": subgoal.resources.knowledge_requirements,
                    "dependencies": [f"{subgoal.name} - Execution"],
                    "risk_level": max(subgoal.resources.risk_level - 1, 1)
                }
            ]
        
        # Create child subgoals
        for child_info in children:
            child_id = str(uuid.uuid4())
            
            # Create resource estimate
            resources = ResourceEstimate(
                time_hours=child_info.get("time_hours", 1.0),
                complexity=child_info.get("complexity", 5),
                knowledge_requirements=child_info.get("knowledge_requirements", []),
                dependencies=child_info.get("dependencies", []),
                risk_level=child_info.get("risk_level", 3)
            )
            
            # Create subgoal
            child_subgoal = SubGoal(
                id=child_id,
                name=child_info.get("name", "Unnamed Subgoal"),
                description=child_info.get("description", ""),
                goal_type=goal_type,
                priority=child_info.get("priority", 5),
                resources=resources,
                parent_id=subgoal.id,
                children_ids=[],
                status="pending"
            )
            
            child_subgoals[child_id] = child_subgoal
        
        return child_subgoals
    
    async def _calculate_total_resources(self, subgoals: Dict[str, SubGoal]) -> ResourceEstimate:
        """Calculate total resources for all subgoals.
        
        Args:
            subgoals: Dictionary of subgoals.
            
        Returns:
            ResourceEstimate with total resources.
        """
        total_time = 0.0
        max_complexity = 0
        all_knowledge_requirements = set()
        all_dependencies = set()
        max_risk_level = 0
        
        for subgoal in subgoals.values():
            total_time += subgoal.resources.time_hours
            max_complexity = max(max_complexity, subgoal.resources.complexity)
            all_knowledge_requirements.update(subgoal.resources.knowledge_requirements)
            all_dependencies.update(subgoal.resources.dependencies)
            max_risk_level = max(max_risk_level, subgoal.resources.risk_level)
        
        return ResourceEstimate(
            time_hours=total_time,
            complexity=max_complexity,
            knowledge_requirements=list(all_knowledge_requirements),
            dependencies=list(all_dependencies),
            risk_level=max_risk_level
        )
    
    async def _get_knowledge_context(
        self, 
        goal: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Get knowledge context for a goal.
        
        Args:
            goal: Dictionary containing goal details.
            context: Additional context for decomposition.
            
        Returns:
            Dictionary with knowledge context or None if not available.
        """
        if not self.knowledge_system:
            return None
        
        try:
            # Extract relevant keywords from the goal
            keywords = [
                goal.get("name", ""),
                goal.get("description", ""),
                goal.get("type", "GENERAL")
            ]
            
            # Add context keywords if available
            if context and "keywords" in context:
                keywords.extend(context["keywords"])
            
            # Query the knowledge system
            knowledge_items = await self.knowledge_system.query_semantic_memory(
                query=" ".join(keywords),
                limit=5
            )
            
            # Extract relevant information
            knowledge_context = {
                "relevant_items": knowledge_items,
                "domain_knowledge": {}
            }
            
            # Extract domain-specific knowledge if available
            if goal.get("domain"):
                domain_knowledge = await self.knowledge_system.query_semantic_memory(
                    query=f"domain:{goal.get('domain')}",
                    limit=3
                )
                knowledge_context["domain_knowledge"] = domain_knowledge
            
            return knowledge_context
        
        except Exception as e:
            logger.error(f"Error getting knowledge context: {str(e)}")
            return None
    
    async def prioritize_subgoals(self, goal_id: str) -> List[str]:
        """Prioritize subgoals within a decomposed goal.
        
        Args:
            goal_id: ID of the decomposed goal.
            
        Returns:
            List of subgoal IDs in priority order.
        """
        if goal_id not in self.decomposed_goals:
            logger.error(f"Goal with ID {goal_id} not found")
            return []
        
        decomposed_goal = self.decomposed_goals[goal_id]
        subgoals = decomposed_goal.subgoals
        
        # Create a list of (subgoal_id, priority) tuples
        priority_list = []
        for subgoal_id, subgoal in subgoals.items():
            # Calculate effective priority based on multiple factors
            effective_priority = subgoal.priority
            
            # Adjust for dependencies
            if not subgoal.parent_id:  # Root subgoals
                effective_priority += 1
            
            # Adjust for complexity
            if subgoal.resources.complexity > 7:
                effective_priority += 1
            
            # Adjust for risk
            if subgoal.resources.risk_level > 7:
                effective_priority += 2
            
            priority_list.append((subgoal_id, effective_priority))
        
        # Sort by priority (descending)
        priority_list.sort(key=lambda x: x[1], reverse=True)
        
        # Extract subgoal IDs
        prioritized_ids = [item[0] for item in priority_list]
        
        return prioritized_ids
    
    async def estimate_resources(self, goal_id: str) -> ResourceEstimate:
        """Estimate resources for a decomposed goal.
        
        Args:
            goal_id: ID of the decomposed goal.
            
        Returns:
            ResourceEstimate with estimated resources.
        """
        if goal_id not in self.decomposed_goals:
            logger.error(f"Goal with ID {goal_id} not found")
            return ResourceEstimate(
                time_hours=0.0,
                complexity=0,
                knowledge_requirements=[],
                dependencies=[],
                risk_level=0
            )
        
        decomposed_goal = self.decomposed_goals[goal_id]
        return decomposed_goal.total_resources
    
    async def validate_decomposition(self, goal_id: str) -> Dict[str, Any]:
        """Validate a goal decomposition for completeness and consistency.
        
        Args:
            goal_id: ID of the decomposed goal.
            
        Returns:
            Dictionary with validation results.
        """
        if goal_id not in self.decomposed_goals:
            logger.error(f"Goal with ID {goal_id} not found")
            return {
                "valid": False,
                "errors": ["Goal not found"],
                "warnings": []
            }
        
        decomposed_goal = self.decomposed_goals[goal_id]
        subgoals = decomposed_goal.subgoals
        
        errors = []
        warnings = []
        
        # Check for orphaned subgoals
        for subgoal_id, subgoal in subgoals.items():
            if subgoal.parent_id and subgoal.parent_id not in subgoals:
                errors.append(f"Subgoal {subgoal_id} has invalid parent {subgoal.parent_id}")
        
        # Check for circular dependencies
        dependency_graph = {}
        for subgoal_id, subgoal in subgoals.items():
            dependency_graph[subgoal_id] = subgoal.children_ids
        
        # Simple cycle detection
        visited = set()
        path = set()
        
        def check_cycle(node):
            visited.add(node)
            path.add(node)
            
            for neighbor in dependency_graph.get(node, []):
                if neighbor not in visited:
                    if check_cycle(neighbor):
                        return True
                elif neighbor in path:
                    errors.append(f"Circular dependency detected involving {node} and {neighbor}")
                    return True
            
            path.remove(node)
            return False
        
        for node in dependency_graph:
            if node not in visited:
                check_cycle(node)
        
        # Check for resource consistency
        total_time = 0.0
        for subgoal_id, subgoal in subgoals.items():
            total_time += subgoal.resources.time_hours
        
        if abs(total_time - decomposed_goal.total_resources.time_hours) > 0.1:
            warnings.append(f"Total time inconsistency: {total_time} vs {decomposed_goal.total_resources.time_hours}")
        
        # Check for coverage
        if len(subgoals) < 2:
            warnings.append("Goal decomposition has fewer than 2 subgoals")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings
        }
    
    async def get_decomposed_goal(self, goal_id: str) -> Optional[DecomposedGoal]:
        """Get a decomposed goal by ID.
        
        Args:
            goal_id: ID of the decomposed goal.
            
        Returns:
            DecomposedGoal object or None if not found.
        """
        return self.decomposed_goals.get(goal_id)
    
    async def get_all_decomposed_goals(self) -> Dict[str, DecomposedGoal]:
        """Get all decomposed goals.
        
        Returns:
            Dictionary of all decomposed goals.
        """
        return self.decomposed_goals
    
    async def delete_decomposed_goal(self, goal_id: str) -> bool:
        """Delete a decomposed goal.
        
        Args:
            goal_id: ID of the decomposed goal.
            
        Returns:
            True if successful, False otherwise.
        """
        if goal_id in self.decomposed_goals:
            del self.decomposed_goals[goal_id]
            return True
        return False



Task 3.2: Create Planning Directory Structure
Implementation Instructions:

# Create the planning directory structure
mkdir -p src/server/planning
touch src/server/planning/__init__.py


Task 3.3: Update Self-Aware Integration with Goal Decomposition Engine
File Path: src/server/self_aware_integration.py
Changes Required:
Import the Goal Decomposition Engine
Add it to the SelfAwareSystem class
Add methods to interact with it
Implementation Instructions:

# Add to imports
from src.server.planning.goal_decomposition import (
    GoalDecompositionEngine,
    GoalType,
    DecompositionStrategy
)

# Add to SelfAwareSystem.__init__
# Initialize Goal Decomposition Engine
self.goal_decomposition_engine = GoalDecompositionEngine(
    knowledge_system=self.knowledge_system
)

# Add new methods to SelfAwareSystem
async def decompose_goal(
    self, 
    goal: Dict[str, Any],
    strategy: str = "TOP_DOWN",
    context: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Decompose a high-level goal into subgoals.
    
    Args:
        goal: Dictionary containing goal details.
        strategy: Strategy to use for decomposition.
        context: Additional context for decomposition.
        
    Returns:
        Dictionary with the decomposition results.
    """
    # Convert strategy string to enum
    try:
        decomposition_strategy = DecompositionStrategy[strategy]
    except KeyError:
        logger.warning(f"Invalid strategy: {strategy}, using TOP_DOWN")
        decomposition_strategy = DecompositionStrategy.TOP_DOWN
    
    # Decompose the goal
    decomposed_goal = await self.goal_decomposition_engine.decompose_goal(
        goal=goal,
        strategy=decomposition_strategy,
        context=context
    )
    
    # Convert to dictionary for API response
    result = {
        "id": decomposed_goal.id,
        "name": decomposed_goal.name,
        "description": decomposed_goal.description,
        "goal_type": decomposed_goal.goal_type.name,
        "strategy": decomposed_goal.strategy.name,
        "subgoals_count": len(decomposed_goal.subgoals),
        "root_subgoals": decomposed_goal.root_subgoal_ids,
        "total_time_hours": decomposed_goal.total_resources.time_hours,
        "max_complexity": decomposed_goal.total_resources.complexity,
        "knowledge_requirements": decomposed_goal.total_resources.knowledge_requirements,
        "risk_level": decomposed_goal.total_resources.risk_level,
        "creation_time": decomposed_goal.creation_time,
        "status": decomposed_goal.status
    }
    
    return result

async def get_subgoals(self, goal_id: str) -> List[Dict[str, Any]]:
    """Get all subgoals for a decomposed goal.
    
    Args:
        goal_id: ID of the decomposed goal.
        
    Returns:
        List of dictionaries with subgoal details.
    """
    decomposed_goal = await self.goal_decomposition_engine.get_decomposed_goal(goal_id)
    
    if not decomposed_goal:
        return []
    
    subgoals = []
    for subgoal_id, subgoal in decomposed_goal.subgoals.items():
        subgoals.append({
            "id": subgoal.id,
            "name": subgoal.name,
            "description": subgoal.description,
            "goal_type": decomposed_goal.goal_type.name,
            "priority": subgoal.priority,
            "time_hours": subgoal.resources.time_hours,
            "complexity": subgoal.resources.complexity,
            "knowledge_requirements": subgoal.resources.knowledge_requirements,
            "risk_level": subgoal.resources.risk_level,
            "parent_id": subgoal.parent_id,
            "children_ids": subgoal.children_ids,
            "status": subgoal.status
        })
    
    return subgoals

async def prioritize_subgoals(self, goal_id: str) -> List[Dict[str, Any]]:
    """Prioritize subgoals within a decomposed goal.
    
    Args:
        goal_id: ID of the decomposed goal.
        
    Returns:
        List of dictionaries with prioritized subgoal details.
    """
    prioritized_ids = await self.goal_decomposition_engine.prioritize_subgoals(goal_id)
    
    if not prioritized_ids:
        return []
    
    decomposed_goal = await self.goal_decomposition_engine.get_decomposed_goal(goal_id)
    
    if not decomposed_goal:
        return []
    
    prioritized_subgoals = []
    for subgoal_id in prioritized_ids:
        subgoal = decomposed_goal.subgoals.get(subgoal_id)
        if subgoal:
            prioritized_subgoals.append({
                "id": subgoal.id,
                "name": subgoal.name,
                "description": subgoal.description,
                "priority": subgoal.priority,
                "time_hours": subgoal.resources.time_hours,
                "complexity": subgoal.resources.complexity,
                "risk_level": subgoal.resources.risk_level,
                "status": subgoal.status
            })
    
    return prioritized_subgoals

async def validate_decomposition(self, goal_id: str) -> Dict[str, Any]:
    """Validate a goal decomposition for completeness and consistency.
    
    Args:
        goal_id: ID of the decomposed goal.
        
    Returns:
        Dictionary with validation results.
    """
    return await self.goal_decomposition_engine.validate_decomposition(goal_id)

Task 3.4: Update CLI to Support Goal Decomposition
File Path: src/server/cli.py
Changes Required:
Add commands for goal decomposition
Add commands for subgoal management
Implementation Instructions:


# Add to imports
from src.server.planning.goal_decomposition import GoalType, DecompositionStrategy

# Add to SelfAwareCLI class
async def decompose_goal(self, args):
    """Decompose a high-level goal into subgoals."""
    # Load goal from file if specified
    if args.goal_file:
        with open(args.goal_file, 'r') as f:
            goal = json.load(f)
    else:
        # Create goal from command line arguments
        goal = {
            "name": args.name,
            "description": args.description,
            "type": args.type
        }
    
    # Create context if specified
    context = None
    if args.context_file:
        with open(args.context_file, 'r') as f:
            context = json.load(f)
    
    # Decompose the goal
    result = await self.system.decompose_goal(
        goal=goal,
        strategy=args.strategy,
        context=context
    )
    
    # Print the result
    if args.output_file:
        with open(args.output_file, 'w') as f:
            json.dump(result, f, indent=2)
    else:
        print(json.dumps(result, indent=2))
    
    return result

async def get_subgoals(self, args):
    """Get all subgoals for a decomposed goal."""
    subgoals = await self.system.get_subgoals(args.goal_id)
    
    # Print the result
    if args.output_file:
        with open(args.output_file, 'w') as f:
            json.dump(subgoals, f, indent=2)
    else:
        print(json.dumps(subgoals, indent=2))
    
    return subgoals

async def prioritize_subgoals(self, args):
    """Prioritize subgoals within a decomposed goal."""
    prioritized = await self.system.prioritize_subgoals(args.goal_id)
    
    # Print the result
    if args.output_file:
        with open(args.output_file, 'w') as f:
            json.dump(prioritized, f, indent=2)
    else:
        print(json.dumps(prioritized, indent=2))
    
    return prioritized

async def validate_decomposition(self, args):
    """Validate a goal decomposition for completeness and consistency."""
    validation = await self.system.validate_decomposition(args.goal_id)
    
    # Print the result
    if args.output_file:
        with open(args.output_file, 'w') as f:
            json.dump(validation, f, indent=2)
    else:
        print(json.dumps(validation, indent=2))
    
    return validation

# Add to parse_args function
goal_parser = subparsers.add_parser('goal', help='Goal decomposition commands')
goal_subparsers = goal_parser.add_subparsers(dest='goal_command', help='Goal decomposition subcommands')

# Decompose goal command
decompose_parser = goal_subparsers.add_parser('decompose', help='Decompose a high-level goal')
decompose_parser.add_argument('--goal-file', type=str, help='Path to JSON file with goal details')
decompose_parser.add_argument('--name', type=str, help='Goal name')
decompose_parser.add_argument('--description', type=str, help='Goal description')
decompose_parser.add_argument('--type', type=str, default='GENERAL', choices=[t.name for t in GoalType], help='Goal type')
decompose_parser.add_argument('--strategy', type=str, default='TOP_DOWN', choices=[s.name for s in DecompositionStrategy], help='Decomposition strategy')
decompose_parser.add_argument('--context-file', type=str, help='Path to JSON file with context details')
decompose_parser.add_argument('--output-file', type=str, help='Path to output file')
decompose_parser.set_defaults(func=lambda args: cli.decompose_goal(args))

# Get subgoals command
subgoals_parser = goal_subparsers.add_parser('subgoals', help='Get subgoals for a decomposed goal')
subgoals_parser.add_argument('goal_id', type=str, help='ID of the decomposed goal')
subgoals_parser.add_argument('--output-file', type=str, help='Path to output file')
subgoals_parser.set_defaults(func=lambda args: cli.get_subgoals(args))

# Prioritize subgoals command
prioritize_parser = goal_subparsers.add_parser('prioritize', help='Prioritize subgoals within a decomposed goal')
prioritize_parser.add_argument('goal_id', type=str, help='ID of the decomposed goal')
prioritize_parser.add_argument('--output-file', type=str, help='Path to output file')
prioritize_parser.set_defaults(func=lambda args: cli.prioritize_subgoals(args))

# Validate decomposition command
validate_parser = goal_subparsers.add_parser('validate', help='Validate a goal decomposition')
validate_parser.add_argument('goal_id', type=str, help='ID of the decomposed goal')
validate_parser.add_argument('--output-file', type=str, help='Path to output file')
validate_parser.set_defaults(func=lambda args: cli.validate_decomposition(args))


Task 3.5: Update Streamlit UI to Support Goal Decomposition
File Path: src/server/streamlit_app.py
Changes Required:
Add a Goal Decomposition page
Add UI elements for goal decomposition
Add UI elements for subgoal management
Implementation Instructions:

# Add to imports
from src.server.planning.goal_decomposition import GoalType, DecompositionStrategy

# Add a new page for Goal Decomposition
def goal_decomposition_page():
    st.title("Goal Decomposition")
    
    # Create tabs for different operations
    tab1, tab2, tab3, tab4 = st.tabs(["Decompose Goal", "View Subgoals", "Prioritize Subgoals", "Validate Decomposition"])
    
    with tab1:
        st.header("Decompose a New Goal")
        
        # Goal input form
        with st.form("decompose_goal_form"):
            goal_name = st.text_input("Goal Name", "")
            goal_description = st.text_area("Goal Description", "")
            
            # Goal type selection
            goal_type_options = [t.name for t in GoalType]
            goal_type = st.selectbox("Goal Type", goal_type_options, index=0)
            
            # Strategy selection
            strategy_options = [s.name for s in DecompositionStrategy]
            strategy = st.selectbox("Decomposition Strategy", strategy_options, index=0)
            
            # Advanced options
            with st.expander("Advanced Options"):
                # Context keywords
                context_keywords = st.text_input("Context Keywords (comma-separated)", "")
                
                # Custom template selection
                use_custom_template = st.checkbox("Use Custom Template", False)
                custom_template = None
                if use_custom_template:
                    template_options = ["Research Project", "Software Development", "Content Creation", "Custom"]
                    selected_template = st.selectbox("Template", template_options)
                    
                    if selected_template == "Custom":
                        custom_template = st.text_area("Custom Template (JSON)", "{}")
            
            submitted = st.form_submit_button("Decompose Goal")
            
            if submitted:
                with st.spinner("Decomposing goal..."):
                    # Prepare goal dictionary
                    goal = {
                        "name": goal_name,
                        "description": goal_description,
                        "type": goal_type
                    }
                    
                    # Prepare context
                    context = None
                    if context_keywords:
                        context = {
                            "keywords": [k.strip() for k in context_keywords.split(",")]
                        }
                    
                    # Add template if selected
                    if use_custom_template and custom_template:
                        try:
                            template_data = json.loads(custom_template)
                            if context:
                                context["template"] = template_data
                            else:
                                context = {"template": template_data}
                        except json.JSONDecodeError:
                            st.error("Invalid JSON in custom template")
                            return
                    
                    # Call the decompose_goal method
                    try:
                        result = asyncio.run(st.session_state.system.decompose_goal(
                            goal=goal,
                            strategy=strategy,
                            context=context
                        ))
                        
                        # Store the result in session state
                        if "decomposed_goals" not in st.session_state:
                            st.session_state.decomposed_goals = {}
                        
                        st.session_state.decomposed_goals[result["id"]] = result
                        st.session_state.current_goal_id = result["id"]
                        
                        # Display success message
                        st.success(f"Goal decomposed successfully! ID: {result['id']}")
                        
                        # Display summary
                        st.subheader("Decomposition Summary")
                        st.json({
                            "id": result["id"],
                            "name": result["name"],
                            "subgoals_count": result["subgoals_count"],
                            "total_time_hours": result["total_time_hours"],
                            "max_complexity": result["max_complexity"],
                            "risk_level": result["risk_level"]
                        })
                    
                    except Exception as e:
                        st.error(f"Error decomposing goal: {str(e)}")
    
    with tab2:
        st.header("View Subgoals")
        
        # Goal selection
        if "decomposed_goals" in st.session_state and st.session_state.decomposed_goals:
            goal_options = {g["id"]: f"{g['name']} ({g['id']})" for g in st.session_state.decomposed_goals.values()}
            
            selected_goal_id = st.selectbox(
                "Select Goal", 
                list(goal_options.keys()),
                format_func=lambda x: goal_options[x],
                index=list(goal_options.keys()).index(st.session_state.current_goal_id) if "current_goal_id" in st.session_state else 0
            )
            
            if st.button("View Subgoals"):
                with st.spinner("Loading subgoals..."):
                    try:
                        subgoals = asyncio.run(st.session_state.system.get_subgoals(selected_goal_id))
                        
                        if not subgoals:
                            st.info("No subgoals found for this goal.")
                        else:
                            # Display subgoals in a table
                            st.subheader(f"Subgoals for {goal_options[selected_goal_id]}")
                            
                            # Create a DataFrame for better display
                            subgoals_data = []
                            for sg in subgoals:
                                subgoals_data.append({
                                    "ID": sg["id"],
                                    "Name": sg["name"],
                                    "Priority": sg["priority"],
                                    "Time (hours)": sg["time_hours"],
                                    "Complexity": sg["complexity"],
                                    "Risk Level": sg["risk_level"],
                                    "Status": sg["status"]
                                })
                            
                            df = pd.DataFrame(subgoals_data)
                            st.dataframe(df)
                            
                            # Display subgoal details
                            st.subheader("Subgoal Details")
                            for sg in subgoals:
                                with st.expander(f"{sg['name']} ({sg['id']})"):
                                    st.write(f"**Description:** {sg['description']}")
                                    st.write(f"**Priority:** {sg['priority']}")
                                    st.write(f"**Time Estimate:** {sg['time_hours']} hours")
                                    st.write(f"**Complexity:** {sg['complexity']}/10")
                                    st.write(f"**Risk Level:** {sg['risk_level']}/10")
                                    st.write(f"**Knowledge Requirements:** {', '.join(sg['knowledge_requirements'])}")
                                    st.write(f"**Parent ID:** {sg['parent_id'] or 'None'}")
                                    st.write(f"**Children IDs:** {', '.join(sg['children_ids']) if sg['children_ids'] else 'None'}")
                                    st.write(f"**Status:** {sg['status']}")
                    
                    except Exception as e:
                        st.error(f"Error loading subgoals: {str(e)}")
        else:
            st.info("No decomposed goals available. Please decompose a goal first.")
    
    with tab3:
        st.header("Prioritize Subgoals")
        
        # Goal selection
        if "decomposed_goals" in st.session_state and st.session_state.decomposed_goals:
            goal_options = {g["id"]: f"{g['name']} ({g['id']})" for g in st.session_state.decomposed_goals.values()}
            
            selected_goal_id = st.selectbox(
                "Select Goal for Prioritization", 
                list(goal_options.keys()),
                format_func=lambda x: goal_options[x],
                index=list(goal_options.keys()).index(st.session_state.current_goal_id) if "current_goal_id" in st.session_state else 0,
                key="prioritize_goal_select"
            )
            
            if st.button("Prioritize Subgoals"):
                with st.spinner("Prioritizing subgoals..."):
                    try:
                        prioritized = asyncio.run(st.session_state.system.prioritize_subgoals(selected_goal_id))
                        
                        if not prioritized:
                            st.info("No subgoals found for this goal.")
                        else:
                            # Display prioritized subgoals
                            st.subheader(f"Prioritized Subgoals for {goal_options[selected_goal_id]}")
                            
                            # Create a DataFrame for better display
                            priority_data = []
                            for i, sg in enumerate(prioritized):
                                priority_data.append({
                                    "Priority Rank": i + 1,
                                    "ID": sg["id"],
                                    "Name": sg["name"],
                                    "Base Priority": sg["priority"],
                                    "Time (hours)": sg["time_hours"],
                                    "Complexity": sg["complexity"],
                                    "Risk Level": sg["risk_level"],
                                    "Status": sg["status"]
                                })
                            
                            df = pd.DataFrame(priority_data)
                            st.dataframe(df)
                            
                            # Visualization
                            st.subheader("Priority Visualization")
                            
                            # Bar chart of time estimates by priority
                            fig, ax = plt.subplots(figsize=(10, 6))
                            
                            names = [f"{i+1}. {sg['name']}" for i, sg in enumerate(prioritized)]
                            times = [sg["time_hours"] for sg in prioritized]
                            
                            bars = ax.barh(names, times, color='skyblue')
                            
                            # Add risk level as color intensity
                            for i, bar in enumerate(bars):
                                risk = prioritized[i]["risk_level"] / 10
                                bar.set_color(plt.cm.Reds(risk))
                            
                            ax.set_xlabel('Time Estimate (hours)')
                            ax.set_title('Subgoal Time Estimates by Priority')
                            
                            # Add a colorbar for risk level
                            sm = plt.cm.ScalarMappable(cmap=plt.cm.Reds, norm=plt.Normalize(0, 10))
                            sm.set_array([])
                            cbar = plt.colorbar(sm, ax=ax)
                            cbar.set_label('Risk Level')
                            
                            st.pyplot(fig)
                    
                    except Exception as e:
                        st.error(f"Error prioritizing subgoals: {str(e)}")
        else:
            st.info("No decomposed goals available. Please decompose a goal first.")
    
    with tab4:
        st.header("Validate Decomposition")
        
        # Goal selection
        if "decomposed_goals" in st.session_state and st.session_state.decomposed_goals:
            goal_options = {g["id"]: f"{g['name']} ({g['id']})" for g in st.session_state.decomposed_goals.values()}
            
            selected_goal_id = st.selectbox(
                "Select Goal for Validation", 
                list(goal_options.keys()),
                format_func=lambda x: goal_options[x],
                index=list(goal_options.keys()).index(st.session_state.current_goal_id) if "current_goal_id" in st.session_state else 0,
                key="validate_goal_select"
            )
            
            if st.button("Validate Decomposition"):
                with st.spinner("Validating decomposition..."):
                    try:
                        validation = asyncio.run(st.session_state.system.validate_decomposition(selected_goal_id))
                        
                        # Display validation results
                        st.subheader(f"Validation Results for {goal_options[selected_goal_id]}")
                        
                        if validation["valid"]:
                            st.success("✅ Decomposition is valid!")
                        else:
                            st.error("❌ Decomposition has errors!")
                        
                        # Display errors
                        if validation["errors"]:
                            st.subheader("Errors")
                            for error in validation["errors"]:
                                st.error(error)
                        
                        # Display warnings
                        if validation["warnings"]:
                            st.subheader("Warnings")
                            for warning in validation["warnings"]:
                                st.warning(warning)
                        
                        # If no errors or warnings
                        if not validation["errors"] and not validation["warnings"]:
                            st.info("No issues found in the decomposition.")
                    
                    except Exception as e:
                        st.error(f"Error validating decomposition: {str(e)}")
        else:
            st.info("No decomposed goals available. Please decompose a goal first.")

# Add to the main app
def main():
    # ... existing code ...
    
    # Add Goal Decomposition to the sidebar
    pages = {
        "Dashboard": dashboard_page,
        "Knowledge Integration": knowledge_integration_page,
        "AI Parameter Management": ai_parameter_page,
        "Development Cognitive Loop": cognitive_loop_page,
        "Goal Decomposition": goal_decomposition_page,  # Add this line
        "Settings": settings_page,
    }
    
    # ... rest of the main function ...


Task 3.6: Create Tests for Goal Decomposition Engine
File Path: tests/server/planning/test_goal_decomposition.py
Implementation Instructions:

import pytest
import asyncio
from unittest.mock import MagicMock, patch
import uuid

from src.server.planning.goal_decomposition import (
    GoalDecompositionEngine,
    GoalType,
    DecompositionStrategy,
    ResourceEstimate,
    SubGoal,
    DecomposedGoal
)

@pytest.fixture
def mock_knowledge_system():
    """Create a mock knowledge system."""
    mock = MagicMock()
    mock.query_semantic_memory = asyncio.coroutine(lambda query, limit: [
        {"id": "1", "content": "Test knowledge item 1"},
        {"id": "2", "content": "Test knowledge item 2"}
    ])
    return mock

@pytest.fixture
def goal_decomposition_engine(mock_knowledge_system):
    """Create a GoalDecompositionEngine instance with a mock knowledge system."""
    return GoalDecompositionEngine(knowledge_system=mock_knowledge_system)

@pytest.fixture
def sample_goal():
    """Create a sample goal for testing."""
    return {
        "name": "Test Goal",
        "description": "A test goal for unit testing",
        "type": "DEVELOPMENT"
    }

@pytest.mark.asyncio
async def test_decompose_goal_top_down(goal_decomposition_engine, sample_goal):
    """Test decomposing a goal using the TOP_DOWN strategy."""
    # Decompose the goal
    decomposed_goal = await goal_decomposition_engine.decompose_goal(
        goal=sample_goal,
        strategy=DecompositionStrategy.TOP_DOWN
    )
    
    # Check the result
    assert decomposed_goal is not None
    assert decomposed_goal.name == sample_goal["name"]
    assert decomposed_goal.description == sample_goal["description"]
    assert decomposed_goal.goal_type == GoalType.DEVELOPMENT
    assert decomposed_goal.strategy == DecompositionStrategy.TOP_DOWN
    assert len(decomposed_goal.subgoals) > 0
    assert len(decomposed_goal.root_subgoal_ids) > 0
    assert decomposed_goal.total_resources is not None
    assert decomposed_goal.total_resources.time_hours > 0

@pytest.mark.asyncio
async def test_decompose_goal_bottom_up(goal_decomposition_engine, sample_goal):
    """Test decomposing a goal using the BOTTOM_UP strategy."""
    # Decompose the goal
    decomposed_goal = await goal_decomposition_engine.decompose_goal(
        goal=sample_goal,
        strategy=DecompositionStrategy.BOTTOM_UP
    )
    
    # Check the result
    assert decomposed_goal is not None
    assert decomposed_goal.strategy == DecompositionStrategy.BOTTOM_UP
    assert len(decomposed_goal.subgoals) > 0

@pytest.mark.asyncio
async def test_decompose_goal_with_context(goal_decomposition_engine, sample_goal):
    """Test decomposing a goal with additional context."""
    # Create context
    context = {
        "keywords": ["test", "unit testing", "development"],
        "template": {
            "name": "Test Template",
            "subgoals": [
                {
                    "name": "Custom Subgoal 1",
                    "description": "A custom subgoal",
                    "priority": 8,
                    "time_hours": 5.0,
                    "complexity": 7,
                    "knowledge_requirements": ["testing"],
                    "dependencies": [],
                    "risk_level": 4
                }
            ]
        }
    }
    
    # Decompose the goal with context
    decomposed_goal = await goal_decomposition_engine.decompose_goal(
        goal=sample_goal,
        strategy=DecompositionStrategy.TOP_DOWN,
        context=context
    )
    
    # Check the result
    assert decomposed_goal is not None
    assert len(decomposed_goal.subgoals) > 0
    
    # Check if the custom subgoal from the template is included
    custom_subgoal_found = False
    for subgoal in decomposed_goal.subgoals.values():
        if subgoal.name == "Custom Subgoal 1":
            custom_subgoal_found = True
            break
    
    assert custom_subgoal_found

@pytest.mark.asyncio
async def test_prioritize_subgoals(goal_decomposition_engine, sample_goal):
    """Test prioritizing subgoals."""
    # Decompose the goal
    decomposed_goal = await goal_decomposition_engine.decompose_goal(
        goal=sample_goal,
        strategy=DecompositionStrategy.TOP_DOWN
    )
    
    # Prioritize subgoals
    prioritized_ids = await goal_decomposition_engine.prioritize_subgoals(decomposed_goal.id)
    
    # Check the result
    assert len(prioritized_ids) > 0
    assert len(prioritized_ids) == len(decomposed_goal.subgoals)
    
    # Check that all subgoal IDs are included
    for subgoal_id in decomposed_goal.subgoals:
        assert subgoal_id in prioritized_ids

@pytest.mark.asyncio
async def test_estimate_resources(goal_decomposition_engine, sample_goal):
    """Test estimating resources for a decomposed goal."""
    # Decompose the goal
    decomposed_goal = await goal_decomposition_engine.decompose_goal(
        goal=sample_goal,
        strategy=DecompositionStrategy.TOP_DOWN
    )
    
    # Estimate resources
    resources = await goal_decomposition_engine.estimate_resources(decomposed_goal.id)
    
    # Check the result
    assert resources is not None
    assert resources.time_hours > 0
    assert resources.complexity > 0
    assert len(resources.knowledge_requirements) > 0
    assert resources.risk_level > 0

@pytest.mark.asyncio
async def test_validate_decomposition(goal_decomposition_engine, sample_goal):
    """Test validating a goal decomposition."""
    # Decompose the goal
    decomposed_goal = await goal_decomposition_engine.decompose_goal(
        goal=sample_goal,
        strategy=DecompositionStrategy.TOP_DOWN
    )
    
    # Validate the decomposition
    validation = await goal_decomposition_engine.validate_decomposition(decomposed_goal.id)
    
    # Check the result
    assert validation is not None
    assert "valid" in validation
    assert "errors" in validation
    assert "warnings" in validation

@pytest.mark.asyncio
async def test_get_decomposed_goal(goal_decomposition_engine, sample_goal):
    """Test getting a decomposed goal by ID."""
    # Decompose the goal
    decomposed_goal = await goal_decomposition_engine.decompose_goal(
        goal=sample_goal,
        strategy=DecompositionStrategy.TOP_DOWN
    )
    
    # Get the decomposed goal
    retrieved_goal = await goal_decomposition_engine.get_decomposed_goal(decomposed_goal.id)
    
    # Check the result
    assert retrieved_goal is not None
    assert retrieved_goal.id == decomposed_goal.id
    assert retrieved_goal.name == decomposed_goal.name
    assert len(retrieved_goal.subgoals) == len(decomposed_goal.subgoals)

@pytest.mark.asyncio
async def test_get_all_decomposed_goals(goal_decomposition_engine, sample_goal):
    """Test getting all decomposed goals."""
    # Decompose multiple goals
    goal1 = await goal_decomposition_engine.decompose_goal(
        goal=sample_goal,
        strategy=DecompositionStrategy.TOP_DOWN
    )
    
    goal2 = await goal_decomposition_engine.decompose_goal(
        goal={"name": "Another Goal", "description": "Another test goal", "type": "RESEARCH"},
        strategy=DecompositionStrategy.BOTTOM_UP
    )
    
    # Get all decomposed goals
    all_goals = await goal_decomposition_engine.get_all_decomposed_goals()
    
    # Check the result
    assert len(all_goals) >= 2
    assert goal1.id in all_goals
    assert goal2.id in all_goals

@pytest.mark.asyncio
async def test_delete_decomposed_goal(goal_decomposition_engine, sample_goal):
    """Test deleting a decomposed goal."""
    # Decompose the goal
    decomposed_goal = await goal_decomposition_engine.decompose_goal(
        goal=sample_goal,
        strategy=DecompositionStrategy.TOP_DOWN
    )
    
    # Delete the decomposed goal
    result = await goal_decomposition_engine.delete_decomposed_goal(decomposed_goal.id)
    
    # Check the result
    assert result is True
    
    # Try to get the deleted goal
    deleted_goal = await goal_decomposition_engine.get_decomposed_goal(decomposed_goal.id)
    assert deleted_goal is None

@pytest.mark.asyncio
async def test_further_decompose_subgoal(goal_decomposition_engine):
    """Test further decomposing a subgoal."""
    # Create a subgoal
    resources = ResourceEstimate(
        time_hours=10.0,
        complexity=7,
        knowledge_requirements=["python", "testing"],
        dependencies=[],
        risk_level=5
    )
    
    subgoal = SubGoal(
        id=str(uuid.uuid4()),
        name="Test Subgoal",
        description="A test subgoal",
        goal_type=GoalType.DEVELOPMENT,
        priority=8,
        resources=resources,
        parent_id=None,
        children_ids=[],
        status="pending"
    )
    
    # Further decompose the subgoal
    child_subgoals = await goal_decomposition_engine._further_decompose_subgoal(
        subgoal=subgoal,
        goal_type=GoalType.DEVELOPMENT
    )
    
    # Check the result
    assert len(child_subgoals) > 0
    
    # Check that all child subgoals have the parent ID set
    for child in child_subgoals.values():
        assert child.parent_id == subgoal.id

Task 3.7: Update Documentation
File Path: docs/planning/goal_decomposition.md
Implementation Instructions:

# Goal Decomposition Engine

The Goal Decomposition Engine is a component of the Self-Aware Cerebrum system that breaks down high-level goals into manageable subgoals. It provides a structured approach to planning and executing complex tasks by decomposing them into smaller, more manageable pieces.

## Overview

The Goal Decomposition Engine takes a high-level goal and decomposes it into a hierarchy of subgoals using various decomposition strategies. It also provides functionality for prioritizing subgoals, estimating resources, and validating decompositions.

## Key Features

- **Goal Decomposition**: Break down high-level goals into manageable subgoals using different strategies.
- **Resource Estimation**: Estimate the resources required for each subgoal and the overall goal.
- **Subgoal Prioritization**: Prioritize subgoals based on various factors such as dependencies, complexity, and risk.
- **Decomposition Validation**: Validate decompositions for completeness and consistency.
- **Knowledge Integration**: Leverage the Knowledge Integration System to inform the decomposition process.

## Goal Types

The engine supports different types of goals, each with its own decomposition patterns:

- **GENERAL**: General-purpose goals without a specific domain.
- **RESEARCH**: Goals focused on research and information gathering.
- **DEVELOPMENT**: Goals focused on software development.
- **ANALYSIS**: Goals focused on data analysis and interpretation.
- **PLANNING**: Goals focused on planning and organization.
- **LEARNING**: Goals focused on learning and skill acquisition.

## Decomposition Strategies

The engine supports different strategies for decomposing goals:

- **TOP_DOWN**: Start with the high-level goal and break it down into smaller subgoals.
- **BOTTOM_UP**: Start with basic tasks and group them into higher-level subgoals.
- **MIDDLE_OUT**: Start with key components and expand both up and down.
- **TEMPLATE_BASED**: Use predefined templates for common goal types.
- **KNOWLEDGE_BASED**: Use the Knowledge Integration System to inform the decomposition.

## Resource Estimation

For each subgoal, the engine estimates the following resources:

- **Time**: Estimated time required to complete the subgoal (in hours).
- **Complexity**: Complexity level of the subgoal (1-10).
- **Knowledge Requirements**: Specific knowledge areas required for the subgoal.
- **Dependencies**: Other subgoals that must be completed before this one.
- **Risk Level**: Risk level associated with the subgoal (1-10).

## Usage

### Command Line Interface

The Goal Decomposition Engine can be used through the command line interface:

```bash
# Decompose a goal
python -m src.server.cli goal decompose --name "Implement Feature X" --description "Implement a new feature X for the system" --type DEVELOPMENT

# Get subgoals for a decomposed goal
python -m src.server.cli goal subgoals <goal_id>

# Prioritize subgoals
python -m src.server.cli goal prioritize <goal_id>

# Validate a decomposition
python -m src.server.cli goal validate <goal_id>
```

### Streamlit UI

The Goal Decomposition Engine can also be used through the Streamlit UI:

1. Navigate to the "Goal Decomposition" page.
2. Use the "Decompose Goal" tab to decompose a new goal.
3. Use the "View Subgoals" tab to view the subgoals for a decomposed goal.
4. Use the "Prioritize Subgoals" tab to prioritize subgoals.
5. Use the "Validate Decomposition" tab to validate a decomposition.

## Integration with Other Components

The Goal Decomposition Engine integrates with other components of the Self-Aware Cerebrum system:

- **Knowledge Integration System**: Provides relevant knowledge for the decomposition process.
- **AI Parameter Manager**: Configures the AI models used for decomposition.
- **Self-Aware System**: Provides access to the Goal Decomposition Engine through the API.

## Future Enhancements

Planned enhancements for the Goal Decomposition Engine include:

- **Advanced Decomposition Strategies**: More sophisticated strategies for decomposing goals.
- **Machine Learning-Based Resource Estimation**: More accurate resource estimation using machine learning.
- **Interactive Decomposition**: Interactive decomposition process with user feedback.
- **Visualization Improvements**: Better visualization of goal decompositions.
- **Integration with Implementation Planner**: Tighter integration with the Implementation Planner.


Task 3.8: Update README.md
File Path: README.md
Changes Required:
Add information about the Goal Decomposition Engine
Update the list of implemented components
Implementation Instructions:
.
Testing Plan for Goal Decomposition Engine
Unit Tests
Basic Functionality Tests
Test goal decomposition with different strategies
Test resource estimation
Test subgoal prioritization
Test decomposition validation
Edge Case Tests
Test with empty or minimal goals
Test with very complex goals
Test with invalid inputs
Integration Tests
Test integration with Knowledge Integration System
Test integration with Self-Aware System
Test CLI and UI integration
Manual Testing
UI Testing
Test the Streamlit UI for goal decomposition
Test visualization of decomposed goals
Test user interactions with the UI
End-to-End Testing
Test the complete workflow from goal creation to decomposition to prioritization
Test exporting and importing decomposed goals
Test using decomposed goals for planning
Timeline for Implementation
Week 1: Core Implementation
Implement the Goal Decomposition Engine
Implement basic decomposition strategies
Implement resource estimation
Week 2: Integration and Testing
Integrate with Self-Aware System
Update CLI and UI
Implement unit tests
Perform manual testing
Week 3: Documentation and Refinement
Complete documentation
Refine the implementation based on testing
Add advanced features if time permits
Conclusion
The Goal Decomposition Engine is a critical component of the Planning Engine phase of the Self-Aware Cerebrum system. It provides a structured approach to breaking down complex goals into manageable subgoals, which is essential for effective planning and execution. By implementing this component, we are taking a significant step toward completing Phase 3 of the implementation roadmap.


## Goal Decomposition Engine

The Self-Aware Cerebrum system now includes a Goal Decomposition Engine, which breaks down high-level goals into manageable subgoals. This component provides a structured approach to planning and executing complex tasks by decomposing them into smaller, more manageable pieces.

Key features of the Goal Decomposition Engine include:

- **Goal Decomposition**: Break down high-level goals into manageable subgoals using different strategies.
- **Resource Estimation**: Estimate the resources required for each subgoal and the overall goal.
- **Subgoal Prioritization**: Prioritize subgoals based on various factors such as dependencies, complexity, and risk.
- **Decomposition Validation**: Validate decompositions for completeness and consistency.
- **Knowledge Integration**: Leverage the Knowledge Integration System to inform the decomposition process.

For more information, see the [Goal Decomposition Engine documentation](docs/planning/goal_decomposition.md).


Testing Plan for Goal Decomposition Engine
Unit Tests
Basic Functionality Tests
Test goal decomposition with different strategies
Test resource estimation
Test subgoal prioritization
Test decomposition validation
Edge Case Tests
Test with empty or minimal goals
Test with very complex goals
Test with invalid inputs
Integration Tests
Test integration with Knowledge Integration System
Test integration with Self-Aware System
Test CLI and UI integration
Manual Testing
UI Testing
Test the Streamlit UI for goal decomposition
Test visualization of decomposed goals
Test user interactions with the UI
End-to-End Testing
Test the complete workflow from goal creation to decomposition to prioritization
Test exporting and importing decomposed goals
Test using decomposed goals for planning
Timeline for Implementation
Week 1: Core Implementation
Implement the Goal Decomposition Engine
Implement basic decomposition strategies
Implement resource estimation
Week 2: Integration and Testing
Integrate with Self-Aware System
Update CLI and UI
Implement unit tests
Perform manual testing
Week 3: Documentation and Refinement
Complete documentation
Refine the implementation based on testing
Add advanced features if time permits
