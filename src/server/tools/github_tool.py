from typing import Optional

from github import Github


class GithubTool:
    def __init__(self, access_token: str, repo_name: str):
        if access_token is None:
            raise ValueError("Access token cannot be None")
        if repo_name is None:
            raise ValueError("Repository name cannot be None")

        try:
            self.g = Github(access_token)
            self.repo = self.g.get_repo(repo_name)
        except Exception as e:
            print(f"Failed to get repository: {e}")
            self.repo = None

        if self.repo is None:
            raise Exception(f"Could not access repository {repo_name} with provided token.")
            print(f"Could not access repository {repo_name} with provided token.")

        print(f"github connected to {self.repo} success")

    async def ls(self, path: str = '') -> list:
        """List the contents of a directory in the repository"""
        return self.repo.ls(path)

    async def get_readme(self, path: str = '') -> Optional[str]:
        """Get the README file of the repository"""
        return self.repo.get_readme(path)

    async def read_file(self, file_path: str) -> Optional[str]:
        """Read the contents of a file in the repository"""
        return self.repo.read_file(file_path)

    async def create_branch(self, branch_name: str) -> str:
        """Create a new branch in the repository"""
        return self.repo.create_branch(branch_name)

    async def commit_file_changes(self, file_path: str, commit_message: str, file_content: str) -> Optional[str]:
        """Commit changes to a file in the repository"""
        return self.repo.commit_file_changes(file_path, commit_message, file_content)

    async def create_pull_request(self, branch_name: str, title: str, body: str = '') -> Optional[str]:
        """Create a pull request in the repository"""
        return self.repo.create_pull_request(branch_name, title, body)

    async def clone(self, path: str) -> Optional[str]:
        """Clone the repository to the specified path"""
        return self.repo.clone(path)
