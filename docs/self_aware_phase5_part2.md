# Implementation Guide for Phase 5 Work Units 5.3 and 5.4

I'll provide detailed implementations for Work Unit 5.3 (Multi-Human Supervision Hub) and Work Unit 5.4 (Budget & Resource Monitor), including code examples, unit tests, and explanations of connections to the rest of the system.

## Work Unit 5.3: Multi-Human Supervision Hub

The Multi-Human Supervision Hub extends the Intervention Interface to support collaborative supervision with multiple users, role-based access, and approval workflows.

```python
from typing import Dict, List, Optional, Any, Union, Callable, Set
import logging
from enum import Enum
from dataclasses import dataclass, field
import asyncio
import json
from datetime import datetime, timedelta
import os
from pathlib import Path
import hashlib
import uuid
import jwt
from passlib.hash import bcrypt

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

@dataclass
class ApprovalPolicy:
    """Policy for approval workflows."""
    name: str
    description: str
    required_roles: Dict[SupervisorRole, int]  # Role -> minimum count required
    threshold_percentage: int = 75  # Percentage of approvers needed
    expiration_hours: int = 24
    consecutive_order: bool = False  # Whether approvals must happen in order
    enable_override: bool = True     # Whether admin can override
    rejection_blocks: bool = True    # Whether a single rejection blocks

@dataclass
class SupervisorPermission:
    """Permission for a supervisor."""
    role: SupervisorRole
    allowed_actions: List[str]
    allowed_components: List[str]
    
    def can_perform(self, action: str, component: str) -> bool:
        """Check if supervisor can perform action on component."""
        # Admins can do anything
        if self.role == SupervisorRole.ADMIN:
            return True
            
        # Check if action and component are allowed
        return (action in self.allowed_actions and 
                (component in self.allowed_components or "*" in self.allowed_components))

@dataclass
class Supervisor:
    """A human supervisor in the system."""
    id: str
    username: str
    name: str
    email: str
    password_hash: str
    roles: List[SupervisorRole]
    permissions: List[SupervisorPermission]
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    last_login: Optional[str] = None
    active: bool = True
    
    def get_highest_role(self) -> SupervisorRole:
        """Get the highest role for the supervisor."""
        # Order by privilege level
        role_order = [
            SupervisorRole.OBSERVER,
            SupervisorRole.OPERATOR,
            SupervisorRole.EXPERT,
            SupervisorRole.SUPERVISOR,
            SupervisorRole.ADMIN
        ]
        
        highest_role = SupervisorRole.OBSERVER  # Default
        highest_index = 0
        
        for role in self.roles:
            role_index = role_order.index(role)
            if role_index > highest_index:
                highest_index = role_index
                highest_role = role
                
        return highest_role
    
    def can_access(self, intervention_level: 'InterventionLevel') -> bool:
        """Check if supervisor can access intervention of given level."""
        # Map intervention levels to minimum required roles
        level_role_map = {
            InterventionLevel.INFORMATION: SupervisorRole.OBSERVER,
            InterventionLevel.SUGGESTION: SupervisorRole.OPERATOR,
            InterventionLevel.WARNING: SupervisorRole.OPERATOR,
            InterventionLevel.CRITICAL: SupervisorRole.SUPERVISOR,
            InterventionLevel.EMERGENCY: SupervisorRole.ADMIN
        }
        
        required_role = level_role_map.get(intervention_level, SupervisorRole.SUPERVISOR)
        highest_role = self.get_highest_role()
        
        # Compare privilege levels
        role_order = [
            SupervisorRole.OBSERVER,
            SupervisorRole.OPERATOR,
            SupervisorRole.EXPERT,
            SupervisorRole.SUPERVISOR,
            SupervisorRole.ADMIN
        ]
        
        return role_order.index(highest_role) >= role_order.index(required_role)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "id": self.id,
            "username": self.username,
            "name": self.name,
            "email": self.email,
            "password_hash": self.password_hash,
            "roles": [role.value for role in self.roles],
            "permissions": [
                {
                    "role": perm.role.value,
                    "allowed_actions": perm.allowed_actions,
                    "allowed_components": perm.allowed_components
                }
                for perm in self.permissions
            ],
            "created_at": self.created_at,
            "last_login": self.last_login,
            "active": self.active
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Supervisor':
        """Create from dictionary."""
        permissions = [
            SupervisorPermission(
                role=SupervisorRole(perm["role"]),
                allowed_actions=perm["allowed_actions"],
                allowed_components=perm["allowed_components"]
            )
            for perm in data.get("permissions", [])
        ]
        
        roles = [
            SupervisorRole(role) for role in data.get("roles", ["observer"])
        ]
        
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            username=data.get("username", ""),
            name=data.get("name", ""),
            email=data.get("email", ""),
            password_hash=data.get("password_hash", ""),
            roles=roles,
            permissions=permissions,
            created_at=data.get("created_at", datetime.now().isoformat()),
            last_login=data.get("last_login"),
            active=data.get("active", True)
        )

@dataclass
class ApprovalWorkflow:
    """Workflow for multi-person approval."""
    id: str
    title: str
    description: str
    policy: ApprovalPolicy
    created_by: str
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    expires_at: Optional[str] = None
    status: ApprovalStatus = ApprovalStatus.WAITING
    approvals: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    rejections: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "policy": {
                "name": self.policy.name,
                "description": self.policy.description,
                "required_roles": {k.value: v for k, v in self.policy.required_roles.items()},
                "threshold_percentage": self.policy.threshold_percentage,
                "expiration_hours": self.policy.expiration_hours,
                "consecutive_order": self.policy.consecutive_order,
                "enable_override": self.policy.enable_override,
                "rejection_blocks": self.policy.rejection_blocks
            },
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
        policy_data = data.get("policy", {})
        required_roles = {
            SupervisorRole(k): v 
            for k, v in policy_data.get("required_roles", {}).items()
        }
        
        policy = ApprovalPolicy(
            name=policy_data.get("name", "Default Policy"),
            description=policy_data.get("description", ""),
            required_roles=required_roles,
            threshold_percentage=policy_data.get("threshold_percentage", 75),
            expiration_hours=policy_data.get("expiration_hours", 24),
            consecutive_order=policy_data.get("consecutive_order", False),
            enable_override=policy_data.get("enable_override", True),
            rejection_blocks=policy_data.get("rejection_blocks", True)
        )
        
        status_val = data.get("status", "waiting")
        try:
            status = ApprovalStatus(status_val)
        except ValueError:
            status = ApprovalStatus.WAITING
        
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            title=data.get("title", ""),
            description=data.get("description", ""),
            policy=policy,
            created_by=data.get("created_by", ""),
            created_at=data.get("created_at", datetime.now().isoformat()),
            expires_at=data.get("expires_at"),
            status=status,
            approvals=data.get("approvals", {}),
            rejections=data.get("rejections", {}),
            metadata=data.get("metadata", {})
        )

class SupervisionHub:
    """Manages multi-human supervision with role-based access control."""
    
    def __init__(self, 
                intervention_interface: Any,
                config: Optional[Dict[str, Any]] = None):
        """Initialize with access to intervention interface."""
        self.intervention_interface = intervention_interface
        self.config = config or {
            "storage_path": "data/supervision",
            "token_secret": "change_this_in_production",
            "token_expiry_hours": 12,
            "default_policies": self._default_approval_policies(),
            "session_timeout_minutes": 30
        }
        
        self.supervisors: Dict[str, Supervisor] = {}
        self.approval_workflows: Dict[str, ApprovalWorkflow] = {}
        self.tokens: Dict[str, Dict[str, Any]] = {}
        self.active_sessions: Dict[str, Dict[str, Any]] = {}
        
        # Load supervisors and policies
        self._load_data()
    
    def _default_approval_policies(self) -> Dict[str, ApprovalPolicy]:
        """Create default approval policies."""
        return {
            "standard": ApprovalPolicy(
                name="Standard Approval",
                description="Standard approval requiring operator and supervisor",
                required_roles={
                    SupervisorRole.OPERATOR: 1,
                    SupervisorRole.SUPERVISOR: 1
                },
                threshold_percentage=100,
                expiration_hours=24,
                consecutive_order=False,
                enable_override=True,
                rejection_blocks=True
            ),
            "critical": ApprovalPolicy(
                name="Critical Approval",
                description="Critical approval requiring supervisor and admin",
                required_roles={
                    SupervisorRole.SUPERVISOR: 1,
                    SupervisorRole.ADMIN: 1
                },
                threshold_percentage=100,
                expiration_hours=12,
                consecutive_order=True,
                enable_override=False,
                rejection_blocks=True
            ),
            "emergency": ApprovalPolicy(
                name="Emergency Approval",
                description="Emergency approval requiring admin only",
                required_roles={
                    SupervisorRole.ADMIN: 1
                },
                threshold_percentage=100,
                expiration_hours=4,
                consecutive_order=False,
                enable_override=False,
                rejection_blocks=True
            )
        }
    
    async def _load_data(self) -> None:
        """Load supervisors and approval workflows from storage."""
        storage_path = self.config.get("storage_path", "data/supervision")
        
        # Load supervisors
        supervisors_dir = os.path.join(storage_path, "supervisors")
        if os.path.exists(supervisors_dir):
            for filename in os.listdir(supervisors_dir):
                if filename.endswith(".json"):
                    try:
                        with open(os.path.join(supervisors_dir, filename), 'r') as f:
                            data = json.load(f)
                            supervisor = Supervisor.from_dict(data)
                            self.supervisors[supervisor.id] = supervisor
                    except Exception as e:
                        logger.error(f"Error loading supervisor from {filename}: {str(e)}")
        
        # Load approval workflows
        workflows_dir = os.path.join(storage_path, "workflows")
        if os.path.exists(workflows_dir):
            for filename in os.listdir(workflows_dir):
                if filename.endswith(".json"):
                    try:
                        with open(os.path.join(workflows_dir, filename), 'r') as f:
                            data = json.load(f)
                            workflow = ApprovalWorkflow.from_dict(data)
                            self.approval_workflows[workflow.id] = workflow
                    except Exception as e:
                        logger.error(f"Error loading approval workflow from {filename}: {str(e)}")
    
    async def create_supervisor(self, 
                              username: str,
                              name: str,
                              email: str,
                              password: str,
                              roles: List[SupervisorRole],
                              permissions: Optional[List[SupervisorPermission]] = None) -> Supervisor:
        """Create a new supervisor."""
        # Check if username already exists
        if any(s.username == username for s in self.supervisors.values()):
            raise ValueError(f"Username {username} already exists")
        
        # Generate supervisor ID
        supervisor_id = str(uuid.uuid4())
        
        # Hash password
        password_hash = bcrypt.hash(password)
        
        # Create default permissions if none provided
        if not permissions:
            permissions = self._default_permissions_for_roles(roles)
        
        # Create supervisor
        supervisor = Supervisor(
            id=supervisor_id,
            username=username,
            name=name,
            email=email,
            password_hash=password_hash,
            roles=roles,
            permissions=permissions
        )
        
        # Store supervisor
        self.supervisors[supervisor_id] = supervisor
        
        # Save to storage
        await self._save_supervisor(supervisor)
        
        logger.info(f"Created supervisor {username} with roles {[r.value for r in roles]}")
        
        return supervisor
    
    def _default_permissions_for_roles(self, roles: List[SupervisorRole]) -> List[SupervisorPermission]:
        """Create default permissions based on roles."""
        permissions = []
        
        for role in roles:
            if role == SupervisorRole.OBSERVER:
                permissions.append(SupervisorPermission(
                    role=role,
                    allowed_actions=["view"],
                    allowed_components=["*"]
                ))
            elif role == SupervisorRole.OPERATOR:
                permissions.append(SupervisorPermission(
                    role=role,
                    allowed_actions=["view", "respond", "acknowledge"],
                    allowed_components=["*"]
                ))
            elif role == SupervisorRole.EXPERT:
                permissions.append(SupervisorPermission(
                    role=role,
                    allowed_actions=["view", "respond", "acknowledge", "analyze"],
                    allowed_components=["*"]
                ))
            elif role == SupervisorRole.SUPERVISOR:
                permissions.append(SupervisorPermission(
                    role=role,
                    allowed_actions=["view", "respond", "acknowledge", "analyze", "approve", "reject", "escalate"],
                    allowed_components=["*"]
                ))
            elif role == SupervisorRole.ADMIN:
                permissions.append(SupervisorPermission(
                    role=role,
                    allowed_actions=["*"],
                    allowed_components=["*"]
                ))
        
        return permissions
    
    async def authenticate(self, username: str, password: str) -> Dict[str, Any]:
        """Authenticate a supervisor and return access token."""
        # Find supervisor by username
        supervisor = None
        for s in self.supervisors.values():
            if s.username == username:
                supervisor = s
                break
        
        if not supervisor:
            raise ValueError("Invalid username or password")
        
        # Verify password
        if not bcrypt.verify(password, supervisor.password_hash):
            raise ValueError("Invalid username or password")
        
        # Check if supervisor is active
        if not supervisor.active:
            raise ValueError("Account is inactive")
        
        # Update last login
        supervisor.last_login = datetime.now().isoformat()
        await self._save_supervisor(supervisor)
        
        # Generate token
        token = self._generate_token(supervisor)
        
        # Create session
        session_id = str(uuid.uuid4())
        session = {
            "id": session_id,
            "supervisor_id": supervisor.id,
            "created_at": datetime.now().isoformat(),
            "last_activity": datetime.now().isoformat(),
            "expires_at": (datetime.now() + timedelta(hours=self.config["token_expiry_hours"])).isoformat()
        }
        
        # Store session
        self.active_sessions[session_id] = session
        
        return {
            "token": token,
            "supervisor": {
                "id": supervisor.id,
                "username": supervisor.username,
                "name": supervisor.name,
                "roles": [r.value for r in supervisor.roles],
                "highest_role": supervisor.get_highest_role().value
            },
            "session_id": session_id,
            "expires_at": session["expires_at"]
        }
    
    def _generate_token(self, supervisor: Supervisor) -> str:
        """Generate JWT token for supervisor."""
        expiry = datetime.now() + timedelta(hours=self.config["token_expiry_hours"])
        
        payload = {
            "sub": supervisor.id,
            "username": supervisor.username,
            "roles": [r.value for r in supervisor.roles],
            "exp": expiry.timestamp()
        }
        
        token = jwt.encode(
            payload,
            self.config["token_secret"],
            algorithm="HS256"
        )
        
        # Store token info
        self.tokens[token] = {
            "supervisor_id": supervisor.id,
            "created_at": datetime.now().isoformat(),
            "expires_at": expiry.isoformat()
        }
        
        return token
    
    async def verify_token(self, token: str) -> Dict[str, Any]:
        """Verify access token and return supervisor info."""
        try:
            # Decode token
            payload = jwt.decode(
                token,
                self.config["token_secret"],
                algorithms=["HS256"]
            )
            
            # Get supervisor
            supervisor_id = payload["sub"]
            if supervisor_id not in self.supervisors:
                raise ValueError("Supervisor not found")
            
            supervisor = self.supervisors[supervisor_id]
            
            # Check if supervisor is active
            if not supervisor.active:
                raise ValueError("Account is inactive")
            
            # Update token last used
            if token in self.tokens:
                self.tokens[token]["last_used"] = datetime.now().isoformat()
            
            return {
                "supervisor_id": supervisor.id,
                "username": supervisor.username,
                "roles": [r.value for r in supervisor.roles],
                "valid": True
            }
            
        except jwt.ExpiredSignatureError:
            raise ValueError("Token expired")
        except jwt.InvalidTokenError:
            raise ValueError("Invalid token")
    
    async def logout(self, token: str, session_id: Optional[str] = None) -> Dict[str, Any]:
        """Log out a supervisor and invalidate token."""
        # Remove token
        if token in self.tokens:
            supervisor_id = self.tokens[token]["supervisor_id"]
            del self.tokens[token]
        else:
            supervisor_id = None
            
        # Remove session if provided
        if session_id and session_id in self.active_sessions:
            del self.active_sessions[session_id]
        
        return {
            "success": True,
            "supervisor_id": supervisor_id
        }
    
    async def get_interventions_for_supervisor(self, 
                                            supervisor_id: str,
                                            status_filter: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """Get interventions relevant to a supervisor."""
        if supervisor_id not in self.supervisors:
            raise ValueError(f"Supervisor {supervisor_id} not found")
        
        supervisor = self.supervisors[supervisor_id]
        highest_role = supervisor.get_highest_role()
        
        # Get all interventions
        all_interventions = []
        for intervention_id in self.intervention_interface.interventions:
            try:
                intervention = await self.intervention_interface.get_intervention(intervention_id)
                all_interventions.append(intervention)
            except Exception as e:
                logger.error(f"Error getting intervention {intervention_id}: {str(e)}")
        
        # Filter by status if requested
        if status_filter:
            all_interventions = [
                i for i in all_interventions 
                if i["status"] in status_filter
            ]
        
        # Filter based on supervisor's role and permissions
        allowed_interventions = []
        for intervention in all_interventions:
            # Check role requirement
            required_role = intervention["request"].get("required_role")
            
            # Admin can see everything
            if highest_role == SupervisorRole.ADMIN:
                allowed_interventions.append(intervention)
                continue
            
            # Check if intervention specifically requires a role
            if required_role and required_role not in [r.value for r in supervisor.roles]:
                continue
            
            # Check intervention level accessibility
            level = intervention["request"].get("level", "information")
            try:
                intervention_level = InterventionLevel(level)
                if not supervisor.can_access(intervention_level):
                    continue
            except ValueError:
                # If level is invalid, default to allowing supervisor+ to see it
                if highest_role not in [SupervisorRole.SUPERVISOR, SupervisorRole.ADMIN]:
                    continue
            
            allowed_interventions.append(intervention)
        
        return allowed_interventions
    
    async def create_approval_workflow(self,
                                     title: str,
                                     description: str,
                                     policy_name: str,
                                     creator_id: str,
                                     metadata: Optional[Dict[str, Any]] = None) -> ApprovalWorkflow:
        """Create a new approval workflow."""
        # Verify supervisor exists
        if creator_id not in self.supervisors:
            raise ValueError(f"Supervisor {creator_id} not found")
        
        # Get policy
        default_policies = self.config.get("default_policies", {})
        if policy_name not in default_policies:
            raise ValueError(f"Policy {policy_name} not found")
            
        policy = default_policies[policy_name]
        
        # Generate workflow ID
        workflow_id = f"wf_{uuid.uuid4().hex[:10]}"
        
        # Calculate expiration
        expiration = datetime.now() + timedelta(hours=policy.expiration_hours)
        
        # Create workflow
        workflow = ApprovalWorkflow(
            id=workflow_id,
            title=title,
            description=description,
            policy=policy,
            created_by=creator_id,
            created_at=datetime.now().isoformat(),
            expires_at=expiration.isoformat(),
            status=ApprovalStatus.WAITING,
            metadata=metadata or {}
        )
        
        # Store workflow
        self.approval_workflows[workflow_id] = workflow
        
        # Save to storage
        await self._save_workflow(workflow)
        
        logger.info(f"Created approval workflow {workflow_id}: {title}")
        
        return workflow
    
    async def submit_approval(self,
                            workflow_id: str,
                            supervisor_id: str,
                            approved: bool,
                            notes: Optional[str] = None) -> Dict[str, Any]:
        """Submit an approval or rejection for a workflow."""
        # Check if workflow exists
        if workflow_id not in self.approval_workflows:
            raise ValueError(f"Workflow {workflow_id} not found")
            
        workflow = self.approval_workflows[workflow_id]
        
        # Check if supervisor exists
        if supervisor_id not in self.supervisors:
            raise ValueError(f"Supervisor {supervisor_id} not found")
            
        supervisor = self.supervisors[supervisor_id]
        
        # Check workflow status
        if workflow.status != ApprovalStatus.WAITING and workflow.status != ApprovalStatus.PARTIAL:
            raise ValueError(f"Workflow has status {workflow.status.value}, cannot submit approval")
        
        # Check if approval already submitted
        if supervisor_id in workflow.approvals or supervisor_id in workflow.rejections:
            raise ValueError(f"Supervisor {supervisor_id} has already submitted an approval or rejection")
        
        # Check if expired
        if workflow.expires_at:
            expiration = datetime.fromisoformat(workflow.expires_at)
            if datetime.now() > expiration:
                workflow.status = ApprovalStatus.EXPIRED
                await self._save_workflow(workflow)
                raise ValueError(f"Workflow has expired")
        
        # Check if supervisor has required role
        supervisor_roles = set(supervisor.roles)
        required_roles = set(workflow.policy.required_roles.keys())
        
        if not supervisor_roles.intersection(required_roles) and SupervisorRole.ADMIN not in supervisor_roles:
            raise ValueError(f"Supervisor {supervisor_id} does not have a required role")
        
        # Check if consecutive order is enforced
        if workflow.policy.consecutive_order:
            # Determine current required role
            approval_sequence = list(workflow.policy.required_roles.keys())
            current_role_index = 0
            
            # Find the current role in the sequence based on existing approvals
            for role in approval_sequence:
                role_approvers = [
                    s_id for s_id in workflow.approvals
                    if role in self.supervisors[s_id].roles
                ]
                
                required_count = workflow.policy.required_roles[role]
                if len(role_approvers) < required_count:
                    break
                    
                current_role_index += 1
            
            # Check if supervisor has the current role
            if current_role_index < len(approval_sequence):
                current_role = approval_sequence[current_role_index]
                if current_role not in supervisor.roles and SupervisorRole.ADMIN not in supervisor.roles:
                    raise ValueError(f"Current approval requires role {current_role.value}")
        
        # Process approval or rejection
        timestamp = datetime.now().isoformat()
        
        if approved:
            # Add approval
            workflow.approvals[supervisor_id] = {
                "timestamp": timestamp,
                "notes": notes,
                "roles": [r.value for r in supervisor.roles]
            }
            
            # Check if workflow is now approved
            if self._check_workflow_approval_status(workflow):
                workflow.status = ApprovalStatus.APPROVED
                logger.info(f"Workflow {workflow_id} approved")
        else:
            # Add rejection
            workflow.rejections[supervisor_id] = {
                "timestamp": timestamp,
                "notes": notes,
                "roles": [r.value for r in supervisor.roles]
            }
            
            # If rejection blocks, set status to rejected
            if workflow.policy.rejection_blocks:
                workflow.status = ApprovalStatus.REJECTED
                logger.info(f"Workflow {workflow_id} rejected")
        
        # Update partial status if not fully approved/rejected
        if workflow.status == ApprovalStatus.WAITING and (workflow.approvals or workflow.rejections):
            workflow.status = ApprovalStatus.PARTIAL
        
        # Save workflow
        await self._save_workflow(workflow)
        
        return {
            "workflow_id": workflow_id,
            "status": workflow.status.value,
            "approved": approved,
            "supervisor_id": supervisor_id,
            "timestamp": timestamp
        }
    
    def _check_workflow_approval_status(self, workflow: ApprovalWorkflow) -> bool:
        """Check if workflow has all required approvals."""
        # Check if any rejections
        if workflow.rejections and workflow.policy.rejection_blocks:
            return False
        
        # Check each required role
        for role, required_count in workflow.policy.required_roles.items():
            # Count approvals for this role
            role_approvers = [
                s_id for s_id in workflow.approvals
                if s_id in self.supervisors and role in self.supervisors[s_id].roles
            ]
            
            if len(role_approvers) < required_count:
                return False
        
        # Check threshold percentage
        total_required = sum(workflow.policy.required_roles.values())
        total_approvals = len(workflow.approvals)
        
        approval_percentage = (total_approvals / total_required) * 100
        if approval_percentage < workflow.policy.threshold_percentage:
            return False
        
        return True
    
    async def cancel_workflow(self,
                            workflow_id: str,
                            supervisor_id: str,
                            reason: str) -> Dict[str, Any]:
        """Cancel an approval workflow."""
        # Check if workflow exists
        if workflow_id not in self.approval_workflows:
            raise ValueError(f"Workflow {workflow_id} not found")
            
        workflow = self.approval_workflows[workflow_id]
        
        # Check if supervisor exists
        if supervisor_id not in self.supervisors:
            raise ValueError(f"Supervisor {supervisor_id} not found")
            
        supervisor = self.supervisors[supervisor_id]
        
        # Check if supervisor has permission to cancel
        if workflow.created_by != supervisor_id and SupervisorRole.ADMIN not in supervisor.roles:
            raise ValueError(f"Supervisor {supervisor_id} does not have permission to cancel workflow")
        
        # Check workflow status
        if workflow.status not in
            ...
            ...
    # continue the implemention

# Continuing SupervisionHub class implementation

    async def cancel_workflow(self,
                            workflow_id: str,
                            supervisor_id: str,
                            reason: str) -> Dict[str, Any]:
        """Cancel an approval workflow."""
        # Check if workflow exists
        if workflow_id not in self.approval_workflows:
            raise ValueError(f"Workflow {workflow_id} not found")
            
        workflow = self.approval_workflows[workflow_id]
        
        # Check if supervisor exists
        if supervisor_id not in self.supervisors:
            raise ValueError(f"Supervisor {supervisor_id} not found")
            
        supervisor = self.supervisors[supervisor_id]
        
        # Check if supervisor has permission to cancel
        if workflow.created_by != supervisor_id and SupervisorRole.ADMIN not in supervisor.roles:
            raise ValueError(f"Supervisor {supervisor_id} does not have permission to cancel workflow")
        
        # Check workflow status
        if workflow.status not in [ApprovalStatus.WAITING, ApprovalStatus.PARTIAL]:
            raise ValueError(f"Workflow has status {workflow.status.value}, cannot cancel")
        
        # Cancel workflow
        workflow.status = ApprovalStatus.CANCELED
        workflow.metadata["canceled_by"] = supervisor_id
        workflow.metadata["cancel_reason"] = reason
        workflow.metadata["canceled_at"] = datetime.now().isoformat()
        
        # Save workflow
        await self._save_workflow(workflow)
        
        logger.info(f"Workflow {workflow_id} canceled by {supervisor_id}: {reason}")
        
        return {
            "workflow_id": workflow_id,
            "status": workflow.status.value,
            "canceled_by": supervisor_id,
            "reason": reason
        }
    
    async def get_approval_workflow(self, workflow_id: str) -> Dict[str, Any]:
        """Get details of an approval workflow."""
        if workflow_id not in self.approval_workflows:
            raise ValueError(f"Workflow {workflow_id} not found")
            
        workflow = self.approval_workflows[workflow_id]
        
        # Build response with supervisor details
        result = workflow.to_dict()
        
        # Add supervisor details for approvals and rejections
        approvals_with_details = {}
        for supervisor_id, approval in workflow.approvals.items():
            supervisor_details = {"unknown": True}
            if supervisor_id in self.supervisors:
                supervisor = self.supervisors[supervisor_id]
                supervisor_details = {
                    "username": supervisor.username,
                    "name": supervisor.name,
                    "roles": [r.value for r in supervisor.roles]
                }
            
            approvals_with_details[supervisor_id] = {
                **approval,
                "supervisor": supervisor_details
            }
        
        rejections_with_details = {}
        for supervisor_id, rejection in workflow.rejections.items():
            supervisor_details = {"unknown": True}
            if supervisor_id in self.supervisors:
                supervisor = self.supervisors[supervisor_id]
                supervisor_details = {
                    "username": supervisor.username,
                    "name": supervisor.name,
                    "roles": [r.value for r in supervisor.roles]
                }
            
            rejections_with_details[supervisor_id] = {
                **rejection,
                "supervisor": supervisor_details
            }
        
        result["approvals"] = approvals_with_details
        result["rejections"] = rejections_with_details
        
        # Add creator details
        creator_id = workflow.created_by
        creator_details = {"unknown": True}
        if creator_id in self.supervisors:
            creator = self.supervisors[creator_id]
            creator_details = {
                "username": creator.username,
                "name": creator.name,
                "roles": [r.value for r in creator.roles]
            }
        
        result["creator"] = creator_details
        
        # Add progress info
        result["progress"] = self._calculate_workflow_progress(workflow)
        
        return result
    
    def _calculate_workflow_progress(self, workflow: ApprovalWorkflow) -> Dict[str, Any]:
        """Calculate progress of approval workflow."""
        progress = {
            "total_required": 0,
            "total_received": len(workflow.approvals),
            "by_role": {},
            "percentage": 0
        }
        
        # Calculate by role
        for role, required_count in workflow.policy.required_roles.items():
            # Count approvals for this role
            role_approvers = [
                s_id for s_id in workflow.approvals
                if s_id in self.supervisors and role in self.supervisors[s_id].roles
            ]
            
            progress["by_role"][role.value] = {
                "required": required_count,
                "received": len(role_approvers),
                "percentage": (len(role_approvers) / required_count * 100) if required_count > 0 else 0
            }
            
            progress["total_required"] += required_count
        
        # Calculate overall percentage
        if progress["total_required"] > 0:
            progress["percentage"] = (progress["total_received"] / progress["total_required"]) * 100
        
        return progress
    
    async def get_workflows_for_supervisor(self, 
                                        supervisor_id: str,
                                        status_filter: Optional[List[ApprovalStatus]] = None) -> List[Dict[str, Any]]:
        """Get approval workflows relevant to a supervisor."""
        if supervisor_id not in self.supervisors:
            raise ValueError(f"Supervisor {supervisor_id} not found")
            
        supervisor = self.supervisors[supervisor_id]
        
        # Prepare result list
        result = []
        
        for workflow_id, workflow in self.approval_workflows.items():
            # Apply status filter if provided
            if status_filter and workflow.status not in status_filter:
                continue
            
            # Check if supervisor created workflow
            is_creator = workflow.created_by == supervisor_id
            
            # Check if supervisor has required role
            has_role = False
            for role in supervisor.roles:
                if role in workflow.policy.required_roles:
                    has_role = True
                    break
            
            # Admin can see all workflows
            is_admin = SupervisorRole.ADMIN in supervisor.roles
            
            # Include if relevant to supervisor
            if is_creator or has_role or is_admin:
                result.append({
                    "id": workflow.id,
                    "title": workflow.title,
                    "description": workflow.description,
                    "status": workflow.status.value,
                    "created_at": workflow.created_at,
                    "expires_at": workflow.expires_at,
                    "is_creator": is_creator,
                    "has_role": has_role,
                    "policy": workflow.policy.name,
                    "progress": self._calculate_workflow_progress(workflow)
                })
        
        return result
    
    async def link_intervention_to_workflow(self,
                                         intervention_id: str,
                                         workflow_id: str) -> Dict[str, Any]:
        """Link an intervention to an approval workflow."""
        # Check if intervention exists
        try:
            intervention = await self.intervention_interface.get_intervention(intervention_id)
        except Exception as e:
            raise ValueError(f"Error getting intervention {intervention_id}: {str(e)}")
        
        # Check if workflow exists
        if workflow_id not in self.approval_workflows:
            raise ValueError(f"Workflow {workflow_id} not found")
            
        workflow = self.approval_workflows[workflow_id]
        
        # Add link metadata
        if "linked_interventions" not in workflow.metadata:
            workflow.metadata["linked_interventions"] = []
            
        if intervention_id not in workflow.metadata["linked_interventions"]:
            workflow.metadata["linked_interventions"].append(intervention_id)
        
        # Save workflow
        await self._save_workflow(workflow)
        
        logger.info(f"Linked intervention {intervention_id} to workflow {workflow_id}")
        
        return {
            "intervention_id": intervention_id,
            "workflow_id": workflow_id,
            "linked": True
        }
    
    async def update_supervisor(self,
                             supervisor_id: str,
                             updates: Dict[str, Any]) -> Supervisor:
        """Update a supervisor's information."""
        if supervisor_id not in self.supervisors:
            raise ValueError(f"Supervisor {supervisor_id} not found")
            
        supervisor = self.supervisors[supervisor_id]
        
        # Apply updates
        if "name" in updates:
            supervisor.name = updates["name"]
            
        if "email" in updates:
            supervisor.email = updates["email"]
            
        if "password" in updates:
            supervisor.password_hash = bcrypt.hash(updates["password"])
            
        if "roles" in updates:
            supervisor.roles = [
                SupervisorRole(role) if isinstance(role, str) else role
                for role in updates["roles"]
            ]
            
        if "permissions" in updates:
            supervisor.permissions = [
                SupervisorPermission(
                    role=SupervisorRole(perm["role"]) if isinstance(perm["role"], str) else perm["role"],
                    allowed_actions=perm["allowed_actions"],
                    allowed_components=perm["allowed_components"]
                )
                for perm in updates["permissions"]
            ]
            
        if "active" in updates:
            supervisor.active = updates["active"]
        
        # Save supervisor
        await self._save_supervisor(supervisor)
        
        logger.info(f"Updated supervisor {supervisor.username}")
        
        return supervisor
    
    async def _save_supervisor(self, supervisor: Supervisor) -> None:
        """Save supervisor to storage."""
        storage_path = self.config.get("storage_path", "data/supervision")
        supervisors_dir = os.path.join(storage_path, "supervisors")
        os.makedirs(supervisors_dir, exist_ok=True)
        
        file_path = os.path.join(supervisors_dir, f"{supervisor.id}.json")
        
        with open(file_path, 'w') as f:
            json.dump(supervisor.to_dict(), f, indent=2)
            
        logger.debug(f"Supervisor {supervisor.id} saved to {file_path}")
    
    async def _save_workflow(self, workflow: ApprovalWorkflow) -> None:
        """Save workflow to storage."""
        storage_path = self.config.get("storage_path", "data/supervision")
        workflows_dir = os.path.join(storage_path, "workflows")
        os.makedirs(workflows_dir, exist_ok=True)
        
        file_path = os.path.join(workflows_dir, f"{workflow.id}.json")
        
        with open(file_path, 'w') as f:
            json.dump(workflow.to_dict(), f, indent=2)
            
        logger.debug(f"Workflow {workflow.id} saved to {file_path}")
```

Now, let's implement the unit tests for the Multi-Human Supervision Hub:

```python
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import os
import tempfile
import jwt
from datetime import datetime, timedelta
import json
import asyncio

@pytest.fixture
def mock_intervention_interface():
    """Create mock intervention interface."""
    return MagicMock(
        get_intervention=AsyncMock(),
        interventions={}
    )

@pytest.fixture
def supervision_hub(mock_intervention_interface):
    """Create SupervisionHub instance for testing."""
    # Use temp directory for storage
    temp_dir = tempfile.mkdtemp()
    
    return SupervisionHub(
        intervention_interface=mock_intervention_interface,
        config={
            "storage_path": temp_dir,
            "token_secret": "test_secret",
            "token_expiry_hours": 1,
            "default_policies": {
                "test_policy": ApprovalPolicy(
                    name="Test Policy",
                    description="Test policy for unit tests",
                    required_roles={
                        SupervisorRole.OPERATOR: 1,
                        SupervisorRole.SUPERVISOR: 1
                    }
                )
            },
            "session_timeout_minutes": 5
        }
    )

class TestSupervisionHub:
    """Test suite for SupervisionHub."""
    
    @pytest.mark.asyncio
    async def test_create_supervisor(self, supervision_hub):
        """Test supervisor creation."""
        supervisor = await supervision_hub.create_supervisor(
            username="testuser",
            name="Test User",
            email="test@example.com",
            password="password123",
            roles=[SupervisorRole.OPERATOR, SupervisorRole.SUPERVISOR]
        )
        
        assert supervisor.username == "testuser"
        assert supervisor.name == "Test User"
        assert supervisor.email == "test@example.com"
        assert len(supervisor.roles) == 2
        assert SupervisorRole.OPERATOR in supervisor.roles
        assert supervisor.id in supervision_hub.supervisors
    
    @pytest.mark.asyncio
    async def test_authenticate(self, supervision_hub):
        """Test supervisor authentication."""
        # Create supervisor
        await supervision_hub.create_supervisor(
            username="testuser",
            name="Test User",
            email="test@example.com",
            password="password123",
            roles=[SupervisorRole.OPERATOR]
        )
        
        # Authenticate
        auth_result = await supervision_hub.authenticate(
            username="testuser",
            password="password123"
        )
        
        assert "token" in auth_result
        assert "supervisor" in auth_result
        assert "session_id" in auth_result
        assert auth_result["supervisor"]["username"] == "testuser"
        
        # Verify token
        verify_result = await supervision_hub.verify_token(auth_result["token"])
        assert verify_result["valid"]
        assert verify_result["username"] == "testuser"
        
        # Test invalid password
        with pytest.raises(ValueError):
            await supervision_hub.authenticate(
                username="testuser",
                password="wrongpassword"
            )
    
    @pytest.mark.asyncio
    async def test_logout(self, supervision_hub):
        """Test supervisor logout."""
        # Create supervisor and authenticate
        await supervision_hub.create_supervisor(
            username="testuser",
            name="Test User",
            email="test@example.com",
            password="password123",
            roles=[SupervisorRole.OPERATOR]
        )
        
        auth_result = await supervision_hub.authenticate(
            username="testuser",
            password="password123"
        )
        
        token = auth_result["token"]
        session_id = auth_result["session_id"]
        
        # Logout
        logout_result = await supervision_hub.logout(token, session_id)
        assert logout_result["success"]
        
        # Verify token is invalidated
        with pytest.raises(ValueError):
            await supervision_hub.verify_token(token)
        
        # Verify session is removed
        assert session_id not in supervision_hub.active_sessions
    
    @pytest.mark.asyncio
    async def test_create_approval_workflow(self, supervision_hub):
        """Test approval workflow creation."""
        # Create supervisor
        supervisor = await supervision_hub.create_supervisor(
            username="testuser",
            name="Test User",
            email="test@example.com",
            password="password123",
            roles=[SupervisorRole.SUPERVISOR]
        )
        
        # Create workflow
        workflow = await supervision_hub.create_approval_workflow(
            title="Test Workflow",
            description="Test approval workflow",
            policy_name="test_policy",
            creator_id=supervisor.id,
            metadata={"test_key": "test_value"}
        )
        
        assert workflow.title == "Test Workflow"
        assert workflow.description == "Test approval workflow"
        assert workflow.created_by == supervisor.id
        assert workflow.status == ApprovalStatus.WAITING
        assert workflow.id in supervision_hub.approval_workflows
        assert workflow.metadata["test_key"] == "test_value"
    
    @pytest.mark.asyncio
    async def test_approval_submission(self, supervision_hub):
        """Test approval submission."""
        # Create supervisors
        supervisor1 = await supervision_hub.create_supervisor(
            username="operator",
            name="Operator User",
            email="operator@example.com",
            password="password123",
            roles=[SupervisorRole.OPERATOR]
        )
        
        supervisor2 = await supervision_hub.create_supervisor(
            username="supervisor",
            name="Supervisor User",
            email="supervisor@example.com",
            password="password123",
            roles=[SupervisorRole.SUPERVISOR]
        )
        
        # Create workflow
        workflow = await supervision_hub.create_approval_workflow(
            title="Test Workflow",
            description="Test approval workflow",
            policy_name="test_policy",
            creator_id=supervisor1.id
        )
        
        # Submit operator approval
        approval1 = await supervision_hub.submit_approval(
            workflow_id=workflow.id,
            supervisor_id=supervisor1.id,
            approved=True,
            notes="Operator approval"
        )
        
        assert approval1["approved"]
        assert workflow.status == ApprovalStatus.PARTIAL
        
        # Get workflow and check progress
        workflow_details = await supervision_hub.get_approval_workflow(workflow.id)
        assert workflow_details["status"] == "partial"
        assert workflow_details["progress"]["total_received"] == 1
        assert workflow_details["progress"]["percentage"] == 50.0  # 1 of 2 required
        
        # Submit supervisor approval
        approval2 = await supervision_hub.submit_approval(
            workflow_id=workflow.id,
            supervisor_id=supervisor2.id,
            approved=True,
            notes="Supervisor approval"
        )
        
        assert approval2["approved"]
        
        # Verify workflow is now approved
        workflow = supervision_hub.approval_workflows[workflow.id]
        assert workflow.status == ApprovalStatus.APPROVED
        
        # Get workflow details again
        workflow_details = await supervision_hub.get_approval_workflow(workflow.id)
        assert workflow_details["status"] == "approved"
        assert workflow_details["progress"]["percentage"] == 100.0
    
    @pytest.mark.asyncio
    async def test_rejection(self, supervision_hub):
        """Test workflow rejection."""
        # Create supervisors
        supervisor1 = await supervision_hub.create_supervisor(
            username="operator",
            name="Operator User",
            email="operator@example.com",
            password="password123",
            roles=[SupervisorRole.OPERATOR]
        )
        
        supervisor2 = await supervision_hub.create_supervisor(
            username="supervisor",
            name="Supervisor User",
            email="supervisor@example.com",
            password="password123",
            roles=[SupervisorRole.SUPERVISOR]
        )
        
        # Create workflow
        workflow = await supervision_hub.create_approval_workflow(
            title="Test Workflow",
            description="Test approval workflow",
            policy_name="test_policy",
            creator_id=supervisor1.id
        )
        
        # Submit rejection
        rejection = await supervision_hub.submit_approval(
            workflow_id=workflow.id,
            supervisor_id=supervisor2.id,
            approved=False,
            notes="Rejecting this workflow"
        )
        
        assert not rejection["approved"]
        
        # Verify workflow is rejected
        workflow = supervision_hub.approval_workflows[workflow.id]
        assert workflow.status == ApprovalStatus.REJECTED
    
    @pytest.mark.asyncio
    async def test_workflow_cancellation(self, supervision_hub):
        """Test workflow cancellation."""
        # Create supervisor
        supervisor = await supervision_hub.create_supervisor(
            username="testuser",
            name="Test User",
            email="test@example.com",
            password="password123",
            roles=[SupervisorRole.SUPERVISOR]
        )
        
        # Create workflow
        workflow = await supervision_hub.create_approval_workflow(
            title="Test Workflow",
            description="Test approval workflow",
            policy_name="test_policy",
            creator_id=supervisor.id
        )
        
        # Cancel workflow
        cancel_result = await supervision_hub.cancel_workflow(
            workflow_id=workflow.id,
            supervisor_id=supervisor.id,
            reason="No longer needed"
        )
        
        assert cancel_result["status"] == ApprovalStatus.CANCELED.value
        
        # Verify workflow status
        workflow = supervision_hub.approval_workflows[workflow.id]
        assert workflow.status == ApprovalStatus.CANCELED
        assert workflow.metadata["cancel_reason"] == "No longer needed"
    
    @pytest.mark.asyncio
    async def test_intervention_workflow_link(self, supervision_hub, mock_intervention_interface):
        """Test linking intervention to approval workflow."""
        # Create supervisor
        supervisor = await supervision_hub.create_supervisor(
            username="testuser",
            name="Test User",
            email="test@example.com",
            password="password123",
            roles=[SupervisorRole.SUPERVISOR]
        )
        
        # Setup mock intervention
        mock_intervention_interface.get_intervention.return_value = {
            "id": "test_intervention",
            "status": "pending"
        }
        
        # Create workflow
        workflow = await supervision_hub.create_approval_workflow(
            title="Test Workflow",
            description="Test approval workflow",
            policy_name="test_policy",
            creator_id=supervisor.id
        )
        
        # Link intervention to workflow
        link_result = await supervision_hub.link_intervention_to_workflow(
            intervention_id="test_intervention",
            workflow_id=workflow.id
        )
        
        assert link_result["linked"]
        assert "test_intervention" in workflow.metadata["linked_interventions"]
    
    @pytest.mark.asyncio
    async def test_get_workflows_for_supervisor(self, supervision_hub):
        """Test getting workflows for a supervisor."""
        # Create supervisors
        supervisor1 = await supervision_hub.create_supervisor(
            username="operator",
            name="Operator User",
            email="operator@example.com",
            password="password123",
            roles=[SupervisorRole.OPERATOR]
        )
        
        supervisor2 = await supervision_hub.create_supervisor(
            username="supervisor",
            name="Supervisor User",
            email="supervisor@example.com",
            password="password123",
            roles=[SupervisorRole.SUPERVISOR]
        )
        
        # Create workflows
        workflow1 = await supervision_hub.create_approval_workflow(
            title="Workflow 1",
            description="First workflow",
            policy_name="test_policy",
            creator_id=supervisor1.id
        )
        
        workflow2 = await supervision_hub.create_approval_workflow(
            title="Workflow 2",
            description="Second workflow",
            policy_name="test_policy",
            creator_id=supervisor2.id
        )
        
        # Get workflows for operator
        operator_workflows = await supervision_hub.get_workflows_for_supervisor(
            supervisor_id=supervisor1.id
        )
        
        assert len(operator_workflows) == 2  # Should see both workflows
        assert any(w["title"] == "Workflow 1" for w in operator_workflows)
        assert any(w["title"] == "Workflow 2" for w in operator_workflows)
        
        # Filter by status
        await supervision_hub.cancel_workflow(
            workflow_id=workflow1.id,
            supervisor_id=supervisor1.id,
            reason="Testing"
        )
        
        active_workflows = await supervision_hub.get_workflows_for_supervisor(
            supervisor_id=supervisor1.id,
            status_filter=[ApprovalStatus.WAITING, ApprovalStatus.PARTIAL]
        )
        
        assert len(active_workflows) == 1
        assert active_workflows[0]["title"] == "Workflow 2"
    
    @pytest.mark.asyncio
    async def test_update_supervisor(self, supervision_hub):
        """Test updating supervisor details."""
        # Create supervisor
        supervisor = await supervision_hub.create_supervisor(
            username="testuser",
            name="Test User",
            email="test@example.com",
            password="password123",
            roles=[SupervisorRole.OPERATOR]
        )
        
        # Update supervisor
        updated = await supervision_hub.update_supervisor(
            supervisor_id=supervisor.id,
            updates={
                "name": "Updated Name",
                "email": "updated@example.com",
                "roles": [SupervisorRole.SUPERVISOR]
            }
        )
        
        assert updated.name == "Updated Name"
        assert updated.email == "updated@example.com"
        assert SupervisorRole.SUPERVISOR in updated.roles
        assert SupervisorRole.OPERATOR not in updated.roles
```

Now, let's implement Work Unit 5.4: Budget & Resource Monitor, which tracks resource usage and budgets across the system:

```python
from typing import Dict, List, Optional, Any, Union, Callable
import logging
from enum import Enum
from dataclasses import dataclass, field
import asyncio
import json
from datetime import datetime, timedelta
import os
from pathlib import Path
import uuid
import time
import matplotlib.pyplot as plt
import pandas as pd
from io import BytesIO
import base64
import psutil
import threading

logger = logging.getLogger(__name__)

class ResourceType(Enum):
    """Types of resources that can be monitored."""
    CPU = "cpu"
    MEMORY = "memory"
    STORAGE = "storage"
    NETWORK = "network"
    API_CALLS = "api_calls"
    MODEL_TOKENS = "model_tokens"
    PROCESSING_TIME = "processing_time"
    CONCURRENT_TASKS = "concurrent_tasks"

class BudgetPeriod(Enum):
    """Time periods for budget tracking."""
    HOURLY = "hourly"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"
    PERPETUAL = "perpetual"

@dataclass
class ResourceUsage:
    """Usage data for a specific resource."""
    resource_type: ResourceType
    component: str
    quantity: float
    unit: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class Budget:
    """Budget for a specific resource."""
    id: str
    resource_type: ResourceType
    components: List[str]  # Components this budget applies to, empty means all
    limit: float
    period: BudgetPeriod
    unit: str
    start_date: str
    name: str
    description: str
    tags: List[str] = field(default_factory=list)
    alert_thresholds: Dict[str, float] = field(default_factory=dict)
    active: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "id": self.id,
            "resource_type": self.resource_type.value,
            "components": self.components,
            "limit": self.limit,
            "period": self.period.value,
            "unit": self.unit,
            "start_date": self.start_date,
            "name": self.name,
            "description": self.description,
            "tags": self.tags,
            "alert_thresholds": self.alert_thresholds,
            "active": self.active
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Budget':
        """Create from dictionary."""
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            resource_type=ResourceType(data.get("resource_type")),
            components=data.get("components", []),
            limit=data.get("limit", 0.0),
            period=BudgetPeriod(data.get("period")),
            unit=data.get("unit", ""),
            start_date=data.get("start_date", datetime.now().isoformat()),
            name=data.get("name", ""),
            description=data.get("description", ""),
            tags=data.get("tags", []),
            alert_thresholds=data.get("alert_thresholds", {}),
            active=data.get("active", True)
        )

@dataclass
class BudgetAlert:
    """Alert when a budget threshold is reached."""
    id: str
    budget_id: str
    threshold_name: str
    threshold_value: float
    current_usage: float
    percentage: float
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    acknowledged: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "id": self.id,
            "budget_id": self.budget_id,
            "threshold_name": self.threshold_name,
            "threshold_value": self.threshold_value,
            "current_usage": self.current_usage,
            "percentage": self.percentage,
            "timestamp": self.timestamp,
            "acknowledged": self.acknowledged
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BudgetAlert':
        """Create from dictionary."""
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            budget_id=data.get("budget_id", ""),
            threshold_name=data.get("threshold_name", ""),
            threshold_value=data.get("threshold_value", 0.0),
            current_usage=data.get("current_usage", 0.0),
            percentage=data.get("percentage", 0.0),
            timestamp=data.get("timestamp", datetime.now().isoformat()),
            acknowledged=data.get("acknowledged", False)
        )

class ResourceMonitor:
    """Monitors and manages system resource usage and budgets."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize with optional configuration."""
        self.config = config or {
            "storage_path": "data/resources",
            "usage_retention_days": 30,
            "system_monitoring_enabled": True,
            "monitoring_interval_seconds": 60,
            "default_alert_thresholds": {
                "warning": 70.0,
                "critical": 90.0
            }
        }
        
        self.budgets: Dict[str, Budget] = {}
        self.usage_records: List[ResourceUsage] = []
        self.alerts: Dict[str, BudgetAlert] = {}
        
        self.system_monitor_task = None
        self.is_monitoring = False
        # Initialize resource type handlers
        self.resource_handlers: Dict[ResourceType, Callable] = {
            ResourceType.CPU: self._monitor_cpu,
            ResourceType.MEMORY: self._monitor_memory,
            ResourceType.STORAGE: self._monitor_storage,
            ResourceType.NETWORK: self._monitor_network,
            ResourceType.API_CALLS: self._monitor_api_calls,
            ResourceType.MODEL_TOKENS: self._monitor_model_tokens,
            ResourceType.PROCESSING_TIME: self._monitor_processing_time,
            ResourceType.CONCURRENT_TASKS: self._monitor_concurrent_tasks
        }
        
        # Load existing data
        self._load_data()
    
    async def start_monitoring(self) -> Dict[str, Any]:
        """Start system resource monitoring."""
        if self.is_monitoring:
            return {"status": "already_monitoring"}
        
        if not self.config.get("system_monitoring_enabled", True):
            return {"status": "monitoring_disabled"}
        
        self.is_monitoring = True
        
        # Start background monitoring task
        self.system_monitor_task = asyncio.create_task(self._run_system_monitoring())
        
        logger.info("System resource monitoring started")
        
        return {
            "status": "monitoring_started",
            "interval": self.config.get("monitoring_interval_seconds", 60)
        }
    
    async def stop_monitoring(self) -> Dict[str, Any]:
        """Stop system resource monitoring."""
        if not self.is_monitoring:
            return {"status": "not_monitoring"}
        
        self.is_monitoring = False
        
        # Cancel monitoring task
        if self.system_monitor_task and not self.system_monitor_task.done():
            self.system_monitor_task.cancel()
            
            try:
                await self.system_monitor_task
            except asyncio.CancelledError:
                pass
        
        logger.info("System resource monitoring stopped")
        
        return {"status": "monitoring_stopped"}
    
    async def create_budget(self,
                          resource_type: ResourceType,
                          limit: float,
                          period: BudgetPeriod,
                          unit: str,
                          name: str,
                          description: str,
                          components: Optional[List[str]] = None,
                          tags: Optional[List[str]] = None,
                          alert_thresholds: Optional[Dict[str, float]] = None,
                          start_date: Optional[str] = None) -> Budget:
        """Create a new resource budget."""
        # Generate budget ID
        budget_id = f"budget_{uuid.uuid4().hex[:8]}"
        
        # Use defaults if not provided
        components = components or []
        tags = tags or []
        alert_thresholds = alert_thresholds or self.config.get("default_alert_thresholds", {})
        start_date = start_date or datetime.now().isoformat()
        
        # Create budget
        budget = Budget(
            id=budget_id,
            resource_type=resource_type,
            components=components,
            limit=limit,
            period=period,
            unit=unit,
            start_date=start_date,
            name=name,
            description=description,
            tags=tags,
            alert_thresholds=alert_thresholds
        )
        
        # Store budget
        self.budgets[budget_id] = budget
        
        # Save to storage
        await self._save_budget(budget)
        
        logger.info(f"Created budget {budget_id}: {name}")
        
        return budget
    
    async def record_usage(self,
                         resource_type: ResourceType,
                         component: str,
                         quantity: float,
                         unit: str,
                         metadata: Optional[Dict[str, Any]] = None) -> ResourceUsage:
        """Record resource usage."""
        # Create usage record
        usage = ResourceUsage(
            resource_type=resource_type,
            component=component,
            quantity=quantity,
            unit=unit,
            timestamp=datetime.now().isoformat(),
            metadata=metadata or {}
        )
        
        # Add to records
        self.usage_records.append(usage)
        
        # Trim records if needed
        if self.config.get("max_usage_records"):
            max_records = self.config["max_usage_records"]
            if len(self.usage_records) > max_records:
                self.usage_records = self.usage_records[-max_records:]
        
        # Check against budgets
        await self._check_budget_thresholds(usage)
        
        # Save to storage periodically
        # (in a real system, would batch these writes)
        if len(self.usage_records) % 100 == 0:
            await self._save_usage_records()
        
        return usage
    
    async def get_budget(self, budget_id: str) -> Dict[str, Any]:
        """Get details of a budget."""
        if budget_id not in self.budgets:
            raise ValueError(f"Budget {budget_id} not found")
        
        budget = self.budgets[budget_id]
        
        # Calculate current usage
        usage_data = await self._calculate_budget_usage(budget)
        
        result = budget.to_dict()
        result.update(usage_data)
        
        return result
    
    async def get_budgets(self, 
                        resource_type: Optional[ResourceType] = None,
                        component: Optional[str] = None,
                        tag: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get all budgets, optionally filtered."""
        results = []
        
        for budget_id, budget in self.budgets.items():
            # Apply filters
            if resource_type and budget.resource_type != resource_type:
                continue
                
            if component and (budget.components and component not in budget.components):
                continue
                
            if tag and tag not in budget.tags:
                continue
            
            # Calculate usage
            usage_data = await self._calculate_budget_usage(budget)
            
            # Build result
            result = budget.to_dict()
            result.update(usage_data)
            
            results.append(result)
        
        return results
    
    async def update_budget(self,
                          budget_id: str,
                          updates: Dict[str, Any]) -> Budget:
        """Update a budget."""
        if budget_id not in self.budgets:
            raise ValueError(f"Budget {budget_id} not found")
        
        budget = self.budgets[budget_id]
        
        # Apply updates
        if "name" in updates:
            budget.name = updates["name"]
            
        if "description" in updates:
            budget.description = updates["description"]
            
        if "limit" in updates:
            budget.limit = updates["limit"]
            
        if "period" in updates:
            budget.period = updates["period"] if isinstance(updates["period"], BudgetPeriod) else BudgetPeriod(updates["period"])
            
        if "components" in updates:
            budget.components = updates["components"]
            
        if "tags" in updates:
            budget.tags = updates["tags"]
            
        if "alert_thresholds" in updates:
            budget.alert_thresholds = updates["alert_thresholds"]
            
        if "active" in updates:
            budget.active = updates["active"]
        
        # Save budget
        await self._save_budget(budget)
        
        # Check thresholds after update
        for usage in self.usage_records[-10:]:  # Check recent usage
            if usage.resource_type == budget.resource_type:
                await self._check_budget_thresholds(usage)
        
        logger.info(f"Updated budget {budget_id}")
        
        return budget
    
    async def get_resource_usage(self,
                               resource_type: Optional[ResourceType] = None,
                               component: Optional[str] = None,
                               start_time: Optional[str] = None,
                               end_time: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get resource usage records, optionally filtered."""
        results = []
        
        for usage in self.usage_records:
            # Apply filters
            if resource_type and usage.resource_type != resource_type:
                continue
                
            if component and usage.component != component:
                continue
                
            if start_time and usage.timestamp < start_time:
                continue
                
            if end_time and usage.timestamp > end_time:
                continue
            
            # Add to results
            results.append({
                "resource_type": usage.resource_type.value,
                "component": usage.component,
                "quantity": usage.quantity,
                "unit": usage.unit,
                "timestamp": usage.timestamp,
                "metadata": usage.metadata
            })
        
        return results
    
    async def get_alerts(self,
                       budget_id: Optional[str] = None,
                       include_acknowledged: bool = False) -> List[Dict[str, Any]]:
        """Get budget alerts, optionally filtered."""
        results = []
        
        for alert_id, alert in self.alerts.items():
            # Apply filters
            if budget_id and alert.budget_id != budget_id:
                continue
                
            if not include_acknowledged and alert.acknowledged:
                continue
            
            # Add to results
            results.append(alert.to_dict())
        
        return results
    
    async def acknowledge_alert(self, alert_id: str) -> Dict[str, Any]:
        """Acknowledge a budget alert."""
        if alert_id not in self.alerts:
            raise ValueError(f"Alert {alert_id} not found")
        
        alert = self.alerts[alert_id]
        alert.acknowledged = True
        
        # Save to storage
        await self._save_alerts()
        
        return alert.to_dict()
    
    async def create_usage_report(self,
                                resource_type: Optional[ResourceType] = None,
                                component: Optional[str] = None,
                                start_time: Optional[str] = None,
                                end_time: Optional[str] = None,
                                group_by: Optional[str] = None) -> Dict[str, Any]:
        """Create a report of resource usage."""
        # Get usage data
        usage_data = await self.get_resource_usage(
            resource_type=resource_type,
            component=component,
            start_time=start_time,
            end_time=end_time
        )
        
        if not usage_data:
            return {
                "status": "no_data",
                "resource_type": resource_type.value if resource_type else "all",
                "component": component or "all"
            }
        
        # Convert to DataFrame for easier analysis
        df = pd.DataFrame(usage_data)
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        
        # Summary stats
        summary = {
            "total_records": len(df),
            "date_range": {
                "start": df["timestamp"].min().isoformat(),
                "end": df["timestamp"].max().isoformat()
            },
            "resource_types": df["resource_type"].unique().tolist(),
            "components": df["component"].unique().tolist()
        }
        
        # Group data if requested
        if group_by:
            if group_by == "resource_type":
                grouped = df.groupby("resource_type")
            elif group_by == "component":
                grouped = df.groupby("component")
            elif group_by == "day":
                grouped = df.groupby(df["timestamp"].dt.date)
            elif group_by == "hour":
                grouped = df.groupby(df["timestamp"].dt.strftime("%Y-%m-%d %H:00"))
            else:
                grouped = df.groupby(group_by)
                
            # Calculate stats by group
            group_stats = []
            for name, group in grouped:
                group_stats.append({
                    "group": str(name),
                    "count": len(group),
                    "total_quantity": group["quantity"].sum(),
                    "average_quantity": group["quantity"].mean(),
                    "min_quantity": group["quantity"].min(),
                    "max_quantity": group["quantity"].max()
                })
                
            summary["grouped_by"] = group_by
            summary["groups"] = group_stats
        
        # Overall stats
        summary["overall"] = {
            "total_quantity": df["quantity"].sum(),
            "average_quantity": df["quantity"].mean(),
            "min_quantity": df["quantity"].min(),
            "max_quantity": df["quantity"].max()
        }
        
        # Create visualization
        visualization = await self._create_usage_visualization(
            df, 
            resource_type.value if resource_type else "all", 
            component or "all",
            group_by
        )
        
        # Build final report
        report = {
            "status": "success",
            "summary": summary,
            "visualization": visualization,
            "timestamp": datetime.now().isoformat()
        }
        
        return report
    
    async def _create_usage_visualization(self,
                                        df: pd.DataFrame,
                                        resource_type_str: str,
                                        component_str: str,
                                        group_by: Optional[str]) -> Dict[str, Any]:
        """Create visualization of usage data."""
        if len(df) < 2:
            return {"status": "insufficient_data"}
        
        # Create different visualizations based on grouping
        if group_by == "resource_type":
            return await self._visualize_by_resource_type(df)
        elif group_by == "component":
            return await self._visualize_by_component(df)
        else:
            # Time series visualization
            return await self._visualize_time_series(df, resource_type_str, component_str)
    
    async def _visualize_time_series(self,
                                   df: pd.DataFrame,
                                   resource_type_str: str,
                                   component_str: str) -> Dict[str, Any]:
        """Create time series visualization."""
        plt.figure(figsize=(12, 6))
        
        # If multiple resource types or components, use a grouped visualization
        if len(df["resource_type"].unique()) > 1 or len(df["component"].unique()) > 1:
            # Group by resource type and component
            groups = df.groupby(["resource_type", "component"])
            
            for (res_type, comp), group in groups:
                plt.plot(
                    group["timestamp"], 
                    group["quantity"], 
                    label=f"{res_type} - {comp}",
                    marker='o' if len(group) < 10 else None
                )
        else:
            plt.plot(
                df["timestamp"], 
                df["quantity"], 
                label=f"{resource_type_str} - {component_str}",
                marker='o' if len(df) < 10 else None
            )
        
        plt.title(f"Resource Usage Over Time: {resource_type_str}")
        plt.xlabel("Time")
        plt.ylabel(f"Quantity ({df['unit'].iloc[0]})")
        plt.grid(True)
        plt.legend()
        
        # Add budget lines if applicable
        for budget in self.budgets.values():
            if (resource_type_str == "all" or budget.resource_type.value == resource_type_str) and \
               (component_str == "all" or not budget.components or component_str in budget.components):
                plt.axhline(
                    y=budget.limit, 
                    color='r', 
                    linestyle='--', 
                    label=f"Budget: {budget.name} ({budget.limit} {budget.unit})"
                )
        
        plt.tight_layout()
        
        # Convert to base64
        buffer = BytesIO()
        plt.savefig(buffer, format="png")
        plt.close()
        
        image_base64 = base64.b64encode(buffer.getvalue()).decode("utf-8")
        
        return {
            "type": "time_series",
            "image": f"data:image/png;base64,{image_base64}"
        }
    
    async def _visualize_by_resource_type(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Create visualization grouped by resource type."""
        plt.figure(figsize=(10, 6))
        
        # Group by resource type
        grouped = df.groupby("resource_type")["quantity"].sum()
        
        # Create bar chart
        ax = grouped.plot(kind="bar", color="skyblue")
        plt.title("Resource Usage by Type")
        plt.xlabel("Resource Type")
        plt.ylabel(f"Total Quantity")
        plt.grid(True, axis='y')
        
        # Add labels
        for i, v in enumerate(grouped):
            ax.text(i, v * 1.01, f"{v:.1f}", ha='center')
        
        plt.tight_layout()
        
        # Convert to base64
        buffer = BytesIO()
        plt.savefig(buffer, format="png")
        plt.close()
        
        image_base64 = base64.b64encode(buffer.getvalue()).decode("utf-8")
        
        return {
            "type": "resource_type_distribution",
            "image": f"data:image/png;base64,{image_base64}"
        }
    
    async def _visualize_by_component(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Create visualization grouped by component."""
        plt.figure(figsize=(12, 6))
        
        # Group by component
        grouped = df.groupby("component")["quantity"].sum().sort_values(ascending=False)
        
        # Limit to top 10 if too many
        if len(grouped) > 10:
            grouped = grouped.head(10)
        
        # Create bar chart
        ax = grouped.plot(kind="bar", color="lightgreen")
        plt.title("Resource Usage by Component")
        plt.xlabel("Component")
        plt.ylabel(f"Total Quantity")
        plt.grid(True, axis='y')
        
        # Add labels
        for i, v in enumerate(grouped):
            ax.text(i, v * 1.01, f"{v:.1f}", ha='center')
        
        plt.tight_layout()
        
        # Convert to base64
        buffer = BytesIO()
        plt.savefig(buffer, format="png")
        plt.close()
        
        image_base64 = base64.b64encode(buffer.getvalue()).decode("utf-8")
        
        return {
            "type": "component_distribution",
            "image": f"data:image/png;base64,{image_base64}"
        }
    
    async def _run_system_monitoring(self) -> None:
        """Run periodic system monitoring."""
        try:
            while self.is_monitoring:
                # Monitor system resources
                await self._collect_system_metrics()
                
                # Sleep until next interval
                interval = self.config.get("monitoring_interval_seconds", 60)
                await asyncio.sleep(interval)
                
        except asyncio.CancelledError:
            logger.info("System monitoring task canceled")
        except Exception as e:
            logger.error(f"Error in system monitoring: {str(e)}")
            self.is_monitoring = False
            raise
    
    async def _collect_system_metrics(self) -> None:
        """Collect system resource metrics."""
        try:
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            await self.record_usage(
                resource_type=ResourceType.CPU,
                component="system",
                quantity=cpu_percent,
                unit="percent"
            )
            
            # Memory usage
            memory = psutil.virtual_memory()
            await self.record_usage(
                resource_type=ResourceType.MEMORY,
                component="system",
                quantity=memory.percent,
                unit="percent",
                metadata={
                    "total": memory.total,
                    "available": memory.available,
                    "used": memory.used
                }
            )
            
            # Disk usage
            disk = psutil.disk_usage('/')
            await self.record_usage(
                resource_type=ResourceType.STORAGE,
                component="system",
                quantity=disk.percent,
                unit="percent",
                metadata={
                    "total": disk.total,
                    "free": disk.free,
                    "used": disk.used
                }
            )
            
            # Network IO
            net_io = psutil.net_io_counters()
            await self.record_usage(
                resource_type=ResourceType.NETWORK,
                component="system",
                quantity=net_io.bytes_sent + net_io.bytes_recv,
                unit="bytes",
                metadata={
                    "bytes_sent": net_io.bytes_sent,
                    "bytes_recv": net_io.bytes_recv,
                    "packets_sent": net_io.packets_sent,
                    "packets_recv": net_io.packets_recv
                }
            )
            
        except Exception as e:
            logger.error(f"Error collecting system metrics: {str(e)}")
    
    async def _calculate_budget_usage(self, budget: Budget) -> Dict[str, Any]:
        """Calculate current usage for a budget."""
        # Determine time window based on budget period
        start_time = None
        
        # Get budget start date
        budget_start = datetime.fromisoformat(budget.start_date)
        
        # Calculate period start time
        now = datetime.now()
        if budget.period == BudgetPeriod.HOURLY:
            start_time = now.replace(minute=0, second=0, microsecond=0)
        elif budget.period == BudgetPeriod.DAILY:
            start_time = now.replace(hour=0, minute=0, second=0, microsecond=0)
        elif budget.period == BudgetPeriod.WEEKLY:
            # Start of week (Monday)
            start_time = (now - timedelta(days=now.weekday())).replace(
                hour=0, minute=0, second=0, microsecond=0
            )
        elif budget.period == BudgetPeriod.MONTHLY:
            start_time = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        elif budget.period == BudgetPeriod.QUARTERLY:
            quarter_month = ((now.month - 1) // 3) * 3 + 1
            start_time = now.replace(
                month=quarter_month, day=1, hour=0, minute=0, second=0, microsecond=0
            )
        elif budget.period == BudgetPeriod.YEARLY:
            start_time = now.replace(
                month=1, day=1, hour=0, minute=0, second=0, microsecond=0
            )
        elif budget.period == BudgetPeriod.PERPETUAL:
            start_time = budget_start
        
        # Ensure we don't go before budget start
        if start_time < budget_start:
            start_time = budget_start
        
        start_time_str = start_time.isoformat()
        
        # Filter usage records
        usage_in_period = []
        for usage in self.usage_records:
            # Match resource type
            if usage.resource_type != budget.resource_type:
                continue
            
            # Match component (if budget specifies components)
            if budget.components and usage.component not in budget.components:
                continue
            
            # Check time period
            if usage.timestamp < start_time_str:
                continue
            
            usage_in_period.append(usage)
        
        # Calculate total usage
        total_usage = sum(usage.quantity for usage in usage_in_period)
        usage_count = len(usage_in_period)
        
        # Calculate percentage of budget used
        percentage_used = (total_usage / budget.limit * 100) if budget.limit > 0 else 0
        
        # Determine status
        status = "ok"
        if percentage_used >= 90:
            status = "critical"
        elif percentage_used >= 70:
            status = "warning"
        
        return {
            "usage": {
                "total": total_usage,
                "count": usage_count,
                "percentage": percentage_used,
                "status": status,
                "period_start": start_time_str,
                "period_end": now.isoformat(),
                "remaining": max(0, budget.limit - total_usage)
            }
        }
    
    async def _check_budget_thresholds(self, usage: ResourceUsage) -> None:
        """Check if usage triggers any budget thresholds."""
        # Find relevant budgets
        for budget_id, budget in self.budgets.items():
            # Skip inactive budgets
            if not budget.active:
                continue
            
            # Match resource type
            if budget.resource_type != usage.resource_type:
                continue
            
            # Match component (if budget specifies components)
            if budget.components and usage.component not in budget.components:
                continue
            
            # Calculate current usage
            usage_data = await self._calculate_budget_usage(budget)
            current_usage = usage_data["usage"]["total"]
            percentage = usage_data["usage"]["percentage"]
            
            # Check thresholds
            for threshold_name, threshold_value in budget.alert_thresholds.items():
                # Convert threshold to percentage if it's not already
                threshold_percentage = threshold_value
                if threshold_value > 1 and threshold_value <= 100:
                    threshold_percentage = threshold_value
                elif threshold_value <= 1:
                    threshold_percentage = threshold_value * 100
                
                # Check if threshold crossed
                if percentage >= threshold_percentage:
                    # Create alert ID
                    alert_id = f"alert_{uuid.uuid4().hex[:8]}"
                    
                    # Check if similar alert already exists
                    for existing_alert in self.alerts.values():
                        if (existing_alert.budget_id == budget_id and
                            existing_alert.threshold_name == threshold_name and
                            not existing_alert.acknowledged):
                            # Already have an unacknowledged alert for this
                            return
                    
                    # Create new alert
                    alert = BudgetAlert(
                        id=alert_id,
                        budget_id=budget_id,
                        threshold_name=threshold_name,
                        threshold_value=threshold_value,
                        current_usage=current_usage,
                        percentage=percentage
                    )
                    
                    # Store alert
                    self.alerts[alert_id] = alert
                    
                    # Save alerts
                    await self._save_alerts()
                    
                    logger.warning(
                        f"Budget alert: {budget.name} ({threshold_name} threshold at {threshold_percentage}%) - "
                        f"Current usage: {current_usage} {budget.unit} ({percentage:.1f}%)"
                    )
    
    def _monitor_cpu(self) -> Dict[str, Any]:
        """Monitor CPU usage."""
        return {
            "percentage": psutil.cpu_percent(interval=1),
            "count": psutil.cpu_count()
        }
    
    def _monitor_memory(self) -> Dict[str, Any]:
        """Monitor memory usage."""
        memory = psutil.virtual_memory()
        return {
            "total": memory.total,
            "available": memory.available,
            "used": memory.used,
            "percentage": memory.percent
        }
    
    def _monitor_storage(self) -> Dict[str, Any]:
        """Monitor storage usage."""
        disk = psutil.disk_usage('/')
        return {
            "total": disk.total,
            "free": disk.free,
            "used": disk.used,
            "percentage": disk.percent
        }
    
    def _monitor_network(self) -> Dict[str, Any]:
        """Monitor network usage."""
        net_io = psutil.net_io_counters()
        return {
            "bytes_sent": net_io.bytes_sent,
            "bytes_recv": net_io.bytes_recv,
            "packets_sent": net_io.packets_sent,
            "packets_recv": net_io.packets_recv
        }
    
    def _monitor_api_calls(self) -> Dict[str, Any]:
        """Monitor API calls."""
        # This would be integrated with your API tracking
        return {}
    
    def _monitor_model_tokens(self) -> Dict[str, Any]:
        """Monitor model token usage."""
        # This would be integrated with your LLM usage tracking
        return {}
    
    def _monitor_processing_time(self) -> Dict[str, Any]:
        """Monitor processing time."""
        # This would track processing time for various operations
        return {}
    
    def _monitor_concurrent_tasks(self) -> Dict[str, Any]:
        """Monitor concurrent tasks."""
        # This would track the number of parallel tasks running
        return {}
    
    async def _load_data(self) -> None:
        """Load budgets, usage records and alerts from storage."""
        storage_path = self.config.get("storage_path", "data/resources")
        
        # Load budgets
        budgets_dir = os.path.join(storage_path, "budgets")
        if os.path.exists(budgets_dir):
            for filename in os.listdir(budgets_dir):
                if filename.endswith(".json"):
                    try:
                        with open(os.path.join(budgets_dir, filename), 'r') as f:
                            data = json.load(f)
                            budget = Budget.from_dict(data)
                            self.budgets[budget.id] = budget
                    except Exception as e:
                        logger.error(f"Error loading budget from {filename}: {str(e)}")
        
        # Load usage records
        usage_file = os.path.join(storage_path, "usage_records.json")
        if os.path.exists(usage_file):
            try:
                with open(usage_file, 'r') as f:
                    data = json.load(f)
                    
                    records = []
                    for record_data in data:
                        try:
                            resource_type = ResourceType(record_data.get("resource_type"))
                            record = ResourceUsage(
                                resource_type=resource_type,
                                component=record_data.get("component", ""),
                                quantity=record_data.get("quantity", 0.0),
                                unit=record_data.get("unit", ""),
                                timestamp=record_data.get("timestamp", datetime.now().isoformat()),
                                metadata=record_data.get("metadata", {})
                            )
                            records.append(record)
                        except Exception as e:
                            logger.error(f"Error parsing usage record: {str(e)}")
                    
                    self.usage_records = records
            except Exception as e:
                logger.error(f"Error loading usage records: {str(e)}")
        
        # Load alerts
        alerts_file = os.path.join(storage_path, "alerts.json")
        if os.path.exists(alerts_file):
            try:
                with open(alerts_file, 'r') as f:
                    data = json.load(f)
                    
                    alerts = {}
                    for alert_data in data:
                        try:
                            alert = BudgetAlert.from_dict(alert_data)
                            alerts[alert.id] = alert
                        except Exception as e:
                            logger.error(f"Error parsing alert: {str(e)}")
                    
                    self.alerts = alerts
            except Exception as e:
                logger.error(f"Error loading alerts: {str(e)}")
    
    async def _save_budget(self, budget: Budget) -> None:
        """Save budget to storage."""
        storage_path = self.config.get("storage_path", "data/resources")
        budgets_dir = os.path.join(storage_path, "budgets")
        os.makedirs(budgets_dir, exist_ok=True)
        
        file_path = os.path.join(budgets_dir, f"{budget.id}.json")
        
        with open(file_path, 'w') as f:
            json.dump(budget.to_dict(), f, indent=2)
            
        logger.debug(f"Budget {budget.id} saved to {file_path}")
    
    async def _save_usage_records(self) -> None:
        """Save usage records to storage."""
        storage_path = self.config.get("storage_path", "data/resources")
        os.makedirs(storage_path, exist_ok=True)
        
        file_path = os.path.join(storage_path, "usage_records.json")
        
        # Convert to list of dictionaries
        data = []
        for usage in self.usage_records:
            data.append({
                "resource_type": usage.resource_type.value,
                "component": usage.component,
                "quantity": usage.quantity,
                "unit": usage.unit,
                "timestamp": usage.timestamp,
                "metadata": usage.metadata
            })
        
        with open(file_path, 'w') as f:
            json.dump(data, f, indent=2)
            
        logger.debug(f"Saved {len(data)} usage records to {file_path}")
    
    async def _save_alerts(self) -> None:
        """Save alerts to storage."""
        storage_path = self.config.get("storage_path", "data/resources")
        os.makedirs(storage_path, exist_ok=True)
        
        file_path = os.path.join(storage_path, "alerts.json")
        
        # Convert to list of dictionaries
        data = [alert.to_dict() for alert in self.alerts.values()]
        
        with open(file_path, 'w') as f:
            json.dump(data, f, indent=2)
            
        logger.debug(f"Saved {len(data)} alerts to {file_path}")
    
    async def clear_old_data(self) -> Dict[str, Any]:
        """Clear old usage records and acknowledged alerts."""
        now = datetime.now()
        retention_days = self.config.get("usage_retention_days", 30)
        cutoff_date = (now - timedelta(days=retention_days)).isoformat()
        
        # Filter usage records
        old_count = len(self.usage_records)
        self.usage_records = [
            usage for usage in self.usage_records
            if usage.timestamp >= cutoff_date
        ]
        usage_removed = old_count - len(self.usage_records)
        
        # Filter acknowledged alerts
        old_alert_count = len(self.alerts)
        self.alerts = {
            alert_id: alert for alert_id, alert in self.alerts.items()
            if not alert.acknowledged or alert.timestamp >= cutoff_date
        }
        alerts_removed = old_alert_count - len(self.alerts)
        
        # Save updated data
        await self._save_usage_records()
        await self._save_alerts()
        
        return {
            "usage_records_removed": usage_removed,
            "alerts_removed": alerts_removed,
            "cutoff_date": cutoff_date
        }
```

Now, let's implement the unit tests for the Resource Monitor:

```python
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import os
import tempfile
from datetime import datetime, timedelta
import json
import asyncio

@pytest.fixture
def resource_monitor():
    """Create ResourceMonitor instance for testing."""
    # Use temp directory for storage
    temp_dir = tempfile.mkdtemp()
    
    return ResourceMonitor(
        config={
            "storage_path": temp_dir,
            "usage_retention_days": 30,
            "system_monitoring_enabled": True,
            "monitoring_interval_seconds": 0.1,  # Fast for testing
            "default_alert_thresholds": {
                "warning": 70.0,
                "critical": 90.0
            }
        }
    )

class TestResourceMonitor:
    """Test suite for ResourceMonitor."""
    
    @pytest.mark.asyncio
    async def test_create_budget(self, resource_monitor):
        """Test budget creation."""
        budget = await resource_monitor.create_budget(
            resource_type=ResourceType.CPU,
            limit=80.0,
            period=BudgetPeriod.HOURLY,
            unit="percent",
            name="Test CPU Budget",
            description="Test CPU usage budget",
            components=["system"],
            tags=["test"]
        )
        
        assert budget.name == "Test CPU Budget"
        assert budget.resource_type == ResourceType.CPU
        assert budget.limit == 80.0
        assert budget.unit == "percent"
        assert "system" in budget.components
        assert "test" in budget.tags
        assert budget.id in resource_monitor.budgets
    
    @pytest.mark.asyncio
    async def test_record_usage(self, resource_monitor):
        """Test recording resource usage."""
        usage = await resource_monitor.record_usage(
            resource_type=ResourceType.CPU,
            component="system",
            quantity=50.0,
            unit="percent",
            metadata={"test_key": "test_value"}
        )
        
        assert usage.resource_type == ResourceType.CPU
        assert usage.component == "system"
        assert usage.quantity == 50.0
        assert usage.unit == "percent"
        assert usage.metadata["test_key"] == "test_value"
        assert len(resource_monitor.usage_records) == 1
    
    @pytest.mark.asyncio
    async def test_budget_usage_calculation(self, resource_monitor):
        """Test budget usage calculation."""
        # Create budget
        budget = await resource_monitor.create_budget(
            resource_type=ResourceType.MEMORY,
            limit=1000.0,
            period=BudgetPeriod.DAILY,
            unit="MB",
            name="Test Memory Budget",
            description="Test memory usage budget"
        )
        
        # Record usage
        await resource_monitor.record_usage(
            resource_type=ResourceType.MEMORY,
            component="app1",
            quantity=300.0,
            unit="MB"
        )
        
        await resource_monitor.record_usage(
            resource_type=ResourceType.MEMORY,
            component="app2",
            quantity=400.0,
            unit="MB"
        )
        
        # Record usage for different resource type (should not count)
        await resource_monitor.record_usage(
            resource_type=ResourceType.CPU,
            component="system",
            quantity=50.0,
            unit="percent"
        )
        
        # Get budget with usage
        budget_details = await resource_monitor.get_budget(budget.id)
        
        assert budget_details["usage"]["total"] == 700.0
        assert budget_details["usage"]["percentage"] == 70.0
        assert budget_details["usage"]["status"] == "warning"
        assert budget_details["usage"]["remaining"] == 300.0
    
    @pytest.mark.asyncio
    async def test_budget_alerts(self, resource_monitor):
        """Test budget alert generation."""
        # Create budget with low threshold
        budget = await resource_monitor.create_budget(
            resource_type=ResourceType.API_CALLS,
            limit=100.0,
            period=BudgetPeriod.HOURLY,
            unit="calls",
            name="API Budget",
            description="API call budget",
            alert_thresholds={"warning": 60.0, "critical": 80.0}
        )
        
        # Record usage below threshold
        await resource_monitor.record_usage(
            resource_type=ResourceType.API_CALLS,
            component="auth",
            quantity=50.0,
            unit="calls"
        )
        
        # No alerts yet
        alerts = await resource_monitor.get_alerts()
        assert len(alerts) == 0
        
        # Record usage that crosses threshold
        await resource_monitor.record_usage(
            resource_type=ResourceType.API_CALLS,
            component="data",
            quantity=30.0,
            unit="calls"
        )
        
        # Should have warning alert
        alerts = await resource_monitor.get_alerts()
        assert len(alerts) == 1
        assert alerts[0]["threshold_name"] == "warning"
        
        # Record more usage to cross critical
        await resource_monitor.record_usage(
            resource_type=ResourceType.API_CALLS,
            component="search",
            quantity=20.0,
            unit="calls"
        )
        
        # Should have critical alert now too
        alerts = await resource_monitor.get_alerts()
        assert len(alerts) == 2
        
        # Acknowledge one alert
        await resource_monitor.acknowledge_alert(alerts[0]["id"])
        
        # Should only have one unacknowledged alert now
        unack_alerts = await resource_monitor.get_alerts(include_acknowledged=False)
        assert len(unack_alerts) == 1
        
        all_alerts = await resource_monitor.get_alerts(include_acknowledged=True)
        assert len(all_alerts) == 2
    
    @pytest.mark.asyncio
    async def test_system_monitoring(self, resource_monitor):
        """Test system monitoring."""
        # Start monitoring
        result = await resource_monitor.start_monitoring()
        assert result["status"] == "monitoring_started"
        assert resource_monitor.is_monitoring
        
        # Wait for some data collection
        await asyncio.sleep(0.2)
        
        # Stop monitoring
        stop_result = await resource_monitor.stop_monitoring()
        assert stop_result["status"] == "monitoring_stopped"
        assert not resource_monitor.is_monitoring
        
        # Should have some usage records
        usage_data = await resource_monitor.get_resource_usage()
        assert len(usage_data) > 0
        
        # Should have system CPU and memory records
        cpu_data = await resource_monitor.get_resource_usage(
            resource_type=ResourceType.CPU,
            component="system"
        )
        assert len(cpu_data) > 0
        
        memory_data = await resource_monitor.get_resource_usage(
            resource_type=ResourceType.MEMORY,
            component="system"
        )
        assert len(memory_data) > 0
    
    @pytest.mark.asyncio
    async def test_usage_reporting(self, resource_monitor):
        """Test usage reporting."""
        # Record different types of usage
        for i in range(5):
            await resource_monitor.record_usage(
                resource_type=ResourceType.CPU,
                component="system",
                quantity=40.0 + i * 10,
                unit="percent"
            )
            
            await resource_monitor.record_usage(
                resource_type=ResourceType.MEMORY,
                component="system",
                quantity=500.0 + i * 100,
                unit="MB"
            )
            
            await resource_monitor.record_usage(
                resource_type=ResourceType.API_CALLS,
                component="auth",
                quantity=10.0 + i,
                unit="calls"
            )
            
            # Small delay for different timestamps
            await asyncio.sleep(0.01)
        
        # Generate report for CPU
        cpu_report = await resource_monitor.create_usage_report(
            resource_type=ResourceType.CPU
        )
        
        assert cpu_report["status"] == "success"
        assert cpu_report["summary"]["total_records"] == 5
        assert "visualization" in cpu_report
        
        # Generate report grouped by resource type
        grouped_report = await resource_monitor.create_usage_report(
            group_by="resource_type"
        )
        
        assert grouped_report["status"] == "success"
        assert len(grouped_report["summary"]["resource_types"]) == 3
        assert "groups" in grouped_report["summary"]
        assert "visualization" in grouped_report
    
    @pytest.mark.asyncio
    async def test_update_budget(self, resource_monitor):
        """Test updating a budget."""
        # Create budget
        budget = await resource_monitor.create_budget(
            resource_type=ResourceType.MODEL_TOKENS,
            limit=1000.0,
            period=BudgetPeriod.DAILY,
            unit="tokens",
            name="Token Budget",
            description="Model token budget"
        )
        
        # Update budget
        updated = await resource_monitor.update_budget(
            budget_id=budget.id,
            updates={
                "name": "Updated Token Budget",
                "limit": 2000.0,
                "alert_thresholds": {"warning": 50.0, "critical": 75.0}
            }
        )
        
        assert updated.name == "Updated Token Budget"
        assert updated.limit == 2000.0
        assert updated.alert_thresholds["warning"] == 50.0
        
        # Verify persistence
        budget_details = await resource_monitor.get_budget(budget.id)
        assert budget_details["name"] == "Updated Token Budget"
        assert budget_details["limit"] == 2000.0
    
    @pytest.mark.asyncio
    async def test_data_retention(self, resource_monitor):
        """Test clearing old data."""
        # Set retention to 1 day for testing
        resource_monitor.config["usage_retention_days"] = 1
        
        # Create old and new records
        now = datetime.now()
        
        # Create old record (2 days ago)
        old_record = ResourceUsage(
            resource_type=ResourceType.CPU,
            component="system",
            quantity=50.0,
            unit="percent",
            timestamp=(now - timedelta(days=2)).isoformat()
        )
        resource_monitor.usage_records.append(old_record)
        
        # Create new record
        new_record = ResourceUsage(
            resource_type=ResourceType.CPU,
            component="system",
            quantity=60.0,
            unit="percent",
            timestamp=now.isoformat()
        )
        resource_monitor.usage_records.append(new_record)
        
        # Create old alert
        old_alert = BudgetAlert(
            id="old_alert",
            budget_id="budget1",
            threshold_name="warning",
            threshold_value=70.0,
            current_usage=75.0,
            percentage=75.0,
            timestamp=(now - timedelta(days=2)).isoformat(),
            acknowledged=True
        )
        resource_monitor.alerts["old_alert"] = old_alert
        
        # Create new alert
        new_alert = BudgetAlert(
            id="new_alert",
            budget_id="budget1",
            threshold_name="critical",
            threshold_value=90.0,
            current_usage=95.0,
            percentage=95.0,
            timestamp=now.isoformat(),
            acknowledged=False
        )
        resource_monitor.alerts["new_alert"] = new_alert
        
        # Clear old data
        result = await resource_monitor.clear_old_data()
        
        assert result["usage_records_removed"] == 1
        assert result["alerts_removed"] == 1
        assert len(resource_monitor.usage_records) == 1
        assert len(resource_monitor.alerts) == 1
        assert resource_monitor.usage_records[0].timestamp == new_record.timestamp
        assert "new_alert" in resource_monitor.alerts
```

Now, let's explain how these components connect to the Self-Aware Cerebrum system and the previous phases:

## System Integration and Connections

### Multi-Human Supervision Hub (Work Unit 5.3)

The `SupervisionHub` extends the `InterventionInterface` from Work Unit 5.2 to enable collaborative human oversight, with key connections to:

1. **Connection to Intervention Interface (Work Unit 5.2)**:
   - Integrates directly with the `InterventionInterface` to provide a multi-user front-end for handling interventions
   - Extends intervention capabilities with approval workflows and role-based access
   - Provides security and authentication for human supervisors

2. **Connection to Self-Modification Engine (Phase 4)**:
   - Provides oversight for code changes generated by the `CodeGenerator` (4.1)
   - Enables collaborative approval for changes validated by the `SafetyValidator` (4.2)
   - Works with the `IntegrationManager` (4.3) to ensure proper review before integration
   - Supervises the `AgenticDevelopmentController` (4.4) for development workflows

3. **Connection to Execution Engine (Phase 3)**:
   - Provides multi-human oversight for critical tasks managed by the `ParallelExecutionController` (3.3)
   - Allows collaborative decision-making about execution strategies
   - Enables supervisors to inspect and modify execution contexts

4. **Connection to Progress Tracker (Work Unit 5.1)**:
   - Uses progress data to inform supervision decisions
   - Provides context for intervention requests
   - Enables visualization of system progress for human supervisors

Key integration points include:
- The approval workflow system allows for policy-based approval requirements
- Role-based access controls ensure appropriate supervision at different criticality levels
- The authentication system provides secure access to the system
- The callback mechanism allows supervision decisions to propagate to other system components

### Budget & Resource Monitor (Work Unit 5.4)

The `ResourceMonitor` tracks and manages system resources, with connections to:

1. **Connection to Execution Engine (Phase 3)**:
   - Monitors resource usage by the `ParallelExecutionController` (3.3)
   - Provides resource constraints to the `ResourceCoordinator` from Phase 3
   - Supplies performance metrics to the `ExecutionTracker` (3.4)

2. **Connection to Planning Engine (Phase 2)**:
   - Informs the `ResourceAllocationManager` (2.4) about available resources
   - Provides budget constraints for the `ImplementationPlanner` (2.3)
   - Helps the `GoalDecompositionEngine` (2.1) allocate resources efficiently

3. **Connection to Self-Modification Engine (Phase 4)**:
   - Monitors resource impact of self-modifications
   - Provides constraints for the `CodeGenerator` (4.1) to optimize for resource usage
   - Helps the `SafetyValidator` (4.2) assess resource implications of changes
   - Informs the `IntegrationManager` (4.3) about resource availability for deployments

4. **Connection to Other Observability Components**:
   - Provides resource data to the `ProgressTracker` (5.1) for performance metrics
   - Sends resource alerts to the `InterventionInterface` (5.2) when thresholds are crossed
   - Supplies budget status to the `SupervisionHub` (5.3) for human oversight

Key integration points include:
- The budget system allows setting constraints for different resource types
- The alert mechanism detects and notifies when resources are depleted
- The monitoring system tracks system-level and application-level resource usage
- The visualization capabilities provide insights into resource consumption patterns

## System Architecture Impact

These two components complete most of the Observability Layer, adding:

1. **Collaborative Supervision**: Enabling multiple humans to work together in overseeing the system
2. **Resource Constraint Enforcement**: Ensuring the system operates within defined resource limits
3. **Accountability and Tracking**: Recording who made decisions and how resources were used
4. **Visualization and Reporting**: Providing insights into system performance and resource usage

Together with the `ProgressTracker` and `InterventionInterface`, they create a comprehensive observability framework that makes the self-aware system transparent, controllable, and responsible in its resource usage.

The next steps in Phase 5 would be to implement Work Units 5.5 (Metrics Collector) and 5.6 (Observability Integration) to complete the Observability Layer and prepare for the final Cognitive Loop & System Integration phase.
