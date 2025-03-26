"""Tests for the System Access Layer."""
import os
import pytest
import asyncio
import tempfile
from unittest.mock import patch, MagicMock
from src.server.system_access.core.access_layer import (
    SystemAccessLayer,
    AccessPolicy,
    AccessLevel,
    ResourceType
)

@pytest.fixture
def security_config():
    """Security configuration for testing."""
    temp_dir = tempfile.gettempdir()
    return {
        "sandbox_enabled": True,
        "require_approval": False,
        "max_process_time": 30,  # 30 seconds
        "max_file_size": 1024 * 1024,  # 1MB
        "allowed_packages": ["pytest", "pytest-asyncio", "pytest-cov"],
        "protected_paths": [
            "^/etc/.*",
            "^/usr/.*",
            "^/var/log/.*",
            "^/root/.*"
        ],
        "temp_dir": temp_dir
    }

@pytest.fixture
def access_policies(security_config):
    """Access policies for testing."""
    temp_dir = security_config["temp_dir"]
    return [
        AccessPolicy(
            resource_type=ResourceType.FILE,
            path_pattern=f"^{temp_dir}/.*",
            allowed_levels=[AccessLevel.READ, AccessLevel.WRITE],
            requires_approval=False
        ),
        AccessPolicy(
            resource_type=ResourceType.DIRECTORY,
            path_pattern=f"^{temp_dir}/.*",
            allowed_levels=[AccessLevel.READ, AccessLevel.WRITE],
            requires_approval=False
        ),
        AccessPolicy(
            resource_type=ResourceType.COMMAND,
            path_pattern=r"^(echo|ls|cat|pwd|cd|mkdir|rm\s+(?!-rf\s+/)|cp|mv|git|python|pip|sleep\s+\d+)(?:\s+(?!(/etc|/usr|/var|/root|/private)/).*)?$",
            allowed_levels=[AccessLevel.EXECUTE],
            requires_approval=False
        )
    ]

@pytest.fixture
def system_access(security_config, access_policies):
    """System access layer instance for testing."""
    return SystemAccessLayer(security_config, access_policies)

@pytest.fixture
def temp_workspace():
    """Create a temporary workspace for testing."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield temp_dir

class TestSystemAccessLayer:
    """Test cases for the System Access Layer."""

    @pytest.mark.asyncio
    async def test_execute_command_success(self, system_access):
        """Test successful command execution."""
        result = await system_access.execute_command("echo 'test'")
        assert result["success"] is True
        assert result["stdout"] == "test"
        assert result["stderr"] == ""
        assert result["exit_code"] == 0

    @pytest.mark.asyncio
    async def test_execute_command_timeout(self, system_access):
        """Test command execution timeout."""
        with pytest.raises(asyncio.TimeoutError):
            await system_access.execute_command("sleep 10", timeout=1)

    @pytest.mark.asyncio
    async def test_execute_command_validation(self, system_access):
        """Test command validation."""
        with pytest.raises(ValueError, match="Command not allowed"):
            await system_access.execute_command("sudo rm -rf /")

    @pytest.mark.asyncio
    async def test_package_management(self, system_access):
        """Test package management operations."""
        with patch('pkg_resources.require') as mock_require:
            mock_require.return_value = True
            result = await system_access.install_package("pytest")
            assert result["success"] is True

    @pytest.mark.asyncio
    async def test_file_operations(self, system_access, temp_workspace):
        """Test file operations."""
        test_file = os.path.join(temp_workspace, "test.txt")
        test_content = "test content"

        # Test write
        write_result = await system_access.write_file(test_file, test_content)
        assert write_result["success"] is True
        assert write_result["bytes_written"] == len(test_content)

        # Test read
        read_result = await system_access.read_file(test_file)
        assert read_result["success"] is True
        assert read_result["content"] == test_content

    @pytest.mark.asyncio
    async def test_repository_operations(self, system_access, temp_workspace):
        """Test repository operations."""
        repo_url = "https://github.com/test/repo.git"
        target_path = os.path.join(temp_workspace, "repo")

        with patch('git.Repo.clone_from') as mock_clone:
            mock_repo = MagicMock()
            mock_repo.active_branch.name = "main"
            mock_repo.head.commit.hexsha = "abc123"
            mock_clone.return_value = mock_repo

            result = await system_access.clone_repository(
                repo_url,
                target_path
            )
            assert result["success"] is True
            assert result["repo_url"] == repo_url
            assert result["target_path"] == target_path
            assert result["branch"] == "main"
            assert result["commit"] == "abc123"

    @pytest.mark.asyncio
    async def test_access_policy_validation(self, system_access, temp_workspace):
        """Test access policy validation."""
        # Test protected paths
        protected_paths = [
            "/etc/passwd",
            "/usr/bin/python",
            "/var/log/syslog"
        ]
        for path in protected_paths:
            assert not await system_access._validate_path(path, AccessLevel.READ)

        # Test allowed paths
        test_file = os.path.join(temp_workspace, "test.txt")
        assert await system_access._validate_path(test_file, AccessLevel.READ)
        assert await system_access._validate_path(test_file, AccessLevel.WRITE)

    @pytest.mark.asyncio
    async def test_command_validation(self, system_access):
        """Test command validation."""
        # Test allowed commands
        assert await system_access._validate_command("echo 'test'")
        assert await system_access._validate_command("ls -l")
        assert await system_access._validate_command("git status")

        # Test disallowed commands
        assert not await system_access._validate_command("sudo rm -rf /")
        assert not await system_access._validate_command("rm -rf /")
        assert not await system_access._validate_command("cat /etc/passwd")

    @pytest.mark.asyncio
    async def test_operation_history(self, system_access, temp_workspace):
        """Test operation history tracking."""
        test_file = os.path.join(temp_workspace, "test.txt")
        test_content = "test content"

        # Execute some operations
        await system_access.execute_command("echo 'test'")
        await system_access.write_file(test_file, test_content)

        # Check history
        history = system_access.get_operation_history()
        assert len(history) == 2
        assert history[0]["type"] == "command"
        assert history[1]["type"] == "file_write" 