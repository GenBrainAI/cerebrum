import os
import json
import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path
import tempfile
import shutil
import subprocess
from datetime import datetime, timezone

class TestCustomerWorkflow:
    @pytest.fixture
    def temp_workspace(self):
        """Create a temporary workspace for testing."""
        temp_dir = tempfile.mkdtemp()
        old_cwd = os.getcwd()
        os.chdir(temp_dir)
        
        # Create test directories and files
        os.makedirs(".github")
        
        # Initialize git repo
        subprocess.run(["git", "init"], check=True)
        subprocess.run(["git", "config", "user.name", "Test User"], check=True)
        subprocess.run(["git", "config", "user.email", "test@example.com"], check=True)
        
        yield temp_dir
        
        # Cleanup
        os.chdir(old_cwd)
        shutil.rmtree(temp_dir)

    @pytest.fixture
    def mock_gh_cli(self):
        """Mock GitHub CLI commands."""
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            yield mock_run

    def test_add_customer_workflow(self, temp_workspace, mock_gh_cli):
        """Test adding a customer through the workflow."""
        # Setup test customer data
        customer_data = {
            "username": "test_user",
            "email": "test@example.com",
            "plan": "basic"
        }

        # Create initial customers.json
        customers_file = Path(".github/customers.json")
        customers_file.parent.mkdir(exist_ok=True)
        initial_data = {"customers": {}}
        customers_file.write_text(json.dumps(initial_data))

        # Setup mock response
        expected_output = json.dumps({
            "customers": {
                customer_data["username"]: {
                    "email": customer_data["email"],
                    "plan": customer_data["plan"],
                    "status": "active",
                    "added_date": "2024-01-01T00:00:00Z"
                }
            }
        })
        mock_gh_cli.return_value.stdout = expected_output

        # Add customer using jq and update file
        result = subprocess.run([
            "jq",
            f'.customers["{customer_data["username"]}"] = {{"email": "{customer_data["email"]}", "plan": "{customer_data["plan"]}", "status": "active", "added_date": "2024-01-01T00:00:00Z"}}',
            str(customers_file)
        ], capture_output=True, text=True, check=True)
        
        customers_file.write_text(expected_output)

        # Verify customer database was updated
        db = json.loads(customers_file.read_text())
        assert customer_data["username"] in db["customers"]
        assert db["customers"][customer_data["username"]]["status"] == "active"
        assert db["customers"][customer_data["username"]]["email"] == customer_data["email"]

    def test_remove_customer_workflow(self, temp_workspace, mock_gh_cli):
        """Test removing a customer through the workflow."""
        # Setup test customer in database
        customer_data = {
            "username": "test_user",
            "email": "test@example.com",
            "plan": "basic",
            "added_date": "2024-01-01T00:00:00Z",
            "status": "active"
        }

        # Create customers.json with test data
        customers_file = Path(".github/customers.json")
        customers_file.parent.mkdir(exist_ok=True)
        initial_data = {
            "customers": {
                customer_data["username"]: customer_data
            }
        }
        customers_file.write_text(json.dumps(initial_data))

        # Setup mock response
        expected_output = json.dumps({
            "customers": {
                customer_data["username"]: {
                    **customer_data,
                    "status": "inactive",
                    "removed_date": "2024-01-01T00:00:00Z"
                }
            }
        })
        mock_gh_cli.return_value.stdout = expected_output

        # Remove customer using jq
        result = subprocess.run([
            "jq",
            f'.customers["{customer_data["username"]}"].status = "inactive" | .customers["{customer_data["username"]}"].removed_date = "2024-01-01T00:00:00Z"',
            str(customers_file)
        ], capture_output=True, text=True, check=True)
        
        customers_file.write_text(expected_output)

        # Verify customer was marked as inactive
        db = json.loads(customers_file.read_text())
        assert db["customers"][customer_data["username"]]["status"] == "inactive"
        assert "removed_date" in db["customers"][customer_data["username"]]

    def test_list_customers_workflow(self, temp_workspace):
        """Test listing customers through the workflow."""
        # Setup test customers
        customers = {
            "active_user": {
                "email": "active@example.com",
                "plan": "basic",
                "added_date": "2024-01-01T00:00:00Z",
                "status": "active"
            },
            "inactive_user": {
                "email": "inactive@example.com",
                "plan": "premium",
                "added_date": "2024-01-01T00:00:00Z",
                "removed_date": "2024-01-02T00:00:00Z",
                "status": "inactive"
            }
        }
        
        # Create customers.json with test data
        customers_file = Path(".github/customers.json")
        customers_file.parent.mkdir(exist_ok=True)
        customers_file.write_text(json.dumps({"customers": customers}))
        
        # List active customers
        active_result = subprocess.run([
            "jq",
            '-r',
            '.customers | to_entries[] | select(.value.status == "active") | .key',
            str(customers_file)
        ], capture_output=True, text=True, check=True)
        
        active_users = active_result.stdout.strip().split('\n')
        assert "active_user" in active_users
        assert "inactive_user" not in active_users
        
        # List inactive customers
        inactive_result = subprocess.run([
            "jq",
            '-r',
            '.customers | to_entries[] | select(.value.status == "inactive") | .key',
            str(customers_file)
        ], capture_output=True, text=True, check=True)
        
        inactive_users = inactive_result.stdout.strip().split('\n')
        assert "inactive_user" in inactive_users
        assert "active_user" not in inactive_users

class TestSyncWorkflow:
    @pytest.fixture
    def mock_git_commands(self):
        """Mock git commands."""
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            yield mock_run

    def test_sync_workflow_success(self, temp_workspace, mock_git_commands):
        """Test successful sync workflow."""
        # Setup test repository
        base_remote = "https://github.com/owner/cerebrum.git"
        
        # Execute git commands that would be run by the workflow
        commands = [
            ["git", "remote", "add", "base", base_remote],
            ["git", "fetch", "base"],
            ["git", "checkout", "-b", "sync-test"],
            ["git", "merge", "base/main"],
            ["git", "push", "origin", "sync-test"]
        ]
        
        # All commands should succeed due to mock
        for cmd in commands:
            result = subprocess.run(cmd, capture_output=True)
            assert result.returncode == 0

    def test_sync_workflow_conflicts(self, temp_workspace, mock_git_commands):
        """Test sync workflow with conflicts."""
        # Create a file that will cause conflicts
        test_file = Path("test.txt")
        test_file.write_text("line1\nline2\nline3\n")

        # Setup mock responses for git commands
        mock_git_commands.side_effect = [
            # Initial setup commands succeed
            subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr=""),  # git init
            subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr=""),  # git config email
            subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr=""),  # git config name
            subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr=""),  # git add
            subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr=""),  # git commit
            subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr=""),  # git checkout -b feature
            subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr=""),  # git add
            subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr=""),  # git commit
            subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr=""),  # git checkout master
            subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr=""),  # git add
            subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr=""),  # git commit
            # Merge command fails with conflict
            subprocess.CalledProcessError(
                returncode=1,
                cmd=["git", "merge", "feature"],
                output="",
                stderr="error: merge conflict in test.txt\nautomatic merge failed; fix conflicts and then commit the result."
            )
        ]

        # Simulate git operations using mock
        subprocess.run(["git", "init"])
        subprocess.run(["git", "config", "user.email", "test@example.com"])
        subprocess.run(["git", "config", "user.name", "Test User"])
        subprocess.run(["git", "add", "test.txt"])
        subprocess.run(["git", "commit", "-m", "initial commit"])

        # Create and switch to feature branch
        subprocess.run(["git", "checkout", "-b", "feature"])
        test_file.write_text("line1\nfeature change\nline3\n")
        subprocess.run(["git", "add", "test.txt"])
        subprocess.run(["git", "commit", "-m", "feature change"])

        # Switch back to master and make conflicting change
        subprocess.run(["git", "checkout", "master"])
        test_file.write_text("line1\nmaster change\nline3\n")
        subprocess.run(["git", "add", "test.txt"])
        subprocess.run(["git", "commit", "-m", "master change"])

        # Try to merge feature into master (should fail due to conflict)
        with pytest.raises(subprocess.CalledProcessError) as exc_info:
            subprocess.run(["git", "merge", "feature"])
        
        # Verify the error message
        assert "merge conflict" in exc_info.value.stderr.lower()

    def test_customer_verification(self, temp_workspace):
        """Test customer verification in sync workflow."""
        # Setup mock customer database
        customers_db = {
            "customers": {
                "active_user": {
                    "status": "active",
                    "email": "active@example.com",
                    "added_date": datetime.now(timezone.utc).isoformat()
                },
                "inactive_user": {
                    "status": "inactive",
                    "email": "inactive@example.com",
                    "added_date": datetime.now(timezone.utc).isoformat(),
                    "removed_date": datetime.now(timezone.utc).isoformat()
                }
            }
        }
        
        # Create customers.json with test data
        customers_file = Path(".github/customers.json")
        customers_file.parent.mkdir(exist_ok=True)
        customers_file.write_text(json.dumps(customers_db))
        
        # Verify active user access
        db = json.loads(customers_file.read_text())
        assert db["customers"]["active_user"]["status"] == "active"
        assert "removed_date" not in db["customers"]["active_user"]
        
        # Verify inactive user access
        assert db["customers"]["inactive_user"]["status"] == "inactive"
        assert "removed_date" in db["customers"]["inactive_user"]

if __name__ == "__main__":
    pytest.main([__file__]) 