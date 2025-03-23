"""
Planning Engine Workflow Manager.

This module provides workflow management for the Planning Engine,
orchestrating cross-component workflows and managing their execution.
"""

from typing import Dict, List, Optional, Any, Union, Callable, Awaitable
import logging
import asyncio
import json
from enum import Enum, auto
from datetime import datetime
import uuid

from src.server.planning.planning_engine import (
    PlanningEngine, 
    IntegratedPlan,
    PlanType
)
from src.server.planning.goal_decomposition import (
    GoalType,
    DecompositionStrategy
)

logger = logging.getLogger(__name__)

class WorkflowStepStatus(Enum):
    """Status of a workflow step."""
    PENDING = auto()
    IN_PROGRESS = auto()
    COMPLETED = auto()
    FAILED = auto()
    SKIPPED = auto()

class WorkflowStatus(Enum):
    """Status of a workflow."""
    PENDING = auto()
    IN_PROGRESS = auto()
    COMPLETED = auto()
    FAILED = auto()
    CANCELLED = auto()

class PlanningWorkflow:
    """
    Manages workflows that span multiple planning components.
    
    This class orchestrates complex workflows across planning components,
    tracks their execution, and manages state transitions.
    """
    
    def __init__(self, planning_engine: PlanningEngine):
        """
        Initialize the Planning Workflow.
        
        Args:
            planning_engine: The Planning Engine instance
        """
        self.planning_engine = planning_engine
        self.workflows: Dict[str, Dict[str, Any]] = {}
    
    async def create_research_driven_workflow(
        self,
        name: str,
        description: str,
        initial_goal: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Create a research-driven workflow that adapts based on research findings.
        
        This workflow first decomposes a goal, conducts research, and then
        iteratively refines the goal and planning based on findings.
        
        Args:
            name: Name of the workflow
            description: Description of the workflow
            initial_goal: Initial goal definition
            context: Additional context information
            
        Returns:
            Workflow ID
        """
        workflow_id = str(uuid.uuid4())
        
        # Define workflow steps
        steps = [
            {
                "id": "goal_decomposition",
                "name": "Initial Goal Decomposition",
                "function": self._execute_goal_decomposition,
                "params": {
                    "goal": initial_goal,
                    "context": context
                },
                "status": WorkflowStepStatus.PENDING,
                "result": None,
                "dependencies": []
            },
            {
                "id": "research_planning",
                "name": "Research Planning",
                "function": self._execute_research_planning,
                "params": {
                    "context": context
                },
                "status": WorkflowStepStatus.PENDING,
                "result": None,
                "dependencies": ["goal_decomposition"]
            },
            {
                "id": "research_analysis",
                "name": "Research Analysis",
                "function": self._execute_research_analysis,
                "params": {
                    "context": context
                },
                "status": WorkflowStepStatus.PENDING,
                "result": None,
                "dependencies": ["research_planning"]
            },
            {
                "id": "goal_refinement",
                "name": "Goal Refinement",
                "function": self._execute_goal_refinement,
                "params": {
                    "context": context
                },
                "status": WorkflowStepStatus.PENDING,
                "result": None,
                "dependencies": ["research_analysis"]
            },
            {
                "id": "implementation_planning",
                "name": "Implementation Planning",
                "function": self._execute_implementation_planning,
                "params": {
                    "context": context
                },
                "status": WorkflowStepStatus.PENDING,
                "result": None,
                "dependencies": ["goal_refinement"]
            },
            {
                "id": "resource_allocation",
                "name": "Resource Allocation",
                "function": self._execute_resource_allocation,
                "params": {
                    "context": context
                },
                "status": WorkflowStepStatus.PENDING,
                "result": None,
                "dependencies": ["implementation_planning"]
            },
            {
                "id": "plan_integration",
                "name": "Plan Integration",
                "function": self._execute_plan_integration,
                "params": {
                    "name": name,
                    "description": description,
                    "context": context
                },
                "status": WorkflowStepStatus.PENDING,
                "result": None,
                "dependencies": ["resource_allocation"]
            }
        ]
        
        # Create the workflow
        workflow = {
            "id": workflow_id,
            "name": name,
            "description": description,
            "type": "research_driven",
            "steps": {step["id"]: step for step in steps},
            "step_order": [step["id"] for step in steps],
            "status": WorkflowStatus.PENDING,
            "start_time": None,
            "end_time": None,
            "result": None,
            "context": context or {}
        }
        
        self.workflows[workflow_id] = workflow
        logger.info(f"Created research-driven workflow: {workflow_id}")
        
        return workflow_id
    
    async def create_implementation_focused_workflow(
        self,
        name: str,
        description: str,
        implementation_requirements: List[str],
        constraints: List[str],
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Create an implementation-focused workflow that emphasizes solution design.
        
        This workflow focuses on solution design and implementation planning,
        with resource allocation and dependency management.
        
        Args:
            name: Name of the workflow
            description: Description of the workflow
            implementation_requirements: Implementation requirements
            constraints: Implementation constraints
            context: Additional context information
            
        Returns:
            Workflow ID
        """
        workflow_id = str(uuid.uuid4())
        
        # Define workflow steps
        steps = [
            {
                "id": "solution_design",
                "name": "Solution Design",
                "function": self._execute_solution_design,
                "params": {
                    "requirements": implementation_requirements,
                    "constraints": constraints,
                    "context": context
                },
                "status": WorkflowStepStatus.PENDING,
                "result": None,
                "dependencies": []
            },
            {
                "id": "implementation_planning",
                "name": "Implementation Planning",
                "function": self._execute_implementation_planning_from_design,
                "params": {
                    "context": context
                },
                "status": WorkflowStepStatus.PENDING,
                "result": None,
                "dependencies": ["solution_design"]
            },
            {
                "id": "dependency_analysis",
                "name": "Dependency Analysis",
                "function": self._execute_dependency_analysis,
                "params": {
                    "context": context
                },
                "status": WorkflowStepStatus.PENDING,
                "result": None,
                "dependencies": ["implementation_planning"]
            },
            {
                "id": "resource_allocation",
                "name": "Resource Allocation",
                "function": self._execute_resource_allocation_from_impl,
                "params": {
                    "context": context
                },
                "status": WorkflowStepStatus.PENDING,
                "result": None,
                "dependencies": ["dependency_analysis"]
            },
            {
                "id": "plan_integration",
                "name": "Plan Integration",
                "function": self._execute_plan_integration_impl_focused,
                "params": {
                    "name": name,
                    "description": description,
                    "context": context
                },
                "status": WorkflowStepStatus.PENDING,
                "result": None,
                "dependencies": ["resource_allocation"]
            }
        ]
        
        # Create the workflow
        workflow = {
            "id": workflow_id,
            "name": name,
            "description": description,
            "type": "implementation_focused",
            "steps": {step["id"]: step for step in steps},
            "step_order": [step["id"] for step in steps],
            "status": WorkflowStatus.PENDING,
            "start_time": None,
            "end_time": None,
            "result": None,
            "context": context or {}
        }
        
        self.workflows[workflow_id] = workflow
        logger.info(f"Created implementation-focused workflow: {workflow_id}")
        
        return workflow_id
    
    async def execute_workflow(self, workflow_id: str) -> Dict[str, Any]:
        """
        Execute a workflow by processing its steps in order.
        
        Args:
            workflow_id: ID of the workflow to execute
            
        Returns:
            Workflow execution result
        """
        if workflow_id not in self.workflows:
            raise ValueError(f"Workflow not found: {workflow_id}")
        
        workflow = self.workflows[workflow_id]
        
        # Update workflow status
        workflow["status"] = WorkflowStatus.IN_PROGRESS
        workflow["start_time"] = datetime.now().isoformat()
        
        logger.info(f"Executing workflow: {workflow_id}")
        
        # Create shared workflow context
        workflow_context = {
            "workflow_id": workflow_id,
            "intermediate_results": {},
            **(workflow["context"] or {})
        }
        
        # Process steps in order, respecting dependencies
        for step_id in workflow["step_order"]:
            step = workflow["steps"][step_id]
            
            # Check dependencies
            dependencies_met = all(
                workflow["steps"][dep_id]["status"] == WorkflowStepStatus.COMPLETED
                for dep_id in step["dependencies"]
            )
            
            if not dependencies_met:
                step["status"] = WorkflowStepStatus.SKIPPED
                logger.warning(f"Skipping step {step_id} due to unmet dependencies")
                continue
            
            # Execute step
            try:
                logger.info(f"Executing workflow step: {step_id}")
                step["status"] = WorkflowStepStatus.IN_PROGRESS
                
                # Merge workflow context with step params
                step_params = {
                    **step["params"],
                    "workflow_context": workflow_context
                }
                
                # Execute the step function
                step_result = await step["function"](**step_params)
                
                # Update step status and result
                step["status"] = WorkflowStepStatus.COMPLETED
                step["result"] = step_result
                
                # Update workflow context with step result
                workflow_context["intermediate_results"][step_id] = step_result
                
                logger.info(f"Completed workflow step: {step_id}")
            except Exception as e:
                logger.error(f"Error executing workflow step {step_id}: {e}")
                step["status"] = WorkflowStepStatus.FAILED
                step["error"] = str(e)
                
                # Mark workflow as failed
                workflow["status"] = WorkflowStatus.FAILED
                workflow["end_time"] = datetime.now().isoformat()
                workflow["error"] = f"Failed on step {step_id}: {e}"
                
                return {
                    "workflow_id": workflow_id,
                    "status": "failed",
                    "error": str(e),
                    "completed_steps": [
                        s for s in workflow["step_order"] 
                        if workflow["steps"][s]["status"] == WorkflowStepStatus.COMPLETED
                    ]
                }
        
        # Check if all steps completed successfully
        all_completed = all(
            workflow["steps"][step_id]["status"] == WorkflowStepStatus.COMPLETED
            for step_id in workflow["step_order"]
        )
        
        if all_completed:
            # Mark workflow as completed
            workflow["status"] = WorkflowStatus.COMPLETED
            workflow["end_time"] = datetime.now().isoformat()
            
            # Set workflow result
            final_step_id = workflow["step_order"][-1]
            workflow["result"] = workflow["steps"][final_step_id]["result"]
            
            logger.info(f"Workflow completed successfully: {workflow_id}")
        else:
            # Mark workflow as failed
            workflow["status"] = WorkflowStatus.FAILED
            workflow["end_time"] = datetime.now().isoformat()
            
            logger.warning(f"Workflow did not complete all steps: {workflow_id}")
        
        return {
            "workflow_id": workflow_id,
            "status": workflow["status"].name.lower(),
            "result": workflow["result"],
            "completed_steps": [
                step_id for step_id in workflow["step_order"] 
                if workflow["steps"][step_id]["status"] == WorkflowStepStatus.COMPLETED
            ]
        }
    
    async def get_workflow_status(self, workflow_id: str) -> Dict[str, Any]:
        """
        Get the current status of a workflow.
        
        Args:
            workflow_id: ID of the workflow
            
        Returns:
            Workflow status information
        """
        if workflow_id not in self.workflows:
            raise ValueError(f"Workflow not found: {workflow_id}")
        
        workflow = self.workflows[workflow_id]
        
        return {
            "id": workflow_id,
            "name": workflow["name"],
            "status": workflow["status"].name,
            "start_time": workflow["start_time"],
            "end_time": workflow["end_time"],
            "steps": {
                step_id: {
                    "name": step["name"],
                    "status": step["status"].name,
                    "dependencies": step["dependencies"]
                }
                for step_id, step in workflow["steps"].items()
            },
            "step_order": workflow["step_order"]
        }
    
    # Implementation of step functions
    
    async def _execute_goal_decomposition(
        self,
        goal: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
        workflow_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Execute goal decomposition step."""
        if not self.planning_engine.goal_decomposition_engine:
            raise ValueError("Goal Decomposition Engine not available")
        
        # Merge contexts
        merged_context = {**(context or {}), **(workflow_context or {})}
        
        # Determine goal type
        goal_type = goal.get("goal_type", "RESEARCH")
        if isinstance(goal_type, str):
            goal_type = GoalType.from_str(goal_type)
        
        # Determine decomposition strategy
        strategy = goal.get("strategy", "TOP_DOWN")
        if isinstance(strategy, str):
            strategy = DecompositionStrategy.from_str(strategy)
        
        decomposed_goal = await self.planning_engine.goal_decomposition_engine.decompose_goal(
            goal=goal,
            strategy=strategy,
            context=merged_context
        )
        
        return {
            "goal_id": decomposed_goal.id,
            "subgoal_count": len(decomposed_goal.subgoals)
        }
    
    async def _execute_research_planning(
        self,
        context: Optional[Dict[str, Any]] = None,
        workflow_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Execute research planning step."""
        if not self.planning_engine.research_planner:
            raise ValueError("Research Planner not available")
        
        # Get the decomposed goal from previous step
        if "goal_decomposition" not in workflow_context.get("intermediate_results", {}):
            raise ValueError("Goal decomposition result not found in workflow context")
        
        goal_result = workflow_context["intermediate_results"]["goal_decomposition"]
        goal_id = goal_result["goal_id"]
        
        # Get the decomposed goal
        decomposed_goal = await self.planning_engine.goal_decomposition_engine.get_decomposed_goal(goal_id)
        if not decomposed_goal:
            raise ValueError(f"Decomposed goal not found: {goal_id}")
        
        # Create research plans
        research_plan_ids = await self.planning_engine._create_research_plans_for_goal(
            decomposed_goal=decomposed_goal,
            context=context
        )
        
        return {
            "research_plan_ids": research_plan_ids,
            "research_plan_count": len(research_plan_ids)
        }
    
    async def _execute_research_analysis(
        self,
        context: Optional[Dict[str, Any]] = None,
        workflow_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Execute research analysis step."""
        if not self.planning_engine.research_planner:
            raise ValueError("Research Planner not available")
        
        # Get research plans from previous step
        if "research_planning" not in workflow_context.get("intermediate_results", {}):
            raise ValueError("Research planning result not found in workflow context")
        
        research_result = workflow_context["intermediate_results"]["research_planning"]
        research_plan_ids = research_result["research_plan_ids"]
        
        if not research_plan_ids:
            logger.warning("No research plans found, analysis step will be minimal")
            return {"knowledge_gaps_addressed": 0, "confidence_score": 0.0}
        
        # Analyze research plans and findings
        knowledge_gaps_addressed = 0
        confidence_scores = []
        
        for plan_id in research_plan_ids:
            plan = await self.planning_engine.research_planner.get_research_plan(plan_id)
            if not plan:
                continue
                
            # Count addressed knowledge gaps
            addressed_gaps = sum(1 for item in plan.research_items if item.status == "completed")
            knowledge_gaps_addressed += addressed_gaps
            
            # Calculate confidence score
            total_items = len(plan.research_items) or 1  # Avoid division by zero
            confidence_scores.append(addressed_gaps / total_items)
        
        avg_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0.0
        
        return {
            "knowledge_gaps_addressed": knowledge_gaps_addressed,
            "confidence_score": avg_confidence,
            "research_plan_ids": research_plan_ids
        }
    
    async def _execute_goal_refinement(
        self,
        context: Optional[Dict[str, Any]] = None,
        workflow_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Execute goal refinement step."""
        if not self.planning_engine.goal_decomposition_engine:
            raise ValueError("Goal Decomposition Engine not available")
        
        # Get data from previous steps
        if "goal_decomposition" not in workflow_context.get("intermediate_results", {}):
            raise ValueError("Goal decomposition result not found in workflow context")
            
        if "research_analysis" not in workflow_context.get("intermediate_results", {}):
            raise ValueError("Research analysis result not found in workflow context")
        
        goal_result = workflow_context["intermediate_results"]["goal_decomposition"]
        goal_id = goal_result["goal_id"]
        
        analysis_result = workflow_context["intermediate_results"]["research_analysis"]
        confidence_score = analysis_result["confidence_score"]
        
        # Get the decomposed goal
        decomposed_goal = await self.planning_engine.goal_decomposition_engine.get_decomposed_goal(goal_id)
        if not decomposed_goal:
            raise ValueError(f"Decomposed goal not found: {goal_id}")
        
        # Refine goal based on research findings
        # For this implementation, we just update the metadata
        # In a real implementation, this would involve adjusting subgoals based on research
        
        updates = {
            "metadata": {
                **decomposed_goal.metadata,
                "confidence_score": confidence_score,
                "refined": True,
                "refinement_timestamp": datetime.now().isoformat()
            }
        }
        
        # In a real implementation, you would update the goal with new insights
        # For now, we'll just log that refinement happened
        logger.info(f"Refined goal {goal_id} with confidence score {confidence_score}")
        
        return {
            "refined_goal_id": goal_id,
            "confidence_score": confidence_score,
            "updates": updates
        }
    
    async def _execute_implementation_planning(
        self,
        context: Optional[Dict[str, Any]] = None,
        workflow_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Execute implementation planning step."""
        if not self.planning_engine.implementation_planner or not self.planning_engine.solution_design_system:
            raise ValueError("Implementation Planner or Solution Design System not available")
        
        # Get data from previous steps
        if "goal_decomposition" not in workflow_context.get("intermediate_results", {}):
            raise ValueError("Goal decomposition result not found in workflow context")
            
        if "goal_refinement" not in workflow_context.get("intermediate_results", {}):
            logger.warning("Goal refinement result not found, using original goal")
        
        goal_result = workflow_context["intermediate_results"]["goal_decomposition"]
        goal_id = goal_result["goal_id"]
        
        # Get the decomposed goal
        decomposed_goal = await self.planning_engine.goal_decomposition_engine.get_decomposed_goal(goal_id)
        if not decomposed_goal:
            raise ValueError(f"Decomposed goal not found: {goal_id}")
        
        # Create implementation plan
        implementation_plan = await self.planning_engine._create_implementation_plan_for_goal(
            decomposed_goal=decomposed_goal,
            context=context
        )
        
        return {
            "implementation_plan_id": implementation_plan.id,
            "task_count": len(implementation_plan.tasks)
        }
    
    async def _execute_resource_allocation(
        self,
        context: Optional[Dict[str, Any]] = None,
        workflow_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Execute resource allocation step."""
        if not self.planning_engine.resource_allocation_manager:
            raise ValueError("Resource Allocation Manager not available")
        
        # Get data from previous steps
        if "goal_decomposition" not in workflow_context.get("intermediate_results", {}):
            raise ValueError("Goal decomposition result not found in workflow context")
            
        if "implementation_planning" not in workflow_context.get("intermediate_results", {}):
            raise ValueError("Implementation planning result not found in workflow context")
        
        goal_result = workflow_context["intermediate_results"]["goal_decomposition"]
        goal_id = goal_result["goal_id"]
        
        implementation_result = workflow_context["intermediate_results"]["implementation_planning"]
        implementation_plan_id = implementation_result["implementation_plan_id"]
        
        # Get the decomposed goal
        decomposed_goal = await self.planning_engine.goal_decomposition_engine.get_decomposed_goal(goal_id)
        if not decomposed_goal:
            raise ValueError(f"Decomposed goal not found: {goal_id}")
        
        # Create resource allocation plan
        allocation_plan = await self.planning_engine._create_resource_allocation_for_goal(
            decomposed_goal=decomposed_goal,
            implementation_plan_id=implementation_plan_id,
            context=context
        )
        
        return {
            "allocation_plan_id": allocation_plan.id,
            "allocation_count": len(allocation_plan.allocations)
        }
    
    async def _execute_plan_integration(
        self,
        name: str,
        description: str,
        context: Optional[Dict[str, Any]] = None,
        workflow_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Execute plan integration step."""
        # Get data from all previous steps
        results = workflow_context.get("intermediate_results", {})
        
        if "goal_decomposition" not in results:
            raise ValueError("Goal decomposition result not found")
            
        if "research_planning" not in results:
            logger.warning("Research planning result not found")
            
        if "implementation_planning" not in results:
            logger.warning("Implementation planning result not found")
            
        if "resource_allocation" not in results:
            logger.warning("Resource allocation result not found")
        
        # Create the integrated plan
        plan_id = str(uuid.uuid4())
        
        goal_id = results.get("goal_decomposition", {}).get("goal_id")
        research_plan_ids = results.get("research_planning", {}).get("research_plan_ids", [])
        implementation_plan_id = results.get("implementation_planning", {}).get("implementation_plan_id")
        allocation_plan_id = results.get("resource_allocation", {}).get("allocation_plan_id")
        
        # Additional metadata
        metadata = {
            "workflow_id": workflow_context.get("workflow_id"),
            "confidence_score": results.get("research_analysis", {}).get("confidence_score", 0.0),
            "is_refined": "goal_refinement" in results
        }
        
        # Create integrated plan
        integrated_plan = IntegratedPlan(
            id=plan_id,
            name=name,
            description=description,
            goal_decomposition_id=goal_id,
            research_plan_ids=research_plan_ids,
            implementation_plan_id=implementation_plan_id,
            resource_allocation_id=allocation_plan_id,
            metadata=metadata,
            status="completed",
            plan_type=PlanType.INTEGRATED
        )
        
        # Add to planning engine
        self.planning_engine.integrated_plans[plan_id] = integrated_plan
        self.planning_engine._save_integrated_plan(plan_id)
        
        return {
            "integrated_plan_id": plan_id,
            "goal_id": goal_id,
            "research_plan_count": len(research_plan_ids),
            "has_implementation": implementation_plan_id is not None,
            "has_resource_allocation": allocation_plan_id is not None
        }
    
    async def _execute_solution_design(
        self,
        requirements: List[str],
        constraints: List[str],
        context: Optional[Dict[str, Any]] = None,
        workflow_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Execute solution design step."""
        if not self.planning_engine.solution_design_system:
            raise ValueError("Solution Design System not available")
        
        # Merge contexts
        merged_context = {**(context or {}), **(workflow_context or {})}
        
        # Create solution design
        solution_design = await self.planning_engine.solution_design_system.create_solution_design(
            name=f"Design for {workflow_context.get('workflow_id', 'unknown')}",
            description="Solution design created by workflow",
            requirements=requirements,
            constraints=constraints,
            context=merged_context
        )
        
        return {
            "solution_design_id": solution_design.id,
            "component_count": len(solution_design.components)
        }
    
    async def _execute_implementation_planning_from_design(
        self,
        context: Optional[Dict[str, Any]] = None,
        workflow_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Execute implementation planning from solution design."""
        if not self.planning_engine.implementation_planner:
            raise ValueError("Implementation Planner not available")
        
        # Get the solution design from previous step
        if "solution_design" not in workflow_context.get("intermediate_results", {}):
            raise ValueError("Solution design result not found in workflow context")
        
        design_result = workflow_context["intermediate_results"]["solution_design"]
        design_id = design_result["solution_design_id"]
        
        # Merge contexts
        merged_context = {**(context or {}), **(workflow_context or {})}
        
        # Create implementation plan
        implementation_plan = await self.planning_engine.implementation_planner.create_implementation_plan(
            name=f"Implementation for {workflow_context.get('workflow_id', 'unknown')}",
            description="Implementation plan created by workflow",
            solution_design_id=design_id,
            context=merged_context
        )
        
        return {
            "implementation_plan_id": implementation_plan.id,
            "task_count": len(implementation_plan.tasks)
        }
    
    async def _execute_dependency_analysis(
        self,
        context: Optional[Dict[str, Any]] = None,
        workflow_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Execute dependency analysis step."""
        if not self.planning_engine.implementation_planner:
            raise ValueError("Implementation Planner not available")
        
        # Get implementation plan from previous step
        if "implementation_planning" not in workflow_context.get("intermediate_results", {}):
            raise ValueError("Implementation planning result not found in workflow context")
        
        impl_result = workflow_context["intermediate_results"]["implementation_planning"]
        impl_plan_id = impl_result["implementation_plan_id"]
        
        # Get implementation plan
        implementation_plan = await self.planning_engine.implementation_planner.get_implementation_plan(impl_plan_id)
        if not implementation_plan:
            raise ValueError(f"Implementation plan not found: {impl_plan_id}")
        
        # Analyze dependencies (simplified for this implementation)
        dependency_count = 0
        critical_path_length = 0
        
        for task in implementation_plan.tasks.values():
            dependency_count += len(task.dependencies)
            
            # Calculate the longest path (simplified)
            path_length = task.estimated_duration
            if path_length > critical_path_length:
                critical_path_length = path_length
        
        return {
            "implementation_plan_id": impl_plan_id,
            "dependency_count": dependency_count,
            "critical_path_length": critical_path_length
        }
    
    async def _execute_resource_allocation_from_impl(
        self,
        context: Optional[Dict[str, Any]] = None,
        workflow_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Execute resource allocation from implementation plan."""
        if not self.planning_engine.resource_allocation_manager:
            raise ValueError("Resource Allocation Manager not available")
        
        # Get implementation plan from previous steps
        if "implementation_planning" not in workflow_context.get("intermediate_results", {}):
            raise ValueError("Implementation planning result not found in workflow context")
        
        impl_result = workflow_context["intermediate_results"]["implementation_planning"]
        impl_plan_id = impl_result["implementation_plan_id"]
        
        # Get implementation plan
        implementation_plan = await self.planning_engine.implementation_planner.get_implementation_plan(impl_plan_id)
        if not implementation_plan:
            raise ValueError(f"Implementation plan not found: {impl_plan_id}")
        
        # Get resource pools
        pools = await self.planning_engine.resource_allocation_manager.get_all_resource_pools()
        if not pools:
            raise ValueError("No resource pools available")
        
        pool = list(pools.values())[0]
        
        # Prepare task requirements
        task_requirements = {}
        task_priorities = {}
        
        for task_id, task in implementation_plan.tasks.items():
            # Convert task resource needs to resource types
            resource_reqs = {
                "compute": task.metadata.get("compute_requirements", 1),
                "memory": task.metadata.get("memory_requirements", 1),
                "storage": task.metadata.get("storage_requirements", 1),
                "time": task.estimated_duration
            }
            task_requirements[task_id] = resource_reqs
            task_priorities[task_id] = task.priority
        
        # Create allocation plan
        allocation_plan = await self.planning_engine.resource_allocation_manager.create_allocation_plan(
            name=f"Resources for {implementation_plan.name}",
            description=f"Resource allocation for {implementation_plan.description}",
            pool_id=pool.id,
            task_requirements=task_requirements,
            task_priorities=task_priorities,
            context=context
        )
        
        return {
            "allocation_plan_id": allocation_plan.id,
            "allocation_count": len(allocation_plan.allocations)
        }
    
    async def _execute_plan_integration_impl_focused(
        self,
        name: str,
        description: str,
        context: Optional[Dict[str, Any]] = None,
        workflow_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Execute plan integration for implementation-focused workflow."""
        # Get data from all previous steps
        results = workflow_context.get("intermediate_results", {})
        
        if "solution_design" not in results:
            raise ValueError("Solution design result not found")
            
        if "implementation_planning" not in results:
            raise ValueError("Implementation planning result not found")
            
        if "resource_allocation" not in results:
            logger.warning("Resource allocation result not found")
        
        # Create the integrated plan
        plan_id = str(uuid.uuid4())
        
        solution_design_id = results.get("solution_design", {}).get("solution_design_id")
        implementation_plan_id = results.get("implementation_planning", {}).get("implementation_plan_id")
        allocation_plan_id = results.get("resource_allocation", {}).get("allocation_plan_id")
        
        # Get solution design
        solution_design = await self.planning_engine.solution_design_system.get_solution_design(
            solution_design_id
        )
        
        # Additional metadata
        metadata = {
            "workflow_id": workflow_context.get("workflow_id"),
            "workflow_type": "implementation_focused",
            "dependency_count": results.get("dependency_analysis", {}).get("dependency_count", 0),
            "critical_path_length": results.get("dependency_analysis", {}).get("critical_path_length", 0)
        }
        
        # Create integrated plan
        integrated_plan = IntegratedPlan(
            id=plan_id,
            name=name,
            description=description,
            implementation_plan_id=implementation_plan_id,
            resource_allocation_id=allocation_plan_id,
            metadata=metadata,
            status="completed",
            plan_type=PlanType.IMPLEMENTATION
        )
        
        # Add to planning engine
        self.planning_engine.integrated_plans[plan_id] = integrated_plan
        self.planning_engine._save_integrated_plan(plan_id)
        
        return {
            "integrated_plan_id": plan_id,
            "solution_design_id": solution_design_id,
            "implementation_plan_id": implementation_plan_id,
            "has_resource_allocation": allocation_plan_id is not None
        } 