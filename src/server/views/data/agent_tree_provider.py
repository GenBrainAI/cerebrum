from typing import List, Dict, Any
from uuid import UUID, uuid4
from ..components.tree_component import TreeNode

class AgentTreeProvider:
    """Manages agentic configuration trees."""
    
    def __init__(self, persistence_model):
        self.persistence_model = persistence_model
        
    def get_agent_tree(self) -> TreeNode:
        """Build tree structure from agent configurations."""
        # Create root node
        root = TreeNode(
            id=uuid4(),
            name="Agent Configurations",
            node_type="root"
        )
        
        # Create main sections
        roles = TreeNode(id=uuid4(), name="Agent Roles", node_type="section")
        workflows = TreeNode(id=uuid4(), name="Workflows", node_type="section")
        
        # Add agent roles
        agent_roles = self._get_agent_roles()
        for role in agent_roles:
            role_node = TreeNode(
                id=uuid4(),
                name=role["name"],
                node_type="role",
                metadata=role
            )
            roles.children.append(role_node)
            
        # Add workflows
        workflow_configs = self._get_workflows()
        for workflow in workflow_configs:
            workflow_node = TreeNode(
                id=uuid4(),
                name=workflow["name"],
                node_type="workflow",
                metadata=workflow
            )
            workflows.children.append(workflow_node)
            
        root.children = [roles, workflows]
        return root
        
    def _get_agent_roles(self) -> List[Dict[str, Any]]:
        """Get agent roles from persistence model."""
        # TODO: Implement actual role retrieval from persistence model
        roles = self.persistence_model.roles.list() if hasattr(self.persistence_model, 'roles') else []
        
        # Convert roles to dictionary format
        return [
            {
                "name": role.name,
                "description": getattr(role, "description", ""),
                "model": getattr(role, "model", "gpt-4o-mini")
            }
            for role in roles
        ] or [
            {"name": "Task Manager", "description": "Manages task execution"},
            {"name": "Research Agent", "description": "Performs research tasks"}
        ]
        
    def _get_workflows(self) -> List[Dict[str, Any]]:
        """Get workflow configurations from persistence model."""
        # TODO: Implement actual workflow retrieval from persistence model
        workflows = self.persistence_model.workflows.list() if hasattr(self.persistence_model, 'workflows') else []
        
        # Convert workflows to dictionary format
        return [
            {
                "name": workflow.name,
                "agents": getattr(workflow, "agents", []),
                "type": getattr(workflow, "type", "sequential")
            }
            for workflow in workflows
        ] or [
            {"name": "Research Workflow", "agents": ["Research Agent", "Task Manager"]},
            {"name": "Development Workflow", "agents": ["Developer", "Reviewer"]}
        ]
