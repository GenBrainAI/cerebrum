"""
Command-line interface for the Cerebrum System Core.

This module provides a command-line interface for interacting with the Cerebrum
System Core, allowing users to execute commands, search the codebase, and
view system context.
"""

import os
import json
import asyncio
import argparse
from typing import Dict, List, Any, Optional, Union
from datetime import datetime

from src.server.self_aware_core import CerebrumSystemCore

async def main():
    """Main entry point for the command-line interface."""
    parser = argparse.ArgumentParser(description="Cerebrum System Core CLI")
    
    # Configuration
    parser.add_argument("--config", type=str, help="Path to configuration file")
    
    # Subcommands
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")
    
    # Index command
    index_parser = subparsers.add_parser("index", help="Index the codebase")
    index_parser.add_argument("--incremental", action="store_true", help="Perform incremental indexing")
    
    # Search command
    search_parser = subparsers.add_parser("search", help="Search the codebase")
    search_parser.add_argument("query", type=str, help="Search query")
    search_parser.add_argument("--top-k", type=int, default=5, help="Number of results to return")
    
    # Execute command
    execute_parser = subparsers.add_parser("execute", help="Execute a command")
    execute_parser.add_argument("cmd", type=str, help="Command to execute")
    execute_parser.add_argument("--working-dir", type=str, default=".", help="Working directory")
    execute_parser.add_argument("--timeout", type=int, default=30, help="Timeout in seconds")
    execute_parser.add_argument("--no-approval", action="store_true", help="Skip approval")
    
    # Approve command
    approve_parser = subparsers.add_parser("approve", help="Approve a pending command")
    approve_parser.add_argument("approval_id", type=str, help="Approval ID")
    
    # Reject command
    reject_parser = subparsers.add_parser("reject", help="Reject a pending command")
    reject_parser.add_argument("approval_id", type=str, help="Approval ID")
    
    # List approvals command
    subparsers.add_parser("list-approvals", help="List pending approvals")
    
    # Get context command
    context_parser = subparsers.add_parser("context", help="Get system context")
    context_parser.add_argument("--max-tokens", type=int, default=1000, help="Maximum number of tokens")
    context_parser.add_argument("--include-metadata", action="store_true", help="Include metadata")
    
    # Get file command
    file_parser = subparsers.add_parser("file", help="Get file content")
    file_parser.add_argument("file_path", type=str, help="File path")
    
    # Stats command
    subparsers.add_parser("stats", help="Get codebase statistics")
    
    # Parse arguments
    args = parser.parse_args()
    
    # Load configuration
    config = {}
    config_path = args.config or os.environ.get("CEREBRUM_CONFIG", "config/cerebrum_system_config.json")
    
    if os.path.exists(config_path):
        with open(config_path, 'r') as f:
            config = json.load(f)
    
    # Initialize core
    core = CerebrumSystemCore(
        base_path=config.get("base_path", "persistent_state/cerebrum_system"),
        codebase_root=config.get("codebase_root", "."),
        config=config
    )
    
    # Execute command
    if args.command == "index":
        result = await core.index_codebase(incremental=args.incremental)
        print(f"Indexed {result.get('indexed_files', 0)} files")
        print(f"Total files: {result.get('total_files', 0)}")
        print(f"Skipped files: {result.get('skipped_files', 0)}")
    
    elif args.command == "search":
        results = await core.search_code(query=args.query, top_k=args.top_k)
        print(f"Found {len(results)} results for '{args.query}':")
        for i, result in enumerate(results):
            print(f"\nResult {i+1}: {result.file_path} (lines {result.start_line}-{result.end_line})")
            print(f"Relevance: {result.relevance_score:.4f}")
            print(f"Language: {result.language}")
            print("---")
            print(result.content)
            print("---")
    
    elif args.command == "execute":
        result = await core.execute_command(
            command=args.cmd,
            working_directory=args.working_dir,
            timeout=args.timeout,
            requires_approval=not args.no_approval
        )
        
        if isinstance(result, str):
            print(f"Command submitted for approval. Approval ID: {result}")
        else:
            if result.success:
                print("Command executed successfully:")
                print(result.stdout)
            else:
                print("Command execution failed:")
                print(result.stderr)
    
    elif args.command == "approve":
        result = await core.execute_approved_command(approval_id=args.approval_id)
        if result.success:
            print("Command executed successfully:")
            print(result.stdout)
        else:
            print("Command execution failed:")
            print(result.stderr)
    
    elif args.command == "reject":
        result = await core.reject_command(approval_id=args.approval_id)
        if result:
            print("Command rejected successfully")
        else:
            print("Failed to reject command")
    
    elif args.command == "list-approvals":
        approvals = await core.get_pending_approvals()
        if approvals:
            print(f"Found {len(approvals)} pending approvals:")
            for i, approval in enumerate(approvals):
                print(f"\nApproval {i+1}:")
                print(f"ID: {approval.get('id')}")
                print(f"Command: {approval.get('command')}")
                print(f"Submitted: {approval.get('submitted_at')}")
                print(f"Risk Level: {approval.get('risk_level')}")
        else:
            print("No pending approvals")
    
    elif args.command == "context":
        context = await core.get_context(
            max_tokens=args.max_tokens,
            include_metadata=args.include_metadata
        )
        
        if isinstance(context, str):
            print(context)
        else:
            print(json.dumps(context, indent=2))
    
    elif args.command == "file":
        content = await core.get_file_content(file_path=args.file_path)
        if content:
            print(content)
        else:
            print(f"File not found: {args.file_path}")
    
    elif args.command == "stats":
        stats = await core.get_codebase_stats()
        print("Codebase Statistics:")
        print(f"Total Files: {stats.get('total_files', 0)}")
        print(f"Total Lines: {stats.get('total_lines', 0)}")
        
        if "languages" in stats:
            print("\nLanguage Distribution:")
            for lang, count in stats["languages"].items():
                print(f"  {lang}: {count} files")
        
        print(f"\nLast Updated: {stats.get('last_updated', 'Never')}")
    
    else:
        parser.print_help()

if __name__ == "__main__":
    asyncio.run(main()) 