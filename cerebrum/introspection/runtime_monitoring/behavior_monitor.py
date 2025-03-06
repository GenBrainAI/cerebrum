import asyncio
import time
from typing import Dict, List, Optional, Set
from dataclasses import dataclass
import uuid
from pathlib import Path

@dataclass
class MonitoringSession:
    id: str
    start_time: float
    components: List[str]
    telemetry_data: Dict[str, List[Dict]]
    active: bool

@dataclass
class PerformanceMetrics:
    execution_times: Dict[str, float]
    memory_usage: Dict[str, float]
    cpu_usage: Dict[str, float]
    io_operations: Dict[str, int]
    hotspots: List[Dict[str, any]]

class BehaviorMonitor:
    def __init__(self, telemetry_system):
        self.telemetry_system = telemetry_system
        self.behavior_patterns: Dict[str, Dict] = {}
        self.monitoring_sessions: Dict[str, MonitoringSession] = {}
        self.active_monitors: Set[str] = set()
        self.telemetry_collector = TelemetryCollector()
        self.anomaly_detector = AnomalyDetector()
        self.performance_analyzer = PerformanceAnalyzer()

    async def start_monitoring(
        self, components: Optional[List[str]] = None
    ) -> str:
        """
        Start monitoring system behavior.
        
        Args:
            components (List[str], optional): List of component paths to monitor.
                                           If None, monitors all components.
        
        Returns:
            str: Monitoring session ID
        """
        session_id = str(uuid.uuid4())
        
        # If no components specified, discover all components
        if components is None:
            components = await self._discover_components()
            
        # Create new monitoring session
        session = MonitoringSession(
            id=session_id,
            start_time=time.time(),
            components=components,
            telemetry_data={},
            active=True
        )
        
        # Set up instrumentation
        for component in components:
            await self.telemetry_collector.instrument_component(component)
            session.telemetry_data[component] = []
            
        # Store session and mark as active
        self.monitoring_sessions[session_id] = session
        self.active_monitors.add(session_id)
        
        # Start telemetry collection task
        asyncio.create_task(
            self._collect_telemetry(session_id)
        )
        
        return session_id

    async def analyze_performance(
        self, time_period: Dict[str, float]
    ) -> PerformanceMetrics:
        """
        Analyze system performance over a time period.
        
        Args:
            time_period (dict): Time period specification
            
        Returns:
            PerformanceMetrics: Performance analysis results
        """
        # Get active session data
        active_sessions = [
            session for session in self.monitoring_sessions.values()
            if session.active
        ]
        
        if not active_sessions:
            raise RuntimeError("No active monitoring sessions found")
            
        # Calculate time range
        if "duration" in time_period:
            end_time = time.time()
            start_time = end_time - time_period["duration"]
        else:
            start_time = time_period["start_time"]
            end_time = time_period["end_time"]
            
        # Collect metrics for each component
        execution_times = {}
        memory_usage = {}
        cpu_usage = {}
        io_operations = {}
        
        for session in active_sessions:
            for component, data in session.telemetry_data.items():
                # Filter data for time period
                period_data = [
                    entry for entry in data
                    if start_time <= entry["timestamp"] <= end_time
                ]
                
                # Calculate metrics
                execution_times[component] = (
                    self.performance_analyzer.calculate_execution_times(period_data)
                )
                memory_usage[component] = (
                    self.performance_analyzer.calculate_memory_usage(period_data)
                )
                cpu_usage[component] = (
                    self.performance_analyzer.calculate_cpu_usage(period_data)
                )
                io_operations[component] = (
                    self.performance_analyzer.calculate_io_operations(period_data)
                )
                
        # Identify performance hotspots
        hotspots = self.performance_analyzer.identify_hotspots(
            execution_times, memory_usage, cpu_usage, io_operations
        )
        
        return PerformanceMetrics(
            execution_times=execution_times,
            memory_usage=memory_usage,
            cpu_usage=cpu_usage,
            io_operations=io_operations,
            hotspots=hotspots
        )

    async def detect_anomalies(self) -> List[Dict[str, any]]:
        """
        Detect anomalies in system behavior.
        
        Returns:
            List[Dict]: Detected anomalies
        """
        anomalies = []
        
        # Get active session data
        active_sessions = [
            session for session in self.monitoring_sessions.values()
            if session.active
        ]
        
        if not active_sessions:
            return anomalies
            
        # Analyze each component in each session
        for session in active_sessions:
            for component, data in session.telemetry_data.items():
                # Skip if not enough data
                if len(data) < 2:
                    continue
                    
                # Detect statistical anomalies
                stat_anomalies = (
                    self.anomaly_detector.detect_statistical_anomalies(data)
                )
                if stat_anomalies:
                    anomalies.extend(stat_anomalies)
                    
                # Detect pattern anomalies
                pattern_anomalies = (
                    self.anomaly_detector.detect_pattern_anomalies(
                        data, self.behavior_patterns.get(component, {})
                    )
                )
                if pattern_anomalies:
                    anomalies.extend(pattern_anomalies)
                    
        # Classify and assess severity of anomalies
        for anomaly in anomalies:
            self.anomaly_detector.classify_anomaly(anomaly)
            
        return anomalies

    async def identify_bottlenecks(self) -> List[Dict[str, any]]:
        """
        Identify performance bottlenecks in the system.
        
        Returns:
            List[Dict]: Identified bottlenecks
        """
        bottlenecks = []
        
        # Get performance metrics
        metrics = await self.analyze_performance({"duration": 300})  # Last 5 minutes
        
        # Analyze execution times
        for component, times in metrics.execution_times.items():
            slow_methods = self.performance_analyzer.identify_slow_methods(times)
            if slow_methods:
                bottlenecks.extend([
                    {
                        "component": component,
                        "method": method,
                        "execution_time": time,
                        "type": "slow_execution",
                        "impact": "high" if time > 1.0 else "medium",
                        "frequency": frequency
                    }
                    for method, (time, frequency) in slow_methods.items()
                ])
                
        # Analyze resource usage
        resource_bottlenecks = (
            self.performance_analyzer.identify_resource_bottlenecks(
                metrics.memory_usage,
                metrics.cpu_usage,
                metrics.io_operations
            )
        )
        bottlenecks.extend(resource_bottlenecks)
        
        # Analyze call patterns
        call_bottlenecks = (
            self.performance_analyzer.analyze_call_chains(
                metrics.execution_times
            )
        )
        bottlenecks.extend(call_bottlenecks)
        
        # Generate improvement suggestions
        for bottleneck in bottlenecks:
            bottleneck["suggestions"] = (
                self._generate_improvement_suggestions(bottleneck)
            )
            
        return bottlenecks

    async def _discover_components(self) -> List[str]:
        """Discover all monitorable components in the system."""
        components = []
        codebase_path = Path(self.telemetry_system.codebase_path)
        
        for file_path in codebase_path.rglob('*.py'):
            if not any(part.startswith('_') for part in file_path.parts):
                components.append(str(file_path))
                
        return components

    async def _collect_telemetry(self, session_id: str):
        """Collect telemetry data for a monitoring session."""
        session = self.monitoring_sessions[session_id]
        
        while session.active:
            for component in session.components:
                try:
                    # Collect various metrics
                    exec_data = (
                        await self.telemetry_collector.collect_execution_times(
                            component
                        )
                    )
                    memory_data = (
                        await self.telemetry_collector.collect_memory_usage(
                            component
                        )
                    )
                    error_data = (
                        await self.telemetry_collector.collect_error_data(
                            component
                        )
                    )
                    
                    # Combine metrics
                    telemetry = {
                        "timestamp": time.time(),
                        "execution_times": exec_data,
                        "memory_usage": memory_data,
                        "errors": error_data
                    }
                    
                    # Store telemetry data
                    session.telemetry_data[component].append(telemetry)
                    
                except Exception as e:
                    print(f"Error collecting telemetry for {component}: {e}")
                    
            await asyncio.sleep(1)  # Collect every second

    def _generate_improvement_suggestions(
        self, bottleneck: Dict[str, any]
    ) -> List[str]:
        """Generate improvement suggestions for a bottleneck."""
        suggestions = []
        
        if bottleneck["type"] == "slow_execution":
            suggestions.extend([
                "Consider caching frequently accessed data",
                "Optimize database queries",
                "Use async/await for I/O operations"
            ])
        elif bottleneck["type"] == "high_memory":
            suggestions.extend([
                "Implement memory pooling",
                "Use generators for large datasets",
                "Profile memory usage to identify leaks"
            ])
        elif bottleneck["type"] == "high_cpu":
            suggestions.extend([
                "Use multiprocessing for CPU-intensive tasks",
                "Optimize algorithms",
                "Consider using compiled extensions"
            ])
            
        return suggestions 