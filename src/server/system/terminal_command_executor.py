"""
Terminal Command Executor for the Self-Aware Cerebrum system.

This module provides secure command validation and execution with sandboxing
for safety. It ensures that commands are properly validated, executed in a
controlled environment, and logged for auditing purposes.
"""

import os
import re
import json
import uuid
import shlex
import logging
import asyncio
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple, Union
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

@dataclass
class CommandValidationResult:
    """Result of command validation."""
    is_valid: bool
    risk_level: str  # "low", "medium", "high"
    requires_approval: bool
    reason: str
    sanitized_command: Optional[str] = None
    validation_details: Dict[str, Any] = field(default_factory=dict)

@dataclass
class CommandExecutionResult:
    """Result of command execution."""
    command_id: str
    command: str
    exit_code: int
    stdout: str
    stderr: str
    execution_time: float
    started_at: str
    completed_at: str
    working_directory: str
    environment_vars: Dict[str, str]
    sandbox_type: str
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class SecurityConfig:
    """Security configuration for command execution."""
    # Command validation
    allowed_commands: List[str] = field(default_factory=list)
    blocked_commands: List[str] = field(default_factory=list)
    allowed_patterns: List[str] = field(default_factory=list)
    blocked_patterns: List[str] = field(default_factory=list)
    
    # Execution limits
    max_execution_time: int = 60  # seconds
    max_output_size: int = 1024 * 1024  # 1MB
    
    # Sandboxing
    sandbox_type: str = "subprocess"  # "subprocess", "docker", "none"
    sandbox_image: str = "python:3.9-slim"
    
    # Logging
    log_commands: bool = True
    log_output: bool = True
    log_directory: str = "logs/commands"
    
    # Approval
    require_approval_for_risk_level: str = "medium"  # "none", "low", "medium", "high", "all"

class TerminalCommandExecutor:
    """
    Provides secure command validation and execution with sandboxing for safety.
    
    This class ensures that commands are properly validated, executed in a
    controlled environment, and logged for auditing purposes.
    """
    
    def __init__(self, config: Optional[SecurityConfig] = None):
        """Initialize the Terminal Command Executor."""
        self.config = config or SecurityConfig()
        
        # Create log directory
        if self.config.log_commands:
            os.makedirs(self.config.log_directory, exist_ok=True)
        
        # Initialize execution history
        self.execution_history: List[CommandExecutionResult] = []
        
        # Initialize pending approvals
        self.pending_approvals: Dict[str, Dict[str, Any]] = {}
        
        logger.info("Terminal Command Executor initialized")
    
    async def validate_command(self, command: str) -> CommandValidationResult:
        """
        Validate a command against security policies.
        
        Args:
            command: The command to validate
            
        Returns:
            CommandValidationResult: The validation result
        """
        # Basic sanitization
        sanitized_command = command.strip()
        
        # Check for empty command
        if not sanitized_command:
            return CommandValidationResult(
                is_valid=False,
                risk_level="low",
                requires_approval=False,
                reason="Empty command",
                sanitized_command=None
            )
        
        # Check against blocked commands
        command_parts = shlex.split(sanitized_command)
        base_command = command_parts[0]
        
        if base_command in self.config.blocked_commands:
            return CommandValidationResult(
                is_valid=False,
                risk_level="high",
                requires_approval=True,
                reason=f"Command '{base_command}' is blocked",
                sanitized_command=None
            )
        
        # Check against blocked patterns
        for pattern in self.config.blocked_patterns:
            if re.search(pattern, sanitized_command):
                return CommandValidationResult(
                    is_valid=False,
                    risk_level="high",
                    requires_approval=True,
                    reason=f"Command matches blocked pattern: {pattern}",
                    sanitized_command=None
                )
        
        # Determine risk level
        risk_level = "low"
        
        # Higher risk for commands with pipes, redirects, or shell metacharacters
        if any(char in sanitized_command for char in ['|', '>', '<', ';', '&&', '||', '`', '$(']):
            risk_level = "medium"
        
        # Higher risk for commands that might modify the system
        if any(cmd in sanitized_command.lower() for cmd in ['rm', 'mv', 'cp', 'chmod', 'chown', 'sudo', 'apt', 'yum', 'brew']):
            risk_level = "medium"
        
        # Highest risk for commands that might be destructive
        if 'rm -rf' in sanitized_command or 'rm -r' in sanitized_command:
            risk_level = "high"
        
        # Determine if approval is required
        requires_approval = False
        if self.config.require_approval_for_risk_level == "all":
            requires_approval = True
        elif self.config.require_approval_for_risk_level == "high" and risk_level == "high":
            requires_approval = True
        elif self.config.require_approval_for_risk_level == "medium" and risk_level in ["medium", "high"]:
            requires_approval = True
        elif self.config.require_approval_for_risk_level == "low" and risk_level in ["low", "medium", "high"]:
            requires_approval = True
        
        return CommandValidationResult(
            is_valid=True,
            risk_level=risk_level,
            requires_approval=requires_approval,
            reason="Command validated successfully",
            sanitized_command=sanitized_command,
            validation_details={
                "base_command": base_command,
                "arguments": command_parts[1:],
                "contains_shell_metacharacters": any(char in sanitized_command for char in ['|', '>', '<', ';', '&&', '||', '`', '$(']),
                "contains_system_modifiers": any(cmd in sanitized_command.lower() for cmd in ['rm', 'mv', 'cp', 'chmod', 'chown', 'sudo', 'apt', 'yum', 'brew'])
            }
        )
    
    async def execute_command(
        self,
        command: str,
        working_directory: Optional[str] = None,
        environment_vars: Optional[Dict[str, str]] = None,
        timeout: Optional[int] = None,
        requires_approval: bool = True
    ) -> Union[CommandExecutionResult, str]:
        """
        Execute a command with appropriate security controls.
        
        Args:
            command: The command to execute
            working_directory: The working directory for the command
            environment_vars: Environment variables for the command
            timeout: Timeout in seconds (overrides config)
            requires_approval: Whether the command requires approval
            
        Returns:
            Union[CommandExecutionResult, str]: The execution result or approval ID
        """
        # Validate command
        validation_result = await self.validate_command(command)
        
        if not validation_result.is_valid:
            raise ValueError(f"Invalid command: {validation_result.reason}")
        
        # Check if approval is required
        if validation_result.requires_approval and requires_approval:
            approval_id = str(uuid.uuid4())
            
            self.pending_approvals[approval_id] = {
                "command": validation_result.sanitized_command,
                "working_directory": working_directory,
                "environment_vars": environment_vars,
                "timeout": timeout,
                "validation_result": {
                    "risk_level": validation_result.risk_level,
                    "reason": validation_result.reason,
                    "validation_details": validation_result.validation_details
                },
                "requested_at": datetime.now().isoformat()
            }
            
            logger.info(f"Command requires approval: {validation_result.sanitized_command} (ID: {approval_id})")
            return approval_id
        
        # Execute command
        return await self._execute_command_internal(
            validation_result.sanitized_command,
            working_directory,
            environment_vars,
            timeout
        )
    
    async def execute_approved_command(self, approval_id: str) -> CommandExecutionResult:
        """
        Execute a previously approved command.
        
        Args:
            approval_id: The approval ID
            
        Returns:
            CommandExecutionResult: The execution result
        """
        if approval_id not in self.pending_approvals:
            raise ValueError(f"Approval ID not found: {approval_id}")
        
        approval_data = self.pending_approvals[approval_id]
        
        # Execute command
        result = await self._execute_command_internal(
            approval_data["command"],
            approval_data["working_directory"],
            approval_data["environment_vars"],
            approval_data["timeout"]
        )
        
        # Remove from pending approvals
        del self.pending_approvals[approval_id]
        
        return result
    
    async def _execute_command_internal(
        self,
        command: str,
        working_directory: Optional[str] = None,
        environment_vars: Optional[Dict[str, str]] = None,
        timeout: Optional[int] = None
    ) -> CommandExecutionResult:
        """
        Internal method to execute a command.
        
        Args:
            command: The command to execute
            working_directory: The working directory for the command
            environment_vars: Environment variables for the command
            timeout: Timeout in seconds (overrides config)
            
        Returns:
            CommandExecutionResult: The execution result
        """
        command_id = str(uuid.uuid4())
        started_at = datetime.now()
        
        # Set working directory
        if working_directory is None:
            working_directory = os.getcwd()
        
        # Set environment variables
        env = os.environ.copy()
        if environment_vars:
            env.update(environment_vars)
        
        # Set timeout
        if timeout is None:
            timeout = self.config.max_execution_time
        
        logger.info(f"Executing command: {command} (ID: {command_id})")
        
        try:
            # Execute command based on sandbox type
            if self.config.sandbox_type == "subprocess":
                result = await self._execute_in_subprocess(command, working_directory, env, timeout)
            elif self.config.sandbox_type == "docker":
                result = await self._execute_in_docker(command, working_directory, env, timeout)
            else:
                raise ValueError(f"Unsupported sandbox type: {self.config.sandbox_type}")
            
            completed_at = datetime.now()
            execution_time = (completed_at - started_at).total_seconds()
            
            # Create execution result
            execution_result = CommandExecutionResult(
                command_id=command_id,
                command=command,
                exit_code=result["exit_code"],
                stdout=result["stdout"],
                stderr=result["stderr"],
                execution_time=execution_time,
                started_at=started_at.isoformat(),
                completed_at=completed_at.isoformat(),
                working_directory=working_directory,
                environment_vars={k: v for k, v in env.items() if k in environment_vars} if environment_vars else {},
                sandbox_type=self.config.sandbox_type,
                metadata={
                    "timeout": timeout,
                    "output_truncated": len(result["stdout"]) > self.config.max_output_size or len(result["stderr"]) > self.config.max_output_size
                }
            )
            
            # Add to execution history
            self.execution_history.append(execution_result)
            
            # Log execution
            if self.config.log_commands:
                await self._log_execution(execution_result)
            
            return execution_result
            
        except asyncio.TimeoutError:
            completed_at = datetime.now()
            execution_time = (completed_at - started_at).total_seconds()
            
            # Create timeout result
            timeout_result = CommandExecutionResult(
                command_id=command_id,
                command=command,
                exit_code=-1,
                stdout="",
                stderr=f"Command execution timed out after {timeout} seconds",
                execution_time=execution_time,
                started_at=started_at.isoformat(),
                completed_at=completed_at.isoformat(),
                working_directory=working_directory,
                environment_vars={k: v for k, v in env.items() if k in environment_vars} if environment_vars else {},
                sandbox_type=self.config.sandbox_type,
                metadata={
                    "timeout": timeout,
                    "error": "timeout"
                }
            )
            
            # Add to execution history
            self.execution_history.append(timeout_result)
            
            # Log execution
            if self.config.log_commands:
                await self._log_execution(timeout_result)
            
            return timeout_result
            
        except Exception as e:
            completed_at = datetime.now()
            execution_time = (completed_at - started_at).total_seconds()
            
            # Create error result
            error_result = CommandExecutionResult(
                command_id=command_id,
                command=command,
                exit_code=-1,
                stdout="",
                stderr=f"Error executing command: {str(e)}",
                execution_time=execution_time,
                started_at=started_at.isoformat(),
                completed_at=completed_at.isoformat(),
                working_directory=working_directory,
                environment_vars={k: v for k, v in env.items() if k in environment_vars} if environment_vars else {},
                sandbox_type=self.config.sandbox_type,
                metadata={
                    "timeout": timeout,
                    "error": str(e),
                    "error_type": type(e).__name__
                }
            )
            
            # Add to execution history
            self.execution_history.append(error_result)
            
            # Log execution
            if self.config.log_commands:
                await self._log_execution(error_result)
            
            return error_result
    
    async def _execute_in_subprocess(
        self,
        command: str,
        working_directory: str,
        env: Dict[str, str],
        timeout: int
    ) -> Dict[str, Any]:
        """
        Execute a command in a subprocess.
        
        Args:
            command: The command to execute
            working_directory: The working directory for the command
            env: Environment variables for the command
            timeout: Timeout in seconds
            
        Returns:
            Dict[str, Any]: The execution result
        """
        # Determine if shell is needed
        use_shell = any(char in command for char in ['|', '>', '<', ';', '&&', '||', '`', '$', '*', '?', '{', '}', '[', ']'])
        
        process = None
        try:
            # Create subprocess
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=working_directory,
                env=env,
                shell=use_shell
            ) if use_shell else await asyncio.create_subprocess_exec(
                *shlex.split(command),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=working_directory,
                env=env
            )
            
            # Wait for process to complete with timeout
            try:
                stdout, stderr = await asyncio.wait_for(process.communicate(), timeout)
                stdout_str = stdout.decode('utf-8', errors='replace')
                stderr_str = stderr.decode('utf-8', errors='replace')
                
                # Truncate output if too large
                if len(stdout_str) > self.config.max_output_size:
                    stdout_str = stdout_str[:self.config.max_output_size] + f"\n... Output truncated (max size: {self.config.max_output_size} bytes)"
                
                if len(stderr_str) > self.config.max_output_size:
                    stderr_str = stderr_str[:self.config.max_output_size] + f"\n... Error output truncated (max size: {self.config.max_output_size} bytes)"
                
                return {
                    "exit_code": process.returncode,
                    "stdout": stdout_str,
                    "stderr": stderr_str
                }
                
            except asyncio.TimeoutError:
                # Attempt to terminate the process
                if process and process.returncode is None:
                    try:
                        process.terminate()
                        # Wait a short time for graceful termination
                        try:
                            await asyncio.wait_for(process.wait(), 1.0)
                        except asyncio.TimeoutError:
                            # Force kill if termination didn't work
                            process.kill()
                    except Exception as e:
                        logger.warning(f"Error terminating process: {str(e)}")
                
                # Re-raise the TimeoutError to be caught by the calling method
                raise asyncio.TimeoutError(f"Command execution timed out after {timeout} seconds: {command}")
                
        except asyncio.TimeoutError:
            # Re-raise to be handled by the calling method
            raise
        except Exception as e:
            return {
                "exit_code": -1,
                "stdout": "",
                "stderr": f"Error executing command: {str(e)}"
            }
    
    async def _execute_in_docker(
        self,
        command: str,
        working_directory: str,
        env: Dict[str, str],
        timeout: int
    ) -> Dict[str, Any]:
        """
        Execute a command in a Docker container.
        
        Args:
            command: The command to execute
            working_directory: The working directory for the command
            env: Environment variables for the command
            timeout: Timeout in seconds
            
        Returns:
            Dict[str, Any]: The execution result
        """
        # This is a placeholder implementation
        # In a real implementation, this would use Docker Python SDK
        # to create and run a container with the command
        
        logger.warning("Docker sandbox not fully implemented, falling back to subprocess")
        return await self._execute_in_subprocess(command, working_directory, env, timeout)
    
    async def _log_execution(self, result: CommandExecutionResult) -> None:
        """
        Log command execution.
        
        Args:
            result: The execution result
        """
        log_file = os.path.join(self.config.log_directory, f"{result.command_id}.json")
        
        log_data = {
            "command_id": result.command_id,
            "command": result.command,
            "exit_code": result.exit_code,
            "execution_time": result.execution_time,
            "started_at": result.started_at,
            "completed_at": result.completed_at,
            "working_directory": result.working_directory,
            "environment_vars": result.environment_vars,
            "sandbox_type": result.sandbox_type,
            "metadata": result.metadata
        }
        
        # Include output if configured
        if self.config.log_output:
            log_data["stdout"] = result.stdout
            log_data["stderr"] = result.stderr
        
        # Write log file
        with open(log_file, 'w') as f:
            json.dump(log_data, f, indent=2)
    
    def get_pending_approvals(self) -> List[Dict[str, Any]]:
        """
        Get all pending command approvals.
        
        Returns:
            List[Dict[str, Any]]: List of pending approvals
        """
        return [
            {
                "approval_id": approval_id,
                "command": data["command"],
                "working_directory": data["working_directory"],
                "risk_level": data["validation_result"]["risk_level"],
                "requested_at": data["requested_at"]
            }
            for approval_id, data in self.pending_approvals.items()
        ]
    
    def get_execution_history(
        self,
        limit: Optional[int] = None,
        filter_successful: Optional[bool] = None
    ) -> List[CommandExecutionResult]:
        """
        Get command execution history.
        
        Args:
            limit: Maximum number of results to return
            filter_successful: Filter by success status
            
        Returns:
            List[CommandExecutionResult]: List of execution results
        """
        # Apply filters
        filtered_history = self.execution_history
        
        if filter_successful is not None:
            filtered_history = [
                result for result in filtered_history
                if (result.exit_code == 0) == filter_successful
            ]
        
        # Apply limit
        if limit is not None:
            filtered_history = filtered_history[-limit:]
        
        return filtered_history
    
    def reject_command(self, approval_id: str) -> bool:
        """
        Reject a pending command.
        
        Args:
            approval_id: The approval ID
            
        Returns:
            bool: True if successful
        """
        if approval_id not in self.pending_approvals:
            return False
        
        del self.pending_approvals[approval_id]
        logger.info(f"Command rejected: {approval_id}")
        return True 