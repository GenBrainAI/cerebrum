import asyncio
import inspect
import psutil
import time
import importlib.util
from typing import Dict, List, Optional
from pathlib import Path
import sys
import tracemalloc
import traceback
from functools import wraps

class TelemetryCollector:
    """Collects telemetry data from system components."""
    
    def __init__(self):
        self.instrumented_components = {}
        self.execution_times = {}
        self.memory_snapshots = {}
        self.error_logs = {}
        tracemalloc.start()
        
    async def instrument_component(self, component_path: str):
        """
        Add instrumentation to a component.
        
        Args:
            component_path (str): Path to the component file
        """
        if component_path in self.instrumented_components:
            return
            
        try:
            # Import the component module
            module_name = Path(component_path).stem
            spec = importlib.util.spec_from_file_location(
                module_name, component_path
            )
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            # Initialize tracking for this component
            self.execution_times[component_path] = {}
            self.memory_snapshots[component_path] = []
            self.error_logs[component_path] = []
            
            # Instrument all functions and methods
            for name, obj in inspect.getmembers(module):
                if inspect.isfunction(obj) or inspect.ismethod(obj):
                    setattr(
                        module, name, 
                        self._instrument_function(obj, component_path)
                    )
                    
            self.instrumented_components[component_path] = module
            
        except Exception as e:
            print(f"Error instrumenting {component_path}: {e}")
            
    async def collect_execution_times(
        self, component_path: str
    ) -> Dict[str, List[float]]:
        """
        Collect method execution time data.
        
        Args:
            component_path (str): Path to the component
            
        Returns:
            Dict[str, List[float]]: Execution times by method
        """
        if component_path not in self.execution_times:
            return {}
            
        return self.execution_times[component_path].copy()
        
    async def collect_memory_usage(
        self, component_path: str
    ) -> Dict[str, float]:
        """
        Collect memory usage data.
        
        Args:
            component_path (str): Path to the component
            
        Returns:
            Dict[str, float]: Memory usage statistics
        """
        if component_path not in self.memory_snapshots:
            return {}
            
        try:
            # Take a new memory snapshot
            snapshot = tracemalloc.take_snapshot()
            
            # Filter statistics for this component
            component_stats = [
                stat for stat in snapshot.statistics('filename')
                if component_path in stat.traceback[0].filename
            ]
            
            # Calculate memory metrics
            total_size = sum(stat.size for stat in component_stats)
            peak_size = max(
                (stat.size for stat in component_stats), 
                default=0
            )
            
            # Get process memory info
            process = psutil.Process()
            process_memory = process.memory_info()
            
            memory_data = {
                "total_size": total_size,
                "peak_size": peak_size,
                "rss": process_memory.rss,
                "vms": process_memory.vms,
                "timestamp": time.time()
            }
            
            # Store snapshot
            self.memory_snapshots[component_path].append(memory_data)
            
            # Keep only last 100 snapshots
            if len(self.memory_snapshots[component_path]) > 100:
                self.memory_snapshots[component_path].pop(0)
                
            return memory_data
            
        except Exception as e:
            print(f"Error collecting memory data for {component_path}: {e}")
            return {}
            
    async def collect_error_data(
        self, component_path: str
    ) -> List[Dict[str, any]]:
        """
        Collect error and exception data.
        
        Args:
            component_path (str): Path to the component
            
        Returns:
            List[Dict]: Error and exception data
        """
        if component_path not in self.error_logs:
            return []
            
        return self.error_logs[component_path].copy()
        
    def _instrument_function(self, func, component_path: str):
        """Wrap a function with telemetry collection."""
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            error_data = None
            
            try:
                if inspect.iscoroutinefunction(func):
                    result = await func(*args, **kwargs)
                else:
                    result = func(*args, **kwargs)
                    
            except Exception as e:
                error_data = {
                    "timestamp": time.time(),
                    "type": type(e).__name__,
                    "message": str(e),
                    "traceback": traceback.format_exc(),
                    "function": func.__name__
                }
                if component_path not in self.error_logs:
                    self.error_logs[component_path] = []
                self.error_logs[component_path].append(error_data)
                raise
                
            finally:
                end_time = time.time()
                execution_time = end_time - start_time
                
                # Initialize dictionaries if they don't exist
                if component_path not in self.execution_times:
                    self.execution_times[component_path] = {}
                    
                # Record execution time
                if func.__name__ not in self.execution_times[component_path]:
                    self.execution_times[component_path][func.__name__] = []
                    
                self.execution_times[component_path][func.__name__].append(
                    execution_time
                )
                
                # Keep only last 100 execution times
                if len(self.execution_times[component_path][func.__name__]) > 100:
                    self.execution_times[component_path][func.__name__].pop(0)
                    
            return result
            
        return wrapper 