from github import Github, GithubException
from typing import Dict, Any, List
import base64
import logging

logger = logging.getLogger(__name__)

class GitHubTool:
    def __init__(self, access_token: str, repo_name: str):
        self.github = Github(access_token)
        self.repo = self.github.get_repo(repo_name)

    def get_file_contents(self, path: str, ref: str = "main") -> Dict[str, Any]:
        """
        Get the contents of a file in the repository.
        
        :param path: Path to the file in the repository
        :param ref: The name of the reference (branch, tag, or commit SHA)
        :return: Dictionary containing file path, SHA, and decoded content
        """
        try:
            content_file = self.repo.get_contents(path, ref=ref)
            return {
                "path": content_file.path,
                "sha": content_file.sha,
                "content": base64.b64decode(content_file.content).decode('utf-8'),
            }
        except GithubException as e:
            logger.error(f"Error getting file contents: {str(e)}")
            return {"error": str(e)}

    def update_file(self, path: str, message: str, content: str, branch: str = "main") -> Dict[str, Any]:
        """
        Update an existing file in the repository.
        
        :param path: Path to the file to update
        :param message: Commit message for the update
        :param content: New content of the file
        :param branch: Branch name where the file should be updated
        :return: Dictionary containing update status message
        """
        try:
            current_file = self.repo.get_contents(path, ref=branch)
            self.repo.update_file(path, message, content, current_file.sha, branch=branch)
            return {"message": f"File {path} updated successfully"}
        except GithubException as e:
            logger.error(f"Error updating file: {str(e)}")
            return {"error": str(e)}

    def create_file(self, path: str, message: str, content: str, branch: str = "main") -> Dict[str, Any]:
        """
        Create a new file in the repository.
        
        :param path: Path where the new file should be created
        :param message: Commit message for the file creation
        :param content: Content of the new file
        :param branch: Branch name where the file should be created
        :return: Dictionary containing creation status message
        """
        try:
            self.repo.create_file(path, message, content, branch=branch)
            return {"message": f"File {path} created successfully"}
        except GithubException as e:
            logger.error(f"Error creating file: {str(e)}")
            return {"error": str(e)}

    def create_branch(self, branch_name: str, base_branch: str = "main") -> Dict[str, Any]:
        """
        Creates a new branch in the repository.
        
        :param branch_name: Name of the new branch to create
        :param base_branch: Name of the base branch to use as base
        :return: Dictionary containing creation status
        """
        try:
            base_branch_obj = self.repo.get_branch(base_branch)
            self.repo.create_git_ref(f"refs/heads/{branch_name}", base_branch_obj.commit.sha)
            return {"message": f"Branch {branch_name} created successfully"}
        except GithubException as e:
            logger.error(f"Error creating branch: {str(e)}")
            return {"error": str(e)}

    def create_pull_request(self, title: str, body: str, head: str, base: str = "main") -> Dict[str, Any]:
        """
        Create a new pull request.
        
        :param title: Title of the pull request
        :param body: Description/body of the pull request
        :param head: Name of the branch where changes are implemented
        :param base: Name of the branch where changes should be merged into
        :return: Dictionary containing pull request number and HTML URL
        """
        try:
            pull = self.repo.create_pull(title=title, body=body, head=head, base=base)
            return {"number": pull.number, "html_url": pull.html_url}
        except GithubException as e:
            logger.error(f"Error creating pull request: {str(e)}")
            return {"error": str(e)}

    def update_pull_request(self, number: int, title: str = None, body: str = None, state: str = None) -> Dict[str, Any]:
        """
        Update an existing pull request.
        
        :param number: Pull request number to update
        :param title: New title for the pull request (optional)
        :param body: New description/body for the pull request (optional)
        :param state: New state for the pull request (optional)
        :return: Dictionary containing update status message
        """
        try:
            pull = self.repo.get_pull(number)
            pull.edit(title=title, body=body, state=state)
            return {"message": f"Pull request #{number} updated successfully"}
        except GithubException as e:
            logger.error(f"Error updating pull request: {str(e)}")
            return {"error": str(e)}

    def get_pull_requests(self, state: str = "open", head: str = "", base: str = "") -> List[Dict[str, Any]]:
        """
        Get a list of pull requests.
        
        :param state: State of pull requests to fetch ('open', 'closed', 'all')
        :param head: Filter pulls by head user or head organization and branch name
        :param base: Filter pulls by base branch name
        :return: List of dictionaries containing pull request details
        """
        try:
            pulls = self.repo.get_pulls(state=state, head=head, base=base)
            return [{"number": pr.number, "title": pr.title, "html_url": pr.html_url} for pr in pulls]
        except GithubException as e:
            logger.error(f"Error getting pull requests: {str(e)}")
            return [{"error": str(e)}]

    def merge_pull_request(self, number: int, commit_message: str = "") -> Dict[str, Any]:
        """
        Merge a pull request.
        
        :param number: Pull request number to merge
        :param commit_message: Custom merge commit message (optional)
        :return: Dictionary containing merge status and message
        """
        try:
            pull = self.repo.get_pull(number)
            merge_result = pull.merge(commit_message=commit_message)
            return {"merged": merge_result.merged, "message": merge_result.message}
        except GithubException as e:
            logger.error(f"Error merging pull request: {str(e)}")
            return {"error": str(e)}