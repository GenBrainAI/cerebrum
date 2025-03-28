from typing import Dict, List, Optional, Any, Set
import asyncio
import logging
import os
import json
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from enum import Enum
import jwt
from passlib.hash import bcrypt

from .intervention_interface import InterventionLevel, InterventionStatus, ResponseAction

logger = logging.getLogger(__name__)

class SupervisorRole(Enum):
    """Roles for supervisors in the system."""
    OBSERVER = "observer"       # Can view but not intervene
    OPERATOR = "operator"       # Basic intervention capabilities
    EXPERT = "expert"           # Domain-specific intervention
    SUPERVISOR = "supervisor"   # Can override operators and experts
    ADMIN = "admin"             # Full system control

class ApprovalStatus(Enum):
    """Status of an approval workflow."""
    WAITING = "waiting"         # Waiting for required approvals
    PARTIAL = "partial"         # Some approvals received
    APPROVED = "approved"       # All required approvals received
    REJECTED = "rejected"       # Rejected by at least one required approver
    EXPIRED = "expired"         # Approval window expired
    CANCELED = "canceled"       # Approval workflow canceled

class ApprovalPolicy:
    """Policy for approval workflows."""
    
    def __init__(self, name: str, description: str, 
                 required_roles: Dict[str, int], 
                 threshold_percentage: int = 75,
                 expiration_hours: int = 24,
                 consecutive_order: bool = False,
                 enable_override: bool = True,
                 rejection_blocks: bool = True):
        """
        Initialize approval policy.
        
        Args:
            name: Policy name
            description: Policy description
            required_roles: Dict mapping role names to minimum count required
            threshold_percentage: Percentage of approvers needed
            expiration_hours: Hours until request expires
            consecutive_order: Whether approvals must happen in order
            enable_override: Whether admin can override
            rejection_blocks: Whether a single rejection blocks
        """
        self.name = name
        self.description = description
        self.required_roles = required_roles
        self.threshold_percentage = threshold_percentage
        self.expiration_hours = expiration_hours
        self.consecutive_order = consecutive_order
        self.enable_override = enable_override
        self.rejection_blocks = rejection_blocks
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "name": self.name,
            "description": self.description,
            "required_roles": self.required_roles,
            "threshold_percentage": self.threshold_percentage,
            "expiration_hours": self.expiration_hours,
            "consecutive_order": self.consecutive_order,
            "enable_override": self.enable_override,
            "rejection_blocks": self.rejection_blocks
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ApprovalPolicy':
        """Create from dictionary."""
        return cls(
            name=data.get("name", "Default Policy"),
            description=data.get("description", ""),
            required_roles=data.get("required_roles", {}),
            threshold_percentage=data.get("threshold_percentage", 75),
            expiration_hours=data.get("expiration_hours", 24),
            consecutive_order=data.get("consecutive_order", False),
            enable_override=data.get("enable_override", True),
            rejection_blocks=data.get("rejection_blocks", True)
        )

class ApprovalWorkflow:
    """Workflow for multi-person approval."""
    
    def __init__(self, workflow_id: str, title: str, description: str,
                 policy: ApprovalPolicy, created_by: str,
                 metadata: Optional[Dict[str, Any]] = None):
        """
        Initialize approval workflow.
        
        Args:
            workflow_id: Unique workflow ID
            title: Workflow title
            description: Workflow description
            policy: Approval policy
            created_by: ID of supervisor who created workflow
            metadata: Additional metadata
        """
        self.id = workflow_id
        self.title = title
        self.description = description
        self.policy = policy
        self.created_by = created_by
        self.created_at = datetime.now().isoformat()
        
        # Calculate expiration
        expires_at = datetime.now() + timedelta(hours=policy.expiration_hours)
        self.expires_at = expires_at.isoformat()
        
        self.status = ApprovalStatus.WAITING
        self.approvals = {}  # supervisor_id -> approval info
        self.rejections = {}  # supervisor_id -> rejection info
        self.metadata = metadata or {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "policy": self.policy.to_dict(),
            "created_by": self.created_by,
            "created_at": self.created_at,
            "expires_at": self.expires_at,
            "status": self.status.value,
            "approvals": self.approvals,
            "rejections": self.rejections,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ApprovalWorkflow':
        """Create from dictionary."""
        # Create instance
        workflow = cls(
            workflow_id=data.get("id", str(uuid.uuid4())),
            title=data.get("title", ""),
            description=data.get("description", ""),
            policy=ApprovalPolicy.from_dict(data.get("policy", {})),
            created_by=data.get("created_by", ""),
            metadata=data.get("metadata", {})
        )
        
        # Override defaults
        workflow.created_at = data.get("created_at", workflow.created_at)
        workflow.expires_at = data.get("expires_at", workflow.expires_at)
        
        # Convert status from string
        status_val = data.get("status", "waiting")
        try:
            workflow.status = ApprovalStatus(status_val)
        except ValueError:
            workflow.status = ApprovalStatus.WAITING
        
        workflow.approvals = data.get("approvals", {})
        workflow.rejections = data.get("rejections", {})
        
        return workflow

class SupervisionHub:
    """Manages supervision by multiple humans with different roles."""
    
    def __init__(self, storage_path: Optional[str] = None, config: Optional[Dict[str, Any]] = None):
        """
        Initialize with storage path for supervision data.
        
        Args:
            storage_path: Path to store supervision data
            config: Configuration options
        """
        self.storage_path = storage_path or os.path.join(os.path.expanduser("~"), ".cerebrum", "supervision")
        os.makedirs(self.storage_path, exist_ok=True)
        
        # Set default configuration
        self.config = {
            "jwt_secret": os.environ.get("SUPERVISION_JWT_SECRET", "cerebrum_supervision_secret"),
            "token_expiry_hours": 24,
            "enable_websocket_notifications": True,
            "notification_retention_days": 30,
            "default_approval_timeout_hours": 24,
            "password_min_length": 8,
            "intervention_level_role_map": {
                "information": "observer",
                "suggestion": "operator",
                "warning": "operator",
                "critical": "supervisor",
                "emergency": "admin"
            }
        }
        
        # Override with provided config
        if config:
            self.config.update(config)
        
        # Create subdirectories
        self.supervisors_path = os.path.join(self.storage_path, "supervisors")
        self.requests_path = os.path.join(self.storage_path, "requests")
        self.notifications_path = os.path.join(self.storage_path, "notifications")
        self.logs_path = os.path.join(self.storage_path, "logs")
        self.policies_path = os.path.join(self.storage_path, "policies")
        self.workflows_path = os.path.join(self.storage_path, "workflows")
        
        os.makedirs(self.supervisors_path, exist_ok=True)
        os.makedirs(self.requests_path, exist_ok=True)
        os.makedirs(self.notifications_path, exist_ok=True)
        os.makedirs(self.logs_path, exist_ok=True)
        os.makedirs(self.policies_path, exist_ok=True)
        os.makedirs(self.workflows_path, exist_ok=True)
        
        # Load existing data
        self.supervisors: Dict[str, Dict[str, Any]] = self._load_supervisors()
        self.requests: Dict[str, Dict[str, Any]] = self._load_requests()
        self.notifications: Dict[str, Dict[str, Any]] = self._load_notifications()
        self.policies: Dict[str, ApprovalPolicy] = self._load_policies()
        self.workflows: Dict[str, ApprovalWorkflow] = self._load_workflows()
        
        # Active WebSocket connections for real-time notifications
        self.websocket_connections: Dict[str, Any] = {}
        
        # Intervention interface reference (for integration)
        self.intervention_interface = None
    
    async def register_supervisor(self, username: str, name: str, email: str, 
                                password: str, roles: List[str], 
                                permissions: Optional[Dict[str, List[str]]] = None) -> Dict[str, Any]:
        """
        Register a new supervisor with secure credentials.
        
        Args:
            username: Unique username for the supervisor
            name: Full name of the supervisor
            email: Email address
            password: Password (will be hashed)
            roles: List of role names
            permissions: Dict mapping components to allowed actions
            
        Returns:
            Dictionary with registration result
        """
        # Check if username already exists
        for supervisor_id, supervisor in self.supervisors.items():
            if supervisor.get("username") == username:
                return {
                    "success": False,
                    "message": f"Supervisor with username {username} already exists"
                }
        
        # Validate password
        if len(password) < self.config["password_min_length"]:
            return {
                "success": False,
                "message": f"Password must be at least {self.config['password_min_length']} characters"
            }
        
        # Hash password
        password_hash = bcrypt.hash(password)
        
        # Generate supervisor ID
        supervisor_id = str(uuid.uuid4())
        
        # Process roles and permissions
        validated_roles = []
        for role in roles:
            try:
                # Convert string role to enum if possible
                validated_roles.append(SupervisorRole(role).value)
            except ValueError:
                # If not a valid enum, use as-is
                validated_roles.append(role)
        
        processed_permissions = {}
        if permissions:
            for component, actions in permissions.items():
                processed_permissions[component] = list(set(actions))  # Deduplicate
        
        # Create supervisor record
        supervisor = {
            "id": supervisor_id,
            "username": username,
            "name": name,
            "email": email,
            "password_hash": password_hash,
            "roles": validated_roles,
            "permissions": processed_permissions,
            "created_at": datetime.now().isoformat(),
            "last_active": datetime.now().isoformat(),
            "approved_requests": [],
            "rejected_requests": [],
            "pending_notifications": []
        }
        
        # Save supervisor
        self.supervisors[supervisor_id] = supervisor
        self._save_supervisor(supervisor_id, supervisor)
        
        # Log the registration
        await self._log_event(
            event_type="supervisor_registered",
            details={
                "supervisor_id": supervisor_id,
                "username": username,
                "roles": validated_roles,
                # Don't log permissions for security
            }
        )
        
        # Generate auth token
        token = self._generate_auth_token(supervisor_id, username, validated_roles)
        
        return {
            "success": True,
            "message": f"Supervisor {username} registered successfully",
            "supervisor_id": supervisor_id,
            "roles": validated_roles,
            "token": token
        }
    
    def _generate_auth_token(self, supervisor_id: str, username: str, roles: List[str]) -> str:
        """Generate JWT authentication token for supervisor."""
        expiry = datetime.now() + timedelta(hours=self.config["token_expiry_hours"])
        
        payload = {
            "sub": supervisor_id,
            "username": username,
            "roles": roles,
            "exp": expiry.timestamp()
        }
        
        return jwt.encode(payload, self.config["jwt_secret"], algorithm="HS256")
    
    async def authenticate_supervisor(self, username: str, password: str) -> Dict[str, Any]:
        """
        Authenticate a supervisor with username and password.
        
        Args:
            username: Supervisor username
            password: Supervisor password
            
        Returns:
            Dictionary with authentication result
        """
        # Find supervisor by username
        supervisor_id = None
        supervisor = None
        
        for sup_id, sup in self.supervisors.items():
            if sup.get("username") == username:
                supervisor_id = sup_id
                supervisor = sup
                break
        
        if not supervisor:
            return {
                "success": False,
                "message": "Invalid username or password"
            }
        
        # Verify password
        if not bcrypt.verify(password, supervisor["password_hash"]):
            return {
                "success": False,
                "message": "Invalid username or password"
            }
        
        # Update last active
        supervisor["last_active"] = datetime.now().isoformat()
        self._save_supervisor(supervisor_id, supervisor)
        
        # Log the authentication
        await self._log_event(
            event_type="supervisor_authenticated",
            details={
                "supervisor_id": supervisor_id,
                "username": username
            }
        )
        
        # Generate auth token
        token = self._generate_auth_token(supervisor_id, username, supervisor["roles"])
        
        return {
            "success": True,
            "message": "Authentication successful",
            "supervisor_id": supervisor_id,
            "username": username,
            "name": supervisor.get("name", ""),
            "roles": supervisor["roles"],
            "token": token
        }
    
    async def create_approval_request(self, operation_type: str, details: Dict[str, Any], 
                                     required_role: str) -> str:
        """
        Create a request for approval of an operation.
        
        Args:
            operation_type: Type of operation (e.g., "package_install", "git_push")
            details: Dictionary with operation details
            required_role: Role required to approve this request
            
        Returns:
            Request ID
        """
        # Generate request ID
        request_id = str(uuid.uuid4())
        
        # Create request record
        request = {
            "id": request_id,
            "operation_type": operation_type,
            "details": details,
            "required_role": required_role,
            "status": "pending",
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "approved_by": None,
            "rejected_by": None,
            "approval_time": None,
            "rejection_time": None,
            "comments": None
        }
        
        # Save request
        self.requests[request_id] = request
        self._save_request(request_id, request)
        
        # Log the request creation
        await self._log_event(
            event_type="approval_request_created",
            details={
                "request_id": request_id,
                "operation_type": operation_type,
                "required_role": required_role
            }
        )
        
        # Create notifications for eligible supervisors
        eligible_supervisors = [
            supervisor_id for supervisor_id, supervisor in self.supervisors.items()
            if required_role in supervisor["roles"]
        ]
        
        for supervisor_id in eligible_supervisors:
            await self.create_notification(
                supervisor_ids=[supervisor_id],
                message=f"New approval request for {operation_type}",
                level="info",
                context={
                    "request_id": request_id,
                    "operation_type": operation_type
                }
            )
        
        return request_id
    
    async def approve_request(self, request_id: str, supervisor_id: str, 
                             comments: Optional[str] = None) -> Dict[str, Any]:
        """
        Approve a pending request.
        
        Args:
            request_id: ID of the request to approve
            supervisor_id: ID of the supervisor approving the request
            comments: Optional comments about the approval
            
        Returns:
            Dictionary with approval result
        """
        # Check if request exists
        if request_id not in self.requests:
            return {
                "success": False,
                "message": f"Request with ID {request_id} not found",
                "request_id": request_id
            }
        
        # Check if supervisor exists
        if supervisor_id not in self.supervisors:
            return {
                "success": False,
                "message": f"Supervisor with ID {supervisor_id} not found",
                "supervisor_id": supervisor_id
            }
        
        # Get request and supervisor
        request = self.requests[request_id]
        supervisor = self.supervisors[supervisor_id]
        
        # Check if request is pending
        if request["status"] != "pending":
            return {
                "success": False,
                "message": f"Request with ID {request_id} is not pending (status: {request['status']})",
                "request_id": request_id,
                "status": request["status"]
            }
        
        # Check if supervisor has the required role
        if request["required_role"] not in supervisor["roles"]:
            return {
                "success": False,
                "message": f"Supervisor {supervisor_id} does not have the required role ({request['required_role']})",
                "supervisor_id": supervisor_id,
                "supervisor_roles": supervisor["roles"],
                "required_role": request["required_role"]
            }
        
        # Update request
        request["status"] = "approved"
        request["approved_by"] = supervisor_id
        request["approval_time"] = datetime.now().isoformat()
        request["updated_at"] = datetime.now().isoformat()
        request["comments"] = comments
        
        # Update supervisor
        supervisor["approved_requests"].append(request_id)
        supervisor["last_active"] = datetime.now().isoformat()
        
        # Save changes
        self._save_request(request_id, request)
        self._save_supervisor(supervisor_id, supervisor)
        
        # If this is an intervention request, update the intervention
        if (request["operation_type"] == "intervention_response" and 
            "intervention_id" in request["details"] and 
            self.intervention_interface):
            
            intervention_id = request["details"]["intervention_id"]
            
            # Check if intervention exists in the interface
            if hasattr(self.intervention_interface, "interventions") and intervention_id in self.intervention_interface.interventions:
                # Update intervention status
                intervention = self.intervention_interface.interventions[intervention_id]
                intervention["status"] = InterventionStatus.RESOLVED.value
                
                # Create response
                intervention["response"] = {
                    "approved": True,
                    "message": comments or "Request approved",
                    "action": ResponseAction.CONTINUE.value,
                    "modifications": {},
                    "timestamp": datetime.now().isoformat(),
                    "supervisor_id": supervisor_id
                }
                
                intervention["responded_at"] = datetime.now().isoformat()
                
                # Save the updated intervention
                if hasattr(self.intervention_interface, "_save_intervention"):
                    await self.intervention_interface._save_intervention(intervention_id)
        
        # Log the approval
        await self._log_event(
            event_type="request_approved",
            details={
                "request_id": request_id,
                "supervisor_id": supervisor_id,
                "operation_type": request["operation_type"],
                "comments": comments
            }
        )
        
        return {
            "success": True,
            "message": f"Request {request_id} approved by supervisor {supervisor_id}",
            "request_id": request_id,
            "supervisor_id": supervisor_id,
            "operation_type": request["operation_type"],
            "details": request["details"]
        }
    
    async def reject_request(self, request_id: str, supervisor_id: str, 
                            reason: str) -> Dict[str, Any]:
        """
        Reject a pending request.
        
        Args:
            request_id: ID of the request to reject
            supervisor_id: ID of the supervisor rejecting the request
            reason: Reason for rejection
            
        Returns:
            Dictionary with rejection result
        """
        # Check if request exists
        if request_id not in self.requests:
            return {
                "success": False,
                "message": f"Request with ID {request_id} not found",
                "request_id": request_id
            }
        
        # Check if supervisor exists
        if supervisor_id not in self.supervisors:
            return {
                "success": False,
                "message": f"Supervisor with ID {supervisor_id} not found",
                "supervisor_id": supervisor_id
            }
        
        # Get request and supervisor
        request = self.requests[request_id]
        supervisor = self.supervisors[supervisor_id]
        
        # Check if request is pending
        if request["status"] != "pending":
            return {
                "success": False,
                "message": f"Request with ID {request_id} is not pending (status: {request['status']})",
                "request_id": request_id,
                "status": request["status"]
            }
        
        # Check if supervisor has the required role
        if request["required_role"] not in supervisor["roles"]:
            return {
                "success": False,
                "message": f"Supervisor {supervisor_id} does not have the required role ({request['required_role']})",
                "supervisor_id": supervisor_id,
                "supervisor_roles": supervisor["roles"],
                "required_role": request["required_role"]
            }
        
        # Update request
        request["status"] = "rejected"
        request["rejected_by"] = supervisor_id
        request["rejection_time"] = datetime.now().isoformat()
        request["updated_at"] = datetime.now().isoformat()
        request["comments"] = reason
        
        # Update supervisor
        supervisor["rejected_requests"].append(request_id)
        supervisor["last_active"] = datetime.now().isoformat()
        
        # Save changes
        self._save_request(request_id, request)
        self._save_supervisor(supervisor_id, supervisor)
        
        # If this is an intervention request, update the intervention
        if (request["operation_type"] == "intervention_response" and 
            "intervention_id" in request["details"] and 
            self.intervention_interface):
            
            intervention_id = request["details"]["intervention_id"]
            
            # Check if intervention exists in the interface
            if hasattr(self.intervention_interface, "interventions") and intervention_id in self.intervention_interface.interventions:
                # Update intervention status
                intervention = self.intervention_interface.interventions[intervention_id]
                intervention["status"] = InterventionStatus.DISMISSED.value
                
                # Create response
                intervention["response"] = {
                    "approved": False,
                    "message": reason,
                    "action": ResponseAction.CANCEL.value,
                    "modifications": {},
                    "timestamp": datetime.now().isoformat(),
                    "supervisor_id": supervisor_id
                }
                
                intervention["responded_at"] = datetime.now().isoformat()
                
                # Save the updated intervention
                if hasattr(self.intervention_interface, "_save_intervention"):
                    await self.intervention_interface._save_intervention(intervention_id)
        
        # Log the rejection
        await self._log_event(
            event_type="request_rejected",
            details={
                "request_id": request_id,
                "supervisor_id": supervisor_id,
                "operation_type": request["operation_type"],
                "reason": reason
            }
        )
        
        return {
            "success": True,
            "message": f"Request {request_id} rejected by supervisor {supervisor_id}",
            "request_id": request_id,
            "supervisor_id": supervisor_id,
            "operation_type": request["operation_type"],
            "reason": reason
        }
    
    async def get_pending_requests(self, supervisor_id: Optional[str] = None, 
                                  role: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get pending approval requests, optionally filtered by supervisor or role.
        
        Args:
            supervisor_id: Optional supervisor ID to filter by
            role: Optional role to filter by
            
        Returns:
            List of pending requests
        """
        # Filter requests
        pending_requests = []
        
        for request_id, request in self.requests.items():
            if request["status"] != "pending":
                continue
                
            if role and request["required_role"] != role:
                continue
                
            if supervisor_id:
                # Check if supervisor has the required role
                if supervisor_id not in self.supervisors:
                    continue
                    
                if request["required_role"] not in self.supervisors[supervisor_id]["roles"]:
                    continue
            
            pending_requests.append(request)
        
        return pending_requests
    
    async def create_notification(self, supervisor_ids: List[str], message: str, 
                                 level: str = "info", context: Optional[Dict[str, Any]] = None) -> str:
        """
        Create a notification for supervisors and send via WebSocket if available.
        
        Args:
            supervisor_ids: List of supervisor IDs to notify
            message: Notification message
            level: Notification level (info, warning, error)
            context: Optional context information
            
        Returns:
            Notification ID
        """
        # Generate notification ID
        notification_id = str(uuid.uuid4())
        
        # Create notification record
        notification = {
            "id": notification_id,
            "message": message,
            "level": level,
            "context": context or {},
            "created_at": datetime.now().isoformat(),
            "supervisor_ids": supervisor_ids,
            "read_by": []
        }
        
        # Save notification
        self.notifications[notification_id] = notification
        self._save_notification(notification_id, notification)
        
        # Update supervisors
        for supervisor_id in supervisor_ids:
            if supervisor_id in self.supervisors:
                self.supervisors[supervisor_id]["pending_notifications"].append(notification_id)
                self._save_supervisor(supervisor_id, self.supervisors[supervisor_id])
        
        # Log the notification creation
        await self._log_event(
            event_type="notification_created",
            details={
                "notification_id": notification_id,
                "supervisor_ids": supervisor_ids,
                "level": level,
                "message": message
            }
        )
        
        # Send via WebSocket if enabled
        if self.config.get("enable_websocket_notifications", True):
            await self.notify_supervisors_websocket(
                supervisor_ids=supervisor_ids,
                event_type="notification",
                data=notification
            )
        
        return notification_id
    
    async def mark_notification_read(self, notification_id: str, supervisor_id: str) -> Dict[str, Any]:
        """
        Mark a notification as read by a supervisor.
        
        Args:
            notification_id: ID of the notification
            supervisor_id: ID of the supervisor
            
        Returns:
            Dictionary with result
        """
        # Check if notification exists
        if notification_id not in self.notifications:
            return {
                "success": False,
                "message": f"Notification with ID {notification_id} not found",
                "notification_id": notification_id
            }
        
        # Check if supervisor exists
        if supervisor_id not in self.supervisors:
            return {
                "success": False,
                "message": f"Supervisor with ID {supervisor_id} not found",
                "supervisor_id": supervisor_id
            }
        
        # Get notification and supervisor
        notification = self.notifications[notification_id]
        supervisor = self.supervisors[supervisor_id]
        
        # Check if notification is for this supervisor
        if supervisor_id not in notification["supervisor_ids"]:
            return {
                "success": False,
                "message": f"Notification {notification_id} is not for supervisor {supervisor_id}",
                "notification_id": notification_id,
                "supervisor_id": supervisor_id
            }
        
        # Check if already read
        if supervisor_id in notification["read_by"]:
            return {
                "success": True,
                "message": f"Notification {notification_id} already marked as read by supervisor {supervisor_id}",
                "notification_id": notification_id,
                "supervisor_id": supervisor_id
            }
        
        # Update notification
        notification["read_by"].append(supervisor_id)
        
        # Update supervisor
        if notification_id in supervisor["pending_notifications"]:
            supervisor["pending_notifications"].remove(notification_id)
        
        supervisor["last_active"] = datetime.now().isoformat()
        
        # Save changes
        self._save_notification(notification_id, notification)
        self._save_supervisor(supervisor_id, supervisor)
        
        return {
            "success": True,
            "message": f"Notification {notification_id} marked as read by supervisor {supervisor_id}",
            "notification_id": notification_id,
            "supervisor_id": supervisor_id
        }
    
    async def get_supervisor_notifications(self, supervisor_id: str, 
                                          include_read: bool = False) -> List[Dict[str, Any]]:
        """
        Get notifications for a supervisor.
        
        Args:
            supervisor_id: ID of the supervisor
            include_read: Whether to include read notifications
            
        Returns:
            List of notifications
        """
        # Check if supervisor exists
        if supervisor_id not in self.supervisors:
            return []
        
        # Get supervisor
        supervisor = self.supervisors[supervisor_id]
        
        # Get notifications
        notifications = []
        
        for notification_id, notification in self.notifications.items():
            if supervisor_id not in notification["supervisor_ids"]:
                continue
                
            if not include_read and supervisor_id in notification["read_by"]:
                continue
                
            notifications.append(notification)
        
        # Sort by creation time (newest first)
        notifications.sort(key=lambda n: n["created_at"], reverse=True)
        
        return notifications
    
    async def get_request_history(self, operation_type: Optional[str] = None, 
                                 supervisor_id: Optional[str] = None,
                                 status: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get request history, optionally filtered.
        
        Args:
            operation_type: Optional operation type to filter by
            supervisor_id: Optional supervisor ID to filter by
            status: Optional status to filter by
            
        Returns:
            List of requests
        """
        # Filter requests
        filtered_requests = []
        
        for request_id, request in self.requests.items():
            if operation_type and request["operation_type"] != operation_type:
                continue
                
            if status and request["status"] != status:
                continue
                
            if supervisor_id:
                if request["status"] == "approved" and request["approved_by"] != supervisor_id:
                    continue
                    
                if request["status"] == "rejected" and request["rejected_by"] != supervisor_id:
                    continue
            
            filtered_requests.append(request)
        
        # Sort by update time (newest first)
        filtered_requests.sort(key=lambda r: r["updated_at"], reverse=True)
        
        return filtered_requests
    
    def _load_supervisors(self) -> Dict[str, Dict[str, Any]]:
        """Load supervisors from storage."""
        supervisors = {}
        
        try:
            for file_path in Path(self.supervisors_path).glob("*.json"):
                with open(file_path, "r") as f:
                    supervisor = json.load(f)
                    supervisors[supervisor["id"]] = supervisor
        except Exception as e:
            logger.exception(f"Error loading supervisors: {e}")
        
        return supervisors
    
    def _load_requests(self) -> Dict[str, Dict[str, Any]]:
        """Load requests from storage."""
        requests = {}
        
        try:
            for file_path in Path(self.requests_path).glob("*.json"):
                with open(file_path, "r") as f:
                    request = json.load(f)
                    requests[request["id"]] = request
        except Exception as e:
            logger.exception(f"Error loading requests: {e}")
        
        return requests
    
    def _load_notifications(self) -> Dict[str, Dict[str, Any]]:
        """Load notifications from storage."""
        notifications = {}
        
        try:
            for file_path in Path(self.notifications_path).glob("*.json"):
                with open(file_path, "r") as f:
                    notification = json.load(f)
                    notifications[notification["id"]] = notification
        except Exception as e:
            logger.exception(f"Error loading notifications: {e}")
        
        return notifications
    
    def _load_policies(self) -> Dict[str, ApprovalPolicy]:
        """Load approval policies from storage."""
        policies = {}
        
        try:
            for file_path in Path(self.policies_path).glob("*.json"):
                with open(file_path, "r") as f:
                    policy_data = json.load(f)
                    policy_id = policy_data.get("id")
                    if policy_id:
                        policies[policy_id] = ApprovalPolicy.from_dict(policy_data)
        except Exception as e:
            logger.exception(f"Error loading policies: {e}")
        
        # Create default policy if none exist
        if not policies:
            default_policy = ApprovalPolicy(
                name="Default Policy",
                description="Default approval policy requiring supervisor approval",
                required_roles={"supervisor": 1}
            )
            policy_id = "default_policy"
            policies[policy_id] = default_policy
            self._save_policy(policy_id, default_policy)
        
        return policies
    
    def _save_policy(self, policy_id: str, policy: ApprovalPolicy) -> None:
        """Save approval policy to storage."""
        try:
            policy_data = policy.to_dict()
            policy_data["id"] = policy_id
            
            file_path = os.path.join(self.policies_path, f"{policy_id}.json")
            with open(file_path, "w") as f:
                json.dump(policy_data, f, indent=2)
        except Exception as e:
            logger.exception(f"Error saving policy {policy_id}: {e}")
    
    def _load_workflows(self) -> Dict[str, ApprovalWorkflow]:
        """Load approval workflows from storage."""
        workflows = {}
        
        try:
            for file_path in Path(self.workflows_path).glob("*.json"):
                with open(file_path, "r") as f:
                    workflow_data = json.load(f)
                    workflow_id = workflow_data.get("id")
                    if workflow_id:
                        workflows[workflow_id] = ApprovalWorkflow.from_dict(workflow_data)
        except Exception as e:
            logger.exception(f"Error loading workflows: {e}")
        
        return workflows
    
    def _save_workflow(self, workflow_id: str, workflow: ApprovalWorkflow) -> None:
        """Save approval workflow to storage."""
        try:
            file_path = os.path.join(self.workflows_path, f"{workflow_id}.json")
            with open(file_path, "w") as f:
                json.dump(workflow.to_dict(), f, indent=2)
        except Exception as e:
            logger.exception(f"Error saving workflow {workflow_id}: {e}")
    
    def _save_supervisor(self, supervisor_id: str, supervisor: Dict[str, Any]) -> None:
        """Save supervisor to storage."""
        try:
            file_path = os.path.join(self.supervisors_path, f"{supervisor_id}.json")
            with open(file_path, "w") as f:
                json.dump(supervisor, f, indent=2)
        except Exception as e:
            logger.exception(f"Error saving supervisor {supervisor_id}: {e}")
    
    def _save_request(self, request_id: str, request: Dict[str, Any]) -> None:
        """Save request to storage."""
        try:
            file_path = os.path.join(self.requests_path, f"{request_id}.json")
            with open(file_path, "w") as f:
                json.dump(request, f, indent=2)
        except Exception as e:
            logger.exception(f"Error saving request {request_id}: {e}")
    
    def _save_notification(self, notification_id: str, notification: Dict[str, Any]) -> None:
        """Save notification to storage."""
        try:
            file_path = os.path.join(self.notifications_path, f"{notification_id}.json")
            with open(file_path, "w") as f:
                json.dump(notification, f, indent=2)
        except Exception as e:
            logger.exception(f"Error saving notification {notification_id}: {e}")
    
    async def _log_event(self, event_type: str, details: Dict[str, Any]) -> None:
        """Log an event to the supervision log."""
        try:
            event = {
                "id": str(uuid.uuid4()),
                "type": event_type,
                "timestamp": datetime.now().isoformat(),
                "details": details
            }
            
            # Create log file for the current day
            date_str = datetime.now().strftime("%Y-%m-%d")
            log_file = os.path.join(self.logs_path, f"{date_str}.jsonl")
            
            # Append event to log file
            with open(log_file, "a") as f:
                f.write(json.dumps(event) + "\n")
        except Exception as e:
            logger.exception(f"Error logging event: {e}")
    
    async def get_supervision_logs(self, start_date: Optional[str] = None, 
                                  end_date: Optional[str] = None,
                                  event_types: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """
        Get supervision logs, optionally filtered.
        
        Args:
            start_date: Optional start date (YYYY-MM-DD)
            end_date: Optional end date (YYYY-MM-DD)
            event_types: Optional list of event types to include
            
        Returns:
            List of log events
        """
        logs = []
        
        try:
            # Determine date range
            if start_date:
                start = datetime.strptime(start_date, "%Y-%m-%d")
            else:
                # Default to 7 days ago
                start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
                start = start.replace(day=start.day - 7)
            
            if end_date:
                end = datetime.strptime(end_date, "%Y-%m-%d")
            else:
                # Default to today
                end = datetime.now().replace(hour=23, minute=59, second=59, microsecond=999999)
            
            # Get log files in date range
            current_date = start.replace(hour=0, minute=0, second=0, microsecond=0)
            while current_date <= end:
                date_str = current_date.strftime("%Y-%m-%d")
                log_file = os.path.join(self.logs_path, f"{date_str}.jsonl")
                
                if os.path.isfile(log_file):
                    with open(log_file, "r") as f:
                        for line in f:
                            event = json.loads(line.strip())
                            
                            # Filter by event type
                            if event_types and event["type"] not in event_types:
                                continue
                                
                            # Filter by timestamp
                            timestamp = datetime.fromisoformat(event["timestamp"])
                            if timestamp < start or timestamp > end:
                                continue
                                
                            logs.append(event)
                
                # Move to next day
                current_date = current_date.replace(day=current_date.day + 1)
            
            # Sort by timestamp (newest first)
            logs.sort(key=lambda e: e["timestamp"], reverse=True)
        except Exception as e:
            logger.exception(f"Error getting supervision logs: {e}")
        
        return logs
    
    async def set_intervention_interface(self, interface: Any) -> None:
        """
        Set the intervention interface for integration.
        
        Args:
            interface: The InterventionInterface instance
        """
        self.intervention_interface = interface
        logger.info("Intervention interface connected to Supervision Hub")
    
    async def handle_intervention_request(self, intervention_id: str, level: InterventionLevel, 
                                        title: str, description: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle an intervention request from the InterventionInterface.
        
        Args:
            intervention_id: ID of the intervention
            level: Intervention level
            title: Intervention title
            description: Intervention description
            context: Intervention context
            
        Returns:
            Dictionary with handling result
        """
        # Map intervention level to required role
        level_role_map = self.config["intervention_level_role_map"]
        level_name = level.name.lower()
        required_role = level_role_map.get(level_name, "supervisor")
        
        # Create the intervention if it doesn't exist and we have an intervention interface
        if self.intervention_interface and intervention_id not in getattr(self.intervention_interface, "interventions", {}):
            # Create intervention context
            intervention_context = {
                "component": context.get("component", "unknown"),
                "action": context.get("action", "unknown"),
                "data": context,
                "timestamp": datetime.now().isoformat()
            }
            
            # Create the intervention in the interface
            intervention = {
                "id": intervention_id,
                "request": {
                    "title": title,
                    "description": description,
                    "options": ["approve", "reject"],
                },
                "level": level,
                "context": intervention_context,
                "require_response": True,
                "status": InterventionStatus.PENDING,
                "created_at": datetime.now().isoformat(),
                "timeout_seconds": self.config.get("default_intervention_timeout", 3600),
                "role": required_role
            }
            
            # Add to interface's interventions
            self.intervention_interface.interventions[intervention_id] = intervention
            
            # Save the intervention
            if hasattr(self.intervention_interface, "_save_intervention"):
                await self.intervention_interface._save_intervention(intervention_id)
        
        # Create workflow if high-level intervention
        if level in [InterventionLevel.CRITICAL, InterventionLevel.EMERGENCY]:
            # Use policy with stricter requirements for emergency
            policy_name = "emergency_policy" if level == InterventionLevel.EMERGENCY else "critical_policy"
            
            # Find or create appropriate policy
            policy = next((p for p_id, p in self.policies.items() if p.name == policy_name), None)
            
            if not policy:
                # Create default policy for this level
                required_roles = {"admin": 1} if level == InterventionLevel.EMERGENCY else {"supervisor": 1}
                policy = ApprovalPolicy(
                    name=policy_name,
                    description=f"Policy for {level_name} interventions",
                    required_roles=required_roles,
                    expiration_hours=1 if level == InterventionLevel.EMERGENCY else 4
                )
                policy_id = f"{level_name}_policy_{uuid.uuid4()}"
                self.policies[policy_id] = policy
                self._save_policy(policy_id, policy)
            
            # Create workflow
            workflow_id = str(uuid.uuid4())
            workflow = ApprovalWorkflow(
                workflow_id=workflow_id,
                title=f"Intervention: {title}",
                description=description,
                policy=policy,
                created_by="system",
                metadata={
                    "intervention_id": intervention_id,
                    "level": level_name,
                    "context": context
                }
            )
            
            self.workflows[workflow_id] = workflow
            self._save_workflow(workflow_id, workflow)
            
            # Notify eligible supervisors
            await self._notify_for_workflow(workflow)
            
            return {
                "success": True,
                "message": f"{level_name} intervention routed to approval workflow",
                "intervention_id": intervention_id,
                "workflow_id": workflow_id
            }
        else:
            # For lower levels, create a simple approval request
            request_id = await self.create_approval_request(
                operation_type="intervention_response",
                details={
                    "intervention_id": intervention_id,
                    "level": level_name,
                    "title": title,
                    "description": description,
                    "context": context
                },
                required_role=required_role
            )
            
            return {
                "success": True,
                "message": f"{level_name} intervention routed to approval request",
                "intervention_id": intervention_id,
                "request_id": request_id
            }
    
    async def create_approval_workflow(self, title: str, description: str, 
                                    policy_id: str, supervisor_id: str,
                                    metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Create a multi-person approval workflow.
        
        Args:
            title: Workflow title
            description: Workflow description
            policy_id: ID of the approval policy to use
            supervisor_id: ID of the supervisor creating the workflow
            metadata: Additional metadata
            
        Returns:
            Dictionary with workflow details
        """
        # Check if supervisor exists
        if supervisor_id not in self.supervisors:
            return {
                "success": False,
                "message": f"Supervisor with ID {supervisor_id} not found",
                "supervisor_id": supervisor_id
            }
        
        # Check if policy exists
        if policy_id not in self.policies:
            return {
                "success": False,
                "message": f"Policy with ID {policy_id} not found",
                "policy_id": policy_id
            }
        
        # Generate workflow ID
        workflow_id = str(uuid.uuid4())
        
        # Create workflow
        workflow = ApprovalWorkflow(
            workflow_id=workflow_id,
            title=title,
            description=description,
            policy=self.policies[policy_id],
            created_by=supervisor_id,
            metadata=metadata
        )
        
        # Save workflow
        self.workflows[workflow_id] = workflow
        self._save_workflow(workflow_id, workflow)
        
        # Log workflow creation
        await self._log_event(
            event_type="approval_workflow_created",
            details={
                "workflow_id": workflow_id,
                "supervisor_id": supervisor_id,
                "title": title,
                "policy_id": policy_id
            }
        )
        
        # Notify eligible supervisors
        await self._notify_for_workflow(workflow)
        
        return {
            "success": True,
            "message": f"Approval workflow {workflow_id} created",
            "workflow_id": workflow_id,
            "title": title,
            "policy_id": policy_id
        }
    
    async def _notify_for_workflow(self, workflow: ApprovalWorkflow) -> None:
        """Notify eligible supervisors about a workflow."""
        # Find eligible supervisors based on required roles
        eligible_supervisors = []
        
        for supervisor_id, supervisor in self.supervisors.items():
            for role, count in workflow.policy.required_roles.items():
                if role in supervisor["roles"]:
                    eligible_supervisors.append(supervisor_id)
                    break
        
        # Create notification for eligible supervisors
        if eligible_supervisors:
            await self.create_notification(
                supervisor_ids=eligible_supervisors,
                message=f"New approval workflow: {workflow.title}",
                level="info",
                context={
                    "workflow_id": workflow.id,
                    "title": workflow.title,
                    "expiration": workflow.expires_at
                }
            )
    
    async def approve_workflow(self, workflow_id: str, supervisor_id: str, 
                            comments: Optional[str] = None) -> Dict[str, Any]:
        """
        Approve a workflow step.
        
        Args:
            workflow_id: ID of the workflow
            supervisor_id: ID of the supervisor approving
            comments: Optional comments
            
        Returns:
            Dictionary with approval result
        """
        # Check if workflow exists
        if workflow_id not in self.workflows:
            return {
                "success": False,
                "message": f"Workflow with ID {workflow_id} not found",
                "workflow_id": workflow_id
            }
        
        # Check if supervisor exists
        if supervisor_id not in self.supervisors:
            return {
                "success": False,
                "message": f"Supervisor with ID {supervisor_id} not found",
                "supervisor_id": supervisor_id
            }
        
        # Get workflow and supervisor
        workflow = self.workflows[workflow_id]
        supervisor = self.supervisors[supervisor_id]
        
        # Check if workflow is still active
        if workflow.status != ApprovalStatus.WAITING and workflow.status != ApprovalStatus.PARTIAL:
            return {
                "success": False,
                "message": f"Workflow is not in waiting state (status: {workflow.status.value})",
                "workflow_id": workflow_id,
                "status": workflow.status.value
            }
        
        # Check if supervisor is eligible (has one of the required roles)
        supervisor_eligible = False
        supervisor_role = None
        
        for role in supervisor["roles"]:
            if role in workflow.policy.required_roles:
                supervisor_eligible = True
                supervisor_role = role
                break
        
        if not supervisor_eligible:
            return {
                "success": False,
                "message": f"Supervisor {supervisor_id} does not have any of the required roles",
                "supervisor_id": supervisor_id,
                "required_roles": list(workflow.policy.required_roles.keys())
            }
        
        # Check if supervisor already approved
        if supervisor_id in workflow.approvals:
            return {
                "success": False,
                "message": f"Supervisor {supervisor_id} already approved this workflow",
                "workflow_id": workflow_id,
                "supervisor_id": supervisor_id
            }
        
        # Add approval
        workflow.approvals[supervisor_id] = {
            "role": supervisor_role,
            "timestamp": datetime.now().isoformat(),
            "comments": comments
        }
        
        # Check if workflow is now approved
        is_approved = self._check_workflow_approval_status(workflow)
        
        # Save workflow
        self._save_workflow(workflow_id, workflow)
        
        # Update supervisor
        supervisor["last_active"] = datetime.now().isoformat()
        self._save_supervisor(supervisor_id, supervisor)
        
        # Log the approval
        await self._log_event(
            event_type="workflow_approval",
            details={
                "workflow_id": workflow_id,
                "supervisor_id": supervisor_id,
                "status": workflow.status.value,
                "comments": comments
            }
        )
        
        # If workflow is approved and related to intervention, process it
        if is_approved and "intervention_id" in workflow.metadata:
            await self._process_approved_intervention(workflow)
        
        return {
            "success": True,
            "message": f"Workflow {workflow_id} approved by supervisor {supervisor_id}",
            "workflow_id": workflow_id,
            "supervisor_id": supervisor_id,
            "status": workflow.status.value
        }
    
    def _check_workflow_approval_status(self, workflow: ApprovalWorkflow) -> bool:
        """
        Check if workflow has received sufficient approvals.
        
        Returns:
            True if workflow is now approved, False otherwise
        """
        # Count approvals by role
        approvals_by_role = {}
        for supervisor_id, approval in workflow.approvals.items():
            role = approval["role"]
            approvals_by_role[role] = approvals_by_role.get(role, 0) + 1
        
        # Check if all required roles have sufficient approvals
        all_roles_approved = True
        for role, count in workflow.policy.required_roles.items():
            if approvals_by_role.get(role, 0) < count:
                all_roles_approved = False
                break
        
        # Calculate approval percentage
        total_required = sum(workflow.policy.required_roles.values())
        total_approved = len(workflow.approvals)
        percentage_approved = (total_approved / total_required * 100) if total_required > 0 else 0
        
        # Update workflow status
        if all_roles_approved and percentage_approved >= workflow.policy.threshold_percentage:
            workflow.status = ApprovalStatus.APPROVED
            return True
        elif total_approved > 0:
            workflow.status = ApprovalStatus.PARTIAL
        
        return False
    
    async def _process_approved_intervention(self, workflow: ApprovalWorkflow) -> None:
        """Process an approved intervention workflow."""
        intervention_id = workflow.metadata.get("intervention_id")
        
        if not intervention_id or not self.intervention_interface:
            logger.warning(f"Cannot process intervention for workflow {workflow.id}: missing intervention ID or interface")
            return
        
        # Collect approval comments
        comments = []
        for supervisor_id, approval in workflow.approvals.items():
            if approval.get("comments"):
                supervisor_name = self.supervisors[supervisor_id].get("name", supervisor_id)
                comments.append(f"{supervisor_name}: {approval['comments']}")
        
        # Create response
        response_message = "Approved by supervision workflow"
        if comments:
            response_message += "\n" + "\n".join(comments)
        
        # Get first approver or use "system"
        supervisor_id = next(iter(workflow.approvals.keys()), "system")
        
        # Use intervention interface to respond
        try:
            # Create response object in the expected format
            response = {
                "approved": True,
                "message": response_message,
                "action": ResponseAction.CONTINUE.value,
                "modifications": {}
            }
            
            # Update the intervention directly
            if hasattr(self.intervention_interface, "interventions") and intervention_id in self.intervention_interface.interventions:
                intervention = self.intervention_interface.interventions[intervention_id]
                intervention["status"] = InterventionStatus.RESOLVED.value
                intervention["response"] = {
                    "approved": True,
                    "message": response_message,
                    "action": ResponseAction.CONTINUE.value,
                    "modifications": {},
                    "timestamp": datetime.now().isoformat(),
                    "supervisor_id": supervisor_id
                }
                intervention["responded_at"] = datetime.now().isoformat()
                
                # Save the updated intervention
                if hasattr(self.intervention_interface, "_save_intervention"):
                    await self.intervention_interface._save_intervention(intervention_id)
            
            # Also call the respond method with the correct format
            await self.intervention_interface.respond_to_intervention(
                intervention_id=intervention_id,
                response=response
            )
            
            logger.info(f"Processed approved intervention {intervention_id} from workflow {workflow.id}")
        except Exception as e:
            logger.error(f"Error processing intervention {intervention_id} from workflow {workflow.id}: {e}")
    
    async def reject_workflow(self, workflow_id: str, supervisor_id: str, 
                           reason: str) -> Dict[str, Any]:
        """
        Reject a workflow.
        
        Args:
            workflow_id: ID of the workflow
            supervisor_id: ID of the supervisor rejecting
            reason: Reason for rejection
            
        Returns:
            Dictionary with rejection result
        """
        # Check if workflow exists
        if workflow_id not in self.workflows:
            return {
                "success": False,
                "message": f"Workflow with ID {workflow_id} not found",
                "workflow_id": workflow_id
            }
        
        # Check if supervisor exists
        if supervisor_id not in self.supervisors:
            return {
                "success": False,
                "message": f"Supervisor with ID {supervisor_id} not found",
                "supervisor_id": supervisor_id
            }
        
        # Get workflow and supervisor
        workflow = self.workflows[workflow_id]
        supervisor = self.supervisors[supervisor_id]
        
        # Check if workflow is still active
        if workflow.status != ApprovalStatus.WAITING and workflow.status != ApprovalStatus.PARTIAL:
            return {
                "success": False,
                "message": f"Workflow is not in waiting state (status: {workflow.status.value})",
                "workflow_id": workflow_id,
                "status": workflow.status.value
            }
        
        # Check if supervisor is eligible (has one of the required roles)
        supervisor_eligible = False
        supervisor_role = None
        
        for role in supervisor["roles"]:
            if role in workflow.policy.required_roles:
                supervisor_eligible = True
                supervisor_role = role
                break
        
        if not supervisor_eligible:
            return {
                "success": False,
                "message": f"Supervisor {supervisor_id} does not have any of the required roles",
                "supervisor_id": supervisor_id,
                "required_roles": list(workflow.policy.required_roles.keys())
            }
        
        # Add rejection
        workflow.rejections[supervisor_id] = {
            "role": supervisor_role,
            "timestamp": datetime.now().isoformat(),
            "reason": reason
        }
        
        # If policy says rejection blocks, set workflow status to rejected
        if workflow.policy.rejection_blocks:
            workflow.status = ApprovalStatus.REJECTED
        
        # Save workflow
        self._save_workflow(workflow_id, workflow)
        
        # Update supervisor
        supervisor["last_active"] = datetime.now().isoformat()
        self._save_supervisor(supervisor_id, supervisor)
        
        # Log the rejection
        await self._log_event(
            event_type="workflow_rejection",
            details={
                "workflow_id": workflow_id,
                "supervisor_id": supervisor_id,
                "status": workflow.status.value,
                "reason": reason
            }
        )
        
        # If workflow is rejected and related to intervention, process it
        if workflow.status == ApprovalStatus.REJECTED and "intervention_id" in workflow.metadata:
            await self._process_rejected_intervention(workflow)
        
        return {
            "success": True,
            "message": f"Workflow {workflow_id} rejected by supervisor {supervisor_id}",
            "workflow_id": workflow_id,
            "supervisor_id": supervisor_id,
            "status": workflow.status.value
        }
    
    async def _process_rejected_intervention(self, workflow: ApprovalWorkflow) -> None:
        """Process a rejected intervention workflow."""
        intervention_id = workflow.metadata.get("intervention_id")
        
        if not intervention_id or not self.intervention_interface:
            logger.warning(f"Cannot process intervention for workflow {workflow.id}: missing intervention ID or interface")
            return
        
        # Get rejection reason from the first rejection
        rejection_reason = "Rejected by supervision workflow"
        if workflow.rejections:
            supervisor_id, rejection = next(iter(workflow.rejections.items()))
            if "reason" in rejection and rejection["reason"]:
                rejection_reason = rejection["reason"]
        
        # Create response object in the expected format
        response = {
            "approved": False,
            "message": rejection_reason,
            "action": ResponseAction.STOP.value,
            "modifications": {}
        }
        
        try:
            # Update the intervention directly
            if hasattr(self.intervention_interface, "interventions") and intervention_id in self.intervention_interface.interventions:
                intervention = self.intervention_interface.interventions[intervention_id]
                intervention["status"] = InterventionStatus.DISMISSED.value
                intervention["response"] = {
                    "approved": False,
                    "message": rejection_reason,
                    "action": ResponseAction.STOP.value,
                    "modifications": {},
                    "timestamp": datetime.now().isoformat(),
                    "supervisor_id": supervisor_id if 'supervisor_id' in locals() else "system"
                }
                intervention["responded_at"] = datetime.now().isoformat()
                
                # Save the updated intervention
                if hasattr(self.intervention_interface, "_save_intervention"):
                    await self.intervention_interface._save_intervention(intervention_id)
            
            # Also call the respond method with the correct format
            await self.intervention_interface.respond_to_intervention(
                intervention_id=intervention_id,
                response=response
            )
            
            logger.info(f"Processed rejected intervention {intervention_id} from workflow {workflow.id}")
        except Exception as e:
            logger.error(f"Error processing rejected intervention {intervention_id} from workflow {workflow.id}: {e}")
    
    async def create_approval_policy(self, name: str, description: str,
                                  required_roles: Dict[str, int],
                                  threshold_percentage: int = 75,
                                  expiration_hours: int = 24,
                                  consecutive_order: bool = False,
                                  enable_override: bool = True,
                                  rejection_blocks: bool = True,
                                  supervisor_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Create a new approval policy.
        
        Args:
            name: Policy name
            description: Policy description
            required_roles: Dict mapping role names to minimum count required
            threshold_percentage: Percentage of approvers needed
            expiration_hours: Hours until request expires
            consecutive_order: Whether approvals must happen in order
            enable_override: Whether admin can override
            rejection_blocks: Whether a single rejection blocks
            supervisor_id: ID of supervisor creating the policy
            
        Returns:
            Dictionary with policy details
        """
        # Generate policy ID
        policy_id = str(uuid.uuid4())
        
        # Create policy
        policy = ApprovalPolicy(
            name=name,
            description=description,
            required_roles=required_roles,
            threshold_percentage=threshold_percentage,
            expiration_hours=expiration_hours,
            consecutive_order=consecutive_order,
            enable_override=enable_override,
            rejection_blocks=rejection_blocks
        )
        
        # Save policy
        self.policies[policy_id] = policy
        self._save_policy(policy_id, policy)
        
        # Log policy creation
        await self._log_event(
            event_type="approval_policy_created",
            details={
                "policy_id": policy_id,
                "name": name,
                "supervisor_id": supervisor_id,
                "required_roles": required_roles
            }
        )
        
        return {
            "success": True,
            "message": f"Approval policy {name} created",
            "policy_id": policy_id,
            "name": name,
            "required_roles": required_roles
        }
    
    async def get_approval_policies(self) -> List[Dict[str, Any]]:
        """
        Get all approval policies.
        
        Returns:
            List of policy details
        """
        policies = []
        
        for policy_id, policy in self.policies.items():
            policy_dict = policy.to_dict()
            policy_dict["id"] = policy_id
            policies.append(policy_dict)
        
        return policies
    
    async def get_workflows(self, status: Optional[str] = None,
                          supervisor_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get approval workflows, optionally filtered.
        
        Args:
            status: Optional status to filter by
            supervisor_id: Optional supervisor ID to filter by
            
        Returns:
            List of workflow details
        """
        workflows = []
        
        for workflow_id, workflow in self.workflows.items():
            # Filter by status if provided
            if status and workflow.status.value != status:
                continue
            
            # Filter by supervisor if provided
            if supervisor_id:
                # Check if supervisor created or approved/rejected
                if (workflow.created_by != supervisor_id and
                    supervisor_id not in workflow.approvals and
                    supervisor_id not in workflow.rejections):
                    
                    # Also check if supervisor is eligible
                    supervisor_eligible = False
                    if supervisor_id in self.supervisors:
                        for role in self.supervisors[supervisor_id]["roles"]:
                            if role in workflow.policy.required_roles:
                                supervisor_eligible = True
                                break
                    
                    if not supervisor_eligible:
                        continue
            
            # Add workflow
            workflow_dict = workflow.to_dict()
            workflows.append(workflow_dict)
        
        # Sort by creation time (newest first)
        workflows.sort(key=lambda w: w["created_at"], reverse=True)
        
        return workflows
    
    async def register_websocket(self, websocket, supervisor_id: str) -> Dict[str, Any]:
        """
        Register a WebSocket connection for real-time notifications.
        
        Args:
            websocket: WebSocket connection
            supervisor_id: ID of the supervisor
            
        Returns:
            Dictionary with registration result
        """
        if not self.config.get("enable_websocket_notifications", True):
            return {
                "success": False,
                "message": "WebSocket notifications are disabled"
            }
        
        # Check if supervisor exists
        if supervisor_id not in self.supervisors:
            return {
                "success": False,
                "message": f"Supervisor with ID {supervisor_id} not found",
                "supervisor_id": supervisor_id
            }
        
        # Register WebSocket
        self.websocket_connections[supervisor_id] = websocket
        
        # Log connection
        await self._log_event(
            event_type="websocket_connected",
            details={
                "supervisor_id": supervisor_id
            }
        )
        
        return {
            "success": True,
            "message": f"WebSocket registered for supervisor {supervisor_id}",
            "supervisor_id": supervisor_id
        }
    
    async def unregister_websocket(self, supervisor_id: str) -> Dict[str, Any]:
        """
        Unregister a WebSocket connection.
        
        Args:
            supervisor_id: ID of the supervisor
            
        Returns:
            Dictionary with unregistration result
        """
        # Check if supervisor has a WebSocket
        if supervisor_id not in self.websocket_connections:
            return {
                "success": False,
                "message": f"No WebSocket registered for supervisor {supervisor_id}",
                "supervisor_id": supervisor_id
            }
        
        # Unregister WebSocket
        del self.websocket_connections[supervisor_id]
        
        # Log disconnection
        await self._log_event(
            event_type="websocket_disconnected",
            details={
                "supervisor_id": supervisor_id
            }
        )
        
        return {
            "success": True,
            "message": f"WebSocket unregistered for supervisor {supervisor_id}",
            "supervisor_id": supervisor_id
        }
    
    async def send_websocket_notification(self, supervisor_id: str, 
                                         message: Dict[str, Any]) -> bool:
        """
        Send a notification via WebSocket.
        
        Args:
            supervisor_id: ID of the supervisor to notify
            message: Message to send
            
        Returns:
            True if message was sent, False otherwise
        """
        if not self.config.get("enable_websocket_notifications", True):
            return False
        
        # Check if supervisor has a WebSocket
        if supervisor_id not in self.websocket_connections:
            return False
        
        # Get WebSocket
        websocket = self.websocket_connections[supervisor_id]
        
        # Send message
        try:
            await websocket.send_json(message)
            return True
        except Exception as e:
            logger.exception(f"Error sending WebSocket message to supervisor {supervisor_id}: {e}")
            
            # Unregister failed WebSocket
            await self.unregister_websocket(supervisor_id)
            return False
    
    async def notify_supervisors_websocket(self, supervisor_ids: List[str], 
                                        event_type: str, data: Dict[str, Any]) -> None:
        """
        Notify supervisors via WebSocket.
        
        Args:
            supervisor_ids: List of supervisor IDs to notify
            event_type: Type of event
            data: Event data
        """
        if not self.config.get("enable_websocket_notifications", True):
            return
        
        # Create message
        message = {
            "type": event_type,
            "timestamp": datetime.now().isoformat(),
            "data": data
        }
        
        # Send to each supervisor
        for supervisor_id in supervisor_ids:
            await self.send_websocket_notification(supervisor_id, message) 