from fastapi.testclient import TestClient
from src.server.controllers.curried_proxy import CurriedProxy
from src.server.tools.github_tool import GithubTool
from datetime import datetime
import os
from dotenv import load_dotenv
from pathlib import Path

async def test_github_tool(client: TestClient):
    # Load environment variables
    env_path = Path(__file__).parents[1] / '.env'
    load_dotenv(dotenv_path=env_path)

    github_token = os.getenv("GITHUB_ACCESS_TOKEN")
    assert github_token is not None, "GITHUB_ACCESS_TOKEN is not set in the environment"

    # Create CurriedProxy and add GithubTool
    curried_proxy = CurriedProxy()
    github_tool = GithubTool(access_token=github_token, repo_name="GenBrainAI/cerebrum")
    curried_proxy.add_tool("github", github_tool)

    # Get tool descriptions (for LLM use)
    tool_descriptions = github_tool.get_tool_descriptions()
    print("Available GitHub tools:", list(tool_descriptions.keys()))

    # Get README content
    readme_content = await curried_proxy.curried_proxy("github")({
        "method": "get_contents",
        "arguments": {"path": "README.md"}
    })
    assert readme_content is not None, "Failed to read README.md"

    # Update README content
    current_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    new_content = readme_content.decoded_content.decode() + f"\n\nHello Github {current_date}"
    
    update_result = await curried_proxy.curried_proxy("github")({
        "method": "update_file",
        "arguments": {
            "path": "README.md",
            "message": f"Update README with timestamp {current_date}",
            "content": new_content,
            "sha": readme_content.sha,
            "branch": "test-branch"
        }
    })
    assert update_result is not None, "Failed to update README.md"

    # Create a pull request
    pr_result = await github_tool.execute("create_pull",
        title=f"Update README with timestamp {current_date}",
        body="This is a test pull request created by the GitHub Tool test.",
        base="main",
        head="test-branch"
    )
    assert pr_result is not None, "Failed to create pull request"

    print(f"Successfully created pull request: {pr_result.number}")

    # Clean up: Close the pull request
    await github_tool.execute("get_pull", number=pr_result.number).edit(state="closed")

    print(f"Successfully closed pull request: {pr_result.number}")

# Run the test
# test_github_tool(TestClient())