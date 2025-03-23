import numpy as np
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import networkx as nx
from collections import defaultdict

@dataclass
class PerformanceThresholds:
    slow_execution_threshold: float = 1.0  # seconds
    high_memory_threshold: float = 0.8  # percentage of total memory
    high_cpu_threshold: float = 0.9  # percentage of CPU
    high_io_threshold: int = 1000  # operations per second

class PerformanceAnalyzer:
    """Analyzes system performance data."""
    
    def __init__(self):
        self.thresholds = PerformanceThresholds()
        self.call_graph = nx.DiGraph()
        self.performance_history = defaultdict(list)
        
    def calculate_execution_times(
        self, telemetry_data: List[Dict]
    ) -> Dict[str, List[float]]:
        """
        Calculate statistical measures of performance.
        
        Args:
            telemetry_data (List[Dict]): Performance data to analyze
            
        Returns:
            Dict[str, List[float]]: Execution time statistics
        """
        execution_times = defaultdict(list)
        
        for entry in telemetry_data:
            if "execution_times" not in entry:
                continue
                
            for func_name, times in entry["execution_times"].items():
                execution_times[func_name].extend(times)
                
        # Calculate statistics for each function
        stats = {}
        for func_name, times in execution_times.items():
            if times:
                stats[func_name] = {
                    "mean": np.mean(times),
                    "median": np.median(times),
                    "std": np.std(times),
                    "min": np.min(times),
                    "max": np.max(times),
                    "count": len(times)
                }
                
        return stats
        
    def calculate_memory_usage(
        self, telemetry_data: List[Dict]
    ) -> Dict[str, Dict]:
        """
        Calculate memory usage statistics.
        
        Args:
            telemetry_data (List[Dict]): Memory usage data
            
        Returns:
            Dict[str, Dict]: Memory usage statistics
        """
        memory_stats = {
            "total_allocated": [],
            "peak_usage": []
        }
        
        for entry in telemetry_data:
            if "memory_usage" not in entry:
                continue
                
            memory_data = entry["memory_usage"]
            memory_stats["total_allocated"].append(memory_data.get("total_size", 0))
            memory_stats["peak_usage"].append(memory_data.get("peak_size", 0))
            
        # Calculate statistics
        stats = {}
        for metric, values in memory_stats.items():
            if values:
                stats[metric] = {
                    "current": values[-1],
                    "mean": np.mean(values),
                    "max": np.max(values),
                    "trend": self._calculate_trend(values)
                }
                
        return stats
        
    def calculate_cpu_usage(
        self, telemetry_data: List[Dict]
    ) -> Dict[str, float]:
        """
        Calculate CPU utilization statistics.
        
        Args:
            telemetry_data (List[Dict]): CPU usage data
            
        Returns:
            Dict[str, float]: CPU usage statistics
        """
        cpu_stats = {
            "user_time": [],
            "system_time": [],
            "total_time": []
        }
        
        for entry in telemetry_data:
            if "cpu_usage" not in entry:
                continue
                
            cpu_data = entry["cpu_usage"]
            cpu_stats["user_time"].append(cpu_data.get("user", 0))
            cpu_stats["system_time"].append(cpu_data.get("system", 0))
            cpu_stats["total_time"].append(
                cpu_data.get("user", 0) + cpu_data.get("system", 0)
            )
            
        # Calculate statistics
        stats = {}
        for metric, values in cpu_stats.items():
            if values:
                stats[metric] = {
                    "current": values[-1],
                    "mean": np.mean(values),
                    "max": np.max(values),
                    "trend": self._calculate_trend(values)
                }
                
        return stats
        
    def calculate_io_operations(
        self, telemetry_data: List[Dict]
    ) -> Dict[str, Dict]:
        """
        Calculate I/O operation statistics.
        
        Args:
            telemetry_data (List[Dict]): I/O operation data
            
        Returns:
            Dict[str, Dict]: I/O operation statistics
        """
        io_stats = {
            "read_ops": [],
            "write_ops": [],
            "total_ops": []
        }
        
        for entry in telemetry_data:
            if "io_operations" not in entry:
                continue
                
            io_data = entry["io_operations"]
            read_ops = io_data.get("read_ops", 0)
            write_ops = io_data.get("write_ops", 0)
            
            io_stats["read_ops"].append(read_ops)
            io_stats["write_ops"].append(write_ops)
            io_stats["total_ops"].append(read_ops + write_ops)
            
        # Calculate statistics
        stats = {}
        for metric, values in io_stats.items():
            if values:
                stats[metric] = {
                    "current": values[-1],
                    "mean": np.mean(values),
                    "max": np.max(values),
                    "trend": self._calculate_trend(values)
                }
                
        return stats
        
    def identify_hotspots(
        self,
        execution_times: Dict[str, Dict],
        memory_usage: Dict[str, Dict],
        cpu_usage: Dict[str, Dict],
        io_operations: Dict[str, Dict]
    ) -> List[Dict]:
        """
        Identify performance hotspots.
        
        Args:
            execution_times (Dict): Execution time statistics
            memory_usage (Dict): Memory usage statistics
            cpu_usage (Dict): CPU usage statistics
            io_operations (Dict): I/O operation statistics
            
        Returns:
            List[Dict]: Identified hotspots
        """
        hotspots = []
        
        # Check execution times
        for func, stats in execution_times.items():
            if "mean" in stats and stats["mean"] > self.thresholds.slow_execution_threshold:
                hotspots.append({
                    "type": "slow_execution",
                    "function": func,
                    "metric": "execution_time",
                    "value": stats["mean"],
                    "threshold": self.thresholds.slow_execution_threshold
                })
                
        # Check memory usage
        if "total_allocated" in memory_usage and "current" in memory_usage["total_allocated"]:
            if memory_usage["total_allocated"]["current"] > self.thresholds.high_memory_threshold:
                hotspots.append({
                    "type": "high_memory",
                    "metric": "memory_usage",
                    "value": memory_usage["total_allocated"]["current"],
                    "threshold": self.thresholds.high_memory_threshold
                })
            
        # Check CPU usage
        if "total_time" in cpu_usage and "current" in cpu_usage["total_time"]:
            if cpu_usage["total_time"]["current"] > self.thresholds.high_cpu_threshold:
                hotspots.append({
                    "type": "high_cpu",
                    "metric": "cpu_usage",
                    "value": cpu_usage["total_time"]["current"],
                    "threshold": self.thresholds.high_cpu_threshold
                })
            
        # Check I/O operations
        if "total_ops" in io_operations and "current" in io_operations["total_ops"]:
            if io_operations["total_ops"]["current"] > self.thresholds.high_io_threshold:
                hotspots.append({
                    "type": "high_io",
                    "metric": "io_operations",
                    "value": io_operations["total_ops"]["current"],
                    "threshold": self.thresholds.high_io_threshold
                })
            
        return hotspots
        
    def identify_slow_methods(
        self, execution_times: Dict[str, Dict]
    ) -> Dict[str, Tuple[float, int]]:
        """
        Identify methods with slow execution times.
        
        Args:
            execution_times (Dict): Execution time statistics
            
        Returns:
            Dict[str, Tuple[float, int]]: Slow methods with time and frequency
        """
        slow_methods = {}
        
        for func, stats in execution_times.items():
            if stats["mean"] > self.thresholds.slow_execution_threshold:
                slow_methods[func] = (stats["mean"], stats["count"])
                
        return slow_methods
        
    def identify_resource_bottlenecks(
        self,
        memory_usage: Dict[str, Dict],
        cpu_usage: Dict[str, Dict],
        io_operations: Dict[str, Dict]
    ) -> List[Dict]:
        """
        Identify resource usage bottlenecks.
        
        Args:
            memory_usage (Dict): Memory usage statistics
            cpu_usage (Dict): CPU usage statistics
            io_operations (Dict): I/O operation statistics
            
        Returns:
            List[Dict]: Resource bottlenecks
        """
        bottlenecks = []
        
        # Check for high memory usage
        for component, stats in memory_usage.items():
            if isinstance(stats, dict) and "current" in stats and stats["current"] > self.thresholds.high_memory_threshold:
                bottlenecks.append({
                    "type": "high_memory",
                    "component": component,
                    "current_usage": stats["current"],
                    "threshold": self.thresholds.high_memory_threshold
                })
                
        # Check for high CPU usage
        for component, stats in cpu_usage.items():
            if isinstance(stats, dict) and "current" in stats and stats["current"] > self.thresholds.high_cpu_threshold:
                bottlenecks.append({
                    "type": "high_cpu",
                    "component": component,
                    "current_usage": stats["current"],
                    "threshold": self.thresholds.high_cpu_threshold
                })
                
        # Check for high I/O operations
        for component, stats in io_operations.items():
            if isinstance(stats, dict) and "current" in stats and stats["current"] > self.thresholds.high_io_threshold:
                bottlenecks.append({
                    "type": "high_io",
                    "component": component,
                    "current_usage": stats["current"],
                    "threshold": self.thresholds.high_io_threshold
                })
                
        return bottlenecks
        
    def analyze_call_chains(
        self, execution_times: Dict[str, Dict]
    ) -> List[Dict]:
        """
        Analyze method call chains for bottlenecks.
        
        Args:
            execution_times (Dict): Execution time statistics
            
        Returns:
            List[Dict]: Call chain bottlenecks
        """
        bottlenecks = []
        
        # Build call graph
        for func, stats in execution_times.items():
            # Skip if stats doesn't have mean key
            if not isinstance(stats, dict) or "mean" not in stats:
                continue
                
            self.call_graph.add_node(
                func, execution_time=stats["mean"]
            )
            
        # Find critical paths if we have at least two nodes
        nodes = list(self.call_graph.nodes())
        if len(nodes) < 2:
            return bottlenecks
        
        # Try to find paths between all pairs of nodes
        try:
            # Create a list to store all paths
            all_paths = []
            
            # Get all simple paths between each pair of nodes
            for source in nodes:
                for target in nodes:
                    if source != target:
                        try:
                            paths = list(nx.all_simple_paths(
                                self.call_graph,
                                source=source,
                                target=target,
                                weight="execution_time"
                            ))
                            all_paths.extend(paths)
                        except (nx.NetworkXNoPath, nx.NodeNotFound):
                            continue
            
            # Analyze each path
            for path in all_paths:
                total_time = sum(
                    self.call_graph.nodes[node].get("execution_time", 0)
                    for node in path
                )
                
                if total_time > self.thresholds.slow_execution_threshold:
                    bottlenecks.append({
                        "type": "slow_call_chain",
                        "path": path,
                        "total_time": total_time
                    })
                    
        except Exception as e:
            # Handle any errors in path finding gracefully
            print(f"Error analyzing call chains: {e}")
            
        return bottlenecks
        
    def _calculate_trend(self, values: List[float]) -> float:
        """Calculate the trend in a series of values."""
        if len(values) < 2:
            return 0.0
            
        x = np.arange(len(values))
        y = np.array(values)
        
        # Calculate linear regression
        slope, _ = np.polyfit(x, y, 1)
        return slope 