"""
DEPRECATED: This module is deprecated and will be removed in a future version.
Please use task_tree_flow.py instead.

Task tree model with plugin system support.
Handles task dependencies and execution order with plugin integration.
"""

import warnings
import logging
from typing import List, Optional, Dict, Any, Set
from .task import Task
from ..plugins.plugin_manager import PluginManager

# Show deprecation warning
warnings.warn(
    "tasktree.py is deprecated and will be removed in a future version. "
    "Please use task_tree_flow.py instead.",
    DeprecationWarning,
    stacklevel=2
)

logger = logging.getLogger(__name__)

class TaskNode:
    """Node in the task tree."""
    
    def __init__(self, task: Task):
        self.task = task
        self.parent: Optional[TaskNode] = None
        self.children: List[TaskNode] = []
        self.status: str = "pending"
        self.result: Optional[Dict[str, Any]] = None
    
    def add_child(self, child: 'TaskNode') -> None:
        """Add a child node."""
        self.children.append(child)
        child.parent = self
    
    def remove_child(self, child: 'TaskNode') -> None:
        """Remove a child node."""
        if child in self.children:
            self.children.remove(child)
            child.parent = None
    
    @property
    def is_root(self) -> bool:
        """Check if node is root."""
        return self.parent is None
    
    @property
    def is_leaf(self) -> bool:
        """Check if node is leaf."""
        return len(self.children) == 0
    
    def get_ancestors(self) -> List['TaskNode']:
        """Get all ancestor nodes."""
        ancestors = []
        current = self.parent
        while current:
            ancestors.append(current)
            current = current.parent
        return ancestors
    
    def get_descendants(self) -> List['TaskNode']:
        """Get all descendant nodes."""
        descendants = []
        for child in self.children:
            descendants.append(child)
            descendants.extend(child.get_descendants())
        return descendants

class TaskTree:
    """Tree structure for managing task dependencies with plugin support."""
    
    def __init__(self):
        self.nodes: List[TaskNode] = []
        self.plugin_manager = PluginManager()
    
    def add_node(self, node: TaskNode) -> None:
        """Add a node to the tree."""
        self.nodes.append(node)
    
    def remove_node(self, node: TaskNode) -> None:
        """Remove a node and its descendants from the tree."""
        # Remove from parent
        if node.parent:
            node.parent.remove_child(node)
        
        # Remove descendants
        for descendant in node.get_descendants():
            if descendant in self.nodes:
                self.nodes.remove(descendant)
        
        # Remove node itself
        if node in self.nodes:
            self.nodes.remove(node)
    
    def get_roots(self) -> List[TaskNode]:
        """Get all root nodes."""
        return [node for node in self.nodes if node.is_root]
    
    def get_leaves(self) -> List[TaskNode]:
        """Get all leaf nodes."""
        return [node for node in self.nodes if node.is_leaf]
    
    def get_execution_order(self) -> List[TaskNode]:
        """Get nodes in execution order (topological sort)."""
        visited: Set[TaskNode] = set()
        execution_order: List[TaskNode] = []
        
        def visit(node: TaskNode):
            if node not in visited:
                visited.add(node)
                for ancestor in node.get_ancestors():
                    visit(ancestor)
                execution_order.append(node)
        
        for node in self.nodes:
            visit(node)
        
        return execution_order
    
    async def execute_node(self, node: TaskNode, tasksmanager_id: str) -> Dict[str, Any]:
        """Execute a node's task using appropriate plugin."""
        try:
            # Get plugin for task
            plugin_name = self._get_plugin_for_task(node.task)
            plugin = self.plugin_manager.get_plugin(plugin_name)
            if not plugin:
                raise ValueError(f"Plugin {plugin_name} not found")
            
            # Create agent configuration
            agent_config = {
                "role": node.task.agent_role,
                "goal": node.task.input_data.get("goal", "Complete the assigned task successfully"),
                "backstory": node.task.input_data.get("backstory", f"Expert in {node.task.agent_role}"),
                "tools": node.task.input_data.get("tools", []),
                "allow_delegation": node.task.input_data.get("allow_delegation", False)
            }
            
            # Create agent
            agent = await plugin.create_agent(agent_config)
            
            # Prepare task configuration
            task_config = {
                "name": node.task.name,
                "description": node.task.description,
                "crew_id": tasksmanager_id,
                "expected_output": node.task.input_data.get("expected_output"),
                **node.task.input_data
            }
            
            # Add parent results if available
            if node.parent and node.parent.result:
                task_config["parent_result"] = node.parent.result
            
            # Execute task
            result = await plugin.execute_task(agent, task_config)
            
            # Update node status and result
            node.status = result.get("status", "completed")
            node.result = result
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to execute node {node.task.id}: {str(e)}")
            node.status = "failed"
            node.result = {"status": "failed", "error": str(e)}
            raise
    
    def _get_plugin_for_task(self, task: Task) -> str:
        """Determine which plugin to use for a task."""
        # For now, default to CrewAI
        # In future, could be determined by task type or configuration
        return "crewai"
    
    async def execute_tree(self, tasksmanager_id: str) -> Dict[str, Any]:
        """Execute all tasks in the tree in proper order."""
        results = {}
        execution_order = self.get_execution_order()
        
        for node in execution_order:
            try:
                result = await self.execute_node(node, tasksmanager_id)
                results[node.task.id] = result
                
                # Stop execution if node failed
                if node.status == "failed":
                    break
                    
            except Exception as e:
                logger.error(f"Tree execution failed at node {node.task.id}: {str(e)}")
                results[node.task.id] = {
                    "status": "failed",
                    "error": str(e)
                }
                break
        
        return results 