# src/server/tools/github_tool.py

from github import Github, GithubException
from typing import Dict, Any, List
import base64

class GitHubTool:
    def __init__(self, access_token: str, repo_name: str):
        self.github = Github(access_token)
        self.repo = self.github.get_repo(repo_name)

    def get_file_contents(self, path: str, ref: str = "main") -> Dict[str, Any]:
        """Get the contents of a file in the repository."""
        try:
            content_file = self.repo.get_contents(path, ref=ref)
            return {
                "path": content_file.path,
                "sha": content_file.sha,
                "content": base64.b64decode(content_file.content).decode('utf-8'),
            }
        except GithubException as e:
            return {"error": str(e)}

    def update_file(self, path: str, message: str, content: str, branch: str = "main") -> Dict[str, Any]:
        """Update an existing file in the repository."""
        try:
            current_file = self.repo.get_contents(path, ref=branch)
            self.repo.update_file(path, message, content, current_file.sha, branch=branch)
            return {"message": f"File {path} updated successfully"}
        except GithubException as e:
            return {"error": str(e)}

    def create_file(self, path: str, message: str, content: str, branch: str = "main") -> Dict[str, Any]:
        """Create a new file in the repository."""
        try:
            self.repo.create_file(path, message, content, branch=branch)
            return {"message": f"File {path} created successfully"}
        except GithubException as e:
            return {"error": str(e)}

    def create_pull_request(self, title: str, body: str, head: str, base: str = "main") -> Dict[str, Any]:
        """Create a new pull request."""
        try:
            pull = self.repo.create_pull(title=title, body=body, head=head, base=base)
            return {"number": pull.number, "html_url": pull.html_url}
        except GithubException as e:
            return {"error": str(e)}

    def update_pull_request(self, number: int, title: str = None, body: str = None, state: str = None) -> Dict[str, Any]:
        """Update an existing pull request."""
        try:
            pull = self.repo.get_pull(number)
            pull.edit(title="title", body=body, state="open")
            return {"message": f"Pull request #{number} updated successfully"}
        except Exception as e:
            return {"error": str(e)}
        
        # except GithubException as e:
        #     return {"error": str(e)}

    def get_pull_requests(self, state: str = "open", head: str = "", base: str = "") -> List[Dict[str, Any]]:
        """Get a list of pull requests."""
        try:
            pulls = self.repo.get_pulls(state=state, head=head, base=base)
            return [{"number": pr.number, "title": pr.title, "html_url": pr.html_url} for pr in pulls]
        except GithubException as e:
            return [{"error": str(e)}]

    def merge_pull_request(self, number: int, commit_message: str = "") -> Dict[str, Any]:
        """Merge a pull request."""
        try:
            pull = self.repo.get_pull(number)
            merge_result = pull.merge(commit_message=commit_message)
            return {"merged": merge_result.merged, "message": merge_result.message}
        except GithubException as e:
            return {"error": str(e)}

    def create_branch(self, branch_name: str, sha: str = None) -> Dict[str, Any]:
        """Create a new branch in the repository."""
        try:
            if sha is None:
                sha = self.repo.get_branch(self.repo.default_branch).commit.sha
            self.repo.create_git_ref(f"refs/heads/{branch_name}", sha)
            return {"message": f"Branch {branch_name} created successfully"}
        except GithubException as e:
            return {"error": str(e)}