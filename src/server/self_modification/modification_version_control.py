from typing import Dict, List, Optional, Any
import logging
import asyncio
import json
import os
import re
import uuid
import shutil
import tempfile
from datetime import datetime
from pathlib import Path
import subprocess

# Optional GitPython import - we'll handle missing dependency gracefully
try:
    import git
    GIT_AVAILABLE = True
except ImportError:
    GIT_AVAILABLE = False

logger = logging.getLogger(__name__)

class ModificationVersionControl:
    """Manages version control for code modifications."""
    
    def __init__(self, repository_path: str, config: Optional[Dict[str, Any]] = None):
        """Initialize with repository path and configuration.
        
        Args:
            repository_path: Path to the repository.
            config: Configuration for version control.
                   If None, default configuration will be used.
        """
        self.repository_path = repository_path
        self.config = config or {
            "auto_commit": True,
            "backup_before_changes": True,
            "modification_branch_prefix": "cerebrum-mod-",
            "main_branch": "main",  # or master
            "require_approval": True,
            "commit_message_template": "Cerebrum: {goal}\n\n{details}"
        }
        
        # Check if repository exists and is a git repository
        if not GIT_AVAILABLE:
            logger.warning("GitPython is not installed. Git operations will be simulated.")
        
        # Verify repository exists
        if not os.path.exists(repository_path):
            raise ValueError(f"Repository path does not exist: {repository_path}")
        
        # Initialize git repository if available
        self.repo = None
        if GIT_AVAILABLE:
            try:
                self.repo = git.Repo(repository_path)
                logger.info(f"Git repository initialized at {repository_path}")
            except git.InvalidGitRepositoryError:
                logger.warning(f"{repository_path} is not a valid git repository.")
                self.repo = None
    
    async def create_branch(self, branch_name: str, base_branch: Optional[str] = None) -> Dict[str, Any]:
        """Create a new branch for a modification.
        
        Args:
            branch_name: Name of the branch to create.
            base_branch: Branch to base the new branch on. If None, use main_branch from config.
            
        Returns:
            Result of branch creation.
        """
        if not branch_name:
            branch_name = f"{self.config['modification_branch_prefix']}{uuid.uuid4().hex[:8]}"
        
        if not base_branch:
            base_branch = self.config.get("main_branch", "main")
        
        logger.info(f"Creating branch {branch_name} based on {base_branch}")
        
        if GIT_AVAILABLE and self.repo:
            try:
                # Checkout base branch
                self.repo.git.checkout(base_branch)
                
                # Create new branch
                self.repo.git.checkout('-b', branch_name)
                
                return {
                    "success": True,
                    "branch": branch_name,
                    "base_branch": base_branch,
                    "message": f"Created branch {branch_name} based on {base_branch}"
                }
            except git.GitCommandError as e:
                logger.error(f"Git error creating branch: {str(e)}")
                return {
                    "success": False,
                    "branch": branch_name,
                    "error": str(e),
                    "message": f"Failed to create branch {branch_name}"
                }
        else:
            # Simulate branch creation
            branch_file = os.path.join(self.repository_path, ".cerebrum_current_branch")
            try:
                with open(branch_file, 'w') as f:
                    f.write(branch_name)
                
                return {
                    "success": True,
                    "branch": branch_name,
                    "base_branch": base_branch,
                    "message": f"Simulated branch creation: {branch_name} (git not available)",
                    "simulated": True
                }
            except Exception as e:
                logger.error(f"Error simulating branch creation: {str(e)}")
                return {
                    "success": False,
                    "branch": branch_name,
                    "error": str(e),
                    "message": f"Failed to simulate branch creation",
                    "simulated": True
                }
    
    async def commit_changes(self, 
                           files: List[str], 
                           commit_message: str, 
                           author: Optional[str] = None) -> Dict[str, Any]:
        """Commit changes to the repository.
        
        Args:
            files: List of files to commit.
            commit_message: Commit message.
            author: Author of the commit.
            
        Returns:
            Result of commit operation.
        """
        logger.info(f"Committing changes to {len(files)} files")
        
        # Verify files exist
        non_existent_files = [f for f in files if not os.path.exists(os.path.join(self.repository_path, f))]
        if non_existent_files:
            return {
                "success": False,
                "error": f"Files do not exist: {', '.join(non_existent_files)}",
                "message": "Failed to commit changes: some files do not exist"
            }
        
        if GIT_AVAILABLE and self.repo:
            try:
                # Add files
                for file_path in files:
                    full_path = os.path.join(self.repository_path, file_path)
                    self.repo.git.add(full_path)
                
                # Commit
                commit_args = {}
                if author:
                    commit_args["author"] = author
                
                commit = self.repo.git.commit(m=commit_message, **commit_args)
                commit_hash = self.repo.git.rev_parse("HEAD")
                
                return {
                    "success": True,
                    "commit_hash": commit_hash,
                    "message": f"Committed changes with message: {commit_message}",
                    "files": files
                }
            except git.GitCommandError as e:
                logger.error(f"Git error committing changes: {str(e)}")
                return {
                    "success": False,
                    "error": str(e),
                    "message": "Failed to commit changes"
                }
        else:
            # Simulate commit
            commit_hash = uuid.uuid4().hex
            commit_file = os.path.join(self.repository_path, ".cerebrum_commits")
            try:
                commit_data = {
                    "hash": commit_hash,
                    "message": commit_message,
                    "author": author or "system",
                    "files": files,
                    "timestamp": datetime.now().isoformat()
                }
                
                # Append to commit log
                if os.path.exists(commit_file):
                    with open(commit_file, 'r') as f:
                        try:
                            commits = json.load(f)
                        except json.JSONDecodeError:
                            commits = []
                else:
                    commits = []
                
                commits.append(commit_data)
                
                with open(commit_file, 'w') as f:
                    json.dump(commits, f, indent=2)
                
                return {
                    "success": True,
                    "commit_hash": commit_hash,
                    "message": f"Simulated commit: {commit_message} (git not available)",
                    "files": files,
                    "simulated": True
                }
            except Exception as e:
                logger.error(f"Error simulating commit: {str(e)}")
                return {
                    "success": False,
                    "error": str(e),
                    "message": "Failed to simulate commit",
                    "simulated": True
                }
    
    async def merge_branch(self, 
                          source_branch: str, 
                          target_branch: Optional[str] = None,
                          commit_message: Optional[str] = None) -> Dict[str, Any]:
        """Merge a branch into another branch.
        
        Args:
            source_branch: Branch to merge from.
            target_branch: Branch to merge into. If None, use main_branch from config.
            commit_message: Commit message for the merge.
            
        Returns:
            Result of merge operation.
        """
        if not target_branch:
            target_branch = self.config.get("main_branch", "main")
        
        if not commit_message:
            commit_message = f"Merge branch '{source_branch}' into {target_branch}"
        
        logger.info(f"Merging branch {source_branch} into {target_branch}")
        
        if GIT_AVAILABLE and self.repo:
            try:
                # Backup target branch
                if self.config.get("backup_before_changes", True):
                    backup_branch = f"{target_branch}-backup-{datetime.now().strftime('%Y%m%d%H%M%S')}"
                    current_branch = self.repo.active_branch.name
                    self.repo.git.checkout(target_branch)
                    self.repo.git.branch(backup_branch)
                    logger.info(f"Created backup branch {backup_branch}")
                    
                    # Return to original branch
                    self.repo.git.checkout(current_branch)
                
                # Checkout target branch
                self.repo.git.checkout(target_branch)
                
                # Merge source branch
                self.repo.git.merge(source_branch, m=commit_message)
                
                return {
                    "success": True,
                    "source_branch": source_branch,
                    "target_branch": target_branch,
                    "message": f"Merged {source_branch} into {target_branch}",
                    "backup_branch": backup_branch if self.config.get("backup_before_changes", True) else None
                }
            except git.GitCommandError as e:
                logger.error(f"Git error merging branches: {str(e)}")
                
                # Try to abort merge if it failed
                try:
                    self.repo.git.merge("--abort")
                except:
                    pass
                
                return {
                    "success": False,
                    "error": str(e),
                    "message": f"Failed to merge {source_branch} into {target_branch}"
                }
        else:
            # Simulate merge
            merge_file = os.path.join(self.repository_path, ".cerebrum_merges")
            try:
                merge_data = {
                    "source_branch": source_branch,
                    "target_branch": target_branch,
                    "message": commit_message,
                    "timestamp": datetime.now().isoformat()
                }
                
                # Append to merge log
                if os.path.exists(merge_file):
                    with open(merge_file, 'r') as f:
                        try:
                            merges = json.load(f)
                        except json.JSONDecodeError:
                            merges = []
                else:
                    merges = []
                
                merges.append(merge_data)
                
                with open(merge_file, 'w') as f:
                    json.dump(merges, f, indent=2)
                
                # Also update current branch file
                branch_file = os.path.join(self.repository_path, ".cerebrum_current_branch")
                with open(branch_file, 'w') as f:
                    f.write(target_branch)
                
                return {
                    "success": True,
                    "source_branch": source_branch,
                    "target_branch": target_branch,
                    "message": f"Simulated merge: {source_branch} into {target_branch} (git not available)",
                    "simulated": True
                }
            except Exception as e:
                logger.error(f"Error simulating merge: {str(e)}")
                return {
                    "success": False,
                    "error": str(e),
                    "message": "Failed to simulate merge",
                    "simulated": True
                }
    
    async def revert_changes(self, 
                           file_path: str, 
                           revision: Optional[str] = None) -> Dict[str, Any]:
        """Revert changes to a file.
        
        Args:
            file_path: Path to the file to revert.
            revision: Revision to revert to. If None, revert to last commit.
            
        Returns:
            Result of revert operation.
        """
        logger.info(f"Reverting changes to {file_path}")
        
        full_path = os.path.join(self.repository_path, file_path)
        if not os.path.exists(full_path):
            return {
                "success": False,
                "error": f"File does not exist: {file_path}",
                "message": "Failed to revert changes: file does not exist"
            }
        
        if GIT_AVAILABLE and self.repo:
            try:
                if revision:
                    # Checkout specific revision of the file
                    self.repo.git.checkout(revision, "--", file_path)
                else:
                    # Discard changes to the file
                    self.repo.git.checkout("--", file_path)
                
                return {
                    "success": True,
                    "file": file_path,
                    "revision": revision,
                    "message": f"Reverted changes to {file_path}"
                }
            except git.GitCommandError as e:
                logger.error(f"Git error reverting changes: {str(e)}")
                return {
                    "success": False,
                    "error": str(e),
                    "message": f"Failed to revert changes to {file_path}"
                }
        else:
            # Simulate revert
            backup_dir = os.path.join(self.repository_path, ".cerebrum_backups")
            os.makedirs(backup_dir, exist_ok=True)
            
            backup_files = [f for f in os.listdir(backup_dir) if f.startswith(os.path.basename(file_path) + ".")]
            if not backup_files:
                return {
                    "success": False,
                    "error": "No backup found for file",
                    "message": f"Failed to simulate revert: no backup found for {file_path}",
                    "simulated": True
                }
            
            # Sort by timestamp (newest first)
            backup_files.sort(reverse=True)
            backup_file = os.path.join(backup_dir, backup_files[0])
            
            try:
                shutil.copy2(backup_file, full_path)
                
                return {
                    "success": True,
                    "file": file_path,
                    "backup": backup_file,
                    "message": f"Simulated revert: restored {file_path} from backup (git not available)",
                    "simulated": True
                }
            except Exception as e:
                logger.error(f"Error simulating revert: {str(e)}")
                return {
                    "success": False,
                    "error": str(e),
                    "message": "Failed to simulate revert",
                    "simulated": True
                }
    
    async def get_file_history(self, file_path: str, max_entries: int = 10) -> Dict[str, Any]:
        """Get the history of changes to a file.
        
        Args:
            file_path: Path to the file.
            max_entries: Maximum number of history entries to return.
            
        Returns:
            History of changes to the file.
        """
        logger.info(f"Getting history for {file_path}")
        
        full_path = os.path.join(self.repository_path, file_path)
        if not os.path.exists(full_path):
            return {
                "success": False,
                "error": f"File does not exist: {file_path}",
                "message": "Failed to get history: file does not exist"
            }
        
        if GIT_AVAILABLE and self.repo:
            try:
                # Get commit history for the file
                logs = self.repo.git.log(f"--pretty=format:%H|%an|%ad|%s", "--date=iso", "-n", str(max_entries), "--", file_path)
                
                history = []
                for log in logs.splitlines():
                    parts = log.split("|", 3)
                    if len(parts) >= 4:
                        commit_hash, author, date, message = parts
                        history.append({
                            "hash": commit_hash,
                            "author": author,
                            "date": date,
                            "message": message
                        })
                
                return {
                    "success": True,
                    "file": file_path,
                    "history": history
                }
            except git.GitCommandError as e:
                logger.error(f"Git error getting file history: {str(e)}")
                return {
                    "success": False,
                    "error": str(e),
                    "message": f"Failed to get history for {file_path}"
                }
        else:
            # Simulate getting history
            commit_file = os.path.join(self.repository_path, ".cerebrum_commits")
            if os.path.exists(commit_file):
                try:
                    with open(commit_file, 'r') as f:
                        all_commits = json.load(f)
                    
                    # Filter commits for this file
                    file_commits = []
                    for commit in all_commits:
                        if file_path in commit.get("files", []):
                            file_commits.append({
                                "hash": commit.get("hash"),
                                "author": commit.get("author"),
                                "date": commit.get("timestamp"),
                                "message": commit.get("message")
                            })
                    
                    # Limit to max_entries
                    file_commits = file_commits[:max_entries]
                    
                    return {
                        "success": True,
                        "file": file_path,
                        "history": file_commits,
                        "simulated": True
                    }
                except Exception as e:
                    logger.error(f"Error simulating get history: {str(e)}")
            
            return {
                "success": False,
                "error": "No commit history available",
                "message": f"Failed to simulate getting history for {file_path}",
                "simulated": True
            }
    
    async def create_diff(self, 
                        file_path: str, 
                        old_revision: Optional[str] = None,
                        new_revision: str = "HEAD") -> Dict[str, Any]:
        """Create a diff between two revisions of a file.
        
        Args:
            file_path: Path to the file.
            old_revision: Old revision to compare against. If None, compare against HEAD~1.
            new_revision: New revision to compare. Default is HEAD.
            
        Returns:
            Diff between the two revisions.
        """
        logger.info(f"Creating diff for {file_path}")
        
        full_path = os.path.join(self.repository_path, file_path)
        if not os.path.exists(full_path):
            return {
                "success": False,
                "error": f"File does not exist: {file_path}",
                "message": "Failed to create diff: file does not exist"
            }
        
        if GIT_AVAILABLE and self.repo:
            try:
                if not old_revision:
                    old_revision = "HEAD~1"
                
                # Create diff
                diff = self.repo.git.diff(old_revision, new_revision, "--", file_path)
                
                return {
                    "success": True,
                    "file": file_path,
                    "old_revision": old_revision,
                    "new_revision": new_revision,
                    "diff": diff
                }
            except git.GitCommandError as e:
                logger.error(f"Git error creating diff: {str(e)}")
                return {
                    "success": False,
                    "error": str(e),
                    "message": f"Failed to create diff for {file_path}"
                }
        else:
            # Simulate diff
            backup_dir = os.path.join(self.repository_path, ".cerebrum_backups")
            backup_file = os.path.join(backup_dir, os.path.basename(file_path) + f".{datetime.now().strftime('%Y%m%d%H%M%S')}")
            
            # First, make a backup of the current file
            os.makedirs(backup_dir, exist_ok=True)
            shutil.copy2(full_path, backup_file)
            
            # Find older backup to diff against
            backup_files = [f for f in os.listdir(backup_dir) if f.startswith(os.path.basename(file_path) + ".")]
            if len(backup_files) < 2:
                return {
                    "success": False,
                    "error": "No previous version to diff against",
                    "message": f"Failed to simulate diff: no previous version found for {file_path}",
                    "simulated": True
                }
            
            # Sort by timestamp (oldest first)
            backup_files.sort()
            old_backup_file = os.path.join(backup_dir, backup_files[0])
            
            try:
                # Try to use 'diff' command if available
                try:
                    result = subprocess.run(
                        ["diff", old_backup_file, full_path],
                        capture_output=True, text=True, check=False
                    )
                    diff_text = result.stdout
                except:
                    # Basic diff implementation if command not available
                    with open(old_backup_file, 'r') as f:
                        old_lines = f.readlines()
                    
                    with open(full_path, 'r') as f:
                        new_lines = f.readlines()
                    
                    diff_text = f"--- {old_backup_file}\n+++ {full_path}\n"
                    for i, (old, new) in enumerate(zip(old_lines, new_lines)):
                        if old != new:
                            diff_text += f"@@ line {i+1} @@\n-{old}+{new}"
                    
                    # Handle different lengths
                    if len(old_lines) < len(new_lines):
                        for i, line in enumerate(new_lines[len(old_lines):], start=len(old_lines)):
                            diff_text += f"@@ line {i+1} @@\n+{line}"
                    elif len(old_lines) > len(new_lines):
                        for i, line in enumerate(old_lines[len(new_lines):], start=len(new_lines)):
                            diff_text += f"@@ line {i+1} @@\n-{line}"
                
                return {
                    "success": True,
                    "file": file_path,
                    "old_version": os.path.basename(old_backup_file),
                    "new_version": "current",
                    "diff": diff_text,
                    "simulated": True
                }
            except Exception as e:
                logger.error(f"Error simulating diff: {str(e)}")
                return {
                    "success": False,
                    "error": str(e),
                    "message": "Failed to simulate diff",
                    "simulated": True
                }
    
    async def backup_file(self, file_path: str) -> Dict[str, Any]:
        """Create a backup of a file.
        
        Args:
            file_path: Path to the file to backup.
            
        Returns:
            Result of backup operation.
        """
        logger.info(f"Creating backup of {file_path}")
        
        full_path = os.path.join(self.repository_path, file_path)
        if not os.path.exists(full_path):
            return {
                "success": False,
                "error": f"File does not exist: {file_path}",
                "message": "Failed to create backup: file does not exist"
            }
        
        try:
            # Create backup directory
            backup_dir = os.path.join(self.repository_path, ".cerebrum_backups")
            os.makedirs(backup_dir, exist_ok=True)
            
            # Create backup file with timestamp
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            backup_file = os.path.join(backup_dir, f"{os.path.basename(file_path)}.{timestamp}")
            
            # Copy file
            shutil.copy2(full_path, backup_file)
            
            return {
                "success": True,
                "file": file_path,
                "backup": backup_file,
                "timestamp": timestamp,
                "message": f"Created backup of {file_path}"
            }
        except Exception as e:
            logger.error(f"Error creating backup: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "message": f"Failed to create backup of {file_path}"
            }
    
    async def restore_backup(self, file_path: str, timestamp: Optional[str] = None) -> Dict[str, Any]:
        """Restore a file from backup.
        
        Args:
            file_path: Path to the file to restore.
            timestamp: Timestamp of the backup to restore. If None, restore the latest backup.
            
        Returns:
            Result of restore operation.
        """
        logger.info(f"Restoring backup of {file_path}")
        
        full_path = os.path.join(self.repository_path, file_path)
        backup_dir = os.path.join(self.repository_path, ".cerebrum_backups")
        
        if not os.path.exists(backup_dir):
            return {
                "success": False,
                "error": "No backups available",
                "message": "Failed to restore backup: no backups available"
            }
        
        try:
            # Find backup file
            if timestamp:
                backup_file = os.path.join(backup_dir, f"{os.path.basename(file_path)}.{timestamp}")
                if not os.path.exists(backup_file):
                    return {
                        "success": False,
                        "error": f"Backup with timestamp {timestamp} not found",
                        "message": "Failed to restore backup: backup not found"
                    }
            else:
                # Find latest backup
                backup_files = [f for f in os.listdir(backup_dir) if f.startswith(os.path.basename(file_path) + ".")]
                if not backup_files:
                    return {
                        "success": False,
                        "error": f"No backups found for {file_path}",
                        "message": "Failed to restore backup: no backups found"
                    }
                
                # Sort by timestamp (newest first)
                backup_files.sort(reverse=True)
                backup_file = os.path.join(backup_dir, backup_files[0])
            
            # Create parent directory if it doesn't exist
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            
            # Copy backup to original file
            shutil.copy2(backup_file, full_path)
            
            return {
                "success": True,
                "file": file_path,
                "backup": backup_file,
                "message": f"Restored {file_path} from backup"
            }
        except Exception as e:
            logger.error(f"Error restoring backup: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "message": f"Failed to restore backup of {file_path}"
            }
    
    async def handle_modification(self, modification, modification_goal: str) -> Dict[str, Any]:
        """Handle a code modification from start to finish with version control.
        
        This is a high-level method that orchestrates the complete modification workflow,
        including branch creation, file backup, committing changes, and merging.
        
        Args:
            modification: CodeModification instance.
            modification_goal: Goal of the modification.
            
        Returns:
            Result of the modification process.
        """
        logger.info(f"Handling modification for {modification.target_component}")
        
        try:
            # 1. Create a modification branch
            branch_name = f"{self.config.get('modification_branch_prefix', 'cerebrum-mod-')}{uuid.uuid4().hex[:8]}"
            branch_result = await self.create_branch(branch_name)
            if not branch_result.get("success", False):
                return {
                    "success": False,
                    "error": branch_result.get("error", "Unknown error"),
                    "message": "Failed to create modification branch",
                    "stage": "branch_creation"
                }
            
            # 2. Backup the file
            if self.config.get("backup_before_changes", True):
                backup_result = await self.backup_file(modification.target_component)
                if not backup_result.get("success", False):
                    logger.warning(f"Failed to create backup of {modification.target_component}: {backup_result.get('error')}")
            
            # 3. Apply the modification
            # This is assumed to be done externally
            
            # 4. Commit the changes
            commit_message = self.config.get("commit_message_template", "Cerebrum: {goal}\n\n{details}").format(
                goal=modification_goal,
                details=f"Modified {modification.target_component}"
            )
            
            commit_result = await self.commit_changes(
                [modification.target_component],
                commit_message,
                modification.author
            )
            
            if not commit_result.get("success", False):
                return {
                    "success": False,
                    "error": commit_result.get("error", "Unknown error"),
                    "message": "Failed to commit changes",
                    "stage": "commit",
                    "branch": branch_name
                }
            
            # 5. Merge if auto-commit is enabled and no approval is required
            merge_result = {"success": False, "skipped": True, "message": "Merge skipped"}
            if self.config.get("auto_commit", True) and not self.config.get("require_approval", True):
                merge_result = await self.merge_branch(
                    branch_name,
                    self.config.get("main_branch", "main"),
                    f"Merge modification: {modification_goal}"
                )
            
            return {
                "success": True,
                "branch": branch_name,
                "commit": commit_result.get("commit_hash"),
                "merge": merge_result.get("success", False),
                "file": modification.target_component,
                "message": "Successfully handled modification",
                "backup": backup_result.get("backup") if self.config.get("backup_before_changes", True) else None,
                "details": {
                    "branch_result": branch_result,
                    "commit_result": commit_result,
                    "merge_result": merge_result if not merge_result.get("skipped", True) else None
                }
            }
        except Exception as e:
            logger.error(f"Error handling modification: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to handle modification",
                "stage": "unknown"
            } 