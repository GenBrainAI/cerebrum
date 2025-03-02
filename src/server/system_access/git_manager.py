from typing import Dict, List, Optional, Any, Tuple
import asyncio
import logging
import os
import re
import shutil
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

class GitManager:
    """Manages Git repository operations."""
    
    def __init__(self, security_config: Optional[Dict[str, Any]] = None):
        """
        Initialize with security configuration.
        
        Args:
            security_config: Dictionary with security settings
                - allowed_domains: List of allowed Git domains
                - blocked_domains: List of blocked Git domains
                - require_approval: Whether to require approval for all operations
                - max_repo_size_mb: Maximum repository size in MB
        """
        self.security_config = security_config or {
            "allowed_domains": ["github.com", "gitlab.com", "bitbucket.org"],
            "blocked_domains": [],
            "require_approval": True,
            "max_repo_size_mb": 500
        }
        
        # Track current repository
        self.current_repo_path = None
        self.current_repo_url = None
    
    async def clone_repository(self, url: str, path: Optional[str] = None, 
                              branch: Optional[str] = None, requires_approval: bool = True) -> Dict[str, Any]:
        """
        Clone a Git repository.
        
        Args:
            url: Repository URL
            path: Local path to clone to
            branch: Branch to checkout
            requires_approval: Whether this operation requires approval
            
        Returns:
            Dictionary with clone result information
        """
        # Check security constraints
        security_check = self._check_repo_security(url)
        if not security_check["is_safe"]:
            return {
                "success": False,
                "message": f"Repository {url} failed security check: {security_check['reason']}",
                "details": security_check
            }
        
        # Determine path
        if not path:
            # Extract repo name from URL
            repo_name = url.split("/")[-1]
            if repo_name.endswith(".git"):
                repo_name = repo_name[:-4]
            path = os.path.join(os.getcwd(), repo_name)
        
        # Build the git command
        cmd = ["git", "clone"]
        
        if branch:
            cmd.extend(["-b", branch])
        
        cmd.extend([url, path])
        
        # Check if we need approval
        if requires_approval and self.security_config.get("require_approval", True):
            return {
                "success": False,
                "message": "Clone operation requires approval",
                "command": " ".join(cmd),
                "url": url,
                "path": path,
                "branch": branch,
                "requires_approval": True
            }
        
        # Execute the git command
        try:
            logger.info(f"Cloning repository: {url} to {path}")
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                # Update current repository
                self.current_repo_path = path
                self.current_repo_url = url
                
                # Get repository info
                repo_info = await self.get_repository_status()
                
                return {
                    "success": True,
                    "message": f"Successfully cloned {url} to {path}",
                    "stdout": stdout.decode(),
                    "stderr": stderr.decode(),
                    "path": path,
                    "url": url,
                    "branch": branch or repo_info.get("current_branch"),
                    "repo_info": repo_info
                }
            else:
                return {
                    "success": False,
                    "message": f"Failed to clone {url}",
                    "stdout": stdout.decode(),
                    "stderr": stderr.decode(),
                    "path": path,
                    "url": url,
                    "returncode": process.returncode
                }
        except Exception as e:
            logger.exception(f"Error cloning repository {url}: {e}")
            return {
                "success": False,
                "message": f"Error cloning {url}: {str(e)}",
                "url": url,
                "path": path,
                "error": str(e)
            }
    
    async def commit_changes(self, message: str, files: Optional[List[str]] = None, 
                            requires_approval: bool = True) -> Dict[str, Any]:
        """
        Commit changes to the repository.
        
        Args:
            message: Commit message
            files: List of files to commit, or None for all changes
            requires_approval: Whether this operation requires approval
            
        Returns:
            Dictionary with commit result information
        """
        # Check if we have a current repository
        if not self.current_repo_path:
            return {
                "success": False,
                "message": "No repository is currently active"
            }
        
        # Build the git command for staging
        if files:
            stage_cmd = ["git", "add"] + files
        else:
            stage_cmd = ["git", "add", "."]
        
        # Build the git command for committing
        commit_cmd = ["git", "commit", "-m", message]
        
        # Check if we need approval
        if requires_approval and self.security_config.get("require_approval", True):
            return {
                "success": False,
                "message": "Commit operation requires approval",
                "stage_command": " ".join(stage_cmd),
                "commit_command": " ".join(commit_cmd),
                "message": message,
                "files": files,
                "requires_approval": True
            }
        
        # Execute the git commands
        try:
            logger.info(f"Committing changes to repository at {self.current_repo_path}")
            
            # Change to repository directory
            cwd = os.getcwd()
            os.chdir(self.current_repo_path)
            
            # Stage changes
            stage_process = await asyncio.create_subprocess_exec(
                *stage_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stage_stdout, stage_stderr = await stage_process.communicate()
            
            if stage_process.returncode != 0:
                os.chdir(cwd)
                return {
                    "success": False,
                    "message": "Failed to stage changes",
                    "stdout": stage_stdout.decode(),
                    "stderr": stage_stderr.decode(),
                    "returncode": stage_process.returncode
                }
            
            # Commit changes
            commit_process = await asyncio.create_subprocess_exec(
                *commit_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            commit_stdout, commit_stderr = await commit_process.communicate()
            
            # Change back to original directory
            os.chdir(cwd)
            
            if commit_process.returncode == 0:
                return {
                    "success": True,
                    "message": f"Successfully committed changes with message: {message}",
                    "stdout": commit_stdout.decode(),
                    "stderr": commit_stderr.decode(),
                    "message": message,
                    "files": files
                }
            else:
                return {
                    "success": False,
                    "message": "Failed to commit changes",
                    "stdout": commit_stdout.decode(),
                    "stderr": commit_stderr.decode(),
                    "returncode": commit_process.returncode
                }
        except Exception as e:
            # Make sure we change back to the original directory
            try:
                os.chdir(cwd)
            except:
                pass
                
            logger.exception(f"Error committing changes: {e}")
            return {
                "success": False,
                "message": f"Error committing changes: {str(e)}",
                "error": str(e)
            }
    
    async def push_changes(self, remote: str = "origin", branch: Optional[str] = None, 
                          requires_approval: bool = True) -> Dict[str, Any]:
        """
        Push committed changes to a remote repository.
        
        Args:
            remote: Remote name
            branch: Branch to push to, or None for current branch
            requires_approval: Whether this operation requires approval
            
        Returns:
            Dictionary with push result information
        """
        # Check if we have a current repository
        if not self.current_repo_path:
            return {
                "success": False,
                "message": "No repository is currently active"
            }
        
        # Get current branch if not specified
        if not branch:
            repo_info = await self.get_repository_status()
            branch = repo_info.get("current_branch")
            
            if not branch:
                return {
                    "success": False,
                    "message": "Could not determine current branch"
                }
        
        # Build the git command
        cmd = ["git", "push", remote, branch]
        
        # Check if we need approval
        if requires_approval and self.security_config.get("require_approval", True):
            return {
                "success": False,
                "message": "Push operation requires approval",
                "command": " ".join(cmd),
                "remote": remote,
                "branch": branch,
                "requires_approval": True
            }
        
        # Execute the git command
        try:
            logger.info(f"Pushing changes to {remote}/{branch}")
            
            # Change to repository directory
            cwd = os.getcwd()
            os.chdir(self.current_repo_path)
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            
            # Change back to original directory
            os.chdir(cwd)
            
            if process.returncode == 0:
                return {
                    "success": True,
                    "message": f"Successfully pushed changes to {remote}/{branch}",
                    "stdout": stdout.decode(),
                    "stderr": stderr.decode(),
                    "remote": remote,
                    "branch": branch
                }
            else:
                return {
                    "success": False,
                    "message": f"Failed to push changes to {remote}/{branch}",
                    "stdout": stdout.decode(),
                    "stderr": stderr.decode(),
                    "remote": remote,
                    "branch": branch,
                    "returncode": process.returncode
                }
        except Exception as e:
            # Make sure we change back to the original directory
            try:
                os.chdir(cwd)
            except:
                pass
                
            logger.exception(f"Error pushing changes: {e}")
            return {
                "success": False,
                "message": f"Error pushing changes: {str(e)}",
                "remote": remote,
                "branch": branch,
                "error": str(e)
            }
    
    async def pull_changes(self, remote: str = "origin", branch: Optional[str] = None) -> Dict[str, Any]:
        """
        Pull changes from a remote repository.
        
        Args:
            remote: Remote name
            branch: Branch to pull from, or None for current branch
            
        Returns:
            Dictionary with pull result information
        """
        # Check if we have a current repository
        if not self.current_repo_path:
            return {
                "success": False,
                "message": "No repository is currently active"
            }
        
        # Get current branch if not specified
        if not branch:
            repo_info = await self.get_repository_status()
            branch = repo_info.get("current_branch")
            
            if not branch:
                return {
                    "success": False,
                    "message": "Could not determine current branch"
                }
        
        # Build the git command
        cmd = ["git", "pull", remote, branch]
        
        # Execute the git command
        try:
            logger.info(f"Pulling changes from {remote}/{branch}")
            
            # Change to repository directory
            cwd = os.getcwd()
            os.chdir(self.current_repo_path)
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            
            # Change back to original directory
            os.chdir(cwd)
            
            if process.returncode == 0:
                return {
                    "success": True,
                    "message": f"Successfully pulled changes from {remote}/{branch}",
                    "stdout": stdout.decode(),
                    "stderr": stderr.decode(),
                    "remote": remote,
                    "branch": branch
                }
            else:
                return {
                    "success": False,
                    "message": f"Failed to pull changes from {remote}/{branch}",
                    "stdout": stdout.decode(),
                    "stderr": stderr.decode(),
                    "remote": remote,
                    "branch": branch,
                    "returncode": process.returncode
                }
        except Exception as e:
            # Make sure we change back to the original directory
            try:
                os.chdir(cwd)
            except:
                pass
                
            logger.exception(f"Error pulling changes: {e}")
            return {
                "success": False,
                "message": f"Error pulling changes: {str(e)}",
                "remote": remote,
                "branch": branch,
                "error": str(e)
            }
    
    async def create_branch(self, branch_name: str, base_branch: Optional[str] = None) -> Dict[str, Any]:
        """
        Create a new branch.
        
        Args:
            branch_name: Name of the new branch
            base_branch: Branch to base the new branch on, or None for current branch
            
        Returns:
            Dictionary with branch creation result information
        """
        # Check if we have a current repository
        if not self.current_repo_path:
            return {
                "success": False,
                "message": "No repository is currently active"
            }
        
        # Build the git command
        if base_branch:
            cmd = ["git", "checkout", "-b", branch_name, base_branch]
        else:
            cmd = ["git", "checkout", "-b", branch_name]
        
        # Execute the git command
        try:
            logger.info(f"Creating branch {branch_name}")
            
            # Change to repository directory
            cwd = os.getcwd()
            os.chdir(self.current_repo_path)
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            
            # Change back to original directory
            os.chdir(cwd)
            
            if process.returncode == 0:
                return {
                    "success": True,
                    "message": f"Successfully created branch {branch_name}",
                    "stdout": stdout.decode(),
                    "stderr": stderr.decode(),
                    "branch": branch_name,
                    "base_branch": base_branch
                }
            else:
                return {
                    "success": False,
                    "message": f"Failed to create branch {branch_name}",
                    "stdout": stdout.decode(),
                    "stderr": stderr.decode(),
                    "branch": branch_name,
                    "base_branch": base_branch,
                    "returncode": process.returncode
                }
        except Exception as e:
            # Make sure we change back to the original directory
            try:
                os.chdir(cwd)
            except:
                pass
                
            logger.exception(f"Error creating branch: {e}")
            return {
                "success": False,
                "message": f"Error creating branch: {str(e)}",
                "branch": branch_name,
                "base_branch": base_branch,
                "error": str(e)
            }
    
    async def get_repository_status(self) -> Dict[str, Any]:
        """
        Get the current status of the repository.
        
        Returns:
            Dictionary with repository status information
        """
        # Check if we have a current repository
        if not self.current_repo_path:
            return {
                "success": False,
                "message": "No repository is currently active"
            }
        
        try:
            logger.info(f"Getting repository status for {self.current_repo_path}")
            
            # Change to repository directory
            cwd = os.getcwd()
            os.chdir(self.current_repo_path)
            
            # Get current branch
            branch_cmd = ["git", "rev-parse", "--abbrev-ref", "HEAD"]
            branch_process = await asyncio.create_subprocess_exec(
                *branch_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            branch_stdout, _ = await branch_process.communicate()
            current_branch = branch_stdout.decode().strip() if branch_process.returncode == 0 else None
            
            # Get status
            status_cmd = ["git", "status", "--porcelain"]
            status_process = await asyncio.create_subprocess_exec(
                *status_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            status_stdout, _ = await status_process.communicate()
            status_output = status_stdout.decode()
            
            # Parse status output
            modified_files = []
            untracked_files = []
            staged_files = []
            
            for line in status_output.split("\n"):
                if not line.strip():
                    continue
                    
                status = line[:2]
                file_path = line[3:].strip()
                
                if status.startswith("M"):
                    modified_files.append(file_path)
                elif status.startswith("A"):
                    staged_files.append(file_path)
                elif status.startswith("??"):
                    untracked_files.append(file_path)
                elif status.startswith(" M"):
                    modified_files.append(file_path)
            
            # Get remote URL
            remote_cmd = ["git", "remote", "get-url", "origin"]
            remote_process = await asyncio.create_subprocess_exec(
                *remote_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            remote_stdout, _ = await remote_process.communicate()
            remote_url = remote_stdout.decode().strip() if remote_process.returncode == 0 else None
            
            # Get last commit
            commit_cmd = ["git", "log", "-1", "--pretty=format:%H|%an|%ae|%ad|%s"]
            commit_process = await asyncio.create_subprocess_exec(
                *commit_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            commit_stdout, _ = await commit_process.communicate()
            
            last_commit = {}
            if commit_process.returncode == 0:
                commit_parts = commit_stdout.decode().strip().split("|")
                if len(commit_parts) >= 5:
                    last_commit = {
                        "hash": commit_parts[0],
                        "author": commit_parts[1],
                        "email": commit_parts[2],
                        "date": commit_parts[3],
                        "message": commit_parts[4]
                    }
            
            # Get branches
            branches_cmd = ["git", "branch"]
            branches_process = await asyncio.create_subprocess_exec(
                *branches_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            branches_stdout, _ = await branches_process.communicate()
            
            branches = []
            if branches_process.returncode == 0:
                for line in branches_stdout.decode().split("\n"):
                    if not line.strip():
                        continue
                    if line.startswith("*"):
                        # Current branch, already captured
                        continue
                    branches.append(line.strip())
            
            # Change back to original directory
            os.chdir(cwd)
            
            return {
                "success": True,
                "path": self.current_repo_path,
                "url": remote_url or self.current_repo_url,
                "current_branch": current_branch,
                "branches": branches,
                "modified_files": modified_files,
                "untracked_files": untracked_files,
                "staged_files": staged_files,
                "has_changes": bool(modified_files or untracked_files or staged_files),
                "last_commit": last_commit
            }
        except Exception as e:
            # Make sure we change back to the original directory
            try:
                os.chdir(cwd)
            except:
                pass
                
            logger.exception(f"Error getting repository status: {e}")
            return {
                "success": False,
                "message": f"Error getting repository status: {str(e)}",
                "error": str(e)
            }
    
    def _check_repo_security(self, url: str) -> Dict[str, Any]:
        """
        Check if a repository URL passes security checks.
        
        Args:
            url: Repository URL
            
        Returns:
            Dictionary with security check results
        """
        # Extract domain from URL
        domain_match = re.search(r"(?:https?://|git@)([^/:]+)", url)
        if not domain_match:
            return {
                "is_safe": False,
                "reason": "Could not extract domain from URL",
                "url": url
            }
        
        domain = domain_match.group(1)
        
        # Check if domain is blocked
        if domain in self.security_config.get("blocked_domains", []):
            return {
                "is_safe": False,
                "reason": f"Domain {domain} is in blocked list",
                "url": url,
                "domain": domain
            }
        
        # Check if domain is allowed
        allowed_domains = self.security_config.get("allowed_domains", [])
        if allowed_domains and domain not in allowed_domains:
            return {
                "is_safe": False,
                "reason": f"Domain {domain} is not in allowed list",
                "url": url,
                "domain": domain,
                "allowed_domains": allowed_domains
            }
        
        return {
            "is_safe": True,
            "url": url,
            "domain": domain
        }
    
    async def set_current_repository(self, path: str) -> Dict[str, Any]:
        """
        Set the current repository path.
        
        Args:
            path: Path to the repository
            
        Returns:
            Dictionary with result information
        """
        # Check if path exists and is a git repository
        git_dir = os.path.join(path, ".git")
        if not os.path.isdir(git_dir):
            return {
                "success": False,
                "message": f"Path {path} is not a git repository",
                "path": path
            }
        
        # Set current repository
        self.current_repo_path = path
        
        # Try to get remote URL
        try:
            repo_info = await self.get_repository_status()
            self.current_repo_url = repo_info.get("url")
        except:
            self.current_repo_url = None
        
        return {
            "success": True,
            "message": f"Set current repository to {path}",
            "path": path,
            "url": self.current_repo_url
        } 