from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime
import asyncio

@dataclass
class OptimizationTarget:
    """Represents a target for optimization."""
    id: str
    type: str
    component: str
    metrics: Dict
    priority: float
    metadata: Dict

@dataclass
class OptimizationPlan:
    """Represents a plan for optimization."""
    id: str
    target_id: str
    steps: List[Dict]
    estimated_impact: Dict
    estimated_effort: Dict
    priority: float
    metadata: Dict

@dataclass
class OptimizationResult:
    """Represents the result of an optimization."""
    id: str
    plan_id: str
    success: bool
    metrics: Dict
    impact: Dict
    metadata: Dict

class ContinuousOptimizer:
    """Continuously optimizes system performance based on learning."""
    
    def __init__(self, knowledge_system, modification_engine):
        self.knowledge_system = knowledge_system
        self.modification_engine = modification_engine
        self.optimization_targets: Dict[str, OptimizationTarget] = {}
        self.optimization_plans: Dict[str, OptimizationPlan] = {}
        self.optimization_results: Dict[str, OptimizationResult] = {}
        
    async def identify_optimization_targets(self) -> List[OptimizationTarget]:
        """
        Identify targets for optimization.
        
        Returns:
            List[OptimizationTarget]: Identified optimization targets
        """
        # Get system performance metrics
        metrics = await self.knowledge_system.get_performance_metrics()
        
        targets = []
        
        # Analyze performance metrics for optimization opportunities
        for component, component_metrics in metrics.items():
            # Check execution time metrics
            if self._needs_performance_optimization(component_metrics):
                target = OptimizationTarget(
                    id=f"perf_opt_{len(targets)}",
                    type="performance",
                    component=component,
                    metrics=component_metrics,
                    priority=self._calculate_performance_priority(
                        component_metrics
                    ),
                    metadata={
                        "identified_at": datetime.now().isoformat(),
                        "reason": "performance_degradation",
                        "threshold_violations": self._get_threshold_violations(
                            component_metrics
                        )
                    }
                )
                targets.append(target)
                
            # Check resource usage metrics
            if self._needs_resource_optimization(component_metrics):
                target = OptimizationTarget(
                    id=f"res_opt_{len(targets)}",
                    type="resource",
                    component=component,
                    metrics=component_metrics,
                    priority=self._calculate_resource_priority(
                        component_metrics
                    ),
                    metadata={
                        "identified_at": datetime.now().isoformat(),
                        "reason": "resource_inefficiency",
                        "resource_issues": self._get_resource_issues(
                            component_metrics
                        )
                    }
                )
                targets.append(target)
                
        # Sort targets by priority
        targets.sort(key=lambda x: x.priority, reverse=True)
        
        # Store targets in knowledge system
        await self.knowledge_system.store_optimization_targets(targets)
        
        # Update cache
        self.optimization_targets = {
            target.id: target for target in targets
        }
        
        return targets
        
    async def generate_optimization_plan(
        self, target_id: str
    ) -> OptimizationPlan:
        """
        Generate a plan for optimizing a specific target.
        
        Args:
            target_id (str): ID of optimization target
            
        Returns:
            OptimizationPlan: Generated optimization plan
        """
        if target_id not in self.optimization_targets:
            raise ValueError(f"Unknown optimization target: {target_id}")
            
        target = self.optimization_targets[target_id]
        
        # Generate optimization steps based on target type
        if target.type == "performance":
            steps = self._generate_performance_optimization_steps(target)
        elif target.type == "resource":
            steps = self._generate_resource_optimization_steps(target)
        else:
            steps = []
            
        # Estimate impact and effort
        impact_estimate = self._estimate_optimization_impact(target, steps)
        effort_estimate = self._estimate_optimization_effort(steps)
        
        # Calculate plan priority
        priority = self._calculate_plan_priority(
            target.priority, impact_estimate, effort_estimate
        )
        
        plan = OptimizationPlan(
            id=f"plan_{target_id}",
            target_id=target_id,
            steps=steps,
            estimated_impact=impact_estimate,
            estimated_effort=effort_estimate,
            priority=priority,
            metadata={
                "generated_at": datetime.now().isoformat(),
                "target_type": target.type,
                "component": target.component
            }
        )
        
        # Store plan in knowledge system
        await self.knowledge_system.store_optimization_plan(plan)
        
        # Update cache
        self.optimization_plans[plan.id] = plan
        
        return plan
        
    async def implement_optimization(self, plan_id: str) -> OptimizationResult:
        """
        Implement an optimization plan.
        
        Args:
            plan_id (str): ID of optimization plan
            
        Returns:
            OptimizationResult: Result of optimization implementation
        """
        if plan_id not in self.optimization_plans:
            raise ValueError(f"Unknown optimization plan: {plan_id}")
            
        plan = self.optimization_plans[plan_id]
        target = self.optimization_targets[plan.target_id]
        
        # Execute optimization steps
        step_results = []
        success = True
        
        for step in plan.steps:
            try:
                # Execute step using modification engine
                step_result = await self.modification_engine.execute_modification(
                    component=target.component,
                    modification_type=step["type"],
                    parameters=step["parameters"]
                )
                
                step_results.append({
                    "step": step,
                    "success": True,
                    "result": step_result
                })
                
            except Exception as e:
                step_results.append({
                    "step": step,
                    "success": False,
                    "error": str(e)
                })
                success = False
                break
                
        # Measure impact
        if success:
            impact = await self._measure_optimization_impact(
                target, plan, step_results
            )
        else:
            impact = {"success": False, "error": "Implementation failed"}
            
        result = OptimizationResult(
            id=f"result_{plan_id}",
            plan_id=plan_id,
            success=success,
            metrics=await self._collect_post_optimization_metrics(target),
            impact=impact,
            metadata={
                "implemented_at": datetime.now().isoformat(),
                "step_results": step_results
            }
        )
        
        # Store result in knowledge system
        await self.knowledge_system.store_optimization_result(result)
        
        # Update cache
        self.optimization_results[result.id] = result
        
        return result
        
    async def evaluate_optimization_impact(
        self, optimization_id: str
    ) -> Dict:
        """
        Evaluate the impact of an optimization.
        
        Args:
            optimization_id (str): ID of optimization result
            
        Returns:
            Dict: Impact evaluation data
        """
        if optimization_id not in self.optimization_results:
            raise ValueError(f"Unknown optimization result: {optimization_id}")
            
        result = self.optimization_results[optimization_id]
        plan = self.optimization_plans[result.plan_id]
        target = self.optimization_targets[plan.target_id]
        
        # Compare metrics before and after optimization
        before_metrics = target.metrics
        after_metrics = result.metrics
        
        evaluation = {
            "optimization_id": optimization_id,
            "target_type": target.type,
            "component": target.component,
            "success": result.success,
            "metrics_comparison": self._compare_metrics(
                before_metrics, after_metrics
            ),
            "impact_analysis": {
                "performance_impact": self._analyze_performance_impact(
                    before_metrics, after_metrics
                ),
                "resource_impact": self._analyze_resource_impact(
                    before_metrics, after_metrics
                ),
                "side_effects": self._analyze_optimization_side_effects(
                    target, result
                )
            },
            "effectiveness": {
                "goal_achievement": self._calculate_goal_achievement(
                    target, result
                ),
                "effort_accuracy": self._calculate_effort_accuracy(
                    plan, result
                ),
                "impact_accuracy": self._calculate_impact_accuracy(
                    plan, result
                )
            }
        }
        
        # Store evaluation in knowledge system
        await self.knowledge_system.store_optimization_evaluation(
            optimization_id, evaluation
        )
        
        return evaluation
        
    def _needs_performance_optimization(self, metrics: Dict) -> bool:
        """Check if component needs performance optimization."""
        # Check execution time threshold violations
        if metrics.get("avg_execution_time", 0) > metrics.get("time_threshold", float("inf")):
            return True
            
        # Check latency threshold violations
        if metrics.get("avg_latency", 0) > metrics.get("latency_threshold", float("inf")):
            return True
            
        return False
        
    def _needs_resource_optimization(self, metrics: Dict) -> bool:
        """Check if component needs resource optimization."""
        # Check memory usage threshold violations
        if metrics.get("memory_usage", 0) > metrics.get("memory_threshold", float("inf")):
            return True
            
        # Check CPU usage threshold violations
        if metrics.get("cpu_usage", 0) > metrics.get("cpu_threshold", float("inf")):
            return True
            
        return False
        
    def _calculate_performance_priority(self, metrics: Dict) -> float:
        """Calculate priority for performance optimization."""
        priority = 0.0
        
        # Consider execution time impact
        time_ratio = metrics.get("avg_execution_time", 0) / metrics.get("time_threshold", 1)
        priority += min(1.0, time_ratio) * 0.5
        
        # Consider latency impact
        latency_ratio = metrics.get("avg_latency", 0) / metrics.get("latency_threshold", 1)
        priority += min(1.0, latency_ratio) * 0.3
        
        # Consider usage frequency
        usage_factor = min(1.0, metrics.get("usage_frequency", 0) / 1000)
        priority += usage_factor * 0.2
        
        return priority
        
    def _calculate_resource_priority(self, metrics: Dict) -> float:
        """Calculate priority for resource optimization."""
        priority = 0.0
        
        # Consider memory usage impact
        memory_ratio = metrics.get("memory_usage", 0) / metrics.get("memory_threshold", 1)
        priority += min(1.0, memory_ratio) * 0.4
        
        # Consider CPU usage impact
        cpu_ratio = metrics.get("cpu_usage", 0) / metrics.get("cpu_threshold", 1)
        priority += min(1.0, cpu_ratio) * 0.4
        
        # Consider resource cost
        cost_factor = min(1.0, metrics.get("resource_cost", 0) / 1000)
        priority += cost_factor * 0.2
        
        return priority
        
    def _get_threshold_violations(self, metrics: Dict) -> List[Dict]:
        """Get list of threshold violations."""
        violations = []
        
        # Check execution time threshold
        time_threshold = metrics.get("time_threshold")
        if time_threshold and metrics.get("avg_execution_time", 0) > time_threshold:
            violations.append({
                "metric": "execution_time",
                "threshold": time_threshold,
                "actual": metrics["avg_execution_time"],
                "violation_ratio": metrics["avg_execution_time"] / time_threshold
            })
            
        # Check latency threshold
        latency_threshold = metrics.get("latency_threshold")
        if latency_threshold and metrics.get("avg_latency", 0) > latency_threshold:
            violations.append({
                "metric": "latency",
                "threshold": latency_threshold,
                "actual": metrics["avg_latency"],
                "violation_ratio": metrics["avg_latency"] / latency_threshold
            })
            
        return violations
        
    def _get_resource_issues(self, metrics: Dict) -> List[Dict]:
        """Get list of resource usage issues."""
        issues = []
        
        # Check memory usage
        memory_threshold = metrics.get("memory_threshold")
        if memory_threshold and metrics.get("memory_usage", 0) > memory_threshold:
            issues.append({
                "resource": "memory",
                "threshold": memory_threshold,
                "actual": metrics["memory_usage"],
                "usage_ratio": metrics["memory_usage"] / memory_threshold
            })
            
        # Check CPU usage
        cpu_threshold = metrics.get("cpu_threshold")
        if cpu_threshold and metrics.get("cpu_usage", 0) > cpu_threshold:
            issues.append({
                "resource": "cpu",
                "threshold": cpu_threshold,
                "actual": metrics["cpu_usage"],
                "usage_ratio": metrics["cpu_usage"] / cpu_threshold
            })
            
        return issues
        
    def _generate_performance_optimization_steps(
        self, target: OptimizationTarget
    ) -> List[Dict]:
        """Generate steps for performance optimization."""
        steps = []
        
        # Add profiling step
        steps.append({
            "type": "profile",
            "description": "Profile component execution",
            "parameters": {
                "component": target.component,
                "duration": 300  # 5 minutes
            }
        })
        
        # Add optimization steps based on metrics
        if target.metrics.get("avg_execution_time", 0) > target.metrics.get("time_threshold", 0):
            steps.append({
                "type": "optimize_execution",
                "description": "Optimize execution time",
                "parameters": {
                    "component": target.component,
                    "target_metric": "execution_time",
                    "target_value": target.metrics["time_threshold"]
                }
            })
            
        if target.metrics.get("avg_latency", 0) > target.metrics.get("latency_threshold", 0):
            steps.append({
                "type": "optimize_latency",
                "description": "Optimize latency",
                "parameters": {
                    "component": target.component,
                    "target_metric": "latency",
                    "target_value": target.metrics["latency_threshold"]
                }
            })
            
        return steps
        
    def _generate_resource_optimization_steps(
        self, target: OptimizationTarget
    ) -> List[Dict]:
        """Generate steps for resource optimization."""
        steps = []
        
        # Add resource usage analysis step
        steps.append({
            "type": "analyze_resources",
            "description": "Analyze resource usage patterns",
            "parameters": {
                "component": target.component,
                "resources": ["memory", "cpu"],
                "duration": 300  # 5 minutes
            }
        })
        
        # Add optimization steps based on metrics
        if target.metrics.get("memory_usage", 0) > target.metrics.get("memory_threshold", 0):
            steps.append({
                "type": "optimize_memory",
                "description": "Optimize memory usage",
                "parameters": {
                    "component": target.component,
                    "target_metric": "memory_usage",
                    "target_value": target.metrics["memory_threshold"]
                }
            })
            
        if target.metrics.get("cpu_usage", 0) > target.metrics.get("cpu_threshold", 0):
            steps.append({
                "type": "optimize_cpu",
                "description": "Optimize CPU usage",
                "parameters": {
                    "component": target.component,
                    "target_metric": "cpu_usage",
                    "target_value": target.metrics["cpu_threshold"]
                }
            })
            
        return steps
        
    def _estimate_optimization_impact(
        self, target: OptimizationTarget, steps: List[Dict]
    ) -> Dict:
        """Estimate impact of optimization steps."""
        impact = {
            "performance_improvement": 0.0,
            "resource_savings": 0.0,
            "reliability_improvement": 0.0
        }
        
        for step in steps:
            if step["type"] in ["optimize_execution", "optimize_latency"]:
                impact["performance_improvement"] += 0.2
            elif step["type"] in ["optimize_memory", "optimize_cpu"]:
                impact["resource_savings"] += 0.2
                
        return impact
        
    def _estimate_optimization_effort(self, steps: List[Dict]) -> Dict:
        """Estimate effort required for optimization steps."""
        effort = {
            "development_time": 0,
            "testing_time": 0,
            "risk_level": 0.0
        }
        
        for step in steps:
            if step["type"] in ["profile", "analyze_resources"]:
                effort["development_time"] += 1  # 1 hour
                effort["testing_time"] += 1
                effort["risk_level"] += 0.1
            else:
                effort["development_time"] += 4  # 4 hours
                effort["testing_time"] += 2
                effort["risk_level"] += 0.2
                
        return effort
        
    def _calculate_plan_priority(
        self, target_priority: float, impact: Dict, effort: Dict
    ) -> float:
        """Calculate priority for optimization plan."""
        # Consider target priority (40%)
        priority = target_priority * 0.4
        
        # Consider estimated impact (40%)
        impact_score = (
            impact["performance_improvement"] +
            impact["resource_savings"] +
            impact["reliability_improvement"]
        ) / 3
        priority += impact_score * 0.4
        
        # Consider required effort (20%)
        effort_score = 1.0 - min(
            1.0,
            (effort["development_time"] + effort["testing_time"]) / 16
        )
        priority += effort_score * 0.2
        
        return priority
        
    async def _measure_optimization_impact(
        self, target: OptimizationTarget, 
        plan: OptimizationPlan,
        step_results: List[Dict]
    ) -> Dict:
        """Measure actual impact of optimization."""
        # Get current metrics
        current_metrics = await self.knowledge_system.get_component_metrics(
            target.component
        )
        
        return {
            "metrics_improvement": self._calculate_metrics_improvement(
                target.metrics, current_metrics
            ),
            "goal_achievement": self._calculate_goal_achievement(
                target, {"metrics": current_metrics}
            ),
            "step_impacts": self._analyze_step_impacts(step_results)
        }
        
    async def _collect_post_optimization_metrics(
        self, target: OptimizationTarget
    ) -> Dict:
        """Collect metrics after optimization."""
        return await self.knowledge_system.get_component_metrics(
            target.component
        )
        
    def _compare_metrics(self, before: Dict, after: Dict) -> Dict:
        """Compare metrics before and after optimization."""
        comparison = {}
        
        for metric, before_value in before.items():
            if metric in after:
                comparison[metric] = {
                    "before": before_value,
                    "after": after[metric],
                    "change": after[metric] - before_value,
                    "change_percentage": (
                        (after[metric] - before_value) / before_value * 100
                        if before_value != 0 else float("inf")
                    )
                }
                
        return comparison
        
    def _analyze_performance_impact(self, before: Dict, after: Dict) -> Dict:
        """Analyze impact on performance metrics."""
        return {
            "execution_time_change": self._calculate_metric_change(
                before.get("avg_execution_time", 0),
                after.get("avg_execution_time", 0)
            ),
            "latency_change": self._calculate_metric_change(
                before.get("avg_latency", 0),
                after.get("avg_latency", 0)
            )
        }
        
    def _analyze_resource_impact(self, before: Dict, after: Dict) -> Dict:
        """Analyze impact on resource usage."""
        return {
            "memory_usage_change": self._calculate_metric_change(
                before.get("memory_usage", 0),
                after.get("memory_usage", 0)
            ),
            "cpu_usage_change": self._calculate_metric_change(
                before.get("cpu_usage", 0),
                after.get("cpu_usage", 0)
            )
        }
        
    def _analyze_optimization_side_effects(
        self, target: OptimizationTarget, result: OptimizationResult
    ) -> List[Dict]:
        """Analyze potential side effects of optimization."""
        return []  # Implement side effect analysis
        
    def _calculate_goal_achievement(
        self, target: OptimizationTarget, result: OptimizationResult
    ) -> float:
        """Calculate how well optimization achieved its goals."""
        if not result.success:
            return 0.0
            
        achievements = []
        
        # Check performance goals
        if target.type == "performance":
            if "avg_execution_time" in result.metrics:
                ratio = (
                    target.metrics["avg_execution_time"] /
                    result.metrics["avg_execution_time"]
                )
                achievements.append(min(1.0, ratio))
                
        # Check resource goals
        elif target.type == "resource":
            if "memory_usage" in result.metrics:
                ratio = (
                    target.metrics["memory_usage"] /
                    result.metrics["memory_usage"]
                )
                achievements.append(min(1.0, ratio))
                
        return sum(achievements) / len(achievements) if achievements else 0.0
        
    def _calculate_effort_accuracy(
        self, plan: OptimizationPlan, result: OptimizationResult
    ) -> float:
        """Calculate accuracy of effort estimation."""
        if not result.success:
            return 0.0
            
        # Compare estimated vs actual effort
        estimated = plan.estimated_effort["development_time"] + plan.estimated_effort["testing_time"]
        actual = sum(
            step["result"].get("effort", 0)
            for step in result.metadata["step_results"]
            if step["success"]
        )
        
        return 1.0 - min(1.0, abs(actual - estimated) / estimated)
        
    def _calculate_impact_accuracy(
        self, plan: OptimizationPlan, result: OptimizationResult
    ) -> float:
        """Calculate accuracy of impact estimation."""
        if not result.success:
            return 0.0
            
        # Compare estimated vs actual impact
        estimated_impact = sum(plan.estimated_impact.values())
        actual_impact = sum(
            impact["value"]
            for impact in result.impact.get("metrics_improvement", {}).values()
        )
        
        return 1.0 - min(1.0, abs(actual_impact - estimated_impact) / estimated_impact)
        
    def _calculate_metric_change(self, before: float, after: float) -> Dict:
        """Calculate change in a metric."""
        return {
            "before": before,
            "after": after,
            "absolute_change": after - before,
            "percentage_change": (
                (after - before) / before * 100
                if before != 0 else float("inf")
            )
        }
        
    def _calculate_metrics_improvement(
        self, before: Dict, after: Dict
    ) -> Dict:
        """Calculate improvement in metrics."""
        improvements = {}
        
        for metric, before_value in before.items():
            if metric in after:
                improvements[metric] = {
                    "value": (before_value - after[metric]) / before_value
                    if before_value != 0 else 0.0,
                    "details": self._calculate_metric_change(
                        before_value, after[metric]
                    )
                }
                
        return improvements
        
    def _analyze_step_impacts(self, step_results: List[Dict]) -> List[Dict]:
        """Analyze impact of individual optimization steps."""
        impacts = []
        
        for result in step_results:
            if result["success"]:
                impact = {
                    "step": result["step"]["type"],
                    "metrics": result["result"].get("metrics", {}),
                    "effectiveness": result["result"].get("effectiveness", 0.0)
                }
                impacts.append(impact)
                
        return impacts 