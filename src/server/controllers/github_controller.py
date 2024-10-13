from ..tools.github_tool import GitHubTool
from ..models.github_config import GitHubConfig
import logging

logger = logging.getLogger(__name__)

class GitHubController:
    def __init__(self, config: GitHubConfig):
        self.config = config
        self.github_tool = GitHubTool(config.access_token, config.repo_name)

    def create_feature_branch(self, ticket_id: str, description: str) -> Dict[str, Any]:
        branch_name = f"feature/{ticket_id}_{description.replace(' ', '_')}"
        return self.github_tool.create_branch(branch_name)

    def update_terraform_config(self, branch_name: str, service_name: str, ingress: bool = False, egress: bool = False) -> Dict[str, Any]:
        file_path = f"terraform/{service_name}.tf"
        current_content = self.github_tool.get_file_contents(file_path, ref=branch_name)
        
        if "error" in current_content:
            return current_content

        new_content = self._modify_terraform_content(current_content["content"], service_name, ingress, egress)
        
        return self.github_tool.update_file(
            file_path,
            f"Update {service_name} Terraform config for {'ingress' if ingress else ''}{'egress' if egress else ''} communication",
            new_content,
            branch=branch_name
        )

    def _modify_terraform_content(self, content: str, service_name: str, ingress: bool, egress: bool) -> str:
        # This is a simplified example. In a real scenario, you'd use a Terraform parsing library.
        if ingress:
            content += f'\n\nresource "kubernetes_ingress" "{service_name}_ingress" {{\n  # Ingress configuration\n}}'
        if egress:
            content += f'\n\nresource "kubernetes_network_policy" "{service_name}_egress" {{\n  # Egress configuration\n}}'
        return content

    def create_pull_request(self, branch_name: str, title: str, description: str) -> Dict[str, Any]:
        return self.github_tool.create_pull_request(title, description, branch_name, "main")

    def update_jira_with_pr(self, ticket_id: str, pr_url: str):
        # This method would update the Jira ticket with the PR information
        # For now, we'll just log it
        logger.info(f"Updated Jira ticket {ticket_id} with PR: {pr_url}")