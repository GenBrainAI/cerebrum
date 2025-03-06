import numpy as np
from typing import Dict, List, Optional
from dataclasses import dataclass
from scipy import stats
import time

@dataclass
class AnomalyThresholds:
    z_score_threshold: float = 3.0
    mad_threshold: float = 3.5
    iqr_multiplier: float = 1.5
    min_data_points: int = 10

class AnomalyDetector:
    """Detects anomalies in system behavior."""
    
    def __init__(self):
        self.thresholds = AnomalyThresholds()
        self.baseline_stats = {}
        self.pattern_history = {}
        
    def establish_baseline(self, telemetry_data: List[Dict]):
        """
        Establish baseline behavior from historical data.
        
        Args:
            telemetry_data (List[Dict]): Historical telemetry data
        """
        if len(telemetry_data) < self.thresholds.min_data_points:
            return
            
        # Calculate baseline statistics for different metrics
        execution_times = [
            entry["execution_times"] 
            for entry in telemetry_data 
            if "execution_times" in entry
        ]
        memory_usage = [
            entry["memory_usage"] 
            for entry in telemetry_data 
            if "memory_usage" in entry
        ]
        
        self.baseline_stats = {
            "execution_times": self._calculate_baseline_stats(execution_times),
            "memory_usage": self._calculate_baseline_stats(memory_usage)
        }
        
    def detect_statistical_anomalies(
        self, telemetry_data: List[Dict]
    ) -> List[Dict]:
        """
        Detect anomalies using statistical methods.
        
        Args:
            telemetry_data (List[Dict]): Telemetry data to analyze
            
        Returns:
            List[Dict]: Detected anomalies
        """
        if len(telemetry_data) < self.thresholds.min_data_points:
            return []
            
        anomalies = []
        
        # Analyze execution times
        for entry in telemetry_data:
            if "execution_times" in entry:
                exec_anomalies = self._detect_execution_time_anomalies(
                    entry["execution_times"],
                    self.baseline_stats.get("execution_times", {})
                )
                if exec_anomalies:
                    anomalies.extend(exec_anomalies)
                    
            if "memory_usage" in entry:
                memory_anomalies = self._detect_memory_usage_anomalies(
                    entry["memory_usage"],
                    self.baseline_stats.get("memory_usage", {})
                )
                if memory_anomalies:
                    anomalies.extend(memory_anomalies)
                    
        return anomalies
        
    def detect_pattern_anomalies(
        self, telemetry_data: List[Dict], patterns: Dict
    ) -> List[Dict]:
        """
        Detect anomalies in behavior patterns.
        
        Args:
            telemetry_data (List[Dict]): Telemetry data to analyze
            patterns (Dict): Known behavior patterns
            
        Returns:
            List[Dict]: Detected pattern anomalies
        """
        if len(telemetry_data) < self.thresholds.min_data_points:
            return []
            
        anomalies = []
        
        # Analyze call patterns
        call_patterns = self._extract_call_patterns(telemetry_data)
        pattern_anomalies = self._detect_pattern_deviations(
            call_patterns, patterns
        )
        if pattern_anomalies:
            anomalies.extend(pattern_anomalies)
            
        # Analyze timing patterns
        timing_patterns = self._extract_timing_patterns(telemetry_data)
        timing_anomalies = self._detect_timing_anomalies(
            timing_patterns, patterns
        )
        if timing_anomalies:
            anomalies.extend(timing_anomalies)
            
        return anomalies
        
    def classify_anomaly(self, anomaly: Dict):
        """
        Classify type and severity of anomaly.
        
        Args:
            anomaly (Dict): Anomaly to classify
        """
        # Determine anomaly type
        if "execution_time" in anomaly:
            anomaly["type"] = "performance"
        elif "memory_usage" in anomaly:
            anomaly["type"] = "resource"
        elif "pattern" in anomaly:
            anomaly["type"] = "behavioral"
        else:
            anomaly["type"] = "unknown"
            
        # Assess severity
        severity = self._calculate_severity(anomaly)
        anomaly["severity"] = severity
        
        # Add context information
        anomaly["context"] = self._gather_context(anomaly)
        
    def _calculate_baseline_stats(self, data: List[Dict]) -> Dict:
        """Calculate baseline statistical measures."""
        if not data:
            return {}
            
        # Convert to numpy array for calculations
        values = np.array([
            list(d.values()) for d in data
        ]).flatten()
        
        return {
            "mean": np.mean(values),
            "std": np.std(values),
            "median": np.median(values),
            "mad": stats.median_abs_deviation(values),
            "q1": np.percentile(values, 25),
            "q3": np.percentile(values, 75)
        }
        
    def _detect_execution_time_anomalies(
        self, exec_times: Dict, baseline: Dict
    ) -> List[Dict]:
        """Detect anomalies in execution times."""
        anomalies = []
        
        for func_name, times in exec_times.items():
            if not times:
                continue
                
            current_value = np.mean(times)
            
            # Z-score detection
            z_score = abs(
                (current_value - baseline["mean"]) / baseline["std"]
            )
            if z_score > self.thresholds.z_score_threshold:
                anomalies.append({
                    "function": func_name,
                    "execution_time": current_value,
                    "z_score": z_score,
                    "timestamp": time.time()
                })
                
            # MAD detection
            mad_score = abs(
                (current_value - baseline["median"]) / baseline["mad"]
            )
            if mad_score > self.thresholds.mad_threshold:
                anomalies.append({
                    "function": func_name,
                    "execution_time": current_value,
                    "mad_score": mad_score,
                    "timestamp": time.time()
                })
                
        return anomalies
        
    def _detect_memory_usage_anomalies(
        self, memory_data: Dict, baseline: Dict
    ) -> List[Dict]:
        """Detect anomalies in memory usage."""
        anomalies = []
        
        # IQR-based detection
        iqr = baseline["q3"] - baseline["q1"]
        upper_bound = baseline["q3"] + (iqr * self.thresholds.iqr_multiplier)
        
        if memory_data["total_size"] > upper_bound:
            anomalies.append({
                "memory_usage": memory_data["total_size"],
                "threshold": upper_bound,
                "timestamp": memory_data["timestamp"]
            })
            
        return anomalies
        
    def _extract_call_patterns(self, telemetry_data: List[Dict]) -> Dict:
        """Extract patterns in function call sequences."""
        patterns = {}
        
        for entry in telemetry_data:
            if "execution_times" not in entry:
                continue
                
            # Build call sequence
            call_sequence = list(entry["execution_times"].keys())
            if call_sequence:
                sequence_key = "->".join(call_sequence)
                patterns[sequence_key] = patterns.get(sequence_key, 0) + 1
                
        return patterns
        
    def _extract_timing_patterns(self, telemetry_data: List[Dict]) -> Dict:
        """Extract patterns in execution timing."""
        patterns = {}
        
        for entry in telemetry_data:
            if "execution_times" not in entry:
                continue
                
            for func, times in entry["execution_times"].items():
                if func not in patterns:
                    patterns[func] = []
                patterns[func].extend(times)
                
        return patterns
        
    def _detect_pattern_deviations(
        self, current_patterns: Dict, baseline_patterns: Dict
    ) -> List[Dict]:
        """Detect deviations from established patterns."""
        anomalies = []
        
        for pattern, count in current_patterns.items():
            if pattern in baseline_patterns:
                baseline_count = baseline_patterns[pattern]
                if count < baseline_count * 0.5 or count > baseline_count * 1.5:
                    anomalies.append({
                        "pattern": pattern,
                        "current_count": count,
                        "baseline_count": baseline_count,
                        "timestamp": time.time()
                    })
                    
        return anomalies
        
    def _detect_timing_anomalies(
        self, current_timing: Dict, baseline_timing: Dict
    ) -> List[Dict]:
        """Detect anomalies in execution timing patterns."""
        anomalies = []
        
        for func, times in current_timing.items():
            if func in baseline_timing:
                baseline_times = baseline_timing[func]
                
                # Compare distributions
                try:
                    stat, p_value = stats.ks_2samp(times, baseline_times)
                    if p_value < 0.05:  # Significant difference
                        anomalies.append({
                            "function": func,
                            "p_value": p_value,
                            "statistic": stat,
                            "timestamp": time.time()
                        })
                except Exception:
                    continue
                    
        return anomalies
        
    def _calculate_severity(self, anomaly: Dict) -> str:
        """Calculate anomaly severity level."""
        if "z_score" in anomaly:
            if anomaly["z_score"] > 5.0:
                return "critical"
            elif anomaly["z_score"] > 4.0:
                return "high"
            else:
                return "medium"
        elif "mad_score" in anomaly:
            if anomaly["mad_score"] > 5.0:
                return "critical"
            elif anomaly["mad_score"] > 4.0:
                return "high"
            else:
                return "medium"
        else:
            return "low"
            
    def _gather_context(self, anomaly: Dict) -> Dict:
        """Gather additional context for an anomaly."""
        context = {
            "detection_method": self._determine_detection_method(anomaly),
            "related_metrics": self._find_related_metrics(anomaly),
            "historical_occurrences": self._find_historical_occurrences(anomaly)
        }
        return context
        
    def _determine_detection_method(self, anomaly: Dict) -> str:
        """Determine which method detected the anomaly."""
        if "z_score" in anomaly:
            return "z_score"
        elif "mad_score" in anomaly:
            return "mad"
        elif "pattern" in anomaly:
            return "pattern_analysis"
        else:
            return "unknown"
            
    def _find_related_metrics(self, anomaly: Dict) -> List[str]:
        """Find metrics related to the anomaly."""
        related = []
        
        if "execution_time" in anomaly:
            related.extend(["cpu_usage", "memory_usage"])
        elif "memory_usage" in anomaly:
            related.extend(["gc_stats", "object_count"])
            
        return related
        
    def _find_historical_occurrences(self, anomaly: Dict) -> List[Dict]:
        """Find similar historical anomalies."""
        # This would typically query a historical anomaly database
        # For now, return an empty list
        return [] 