from github import Github
from pydantic import BaseModel
from fastapi import FastAPI

class GithubRepo(BaseModel):
    access_token: str
    repo_name: str

    def __init__(self, **data):
        super().__init__(**data)
        self.g = Github(self.access_token)
        self.repo = self.g.get_repo(self.repo_name)

    def ls(self, path: str = ''):
        contents = self.repo.get_contents(path)
        return [content.name for content in contents]

    def get_readme(self, path: str = ''):
        try:
            readme = self.repo.get_readme(path)
            return readme.decoded_content.decode()
        except:
            return None

    def read_file(self, file_path: str):
        try:
            file_content = self.repo.get_contents(file_path).decoded_content.decode()
            return file_content
        except:
            return None

    def create_branch(self, branch_name: str):
        source_branch = self.repo.get_branch(self.repo.default_branch)
        ref = self.repo.create_git_ref(f"refs/heads/{branch_name}", source_branch.commit.sha)
        return ref.ref

    def commit_file_changes(self, file_path: str, commit_message: str, file_content: str):
        try:
            contents = self.repo.get_contents(file_path)
            self.repo.update_file(file_path, commit_message, file_content, contents.sha)
            return self.repo.get_commits()[0].sha
        except:
            return None

    def create_pull_request(self, branch_name: str, title: str, body: str = ''):
        try:
            base_branch = self.repo.default_branch
            pull_request = self.repo.create_pull(title=title, body=body, head=branch_name, base=base_branch)
            return pull_request.html_url
        except:
            return None
