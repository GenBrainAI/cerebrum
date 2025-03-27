"""
Intervention Interface component for the Self-Aware System.

This module provides functionality for managing human interventions in system
operations, with support for different levels of intervention, response actions,
and notification channels.
"""

import os
import json
import logging
import asyncio
from datetime import datetime, timedelta
from enum import Enum, auto
from typing import Dict, List, Optional, Any, Union, Callable, Awaitable

logger = logging.getLogger(__name__)


class InterventionLevel(Enum):
    """Levels of intervention, from least to most critical."""
    INFORMATION = 0  # Just informing the human, no response needed
    SUGGESTION = 1   # Seeking advice, but can proceed without it
    WARNING = 2      # Potential issue, human should approve
    CRITICAL = 3     # Serious issue, requires human approval
    EMERGENCY = 4    # System cannot proceed without human intervention


class InterventionStatus(Enum):
    """Possible statuses of an intervention request."""
    PENDING = "pending"     # Waiting for human response
    APPROVED = "approved"   # Human approved the action
    REJECTED = "rejected"   # Human rejected the action
    MODIFIED = "modified"   # Human modified and approved the action
    TIMEOUT = "timeout"     # No response within timeout period
    CLOSED = "closed"       # Intervention closed without response


class ResponseAction(Enum):
    """Possible actions in response to an intervention."""
    CONTINUE = "continue"     # Continue with the operation
    MODIFY = "modify"         # Modify the operation
    CANCEL = "cancel"         # Cancel the operation
    RETRY = "retry"           # Retry the operation
    ESCALATE = "escalate"     # Escalate to higher authority


class InterventionContext:
    """Context information for an intervention request."""
    
    def __init__(self, component: str, action: str, 
                data: Dict[str, Any] = None, timestamp: Optional[str] = None):
        """Initialize an intervention context."""
        self.component = component
        self.action = action
        self.data = data or {}
        self.timestamp = timestamp or datetime.now().isoformat()


class InterventionRequest:
    """A request for human intervention."""
    
    def __init__(self, title: str, description: str, 
                level: InterventionLevel = InterventionLevel.WARNING,
                options: List[str] = None, 
                context: Optional[InterventionContext] = None,
                require_response: bool = True):
        """Initialize an intervention request."""
        self.title = title
        self.description = description
        self.level = level
        self.options = options or ["approve", "reject"]
        self.context = context or InterventionContext(
            component="unknown",
            action="unknown"
        )
        self.require_response = require_response


class InterventionResponse:
    """A response to an intervention request."""
    
    def __init__(self, approved: bool, message: str = "", 
                action: Optional[ResponseAction] = None,
                modifications: Dict[str, Any] = None):
        """Initialize an intervention response."""
        self.approved = approved
        self.message = message
        self.action = action
        self.modifications = modifications or {}
        self.timestamp = datetime.now().isoformat()


class InterventionInterface:
    """
    Interface for managing human interventions in system operations.
    
    Features:
    - Different levels of intervention
    - Request/response cycle
    - Timeout handling
    - Notification through multiple channels
    - Callback support
    - Role-based interventions
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the Intervention Interface.
        
        Args:
            config: Configuration for the interface
                - auto_approve_level: Level at which interventions are auto-approved
                - default_timeout: Default timeout in seconds for intervention requests
                - notification_channels: Channels for sending notifications
                - storage_path: Path to store persistent data
                - require_authentication: Whether to require authentication for responses
                - allowed_roles: Roles allowed to respond to interventions
        """
        self.config = config or {
            "auto_approve_level": InterventionLevel.INFORMATION,
            "default_timeout": 3600,  # 1 hour
            "notification_channels": ["console"],
            "storage_path": "persistent_state/interventions",
            "require_authentication": False,
            "allowed_roles": ["operator", "admin", "supervisor"]
        }
        
        # Create storage directory if it doesn't exist
        if "storage_path" in self.config:
            os.makedirs(self.config["storage_path"], exist_ok=True)
        
        # Initialize data structures
        self.interventions: Dict[str, Dict[str, Any]] = {}
        self.callbacks: Dict[str, Union[Callable, Awaitable]] = {}
        self.timeout_tasks: Dict[str, asyncio.Task] = {}
    
    async def initialize(self):
        """Initialize the Intervention Interface."""
        logger.info("Initializing Intervention Interface")
        
        # Load any existing interventions
        if "storage_path" in self.config:
            interventions_dir = self.config["storage_path"]
            if os.path.exists(interventions_dir):
                for filename in os.listdir(interventions_dir):
                    if filename.endswith(".json"):
                        intervention_id = filename.replace(".json", "")
                        await self._load_intervention(intervention_id)
    
    async def cleanup(self):
        """Cancel all active timeout tasks and cleanup resources."""
        for intervention_id, task in list(self.timeout_tasks.items()):
            if not task.done() and not task.cancelled():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    logger.info(f"Timeout task for intervention {intervention_id} cancelled")
                except Exception as e:
                    logger.error(f"Error cleaning up timeout task for intervention {intervention_id}: {e}")
            
            # Remove task from dictionary
            self.timeout_tasks.pop(intervention_id, None)
        
        logger.info("Intervention Interface cleanup completed")
    
    async def request_intervention(self, 
                                  level: Union[InterventionLevel, int] = InterventionLevel.WARNING,
                                  message: Optional[str] = None,
                                  context: Optional[InterventionContext] = None,
                                  require_response: bool = True,
                                  timeout: Optional[float] = None,
                                  role: Optional[str] = None,
                                  callback: Optional[Union[Callable, Awaitable]] = None,
                                  request: Optional[InterventionRequest] = None) -> Dict[str, Any]:
        """
        Request human intervention for a system operation.
        
        Args:
            level: Level of intervention needed
            message: Message to display to the human (used if request is not provided)
            context: Context information for the intervention (used if request is not provided)
            require_response: Whether a response is required
            timeout: Timeout in seconds (default from config)
            role: Role required to respond to this intervention
            callback: Function to call when intervention is responded to
            request: Complete intervention request (alternative to providing individual parameters)
            
        Returns:
            Dictionary with intervention details
        """
        # Use request if provided, otherwise construct from parameters
        if request:
            intervention_request = request
            level = request.level
            require_response = request.require_response
        else:
            # Create context if not provided
            if not context:
                context = InterventionContext(
                    component="unknown",
                    action="unknown"
                )
            
            # Create request
            intervention_request = InterventionRequest(
                title=message or "Intervention required",
                description=message or "A system operation requires human intervention",
                level=level,
                options=["approve", "reject"],
                context=context,
                require_response=require_response
            )
        
        # Generate intervention ID
        intervention_id = f"int_{datetime.now().strftime('%Y%m%d%H%M%S')}_{len(self.interventions) + 1}"
        
        # Use default timeout if not specified
        if timeout is None:
            timeout = self.config.get("default_timeout", 3600)
        
        # Create intervention
        intervention = {
            "id": intervention_id,
            "request": {
                "title": intervention_request.title,
                "description": intervention_request.description,
                "options": intervention_request.options,
            },
            "level": intervention_request.level,
            "context": {
                "component": intervention_request.context.component,
                "action": intervention_request.context.action,
                "data": intervention_request.context.data,
                "timestamp": intervention_request.context.timestamp
            },
            "require_response": intervention_request.require_response,
            "status": InterventionStatus.PENDING,
            "created_at": datetime.now().isoformat(),
            "timeout_seconds": timeout,
            "role": role
        }
        
        # Store callback if provided
        if callback:
            self.callbacks[intervention_id] = callback
        
        # Auto-approve information-level interventions
        if level == InterventionLevel.INFORMATION or (isinstance(level, InterventionLevel) and 
                                                   level.value <= self.config.get("auto_approve_level", InterventionLevel.INFORMATION).value):
            # Auto-approve
            response = InterventionResponse(
                approved=True,
                message="Auto-approved information-level intervention",
                action=ResponseAction.CONTINUE
            )
            
            intervention["status"] = InterventionStatus.APPROVED
            intervention["response"] = {
                "approved": response.approved,
                "message": response.message,
                "action": response.action.value if response.action else None,
                "modifications": response.modifications,
                "timestamp": response.timestamp
            }
            intervention["responded_at"] = datetime.now().isoformat()
            
            # Call callback if provided
            if callback:
                if asyncio.iscoroutinefunction(callback):
                    asyncio.create_task(callback(intervention))
                else:
                    callback(intervention)
        else:
            # Set up timeout task if not auto-approved
            if timeout > 0:
                self.timeout_tasks[intervention_id] = asyncio.create_task(
                    self._handle_timeout(intervention_id, timeout)
                )
            
            # Send notification
            await self._send_notification(intervention)
        
        # Store intervention
        self.interventions[intervention_id] = intervention
        
        # Save to file
        await self._save_intervention(intervention_id)
        
        return intervention
    
    async def get_intervention(self, intervention_id: str) -> Dict[str, Any]:
        """Get details of a specific intervention."""
        if intervention_id not in self.interventions:
            raise ValueError(f"Intervention {intervention_id} not found")
        
        return self.interventions[intervention_id]
    
    async def respond_to_intervention(self, intervention_id: str, 
                                     response: Union[InterventionResponse, Dict[str, Any]]) -> Dict[str, Any]:
        """
        Respond to an intervention request.
        
        Args:
            intervention_id: ID of the intervention to respond to
            response: Response to the intervention
                
        Returns:
            Updated intervention details
        """
        if intervention_id not in self.interventions:
            raise ValueError(f"Intervention {intervention_id} not found")
        
        intervention = self.interventions[intervention_id]
        
        # Check if intervention is already resolved
        if intervention["status"] != InterventionStatus.PENDING:
            raise ValueError(f"Intervention {intervention_id} is already {intervention['status']}")
        
        # Convert dict to InterventionResponse if needed
        if isinstance(response, dict):
            response = InterventionResponse(
                approved=response.get("approved", False),
                message=response.get("message", ""),
                action=response.get("action"),
                modifications=response.get("modifications", {})
            )
        
        # Update intervention
        intervention["status"] = InterventionStatus.APPROVED if response.approved else InterventionStatus.REJECTED
        
        # If modifications are provided, mark as modified
        if response.approved and response.modifications:
            intervention["status"] = InterventionStatus.MODIFIED
        
        intervention["response"] = {
            "approved": response.approved,
            "message": response.message,
            "action": response.action.value if response.action else None,
            "modifications": response.modifications,
            "timestamp": response.timestamp
        }
        intervention["responded_at"] = datetime.now().isoformat()
        
        # Cancel timeout task if exists
        if intervention_id in self.timeout_tasks:
            self.timeout_tasks[intervention_id].cancel()
            del self.timeout_tasks[intervention_id]
        
        # Call callback if exists
        if intervention_id in self.callbacks:
            callback = self.callbacks[intervention_id]
            if asyncio.iscoroutinefunction(callback):
                asyncio.create_task(callback(intervention))
            else:
                callback(intervention)
        
        # Save updated intervention
        await self._save_intervention(intervention_id)
        
        return intervention
    
    async def get_pending_interventions(self, role: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get a list of pending interventions, optionally filtered by role.
        
        Args:
            role: Role to filter by
            
        Returns:
            List of pending interventions
        """
        pending = []
        
        for intervention in self.interventions.values():
            if intervention["status"] == InterventionStatus.PENDING:
                if role is None or intervention.get("role") == role:
                    pending.append(intervention)
        
        # Sort by level (higher level first) and then by creation time
        pending.sort(key=lambda x: (
            -x["level"].value if isinstance(x["level"], InterventionLevel) else -x["level"], 
            x["created_at"]
        ))
        
        return pending
    
    async def close_intervention(self, intervention_id: str, reason: str) -> Dict[str, Any]:
        """
        Close an intervention without a response.
        
        Args:
            intervention_id: ID of the intervention to close
            reason: Reason for closing
            
        Returns:
            Updated intervention details
        """
        if intervention_id not in self.interventions:
            raise ValueError(f"Intervention {intervention_id} not found")
        
        intervention = self.interventions[intervention_id]
        
        # Update intervention
        intervention["status"] = InterventionStatus.CLOSED
        intervention["closure_reason"] = reason
        intervention["closed_at"] = datetime.now().isoformat()
        
        # Cancel timeout task if exists
        if intervention_id in self.timeout_tasks:
            self.timeout_tasks[intervention_id].cancel()
            del self.timeout_tasks[intervention_id]
        
        # Save updated intervention
        await self._save_intervention(intervention_id)
        
        return intervention
    
    async def _handle_timeout(self, intervention_id: str, timeout: float):
        """Handle timeout for an intervention."""
        await asyncio.sleep(timeout)
        
        if intervention_id in self.interventions:
            intervention = self.interventions[intervention_id]
            
            # Only timeout if still pending
            if intervention["status"] == InterventionStatus.PENDING:
                logger.warning(f"Intervention {intervention_id} timed out after {timeout} seconds")
                
                # Update intervention
                intervention["status"] = InterventionStatus.TIMEOUT
                intervention["timeout_at"] = datetime.now().isoformat()
                
                # Call callback if exists
                if intervention_id in self.callbacks:
                    callback = self.callbacks[intervention_id]
                    if asyncio.iscoroutinefunction(callback):
                        asyncio.create_task(callback(intervention))
                    else:
                        callback(intervention)
                
                # Save updated intervention
                await self._save_intervention(intervention_id)
    
    async def _send_notification(self, intervention: Dict[str, Any]):
        """Send notification for an intervention."""
        channels = self.config.get("notification_channels", ["console"])
        
        for channel in channels:
            if channel == "console":
                logger.info(f"INTERVENTION REQUIRED: {intervention['id']} - "
                           f"Level: {intervention['level']} - "
                           f"{intervention['request']['title']}")
            # Add other notification channels here (email, SMS, etc.)
    
    async def _save_intervention(self, intervention_id: str):
        """Save an intervention to a file."""
        if "storage_path" not in self.config:
            return
        
        intervention = self.interventions[intervention_id]
        
        # Prepare for serialization
        serializable = dict(intervention)
        
        # Convert Enum values to strings/ints
        if isinstance(serializable["level"], InterventionLevel):
            serializable["level"] = serializable["level"].value
        
        if isinstance(serializable["status"], InterventionStatus):
            serializable["status"] = serializable["status"].value
        
        # Save to file
        file_path = os.path.join(self.config["storage_path"], f"{intervention_id}.json")
        with open(file_path, 'w') as f:
            json.dump(serializable, f, indent=2)
    
    async def _load_intervention(self, intervention_id: str):
        """Load an intervention from a file."""
        if "storage_path" not in self.config:
            return
        
        file_path = os.path.join(self.config["storage_path"], f"{intervention_id}.json")
        if not os.path.exists(file_path):
            logger.warning(f"Intervention file not found: {file_path}")
            return
        
        try:
            with open(file_path, 'r') as f:
                intervention = json.load(f)
            
            # Convert values to Enums
            if "level" in intervention:
                if isinstance(intervention["level"], int):
                    try:
                        intervention["level"] = InterventionLevel(intervention["level"])
                    except ValueError:
                        logger.warning(f"Invalid level value: {intervention['level']}")
                elif isinstance(intervention["level"], str):
                    try:
                        intervention["level"] = InterventionLevel[intervention["level"]]
                    except KeyError:
                        logger.warning(f"Invalid level value: {intervention['level']}")
            
            if "status" in intervention:
                if isinstance(intervention["status"], str):
                    try:
                        intervention["status"] = InterventionStatus(intervention["status"])
                    except ValueError:
                        logger.warning(f"Invalid status value: {intervention['status']}")
            
            self.interventions[intervention_id] = intervention
            
            # Set up timeout task if still pending
            if (intervention["status"] == InterventionStatus.PENDING and
                "timeout_seconds" in intervention):
                # Check if already timed out
                created_at = datetime.fromisoformat(intervention["created_at"])
                timeout = intervention["timeout_seconds"]
                elapsed = (datetime.now() - created_at).total_seconds()
                
                if elapsed < timeout:
                    # Still has time left
                    remaining = timeout - elapsed
                    self.timeout_tasks[intervention_id] = asyncio.create_task(
                        self._handle_timeout(intervention_id, remaining)
                    )
        except Exception as e:
            logger.error(f"Error loading intervention {intervention_id}: {e}")
    
    async def save_interventions(self, file_path: str):
        """Save all interventions to a single file."""
        # Convert interventions for serialization
        serializable = {}
        for intervention_id, intervention in self.interventions.items():
            # Copy to avoid modifying original
            serialized = dict(intervention)
            
            # Convert Enum values to strings/ints
            if isinstance(serialized["level"], InterventionLevel):
                serialized["level"] = serialized["level"].value
            
            if isinstance(serialized["status"], InterventionStatus):
                serialized["status"] = serialized["status"].value
            
            serializable[intervention_id] = serialized
        
        # Save to file
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, 'w') as f:
            json.dump(serializable, f, indent=2)
        
        logger.info(f"All interventions saved to {file_path}")
    
    async def load_interventions(self, file_path: str):
        """Load all interventions from a single file."""
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Interventions file not found: {file_path}")
        
        try:
            with open(file_path, 'r') as f:
                loaded = json.load(f)
            
            # Clear existing interventions
            self.interventions.clear()
            
            # Cancel existing timeout tasks
            for task in self.timeout_tasks.values():
                task.cancel()
            self.timeout_tasks.clear()
            
            # Load interventions
            for intervention_id, intervention in loaded.items():
                # Convert values to Enums
                if "level" in intervention:
                    if isinstance(intervention["level"], int):
                        try:
                            intervention["level"] = InterventionLevel(intervention["level"])
                        except ValueError:
                            logger.warning(f"Invalid level value: {intervention['level']}")
                    elif isinstance(intervention["level"], str):
                        try:
                            intervention["level"] = InterventionLevel[intervention["level"]]
                        except KeyError:
                            logger.warning(f"Invalid level value: {intervention['level']}")
                
                if "status" in intervention:
                    if isinstance(intervention["status"], str):
                        try:
                            intervention["status"] = InterventionStatus(intervention["status"])
                        except ValueError:
                            logger.warning(f"Invalid status value: {intervention['status']}")
                
                self.interventions[intervention_id] = intervention
                
                # Set up timeout task if still pending
                if (intervention["status"] == InterventionStatus.PENDING and
                    "timeout_seconds" in intervention and
                    "created_at" in intervention):
                    # Check if already timed out
                    created_at = datetime.fromisoformat(intervention["created_at"])
                    timeout = intervention["timeout_seconds"]
                    elapsed = (datetime.now() - created_at).total_seconds()
                    
                    if elapsed < timeout:
                        # Still has time left
                        remaining = timeout - elapsed
                        self.timeout_tasks[intervention_id] = asyncio.create_task(
                            self._handle_timeout(intervention_id, remaining)
                        )
            
            logger.info(f"Loaded {len(self.interventions)} interventions from {file_path}")
        except Exception as e:
            logger.error(f"Error loading interventions: {e}")
            raise 