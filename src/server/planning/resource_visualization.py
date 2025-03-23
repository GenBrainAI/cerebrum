"""
Resource Visualization for the Self-Aware Cerebrum.

This module provides visualization capabilities for resource allocations,
including utilization charts and cost analysis.
"""

from typing import Dict, List, Optional, Any, Tuple, Set
import logging
import json
import os
import uuid
import io
import base64
from datetime import datetime, timedelta
from dataclasses import dataclass, field

from src.server.planning.resource_allocation import ResourcePool, ResourceAllocation, AllocationPlan, ResourceType, AllocationStrategy

logger = logging.getLogger(__name__)

@dataclass
class ResourceUtilizationChart:
    """Resource utilization chart representation."""
    pool_id: str
    pool_name: str
    resource_types: List[str]
    utilization_percentages: List[float]
    timestamp: str
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "pool_id": self.pool_id,
            "pool_name": self.pool_name,
            "resource_types": self.resource_types,
            "utilization_percentages": self.utilization_percentages,
            "timestamp": self.timestamp
        }
    
    def to_html(self) -> str:
        """Generate HTML representation of the utilization chart."""
        # Convert resource types to labels
        labels_json = json.dumps(self.resource_types)
        data_json = json.dumps(self.utilization_percentages)
        
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Resource Utilization: {self.pool_name}</title>
            <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                .chart-container {{ position: relative; height: 400px; }}
                .timestamp {{ color: #777; font-size: 0.8em; margin-top: 10px; }}
            </style>
        </head>
        <body>
            <h1>Resource Utilization: {self.pool_name}</h1>
            <div class="chart-container">
                <canvas id="utilizationChart"></canvas>
            </div>
            <p class="timestamp">Generated at {self.timestamp}</p>
            
            <script>
                const labels = {labels_json};
                const data = {data_json};
                
                const ctx = document.getElementById('utilizationChart').getContext('2d');
                const chart = new Chart(ctx, {{
                    type: 'bar',
                    data: {{
                        labels: labels,
                        datasets: [{{
                            label: 'Utilization (%)',
                            data: data,
                            backgroundColor: [
                                'rgba(54, 162, 235, 0.5)',
                                'rgba(255, 99, 132, 0.5)',
                                'rgba(255, 206, 86, 0.5)',
                                'rgba(75, 192, 192, 0.5)',
                                'rgba(153, 102, 255, 0.5)',
                                'rgba(255, 159, 64, 0.5)',
                                'rgba(199, 199, 199, 0.5)',
                                'rgba(83, 102, 255, 0.5)',
                                'rgba(40, 159, 64, 0.5)'
                            ],
                            borderColor: [
                                'rgba(54, 162, 235, 1)',
                                'rgba(255, 99, 132, 1)',
                                'rgba(255, 206, 86, 1)',
                                'rgba(75, 192, 192, 1)',
                                'rgba(153, 102, 255, 1)',
                                'rgba(255, 159, 64, 1)',
                                'rgba(199, 199, 199, 1)',
                                'rgba(83, 102, 255, 1)',
                                'rgba(40, 159, 64, 1)'
                            ],
                            borderWidth: 1
                        }}]
                    }},
                    options: {{
                        scales: {{
                            y: {{
                                beginAtZero: true,
                                max: 100,
                                title: {{
                                    display: true,
                                    text: 'Utilization (%)'
                                }}
                            }}
                        }}
                    }}
                }});
            </script>
        </body>
        </html>
        """
    
    def to_svg(self) -> str:
        """Generate SVG representation of the utilization chart."""
        # This is a simplified representation using SVG
        
        width = 800
        height = 400
        padding = 50
        bar_width = (width - padding * 2) / len(self.resource_types)
        max_bar_height = height - padding * 2
        
        svg = f'''<?xml version="1.0" encoding="UTF-8" standalone="no"?>
        <svg width="{width}" height="{height}" xmlns="http://www.w3.org/2000/svg">
            <style>
                .bar {{ fill: #3498db; }}
                .axis {{ stroke: #95a5a6; stroke-width: 1; }}
                .label {{ font-family: Arial; font-size: 12px; fill: #7f8c8d; }}
                .title {{ font-family: Arial; font-size: 16px; font-weight: bold; }}
                .timestamp {{ font-family: Arial; font-size: 10px; fill: #95a5a6; }}
            </style>
            <text x="10" y="20" class="title">Resource Utilization: {self.pool_name}</text>
            <text x="{width-10}" y="{height-5}" class="timestamp" text-anchor="end">Generated at {self.timestamp}</text>
            
            <!-- Y-axis -->
            <line x1="{padding}" y1="{padding}" x2="{padding}" y2="{height-padding}" class="axis" />
            
            <!-- X-axis -->
            <line x1="{padding}" y1="{height-padding}" x2="{width-padding}" y2="{height-padding}" class="axis" />
            
            <!-- Y-axis labels -->
            <text x="{padding-5}" y="{padding}" class="label" text-anchor="end">100%</text>
            <text x="{padding-5}" y="{height-padding}" class="label" text-anchor="end">0%</text>
            <text x="{padding-5}" y="{padding+(height-padding*2)/2}" class="label" text-anchor="end">50%</text>
            
            <!-- Y-axis title -->
            <text x="{padding-35}" y="{height/2}" class="label" text-anchor="middle" transform="rotate(-90,{padding-35},{height/2})">Utilization (%)</text>
        '''
        
        # Draw bars
        for i, (resource_type, percentage) in enumerate(zip(self.resource_types, self.utilization_percentages)):
            bar_height = (percentage / 100) * max_bar_height
            x = padding + i * bar_width + 5
            y = height - padding - bar_height
            
            # Get color based on percentage
            if percentage < 30:
                color = "#2ecc71"  # Green
            elif percentage < 70:
                color = "#f39c12"  # Orange
            else:
                color = "#e74c3c"  # Red
            
            svg += f'<rect x="{x}" y="{y}" width="{bar_width-10}" height="{bar_height}" class="bar" fill="{color}" />'
            svg += f'<text x="{x+bar_width/2-5}" y="{height-padding+15}" class="label" text-anchor="middle">{resource_type}</text>'
            svg += f'<text x="{x+bar_width/2-5}" y="{y-5}" class="label" text-anchor="middle">{percentage:.1f}%</text>'
        
        svg += '</svg>'
        
        return svg

@dataclass
class ResourceCostChart:
    """Resource cost chart representation."""
    plan_id: str
    plan_name: str
    resource_types: List[str]
    costs: List[float]
    total_cost: float
    timestamp: str
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "plan_id": self.plan_id,
            "plan_name": self.plan_name,
            "resource_types": self.resource_types,
            "costs": self.costs,
            "total_cost": self.total_cost,
            "timestamp": self.timestamp
        }
    
    def to_html(self) -> str:
        """Generate HTML representation of the cost chart."""
        # Convert resource types to labels
        labels_json = json.dumps(self.resource_types)
        data_json = json.dumps(self.costs)
        
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Resource Cost Analysis: {self.plan_name}</title>
            <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                .chart-container {{ position: relative; height: 400px; }}
                .total-cost {{ font-weight: bold; margin-top: 20px; }}
                .timestamp {{ color: #777; font-size: 0.8em; margin-top: 10px; }}
            </style>
        </head>
        <body>
            <h1>Resource Cost Analysis: {self.plan_name}</h1>
            <div class="chart-container">
                <canvas id="costChart"></canvas>
            </div>
            <p class="total-cost">Total Cost: ${self.total_cost:.2f}</p>
            <p class="timestamp">Generated at {self.timestamp}</p>
            
            <script>
                const labels = {labels_json};
                const data = {data_json};
                
                const ctx = document.getElementById('costChart').getContext('2d');
                
                // Pie chart for cost distribution
                const pieChart = new Chart(ctx, {{
                    type: 'pie',
                    data: {{
                        labels: labels,
                        datasets: [{{
                            label: 'Cost ($)',
                            data: data,
                            backgroundColor: [
                                'rgba(54, 162, 235, 0.5)',
                                'rgba(255, 99, 132, 0.5)',
                                'rgba(255, 206, 86, 0.5)',
                                'rgba(75, 192, 192, 0.5)',
                                'rgba(153, 102, 255, 0.5)',
                                'rgba(255, 159, 64, 0.5)',
                                'rgba(199, 199, 199, 0.5)',
                                'rgba(83, 102, 255, 0.5)',
                                'rgba(40, 159, 64, 0.5)'
                            ],
                            borderColor: [
                                'rgba(54, 162, 235, 1)',
                                'rgba(255, 99, 132, 1)',
                                'rgba(255, 206, 86, 1)',
                                'rgba(75, 192, 192, 1)',
                                'rgba(153, 102, 255, 1)',
                                'rgba(255, 159, 64, 1)',
                                'rgba(199, 199, 199, 1)',
                                'rgba(83, 102, 255, 1)',
                                'rgba(40, 159, 64, 1)'
                            ],
                            borderWidth: 1
                        }}]
                    }},
                    options: {{
                        responsive: true,
                        plugins: {{
                            legend: {{
                                position: 'right',
                            }},
                            tooltip: {{
                                callbacks: {{
                                    label: function(context) {{
                                        const label = context.label || '';
                                        const value = context.raw || 0;
                                        const percentage = context.parsed / {self.total_cost} * 100;
                                        return `${{label}}: $${{value.toFixed(2)}} (${{percentage.toFixed(1)}}%)`;
                                    }}
                                }}
                            }}
                        }}
                    }}
                }});
            </script>
        </body>
        </html>
        """
    
    def to_svg(self) -> str:
        """Generate SVG representation of the cost chart."""
        # This is a simplified representation using SVG for a pie chart
        
        width = 800
        height = 400
        center_x = width / 2 - 100
        center_y = height / 2
        radius = 150
        
        svg = f'''<?xml version="1.0" encoding="UTF-8" standalone="no"?>
        <svg width="{width}" height="{height}" xmlns="http://www.w3.org/2000/svg">
            <style>
                .title {{ font-family: Arial; font-size: 16px; font-weight: bold; }}
                .label {{ font-family: Arial; font-size: 12px; fill: #333; }}
                .timestamp {{ font-family: Arial; font-size: 10px; fill: #95a5a6; }}
                .total {{ font-family: Arial; font-size: 14px; font-weight: bold; }}
            </style>
            <text x="10" y="20" class="title">Resource Cost Analysis: {self.plan_name}</text>
            <text x="{width-10}" y="{height-5}" class="timestamp" text-anchor="end">Generated at {self.timestamp}</text>
            <text x="{center_x}" y="{center_y+radius+40}" class="total" text-anchor="middle">Total Cost: ${self.total_cost:.2f}</text>
        '''
        
        # Calculate total for percentages
        total = sum(self.costs)
        
        # Draw pie segments
        colors = [
            "#3498db", "#e74c3c", "#f1c40f", "#2ecc71", "#9b59b6", 
            "#e67e22", "#1abc9c", "#34495e", "#95a5a6"
        ]
        
        start_angle = 0
        legend_y = 50
        
        for i, (resource_type, cost) in enumerate(zip(self.resource_types, self.costs)):
            # Calculate angle for this segment
            angle = (cost / total) * 360 if total > 0 else 0
            end_angle = start_angle + angle
            
            # Convert to radians
            start_rad = start_angle * (3.14159 / 180)
            end_rad = end_angle * (3.14159 / 180)
            
            # Calculate points
            x1 = center_x + radius * (start_rad == 0)
            y1 = center_y - 0
            
            x2 = center_x + radius * (end_rad == 0)
            y2 = center_y - 0
            
            large_arc_flag = 1 if angle > 180 else 0
            
            # Draw pie segment
            color = colors[i % len(colors)]
            
            # Draw segment only if there's a meaningful angle
            if angle > 0.1:
                start_x = center_x + radius * (start_rad == 0)
                start_y = center_y - 0
                end_x = center_x + radius * (end_rad == 0)
                end_y = center_y - 0
                
                # Path for arc
                path = f"M {center_x} {center_y} "
                path += f"L {center_x + radius * (end_rad == 0)} {center_y - 0} "
                path += f"A {radius} {radius} 0 {large_arc_flag} 0 {center_x + radius * (start_rad == 0)} {center_y - 0} "
                path += "Z"
                
                svg += f'<path d="{path}" fill="{color}" stroke="white" stroke-width="1" />'
            
            # Add to legend
            svg += f'<rect x="{width-150}" y="{legend_y}" width="15" height="15" fill="{color}" />'
            svg += f'<text x="{width-130}" y="{legend_y+12}" class="label">{resource_type}: ${cost:.2f}</text>'
            
            # Update for next segment
            start_angle = end_angle
            legend_y += 25
        
        svg += '</svg>'
        
        return svg

@dataclass
class AllocationComparisonChart:
    """Chart comparing different allocation strategies."""
    plans: List[Dict[str, Any]]  # Plan metadata including id, name, strategy, cost
    resource_types: List[str]
    timestamp: str
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "plans": self.plans,
            "resource_types": self.resource_types,
            "timestamp": self.timestamp
        }
    
    def to_html(self) -> str:
        """Generate HTML representation of the comparison chart."""
        plans_json = json.dumps(self.plans)
        resource_types_json = json.dumps(self.resource_types)
        
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Allocation Strategy Comparison</title>
            <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                .chart-container {{ position: relative; height: 500px; }}
                .timestamp {{ color: #777; font-size: 0.8em; margin-top: 10px; }}
            </style>
        </head>
        <body>
            <h1>Allocation Strategy Comparison</h1>
            <div class="chart-container">
                <canvas id="comparisonChart"></canvas>
            </div>
            <p class="timestamp">Generated at {self.timestamp}</p>
            
            <script>
                const plans = {plans_json};
                const resourceTypes = {resource_types_json};
                
                // Extract data for chart
                const labels = plans.map(p => p.name + ' (' + p.strategy + ')');
                const costs = plans.map(p => p.total_cost);
                
                const ctx = document.getElementById('comparisonChart').getContext('2d');
                const chart = new Chart(ctx, {{
                    type: 'bar',
                    data: {{
                        labels: labels,
                        datasets: [{{
                            label: 'Total Cost ($)',
                            data: costs,
                            backgroundColor: 'rgba(54, 162, 235, 0.5)',
                            borderColor: 'rgba(54, 162, 235, 1)',
                            borderWidth: 1
                        }}]
                    }},
                    options: {{
                        indexAxis: 'y',
                        scales: {{
                            x: {{
                                beginAtZero: true,
                                title: {{
                                    display: true,
                                    text: 'Total Cost ($)'
                                }}
                            }}
                        }}
                    }}
                }});
            </script>
        </body>
        </html>
        """
    
    def to_svg(self) -> str:
        """Generate SVG representation of the comparison chart."""
        width = 800
        height = 400
        padding = 100
        bar_height = 30
        max_cost = max([plan["total_cost"] for plan in self.plans])
        scale = (width - padding * 2) / max_cost if max_cost > 0 else 1
        
        svg = f'''<?xml version="1.0" encoding="UTF-8" standalone="no"?>
        <svg width="{width}" height="{height}" xmlns="http://www.w3.org/2000/svg">
            <style>
                .bar {{ fill: #3498db; }}
                .axis {{ stroke: #95a5a6; stroke-width: 1; }}
                .label {{ font-family: Arial; font-size: 12px; fill: #7f8c8d; }}
                .title {{ font-family: Arial; font-size: 16px; font-weight: bold; }}
                .timestamp {{ font-family: Arial; font-size: 10px; fill: #95a5a6; }}
            </style>
            <text x="10" y="20" class="title">Allocation Strategy Comparison</text>
            <text x="{width-10}" y="{height-5}" class="timestamp" text-anchor="end">Generated at {self.timestamp}</text>
            
            <!-- Y-axis -->
            <line x1="{padding}" y1="{padding}" x2="{padding}" y2="{height-padding}" class="axis" />
            
            <!-- X-axis -->
            <line x1="{padding}" y1="{height-padding}" x2="{width-padding}" y2="{height-padding}" class="axis" />
            
            <!-- X-axis labels -->
            <text x="{padding}" y="{height-padding+15}" class="label">0</text>
            <text x="{width-padding}" y="{height-padding+15}" class="label">${max_cost:.2f}</text>
            
            <!-- X-axis title -->
            <text x="{width/2}" y="{height-padding+35}" class="label" text-anchor="middle">Total Cost ($)</text>
        '''
        
        # Draw bars
        for i, plan in enumerate(self.plans):
            bar_width = plan["total_cost"] * scale
            y = padding + i * (bar_height + 10)
            
            svg += f'<rect x="{padding}" y="{y}" width="{bar_width}" height="{bar_height}" class="bar" />'
            svg += f'<text x="{padding-5}" y="{y+bar_height/2+5}" class="label" text-anchor="end">{plan["name"]} ({plan["strategy"]})</text>'
            svg += f'<text x="{padding+bar_width+5}" y="{y+bar_height/2+5}" class="label">${plan["total_cost"]:.2f}</text>'
        
        svg += '</svg>'
        
        return svg

class ResourceVisualization:
    """Visualization generator for resource allocations."""
    
    def __init__(self, storage_path: Optional[str] = None):
        """
        Initialize the Resource Visualization.
        
        Args:
            storage_path: Path to store visualizations
        """
        self.storage_path = storage_path or os.path.join(os.path.expanduser("~"), ".cerebrum", "visualizations", "resources")
        os.makedirs(self.storage_path, exist_ok=True)
        
        # Create subdirectories
        self.utilization_path = os.path.join(self.storage_path, "utilization")
        self.costs_path = os.path.join(self.storage_path, "costs")
        self.comparisons_path = os.path.join(self.storage_path, "comparisons")
        
        os.makedirs(self.utilization_path, exist_ok=True)
        os.makedirs(self.costs_path, exist_ok=True)
        os.makedirs(self.comparisons_path, exist_ok=True)
    
    async def generate_utilization_chart(
        self,
        pool: ResourcePool,
        utilization: Dict[ResourceType, float]
    ) -> ResourceUtilizationChart:
        """
        Generate a utilization chart for a resource pool.
        
        Args:
            pool: The resource pool
            utilization: Dictionary mapping resource types to utilization percentages
            
        Returns:
            A ResourceUtilizationChart object
        """
        # Convert to lists for chart
        resource_types = []
        percentages = []
        
        for resource_type, percentage in utilization.items():
            resource_types.append(resource_type.name)
            percentages.append(percentage)
        
        timestamp = datetime.now().isoformat()
        
        chart = ResourceUtilizationChart(
            pool_id=pool.id,
            pool_name=pool.name,
            resource_types=resource_types,
            utilization_percentages=percentages,
            timestamp=timestamp
        )
        
        # Save the chart
        self._save_utilization_chart(pool.id, chart)
        
        return chart
    
    async def generate_cost_chart(
        self,
        plan: AllocationPlan,
        pool: ResourcePool
    ) -> ResourceCostChart:
        """
        Generate a cost chart for an allocation plan.
        
        Args:
            plan: The allocation plan
            pool: The resource pool
            
        Returns:
            A ResourceCostChart object
        """
        # Calculate costs by resource type
        resource_costs: Dict[ResourceType, float] = {}
        
        for allocation in plan.allocations.values():
            for resource_type, amount in allocation.resources.items():
                cost = pool.cost(resource_type, amount)
                resource_costs[resource_type] = resource_costs.get(resource_type, 0.0) + cost
        
        # Convert to lists for chart
        resource_types = []
        costs = []
        
        for resource_type, cost in resource_costs.items():
            resource_types.append(resource_type.name)
            costs.append(cost)
        
        timestamp = datetime.now().isoformat()
        
        chart = ResourceCostChart(
            plan_id=plan.id,
            plan_name=plan.name,
            resource_types=resource_types,
            costs=costs,
            total_cost=plan.total_cost,
            timestamp=timestamp
        )
        
        # Save the chart
        self._save_cost_chart(plan.id, chart)
        
        return chart
    
    async def generate_comparison_chart(
        self,
        plans: List[Dict[str, Any]] or List[AllocationPlan],
        comparison_id: Optional[str] = None
    ) -> AllocationComparisonChart:
        """
        Generate a comparison chart for multiple allocation plans.
        
        Args:
            plans: List of allocation plans to compare (either AllocationPlan objects
                  or dictionaries with plan data)
            comparison_id: Optional ID for the comparison, will generate UUID if not provided
            
        Returns:
            An AllocationComparisonChart object
        """
        # Extract plan data
        plan_data = []
        all_resource_types = set()
        
        # Check if plans are already in dictionary format
        if plans and isinstance(plans[0], dict):
            plan_data = plans
            # Extract resource types from plan data
            for plan in plans:
                if "resource_allocation" in plan:
                    for resource_type in plan["resource_allocation"]:
                        all_resource_types.add(resource_type)
        else:
            # Convert AllocationPlan objects to dictionaries
            for plan in plans:
                # Get all resource types used
                for allocation in plan.allocations.values():
                    for resource_type in allocation.resources:
                        all_resource_types.add(resource_type.name)
                
                # Add plan data
                plan_data.append({
                    "id": plan.id,
                    "name": plan.name,
                    "strategy": plan.strategy.name,
                    "total_cost": plan.total_cost
                })
        
        timestamp = datetime.now().isoformat()
        
        chart = AllocationComparisonChart(
            plans=plan_data,
            resource_types=list(all_resource_types),
            timestamp=timestamp
        )
        
        # Generate a unique ID for the comparison if not provided
        if comparison_id is None:
            comparison_id = str(uuid.uuid4())
        
        # Save the chart
        self._save_comparison_chart(comparison_id, chart)
        
        return chart
    
    def _save_utilization_chart(self, pool_id: str, chart: ResourceUtilizationChart) -> None:
        """Save utilization chart to storage."""
        # Create subdirectory for this pool's charts
        chart_dir = os.path.join(self.utilization_path, pool_id)
        os.makedirs(chart_dir, exist_ok=True)
        
        # Save as JSON
        json_path = os.path.join(chart_dir, "latest.json")
        try:
            with open(json_path, 'w') as f:
                json.dump(chart.to_dict(), f, indent=2)
            logger.info(f"Saved utilization chart JSON: {json_path}")
        except Exception as e:
            logger.error(f"Error saving utilization chart JSON: {e}")
        
        # Save as HTML
        html_path = os.path.join(chart_dir, "latest.html")
        try:
            with open(html_path, 'w') as f:
                f.write(chart.to_html())
            logger.info(f"Saved utilization chart HTML: {html_path}")
        except Exception as e:
            logger.error(f"Error saving utilization chart HTML: {e}")
        
        # Save as SVG
        svg_path = os.path.join(chart_dir, "latest.svg")
        try:
            with open(svg_path, 'w') as f:
                f.write(chart.to_svg())
            logger.info(f"Saved utilization chart SVG: {svg_path}")
        except Exception as e:
            logger.error(f"Error saving utilization chart SVG: {e}")
        
        # Also save to the dated file for historical tracking
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        dated_json_path = os.path.join(chart_dir, f"{timestamp}.json")
        try:
            with open(dated_json_path, 'w') as f:
                json.dump(chart.to_dict(), f, indent=2)
        except Exception as e:
            logger.error(f"Error saving dated utilization chart JSON: {e}")
    
    def _save_cost_chart(self, plan_id: str, chart: ResourceCostChart) -> None:
        """Save cost chart to storage."""
        # Create subdirectory for this plan's charts
        chart_dir = os.path.join(self.costs_path, plan_id)
        os.makedirs(chart_dir, exist_ok=True)
        
        # Save as JSON
        json_path = os.path.join(chart_dir, "latest.json")
        try:
            with open(json_path, 'w') as f:
                json.dump(chart.to_dict(), f, indent=2)
            logger.info(f"Saved cost chart JSON: {json_path}")
        except Exception as e:
            logger.error(f"Error saving cost chart JSON: {e}")
        
        # Save as HTML
        html_path = os.path.join(chart_dir, "latest.html")
        try:
            with open(html_path, 'w') as f:
                f.write(chart.to_html())
            logger.info(f"Saved cost chart HTML: {html_path}")
        except Exception as e:
            logger.error(f"Error saving cost chart HTML: {e}")
        
        # Save as SVG
        svg_path = os.path.join(chart_dir, "latest.svg")
        try:
            with open(svg_path, 'w') as f:
                f.write(chart.to_svg())
            logger.info(f"Saved cost chart SVG: {svg_path}")
        except Exception as e:
            logger.error(f"Error saving cost chart SVG: {e}")
        
        # Also save to the dated file for historical tracking
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        dated_json_path = os.path.join(chart_dir, f"{timestamp}.json")
        try:
            with open(dated_json_path, 'w') as f:
                json.dump(chart.to_dict(), f, indent=2)
        except Exception as e:
            logger.error(f"Error saving dated cost chart JSON: {e}")
    
    def _save_comparison_chart(self, comparison_id: str, chart: AllocationComparisonChart) -> None:
        """Save comparison chart to storage."""
        # Create subdirectory for this comparison's charts
        chart_dir = os.path.join(self.comparisons_path, comparison_id)
        os.makedirs(chart_dir, exist_ok=True)
        
        # Save as JSON
        json_path = os.path.join(chart_dir, "latest.json")
        try:
            with open(json_path, 'w') as f:
                json.dump(chart.to_dict(), f, indent=2)
            logger.info(f"Saved comparison chart JSON: {json_path}")
        except Exception as e:
            logger.error(f"Error saving comparison chart JSON: {e}")
        
        # Save as HTML
        html_path = os.path.join(chart_dir, "latest.html")
        try:
            with open(html_path, 'w') as f:
                f.write(chart.to_html())
            logger.info(f"Saved comparison chart HTML: {html_path}")
        except Exception as e:
            logger.error(f"Error saving comparison chart HTML: {e}")
        
        # Save as SVG
        svg_path = os.path.join(chart_dir, "latest.svg")
        try:
            with open(svg_path, 'w') as f:
                f.write(chart.to_svg())
            logger.info(f"Saved comparison chart SVG: {svg_path}")
        except Exception as e:
            logger.error(f"Error saving comparison chart SVG: {e}")
        
        # Also save to the dated file for historical tracking
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        dated_json_path = os.path.join(chart_dir, f"{timestamp}.json")
        try:
            with open(dated_json_path, 'w') as f:
                json.dump(chart.to_dict(), f, indent=2)
        except Exception as e:
            logger.error(f"Error saving dated comparison chart JSON: {e}")
    
    async def load_utilization_chart(self, pool_id: str) -> Optional[ResourceUtilizationChart]:
        """Load utilization chart from storage."""
        json_path = os.path.join(self.utilization_path, f"{pool_id}.json")
        if not os.path.exists(json_path):
            return None
        
        try:
            with open(json_path, 'r') as f:
                data = json.load(f)
                
                return ResourceUtilizationChart(
                    pool_id=data["pool_id"],
                    pool_name=data["pool_name"],
                    resource_types=data["resource_types"],
                    utilization_percentages=data["utilization_percentages"],
                    timestamp=data["timestamp"]
                )
        except Exception as e:
            logger.error(f"Error loading utilization chart: {e}")
            return None
    
    async def load_cost_chart(self, plan_id: str) -> Optional[ResourceCostChart]:
        """Load cost chart from storage."""
        json_path = os.path.join(self.costs_path, f"{plan_id}.json")
        if not os.path.exists(json_path):
            return None
        
        try:
            with open(json_path, 'r') as f:
                data = json.load(f)
                
                return ResourceCostChart(
                    plan_id=data["plan_id"],
                    plan_name=data["plan_name"],
                    resource_types=data["resource_types"],
                    costs=data["costs"],
                    total_cost=data["total_cost"],
                    timestamp=data["timestamp"]
                )
        except Exception as e:
            logger.error(f"Error loading cost chart: {e}")
            return None
    
    async def load_comparison_chart(self, comparison_id: str) -> Optional[AllocationComparisonChart]:
        """Load comparison chart from storage."""
        json_path = os.path.join(self.comparisons_path, f"{comparison_id}.json")
        if not os.path.exists(json_path):
            return None
        
        try:
            with open(json_path, 'r') as f:
                data = json.load(f)
                
                return AllocationComparisonChart(
                    plans=data["plans"],
                    resource_types=data["resource_types"],
                    timestamp=data["timestamp"]
                )
        except Exception as e:
            logger.error(f"Error loading comparison chart: {e}")
            return None 