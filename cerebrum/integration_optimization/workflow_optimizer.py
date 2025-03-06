from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime
import asyncio
import networkx as nx

@dataclass
class WorkflowMetrics:
    """Represents workflow performance metrics."""
    workflow_id: str
    execution_time: float
    success_rate: float
    resource_usage: Dict
    bottlenecks: List[Dict]
    metadata: Dict

@dataclass
class WorkflowBottleneck:
    """Represents a workflow bottleneck."""
    workflow_id: str
    step_id: str
    bottleneck_type: str
    impact: Dict
    recommendations: List[Dict]
    metadata: Dict

@dataclass
class WorkflowOptimization:
    """Represents a workflow optimization."""
    workflow_id: str
    optimization_type: str
    target_steps: List[str]
    estimated_impact: Dict
    implementation_steps: List[Dict]
    metadata: Dict

class WorkflowOptimizer:
    """Optimizes system workflows."""
    
    def __init__(self, knowledge_system, goal_decomposition_engine):
        self.knowledge_system = knowledge_system
        self.goal_decomposition_engine = goal_decomposition_engine
        self.workflow_metrics: Dict[str, WorkflowMetrics] = {}
        self.workflow_bottlenecks: Dict[str, List[WorkflowBottleneck]] = {}
        self.workflow_optimizations: Dict[str, List[WorkflowOptimization]] = {}
        self.workflow_graph = nx.DiGraph()
        
    async def analyze_workflow_efficiency(
        self, workflow_type: str
    ) -> Dict[str, WorkflowMetrics]:
        """
        Analyze the efficiency of specific workflow types.
        
        Args:
            workflow_type (str): Type of workflow to analyze
            
        Returns:
            Dict[str, WorkflowMetrics]: Workflow efficiency metrics
        """
        # Get workflow execution data
        workflows = await self.knowledge_system.get_workflows(workflow_type)
        
        metrics = {}
        
        for workflow_id, workflow in workflows.items():
            # Analyze workflow structure
            self._build_workflow_graph(workflow)
            
            # Calculate metrics
            execution_metrics = self._calculate_execution_metrics(workflow)
            success_metrics = self._calculate_success_metrics(workflow)
            resource_metrics = self._calculate_resource_metrics(workflow)
            bottleneck_analysis = self._analyze_workflow_bottlenecks(workflow)
            
            metrics[workflow_id] = WorkflowMetrics(
                workflow_id=workflow_id,
                execution_time=execution_metrics["total_time"],
                success_rate=success_metrics["success_rate"],
                resource_usage=resource_metrics,
                bottlenecks=bottleneck_analysis,
                metadata={
                    "analyzed_at": datetime.now().isoformat(),
                    "workflow_type": workflow_type,
                    "step_count": len(workflow["steps"]),
                    "execution_history": execution_metrics["history"]
                }
            )
            
        # Store metrics
        self.workflow_metrics.update(metrics)
        
        return metrics
        
    async def identify_workflow_bottlenecks(
        self, workflow_id: str
    ) -> List[WorkflowBottleneck]:
        """
        Identify bottlenecks in specific workflows.
        
        Args:
            workflow_id (str): ID of workflow to analyze
            
        Returns:
            List[WorkflowBottleneck]: Identified workflow bottlenecks
        """
        if workflow_id not in self.workflow_metrics:
            raise ValueError(f"No metrics found for workflow: {workflow_id}")
            
        metrics = self.workflow_metrics[workflow_id]
        bottlenecks = []
        
        # Analyze execution time bottlenecks
        if self._has_execution_bottlenecks(metrics):
            bottlenecks.extend(
                self._identify_execution_bottlenecks(workflow_id, metrics)
            )
            
        # Analyze resource usage bottlenecks
        if self._has_resource_bottlenecks(metrics):
            bottlenecks.extend(
                self._identify_resource_bottlenecks(workflow_id, metrics)
            )
            
        # Analyze dependency bottlenecks
        if self._has_dependency_bottlenecks(workflow_id):
            bottlenecks.extend(
                self._identify_dependency_bottlenecks(workflow_id)
            )
            
        # Store bottlenecks
        self.workflow_bottlenecks[workflow_id] = bottlenecks
        
        return bottlenecks
        
    async def recommend_workflow_improvements(
        self, workflow_id: str
    ) -> List[WorkflowOptimization]:
        """
        Recommend improvements to specific workflows.
        
        Args:
            workflow_id (str): ID of workflow to improve
            
        Returns:
            List[WorkflowOptimization]: Recommended workflow optimizations
        """
        if workflow_id not in self.workflow_bottlenecks:
            await self.identify_workflow_bottlenecks(workflow_id)
            
        bottlenecks = self.workflow_bottlenecks[workflow_id]
        optimizations = []
        
        # Generate optimizations for execution bottlenecks
        execution_bottlenecks = [
            b for b in bottlenecks 
            if b.bottleneck_type == "execution"
        ]
        if execution_bottlenecks:
            optimizations.extend(
                self._generate_execution_optimizations(workflow_id, execution_bottlenecks)
            )
            
        # Generate optimizations for resource bottlenecks
        resource_bottlenecks = [
            b for b in bottlenecks 
            if b.bottleneck_type == "resource"
        ]
        if resource_bottlenecks:
            optimizations.extend(
                self._generate_resource_optimizations(workflow_id, resource_bottlenecks)
            )
            
        # Generate optimizations for dependency bottlenecks
        dependency_bottlenecks = [
            b for b in bottlenecks 
            if b.bottleneck_type == "dependency"
        ]
        if dependency_bottlenecks:
            optimizations.extend(
                self._generate_dependency_optimizations(workflow_id, dependency_bottlenecks)
            )
            
        # Store optimizations
        self.workflow_optimizations[workflow_id] = optimizations
        
        return optimizations
        
    async def implement_workflow_optimizations(
        self, workflow_id: str, optimizations: List[Dict]
    ) -> List[Dict]:
        """
        Implement approved workflow optimizations.
        
        Args:
            workflow_id (str): ID of workflow to optimize
            optimizations (List[Dict]): Optimizations to implement
            
        Returns:
            List[Dict]: Implementation results
        """
        results = []
        
        for optimization in optimizations:
            try:
                # Validate optimization
                if not self._is_valid_optimization(optimization):
                    raise ValueError(f"Invalid optimization: {optimization}")
                    
                # Implement optimization
                if optimization["type"] == "execution":
                    result = await self._implement_execution_optimization(
                        workflow_id, optimization
                    )
                elif optimization["type"] == "resource":
                    result = await self._implement_resource_optimization(
                        workflow_id, optimization
                    )
                elif optimization["type"] == "dependency":
                    result = await self._implement_dependency_optimization(
                        workflow_id, optimization
                    )
                else:
                    raise ValueError(f"Unknown optimization type: {optimization['type']}")
                    
                results.append({
                    "optimization": optimization,
                    "success": True,
                    "result": result
                })
                
            except Exception as e:
                results.append({
                    "optimization": optimization,
                    "success": False,
                    "error": str(e)
                })
                
        return results
        
    def _build_workflow_graph(self, workflow: Dict):
        """Build graph representation of workflow."""
        self.workflow_graph.clear()
        
        # Add nodes for each step
        for step in workflow["steps"]:
            self.workflow_graph.add_node(
                step["id"],
                **step
            )
            
        # Add edges for dependencies
        for step in workflow["steps"]:
            for dep in step.get("dependencies", []):
                self.workflow_graph.add_edge(dep, step["id"])
                
    def _calculate_execution_metrics(self, workflow: Dict) -> Dict:
        """Calculate workflow execution metrics."""
        executions = workflow.get("execution_history", [])
        
        if not executions:
            return {
                "total_time": 0.0,
                "average_time": 0.0,
                "history": []
            }
            
        total_times = []
        for execution in executions:
            start_time = datetime.fromisoformat(execution["start_time"])
            end_time = datetime.fromisoformat(execution["end_time"])
            total_times.append((end_time - start_time).total_seconds())
            
        return {
            "total_time": sum(total_times),
            "average_time": sum(total_times) / len(total_times),
            "history": total_times
        }
        
    def _calculate_success_metrics(self, workflow: Dict) -> Dict:
        """Calculate workflow success metrics."""
        executions = workflow.get("execution_history", [])
        
        if not executions:
            return {
                "success_rate": 0.0,
                "failure_reasons": {}
            }
            
        successes = sum(1 for e in executions if e["status"] == "success")
        
        # Count failure reasons
        failure_reasons = {}
        for execution in executions:
            if execution["status"] == "failure":
                reason = execution.get("failure_reason", "unknown")
                failure_reasons[reason] = failure_reasons.get(reason, 0) + 1
                
        return {
            "success_rate": successes / len(executions),
            "failure_reasons": failure_reasons
        }
        
    def _calculate_resource_metrics(self, workflow: Dict) -> Dict:
        """Calculate workflow resource usage metrics."""
        executions = workflow.get("execution_history", [])
        
        if not executions:
            return {
                "cpu_usage": 0.0,
                "memory_usage": 0.0,
                "io_operations": 0
            }
            
        # Calculate average resource usage
        cpu_usage = []
        memory_usage = []
        io_operations = []
        
        for execution in executions:
            resources = execution.get("resource_usage", {})
            cpu_usage.append(resources.get("cpu", 0.0))
            memory_usage.append(resources.get("memory", 0.0))
            io_operations.append(resources.get("io", 0))
            
        return {
            "cpu_usage": sum(cpu_usage) / len(cpu_usage),
            "memory_usage": sum(memory_usage) / len(memory_usage),
            "io_operations": sum(io_operations) / len(io_operations)
        }
        
    def _analyze_workflow_bottlenecks(self, workflow: Dict) -> List[Dict]:
        """Analyze workflow for bottlenecks."""
        bottlenecks = []
        
        # Analyze step execution times
        step_times = self._analyze_step_times(workflow)
        for step_id, metrics in step_times.items():
            if metrics["average_time"] > self._get_step_time_threshold():
                bottlenecks.append({
                    "type": "execution",
                    "step_id": step_id,
                    "metrics": metrics
                })
                
        # Analyze resource usage
        step_resources = self._analyze_step_resources(workflow)
        for step_id, metrics in step_resources.items():
            if self._is_resource_bottleneck(metrics):
                bottlenecks.append({
                    "type": "resource",
                    "step_id": step_id,
                    "metrics": metrics
                })
                
        # Analyze dependencies
        dependency_issues = self._analyze_dependencies(workflow)
        bottlenecks.extend(dependency_issues)
        
        return bottlenecks
        
    def _has_execution_bottlenecks(self, metrics: WorkflowMetrics) -> bool:
        """Check for execution time bottlenecks."""
        return metrics.execution_time > self._get_workflow_time_threshold()
        
    def _has_resource_bottlenecks(self, metrics: WorkflowMetrics) -> bool:
        """Check for resource usage bottlenecks."""
        return any(
            usage > threshold
            for usage, threshold in [
                (metrics.resource_usage["cpu_usage"], 0.8),
                (metrics.resource_usage["memory_usage"], 0.8),
                (metrics.resource_usage["io_operations"], 1000)
            ]
        )
        
    def _has_dependency_bottlenecks(self, workflow_id: str) -> bool:
        """Check for dependency bottlenecks."""
        try:
            cycles = list(nx.simple_cycles(self.workflow_graph))
            return len(cycles) > 0
        except nx.NetworkXNoCycle:
            return False
            
    def _identify_execution_bottlenecks(
        self, workflow_id: str, metrics: WorkflowMetrics
    ) -> List[WorkflowBottleneck]:
        """Identify execution time bottlenecks."""
        bottlenecks = []
        
        for step_metrics in metrics.bottlenecks:
            if step_metrics["type"] == "execution":
                bottleneck = WorkflowBottleneck(
                    workflow_id=workflow_id,
                    step_id=step_metrics["step_id"],
                    bottleneck_type="execution",
                    impact=self._calculate_execution_impact(step_metrics),
                    recommendations=self._generate_execution_recommendations(step_metrics),
                    metadata={
                        "identified_at": datetime.now().isoformat(),
                        "metrics": step_metrics["metrics"]
                    }
                )
                bottlenecks.append(bottleneck)
                
        return bottlenecks
        
    def _identify_resource_bottlenecks(
        self, workflow_id: str, metrics: WorkflowMetrics
    ) -> List[WorkflowBottleneck]:
        """Identify resource usage bottlenecks."""
        bottlenecks = []
        
        for step_metrics in metrics.bottlenecks:
            if step_metrics["type"] == "resource":
                bottleneck = WorkflowBottleneck(
                    workflow_id=workflow_id,
                    step_id=step_metrics["step_id"],
                    bottleneck_type="resource",
                    impact=self._calculate_resource_impact(step_metrics),
                    recommendations=self._generate_resource_recommendations(step_metrics),
                    metadata={
                        "identified_at": datetime.now().isoformat(),
                        "metrics": step_metrics["metrics"]
                    }
                )
                bottlenecks.append(bottleneck)
                
        return bottlenecks
        
    def _identify_dependency_bottlenecks(
        self, workflow_id: str
    ) -> List[WorkflowBottleneck]:
        """Identify dependency bottlenecks."""
        bottlenecks = []
        
        try:
            cycles = list(nx.simple_cycles(self.workflow_graph))
            for cycle in cycles:
                bottleneck = WorkflowBottleneck(
                    workflow_id=workflow_id,
                    step_id=cycle[0],  # Use first step in cycle
                    bottleneck_type="dependency",
                    impact=self._calculate_dependency_impact(cycle),
                    recommendations=self._generate_dependency_recommendations(cycle),
                    metadata={
                        "identified_at": datetime.now().isoformat(),
                        "cycle": cycle
                    }
                )
                bottlenecks.append(bottleneck)
                
        except nx.NetworkXNoCycle:
            pass
            
        return bottlenecks
        
    def _generate_execution_optimizations(
        self, workflow_id: str, bottlenecks: List[WorkflowBottleneck]
    ) -> List[WorkflowOptimization]:
        """Generate execution time optimizations."""
        optimizations = []
        
        for bottleneck in bottlenecks:
            optimization = WorkflowOptimization(
                workflow_id=workflow_id,
                optimization_type="execution",
                target_steps=[bottleneck.step_id],
                estimated_impact={
                    "time_reduction": 0.3,
                    "resource_savings": 0.2
                },
                implementation_steps=[
                    {
                        "step": 1,
                        "description": "Profile step execution",
                        "effort": "low"
                    },
                    {
                        "step": 2,
                        "description": "Implement caching",
                        "effort": "medium"
                    },
                    {
                        "step": 3,
                        "description": "Optimize algorithms",
                        "effort": "high"
                    }
                ],
                metadata={
                    "priority": "high",
                    "bottleneck": bottleneck
                }
            )
            optimizations.append(optimization)
            
        return optimizations
        
    def _generate_resource_optimizations(
        self, workflow_id: str, bottlenecks: List[WorkflowBottleneck]
    ) -> List[WorkflowOptimization]:
        """Generate resource usage optimizations."""
        optimizations = []
        
        for bottleneck in bottlenecks:
            optimization = WorkflowOptimization(
                workflow_id=workflow_id,
                optimization_type="resource",
                target_steps=[bottleneck.step_id],
                estimated_impact={
                    "resource_reduction": 0.4,
                    "cost_savings": 0.3
                },
                implementation_steps=[
                    {
                        "step": 1,
                        "description": "Profile resource usage",
                        "effort": "low"
                    },
                    {
                        "step": 2,
                        "description": "Implement resource pooling",
                        "effort": "medium"
                    },
                    {
                        "step": 3,
                        "description": "Add cleanup routines",
                        "effort": "medium"
                    }
                ],
                metadata={
                    "priority": "high",
                    "bottleneck": bottleneck
                }
            )
            optimizations.append(optimization)
            
        return optimizations
        
    def _generate_dependency_optimizations(
        self, workflow_id: str, bottlenecks: List[WorkflowBottleneck]
    ) -> List[WorkflowOptimization]:
        """Generate dependency optimizations."""
        optimizations = []
        
        for bottleneck in bottlenecks:
            optimization = WorkflowOptimization(
                workflow_id=workflow_id,
                optimization_type="dependency",
                target_steps=[bottleneck.step_id],
                estimated_impact={
                    "complexity_reduction": 0.3,
                    "maintainability_improvement": 0.4
                },
                implementation_steps=[
                    {
                        "step": 1,
                        "description": "Analyze dependency cycle",
                        "effort": "low"
                    },
                    {
                        "step": 2,
                        "description": "Refactor dependencies",
                        "effort": "high"
                    },
                    {
                        "step": 3,
                        "description": "Update workflow structure",
                        "effort": "medium"
                    }
                ],
                metadata={
                    "priority": "high",
                    "bottleneck": bottleneck
                }
            )
            optimizations.append(optimization)
            
        return optimizations
        
    def _is_valid_optimization(self, optimization: Dict) -> bool:
        """Validate optimization configuration."""
        required_fields = ["type", "steps", "target_workflow"]
        return all(field in optimization for field in required_fields)
        
    async def _implement_execution_optimization(
        self, workflow_id: str, optimization: Dict
    ) -> Dict:
        """Implement execution optimization."""
        # Implementation would include actual optimization steps
        return {
            "status": "implemented",
            "metrics": {
                "time_reduction": 0.3,
                "resource_savings": 0.2
            }
        }
        
    async def _implement_resource_optimization(
        self, workflow_id: str, optimization: Dict
    ) -> Dict:
        """Implement resource optimization."""
        # Implementation would include actual optimization steps
        return {
            "status": "implemented",
            "metrics": {
                "resource_reduction": 0.4,
                "cost_savings": 0.3
            }
        }
        
    async def _implement_dependency_optimization(
        self, workflow_id: str, optimization: Dict
    ) -> Dict:
        """Implement dependency optimization."""
        # Implementation would include actual optimization steps
        return {
            "status": "implemented",
            "metrics": {
                "complexity_reduction": 0.3,
                "maintainability_improvement": 0.4
            }
        }
        
    def _analyze_step_times(self, workflow: Dict) -> Dict[str, Dict]:
        """Analyze execution times for each step."""
        step_times = {}
        
        for execution in workflow.get("execution_history", []):
            for step in execution.get("steps", []):
                step_id = step["id"]
                if step_id not in step_times:
                    step_times[step_id] = []
                    
                start_time = datetime.fromisoformat(step["start_time"])
                end_time = datetime.fromisoformat(step["end_time"])
                step_times[step_id].append(
                    (end_time - start_time).total_seconds()
                )
                
        # Calculate statistics for each step
        return {
            step_id: {
                "average_time": sum(times) / len(times),
                "max_time": max(times),
                "min_time": min(times)
            }
            for step_id, times in step_times.items()
            if times
        }
        
    def _analyze_step_resources(self, workflow: Dict) -> Dict[str, Dict]:
        """Analyze resource usage for each step."""
        step_resources = {}
        
        for execution in workflow.get("execution_history", []):
            for step in execution.get("steps", []):
                step_id = step["id"]
                if step_id not in step_resources:
                    step_resources[step_id] = {
                        "cpu": [],
                        "memory": [],
                        "io": []
                    }
                    
                resources = step.get("resource_usage", {})
                step_resources[step_id]["cpu"].append(resources.get("cpu", 0.0))
                step_resources[step_id]["memory"].append(resources.get("memory", 0.0))
                step_resources[step_id]["io"].append(resources.get("io", 0))
                
        # Calculate statistics for each step
        return {
            step_id: {
                "average_cpu": sum(r["cpu"]) / len(r["cpu"]),
                "average_memory": sum(r["memory"]) / len(r["memory"]),
                "average_io": sum(r["io"]) / len(r["io"])
            }
            for step_id, r in step_resources.items()
            if r["cpu"] and r["memory"] and r["io"]
        }
        
    def _analyze_dependencies(self, workflow: Dict) -> List[Dict]:
        """Analyze workflow dependencies."""
        issues = []
        
        # Check for cycles
        try:
            cycles = list(nx.simple_cycles(self.workflow_graph))
            for cycle in cycles:
                issues.append({
                    "type": "dependency",
                    "issue": "cycle",
                    "steps": cycle
                })
        except nx.NetworkXNoCycle:
            pass
            
        # Check for long dependency chains
        for path in nx.all_simple_paths(self.workflow_graph):
            if len(path) > self._get_max_dependency_chain():
                issues.append({
                    "type": "dependency",
                    "issue": "long_chain",
                    "steps": path
                })
                
        return issues
        
    def _get_step_time_threshold(self) -> float:
        """Get threshold for step execution time."""
        return 60.0  # 60 seconds
        
    def _get_workflow_time_threshold(self) -> float:
        """Get threshold for total workflow execution time."""
        return 300.0  # 5 minutes
        
    def _get_max_dependency_chain(self) -> int:
        """Get maximum allowed length of dependency chain."""
        return 5
        
    def _is_resource_bottleneck(self, metrics: Dict) -> bool:
        """Check if step has resource bottleneck."""
        return any([
            metrics["average_cpu"] > 0.8,
            metrics["average_memory"] > 0.8,
            metrics["average_io"] > 1000
        ])
        
    def _calculate_execution_impact(self, step_metrics: Dict) -> Dict:
        """Calculate impact of execution bottleneck."""
        return {
            "performance_impact": step_metrics["metrics"]["average_time"] / 60.0,
            "resource_impact": 0.5,
            "cost_impact": 0.3
        }
        
    def _calculate_resource_impact(self, step_metrics: Dict) -> Dict:
        """Calculate impact of resource bottleneck."""
        return {
            "performance_impact": 0.3,
            "resource_impact": 0.7,
            "cost_impact": 0.5
        }
        
    def _calculate_dependency_impact(self, cycle: List[str]) -> Dict:
        """Calculate impact of dependency bottleneck."""
        return {
            "complexity_impact": 0.6,
            "maintainability_impact": 0.7,
            "scalability_impact": 0.4
        }
        
    def _generate_execution_recommendations(
        self, step_metrics: Dict
    ) -> List[Dict]:
        """Generate recommendations for execution bottleneck."""
        return [
            {
                "type": "optimization",
                "description": "Implement caching for intermediate results",
                "estimated_impact": 0.3
            },
            {
                "type": "parallelization",
                "description": "Split step into parallel subtasks",
                "estimated_impact": 0.4
            },
            {
                "type": "algorithm",
                "description": "Optimize core algorithms",
                "estimated_impact": 0.3
            }
        ]
        
    def _generate_resource_recommendations(
        self, step_metrics: Dict
    ) -> List[Dict]:
        """Generate recommendations for resource bottleneck."""
        return [
            {
                "type": "pooling",
                "description": "Implement resource pooling",
                "estimated_impact": 0.3
            },
            {
                "type": "cleanup",
                "description": "Add periodic resource cleanup",
                "estimated_impact": 0.2
            },
            {
                "type": "optimization",
                "description": "Optimize resource usage patterns",
                "estimated_impact": 0.4
            }
        ]
        
    def _generate_dependency_recommendations(
        self, cycle: List[str]
    ) -> List[Dict]:
        """Generate recommendations for dependency bottleneck."""
        return [
            {
                "type": "refactor",
                "description": "Break dependency cycle",
                "estimated_impact": 0.5
            },
            {
                "type": "restructure",
                "description": "Reorganize workflow steps",
                "estimated_impact": 0.4
            },
            {
                "type": "interface",
                "description": "Improve step interfaces",
                "estimated_impact": 0.3
            }
        ] 