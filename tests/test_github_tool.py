# test_github_tool.py

import pytest
from src.server.tools.github_tool import GitHubTool
import os
from datetime import datetime

@pytest.mark.asyncio
async def test_github_tool():
    github_token = os.getenv("GITHUB_ACCESS_TOKEN")
    assert github_token is not None, "GITHUB_ACCESS_TOKEN is not set in the environment"

    github_tool = GitHubTool(access_token=github_token, repo_name="GenBrainAI/cerebrum")

    # Create a new branch
    branch_name = f"test-branch-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    create_branch_result = github_tool.create_branch(branch_name)
    assert "message" in create_branch_result
    assert "created successfully" in create_branch_result["message"]

    # Get README content
    readme_content = github_tool.get_file_contents("README.md")
    assert "content" in readme_content
    assert isinstance(readme_content["content"], str)
    # This part is been commented out as I don't want to update the README file
    # TODO: Uncomment this part and fix the test to change other github repository not Cerebrum.
    # Update README content
    # current_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    # new_content = readme_content["content"] + f"\n\nHello Github {current_date}"
    # update_result = github_tool.update_file(
    #     path="README.md",
    #     message=f"Update README with timestamp {current_date}",
    #     content=new_content,
    #     branch=branch_name
    # )
    # assert "message" in update_result
    # assert "updated successfully" in update_result["message"]

    # # Create a pull request
    # pr_result = github_tool.create_pull_request(
    #     title=f"Update README with timestamp {current_date}",
    #     body="This is a test pull request created by the GitHub Tool test.",
    #     head=branch_name,
    #     base="main"
    # )
    # assert "number" in pr_result
    # pr_number = pr_result["number"]

    # # Update the pull request
    # update_pr_result = github_tool.update_pull_request(
    #     number=pr_number,
    #     title="updated pull request title",
    #     body="Updated pull request body",
    #     state="open"
    # )
    # assert "message" in update_pr_result
    # assert "updated successfully" in update_pr_result["message"]

    # # Get pull requests
    # prs = github_tool.get_pull_requests(head=branch_name, base="main")
    # assert len(prs) > 0
    # assert prs[0]["number"] == pr_number

    # # Merge the pull request
    # merge_result = github_tool.merge_pull_request(pr_number, "Merging test pull request")
    # assert merge_result["merged"] is True

    # print(f"Successfully created, updated, and merged pull request: {pr_number}")