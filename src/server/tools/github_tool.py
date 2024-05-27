
from typing import Optional
from crewai import Tool
from .github import GithubRepo

class GithubTool(Tool):
    def __init__(self, access_token: str, repo_name: str):
        super().__init__(name="GithubTool", description="A tool to interact with GitHub repositories.")
        self.github_repo = GithubRepo(access_token=access_token, repo_name=repo_name)

    async def ls(self, path: str = '') -> list:
        return self.github_repo.ls(path)

    async def get_readme(self, path: str = '') -> Optional[str]:
        return self.github_repo.get_readme(path)

    async def read_file(self, file_path: str) -> Optional[str]:
        return self.github_repo.read_file(file_path)

    async def create_branch(self, branch_name: str) -> str:
        return self.github_repo.create_branch(branch_name)

    async def commit_file_changes(self, file_path: str, commit_message: str, file_content: str) -> Optional[str]:
        return self.github_repo.commit_file_changes(file_path, commit_message, file_content)

    async def create_pull_request(self, branch_name: str, title: str, body: str = '') -> Optional[str]:
        return self.github_repo.create_pull_request(branch_name, title, body)