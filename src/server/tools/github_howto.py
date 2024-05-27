ghr = GithubRepo(access_token="YOUR_ACCESS_TOKEN", repo_name="username/repository")

# List files in the root directory
files = ghr.ls()
print(files)

# Get the README content
readme = ghr.get_readme()
print(readme)

# Read a file
file_content = ghr.read_file("path/to/file.txt")
print(file_content)

# Create a new branch
branch_ref = ghr.create_branch("new-branch")
print(branch_ref)

# Commit file changes
commit_sha = ghr.commit_file_changes("path/to/file.txt", "Update file", "New file content")
print(commit_sha)

# Create a pull request
pr_url = ghr.create_pull_request("new-branch", "Pull Request Title", "Pull Request Body")
print(pr_url)