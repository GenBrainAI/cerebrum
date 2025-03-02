#!/usr/bin/env python3
"""
Command-line interface for the Self-Aware System.

This script provides a simple CLI for interacting with the Self-Aware System,
allowing users to execute various commands and view system information.
"""

import os
import sys
import json
import asyncio
import argparse
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))

from src.server.self_aware_integration import SelfAwareSystem

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class SelfAwareCLI:
    """Command-line interface for the Self-Aware System."""
    
    def __init__(self, storage_path: Optional[str] = None):
        """Initialize the CLI with a Self-Aware System instance."""
        self.system = SelfAwareSystem(storage_path=storage_path)
        self.commands = {
            "help": self.show_help,
            "status": self.show_status,
            "resources": self.show_resources,
            "metrics": self.show_metrics,
            "health": self.show_health,
            "packages": self.list_packages,
            "install": self.install_package,
            "uninstall": self.uninstall_package,
            "git-status": self.git_status,
            "git-commit": self.git_commit,
            "git-clone": self.git_clone,
            "tests": self.discover_tests,
            "run-tests": self.run_tests,
            "coverage": self.test_coverage,
            "knowledge": self.show_knowledge,
            "add-knowledge": self.add_knowledge,
            "tasks": self.show_tasks,
            "run-task": self.run_task,
            "cycle": self.start_cycle,
            "continuous": self.start_continuous,
            "shutdown": self.shutdown
        }
    
    async def run(self, args: List[str]):
        """Run the CLI with the given arguments."""
        if not args or args[0] == "help":
            self.show_help()
            return
        
        command = args[0]
        if command in self.commands:
            try:
                await self.commands[command](args[1:])
            except Exception as e:
                logger.error(f"Error executing command '{command}': {str(e)}")
                print(f"Error: {str(e)}")
        else:
            print(f"Unknown command: {command}")
            self.show_help()
    
    def show_help(self, args: List[str] = None):
        """Show help information."""
        print("Self-Aware System CLI")
        print("=====================")
        print("Available commands:")
        print("  help                  Show this help message")
        print("  status                Show system status")
        print("  resources             Show current resource usage")
        print("  metrics NAME          Show metrics for a specific metric name")
        print("  health                Show system health information")
        print("  packages              List installed packages")
        print("  install NAME [VERSION] Install a package")
        print("  uninstall NAME        Uninstall a package")
        print("  git-status            Show Git repository status")
        print("  git-commit MESSAGE    Commit changes with a message")
        print("  git-clone URL [PATH] [BRANCH] Clone a Git repository")
        print("  tests [PATH]          Discover tests in a path")
        print("  run-tests [PATH]      Run tests in a path")
        print("  coverage [PATH]       Get test coverage for a path")
        print("  knowledge QUERY       Search knowledge with a query")
        print("  add-knowledge TYPE NAME CONTENT Add knowledge to the system")
        print("  tasks [PHASE]         Show tasks for a specific phase")
        print("  run-task ID           Run a specific task")
        print("  cycle                 Start a cognitive cycle")
        print("  continuous [INTERVAL] Start continuous operation")
        print("  shutdown              Shutdown the system")
    
    async def show_status(self, args: List[str] = None):
        """Show system status."""
        print("Self-Aware System Status")
        print("=======================")
        
        # Get current phase
        phase = self.system.get_current_phase()
        print(f"Current Phase: {phase}")
        
        # Get resource usage
        usage = await self.system.get_current_resource_usage()
        print(f"CPU Usage: {usage.get('cpu', 0):.1f}%")
        print(f"Memory Usage: {usage.get('memory', 0):.1f} MB")
        print(f"Disk Usage: {usage.get('disk', 0):.1f} MB")
        
        # Get system health
        health = await self.system.get_system_health()
        print(f"Overall Health: {health.get('overall_health', 0):.1f}%")
        
        # Get task counts
        tasks = self.system.get_tasks_by_phase(None)
        print(f"Total Tasks: {len(tasks)}")
        
        # Get knowledge counts
        context = self.system.get_knowledge_context("", max_items=1000)
        print(f"Knowledge Items: {len(context)}")
    
    async def show_resources(self, args: List[str] = None):
        """Show current resource usage."""
        usage = await self.system.get_current_resource_usage()
        print("Resource Usage")
        print("==============")
        for resource, value in usage.items():
            print(f"{resource.upper()}: {value:.2f}")
        
        # Check budgets
        for resource in ["cpu", "memory", "disk", "api_calls", "tokens"]:
            try:
                budget = await self.system.check_resource_budget(resource)
                if budget.get("limit"):
                    print(f"{resource.upper()} Budget: {budget.get('current_usage', 0):.2f}/{budget.get('limit', 0):.2f} "
                          f"({budget.get('percentage_used', 0):.1f}%) - "
                          f"{'Within Budget' if budget.get('within_budget') else 'OVER BUDGET'}")
            except Exception:
                pass
    
    async def show_metrics(self, args: List[str]):
        """Show metrics for a specific metric name."""
        if not args:
            print("Error: Metric name is required")
            return
        
        metric_name = args[0]
        start_time = datetime.now() - timedelta(hours=24)
        end_time = datetime.now()
        aggregation = "avg"
        
        if len(args) > 1:
            hours = int(args[1])
            start_time = datetime.now() - timedelta(hours=hours)
        
        if len(args) > 2:
            aggregation = args[2]
        
        metrics = await self.system.get_metrics(metric_name, start_time, end_time, aggregation)
        
        print(f"Metrics for '{metric_name}' ({aggregation})")
        print("=" * (len(metric_name) + 20))
        
        if not metrics:
            print("No metrics found")
            return
        
        for metric in metrics:
            timestamp = metric.get("timestamp", datetime.now()).strftime("%Y-%m-%d %H:%M:%S")
            value = metric.get("value", 0)
            tags = metric.get("tags", {})
            tags_str = ", ".join([f"{k}={v}" for k, v in tags.items()]) if tags else ""
            
            print(f"{timestamp}: {value:.2f} {tags_str}")
    
    async def show_health(self, args: List[str] = None):
        """Show system health information."""
        health = await self.system.get_system_health()
        print("System Health")
        print("=============")
        for component, value in health.items():
            print(f"{component}: {value:.1f}%")
    
    async def list_packages(self, args: List[str] = None):
        """List installed packages."""
        packages = await self.system.list_installed_packages()
        print("Installed Packages")
        print("=================")
        if not packages:
            print("No packages found")
            return
        
        for package in packages:
            print(f"{package.get('name', 'Unknown')}: {package.get('version', 'Unknown')}")
    
    async def install_package(self, args: List[str]):
        """Install a package."""
        if not args:
            print("Error: Package name is required")
            return
        
        package_name = args[0]
        version = args[1] if len(args) > 1 else None
        
        print(f"Installing package: {package_name}" + (f" (version {version})" if version else ""))
        result = await self.system.install_package(package_name, version)
        
        if result.get("success"):
            print("Package installed successfully")
        elif "approval_request_id" in result:
            print(f"Package installation requires approval. Request ID: {result['approval_request_id']}")
        else:
            print(f"Failed to install package: {result.get('message', 'Unknown error')}")
    
    async def uninstall_package(self, args: List[str]):
        """Uninstall a package."""
        if not args:
            print("Error: Package name is required")
            return
        
        package_name = args[0]
        
        print(f"Uninstalling package: {package_name}")
        result = await self.system.uninstall_package(package_name)
        
        if result.get("success"):
            print("Package uninstalled successfully")
        elif "approval_request_id" in result:
            print(f"Package uninstallation requires approval. Request ID: {result['approval_request_id']}")
        else:
            print(f"Failed to uninstall package: {result.get('message', 'Unknown error')}")
    
    async def git_status(self, args: List[str] = None):
        """Show Git repository status."""
        status = await self.system.get_repository_status()
        print("Git Repository Status")
        print("====================")
        
        if not status.get("success"):
            print(f"Error: {status.get('message', 'Failed to get repository status')}")
            return
        
        print(f"Branch: {status.get('branch', 'Unknown')}")
        print(f"Has Changes: {status.get('has_changes', False)}")
        
        if status.get("untracked_files"):
            print("\nUntracked Files:")
            for file in status.get("untracked_files", []):
                print(f"  {file}")
        
        if status.get("modified_files"):
            print("\nModified Files:")
            for file in status.get("modified_files", []):
                print(f"  {file}")
    
    async def git_commit(self, args: List[str]):
        """Commit changes with a message."""
        if not args:
            print("Error: Commit message is required")
            return
        
        message = args[0]
        files = args[1:] if len(args) > 1 else None
        
        print(f"Committing changes with message: {message}")
        if files:
            print(f"Files: {', '.join(files)}")
        
        result = await self.system.commit_changes(message, files)
        
        if result.get("success"):
            print("Changes committed successfully")
        elif "approval_request_id" in result:
            print(f"Commit requires approval. Request ID: {result['approval_request_id']}")
        else:
            print(f"Failed to commit changes: {result.get('message', 'Unknown error')}")
    
    async def git_clone(self, args: List[str]):
        """Clone a Git repository."""
        if not args:
            print("Error: Repository URL is required")
            return
        
        url = args[0]
        path = args[1] if len(args) > 1 else None
        branch = args[2] if len(args) > 2 else None
        
        print(f"Cloning repository: {url}")
        if path:
            print(f"Path: {path}")
        if branch:
            print(f"Branch: {branch}")
        
        result = await self.system.clone_repository(url, path, branch)
        
        if result.get("success"):
            print("Repository cloned successfully")
        elif "approval_request_id" in result:
            print(f"Clone requires approval. Request ID: {result['approval_request_id']}")
        else:
            print(f"Failed to clone repository: {result.get('message', 'Unknown error')}")
    
    async def discover_tests(self, args: List[str] = None):
        """Discover tests in a path."""
        path = args[0] if args else None
        pattern = args[1] if len(args) > 1 else "test_*.py"
        
        print(f"Discovering tests" + (f" in {path}" if path else ""))
        tests = await self.system.discover_tests(path, pattern)
        
        print(f"Found {len(tests)} tests:")
        for test in tests:
            print(f"  {test.get('name', 'Unknown')} ({test.get('file', 'Unknown')})")
    
    async def run_tests(self, args: List[str] = None):
        """Run tests in a path."""
        path = args[0] if args else None
        pattern = args[1] if len(args) > 1 else None
        verbosity = int(args[2]) if len(args) > 2 else 2
        
        print(f"Running tests" + (f" in {path}" if path else ""))
        results = await self.system.run_tests(path, pattern, verbosity)
        
        if results.get("success"):
            print("Tests completed successfully")
        else:
            print("Tests failed")
        
        print(f"Total: {results.get('total', 0)}")
        print(f"Passed: {results.get('passed', 0)}")
        print(f"Failed: {results.get('failures', 0)}")
        print(f"Errors: {results.get('errors', 0)}")
        print(f"Skipped: {results.get('skipped', 0)}")
        
        if results.get("failures") > 0 and "failure_details" in results:
            print("\nFailure Details:")
            for detail in results.get("failure_details", []):
                print(f"  {detail.get('name', 'Unknown')}: {detail.get('message', 'Unknown error')}")
    
    async def test_coverage(self, args: List[str] = None):
        """Get test coverage for a path."""
        path = args[0] if args else None
        
        print(f"Getting test coverage" + (f" for {path}" if path else ""))
        coverage = await self.system.get_test_coverage(path)
        
        print(f"Total Coverage: {coverage.get('total_coverage', 0):.1f}%")
        
        if "file_coverage" in coverage:
            print("\nFile Coverage:")
            for file, cov in coverage.get("file_coverage", {}).items():
                print(f"  {file}: {cov:.1f}%")
    
    async def show_knowledge(self, args: List[str]):
        """Search knowledge with a query."""
        if not args:
            print("Error: Query is required")
            return
        
        query = args[0]
        max_items = int(args[1]) if len(args) > 1 else 10
        
        print(f"Searching knowledge for: {query}")
        context = self.system.get_knowledge_context(query, max_items)
        
        if not context:
            print("No knowledge found")
            return
        
        print(f"Found {len(context)} items:")
        for item in context:
            if "concept" in item:
                print(f"\nConcept: {item.get('concept', 'Unknown')}")
                print(f"Definition: {item.get('definition', 'No definition')}")
                print(f"Related: {', '.join(item.get('related_concepts', []))}")
            elif "task_name" in item:
                print(f"\nTask: {item.get('task_name', 'Unknown')}")
                print(f"Description: {item.get('description', 'No description')}")
                print("Steps:")
                for step in item.get("steps", []):
                    print(f"  - {step}")
            elif "title" in item:
                print(f"\nEvent: {item.get('title', 'Unknown')}")
                print(f"Description: {item.get('description', 'No description')}")
                print(f"Time: {item.get('timestamp', 'Unknown')}")
                print(f"Actors: {', '.join(item.get('actors', []))}")
            
            if "tags" in item:
                print(f"Tags: {', '.join(item.get('tags', []))}")
    
    async def add_knowledge(self, args: List[str]):
        """Add knowledge to the system."""
        if len(args) < 3:
            print("Error: Knowledge type, name, and content are required")
            print("Usage: add-knowledge TYPE NAME CONTENT")
            print("Types: semantic, procedural, episodic")
            return
        
        knowledge_type = args[0].lower()
        name = args[1]
        content = args[2]
        
        if knowledge_type == "semantic":
            result = self.system.add_semantic_knowledge(
                concept=name,
                definition=content,
                related_concepts=args[3:] if len(args) > 3 else [],
                tags=["cli", "user_added"]
            )
            print(f"Added semantic knowledge: {name}")
        
        elif knowledge_type == "procedural":
            steps = content.split(";")
            result = self.system.add_procedural_knowledge(
                task_name=name,
                description=f"Task added via CLI: {name}",
                steps=steps,
                expected_outcome=args[3] if len(args) > 3 else "Successful completion",
                tags=["cli", "user_added"]
            )
            print(f"Added procedural knowledge: {name} with {len(steps)} steps")
        
        elif knowledge_type == "episodic":
            result = self.system.add_episodic_knowledge(
                title=name,
                description=content,
                timestamp=datetime.now(),
                actors=args[3:] if len(args) > 3 else ["User"],
                tags=["cli", "user_added"]
            )
            print(f"Added episodic knowledge: {name}")
        
        else:
            print(f"Error: Unknown knowledge type: {knowledge_type}")
            print("Valid types: semantic, procedural, episodic")
            return
        
        print(f"Knowledge ID: {result}")
    
    async def show_tasks(self, args: List[str] = None):
        """Show tasks for a specific phase."""
        from src.server.system.cognitive_loop import CognitivePhase
        
        phase = None
        if args:
            phase_name = args[0].upper()
            try:
                phase = CognitivePhase[phase_name]
            except KeyError:
                print(f"Error: Unknown phase: {args[0]}")
                print("Valid phases: UNDERSTAND, PLAN, EXECUTE, REFLECT")
                return
        
        tasks = self.system.get_tasks_by_phase(phase)
        
        if phase:
            print(f"Tasks for phase: {phase.name}")
        else:
            print("All tasks")
        print("=" * 20)
        
        if not tasks:
            print("No tasks found")
            return
        
        for task in tasks:
            print(f"\nID: {task.get('id', 'Unknown')}")
            print(f"Title: {task.get('title', 'Unknown')}")
            print(f"Phase: {task.get('phase', 'Unknown')}")
            print(f"Status: {task.get('status', 'Unknown')}")
            print(f"Priority: {task.get('priority', 'Unknown')}")
            print(f"Created: {task.get('created_at', 'Unknown')}")
            if task.get("completed_at"):
                print(f"Completed: {task.get('completed_at')}")
    
    async def run_task(self, args: List[str]):
        """Run a specific task."""
        if not args:
            print("Error: Task ID is required")
            return
        
        task_id = args[0]
        
        # Get the task
        task = self.system.get_cognitive_task(task_id)
        if not task:
            print(f"Error: Task not found: {task_id}")
            return
        
        print(f"Running task: {task.get('title', 'Unknown')} ({task_id})")
        
        # This is a simplified version - in a real implementation,
        # you would need to handle different task types and execution methods
        print("Task execution not implemented in CLI")
        print("Please use the API or example script to run tasks")
    
    async def start_cycle(self, args: List[str] = None):
        """Start a cognitive cycle."""
        print("Starting cognitive cycle...")
        task_id = await self.system.start_cognitive_cycle()
        print(f"Cognitive cycle started with task ID: {task_id}")
        
        # Wait a bit to let things run
        print("Waiting for 5 seconds...")
        await asyncio.sleep(5)
        
        # Get the task status
        task = self.system.get_cognitive_task(task_id)
        if task:
            print(f"Task status: {task.get('status', 'Unknown')}")
        
        print("Cognitive cycle is running in the background")
        print("Use 'tasks' command to check progress")
    
    async def start_continuous(self, args: List[str] = None):
        """Start continuous operation."""
        interval = float(args[0]) if args else 60.0
        
        print(f"Starting continuous operation with interval: {interval} seconds")
        print("Press Ctrl+C to stop")
        
        try:
            # Start in a separate task so we can handle keyboard interrupt
            task = asyncio.create_task(self.system.start_continuous_operation(interval))
            
            # Wait indefinitely (until Ctrl+C)
            while True:
                await asyncio.sleep(1)
        
        except KeyboardInterrupt:
            print("\nStopping continuous operation...")
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
            print("Continuous operation stopped")
    
    async def shutdown(self, args: List[str] = None):
        """Shutdown the system."""
        print("Shutting down the Self-Aware System...")
        await self.system.shutdown()
        print("Shutdown complete")


async def main():
    """Main function to run the CLI."""
    parser = argparse.ArgumentParser(description="Self-Aware System CLI")
    parser.add_argument("--storage", help="Storage path for the Self-Aware System")
    parser.add_argument("command", nargs="*", help="Command to execute")
    
    args = parser.parse_args()
    
    cli = SelfAwareCLI(storage_path=args.storage)
    await cli.run(args.command)


if __name__ == "__main__":
    asyncio.run(main()) 