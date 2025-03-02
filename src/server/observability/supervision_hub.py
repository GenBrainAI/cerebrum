from typing import Dict, List, Optional, Any, Set
import asyncio
import logging
import os
import json
import uuid
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

class SupervisionHub:
    """Manages supervision by multiple humans with different roles."""
    
    def __init__(self, storage_path: Optional[str] = None):
        """
        Initialize with storage path for supervision data.
        
        Args:
            storage_path: Path to store supervision data
        """
        self.storage_path = storage_path or os.path.join(os.path.expanduser("~"), ".cerebrum", "supervision")
        os.makedirs(self.storage_path, exist_ok=True)
        
        # Create subdirectories
        self.supervisors_path = os.path.join(self.storage_path, "supervisors")
        self.requests_path = os.path.join(self.storage_path, "requests")
        self.notifications_path = os.path.join(self.storage_path, "notifications")
        self.logs_path = os.path.join(self.storage_path, "logs")
        
        os.makedirs(self.supervisors_path, exist_ok=True)
        os.makedirs(self.requests_path, exist_ok=True)
        os.makedirs(self.notifications_path, exist_ok=True)
        os.makedirs(self.logs_path, exist_ok=True)
        
        # Load existing data
        self.supervisors: Dict[str, Dict[str, Any]] = self._load_supervisors()
        self.requests: Dict[str, Dict[str, Any]] = self._load_requests()
        self.notifications: Dict[str, Dict[str, Any]] = self._load_notifications()
    
    async def register_supervisor(self, user_id: str, role: str, permissions: List[str]) -> Dict[str, Any]:
        """
        Register a new supervisor with role and permissions.
        
        Args:
            user_id: Unique identifier for the supervisor
            role: Role of the supervisor (e.g., "admin", "developer", "reviewer")
            permissions: List of permission strings
            
        Returns:
            Dictionary with registration result
        """
        # Check if supervisor already exists
        if user_id in self.supervisors:
            return {
                "success": False,
                "message": f"Supervisor with ID {user_id} already exists",
                "supervisor_id": user_id
            }
        
        # Create supervisor record
        supervisor = {
            "id": user_id,
            "role": role,
            "permissions": permissions,
            "created_at": datetime.now().isoformat(),
            "last_active": datetime.now().isoformat(),
            "approved_requests": [],
            "rejected_requests": [],
            "pending_notifications": []
        }
        
        # Save supervisor
        self.supervisors[user_id] = supervisor
        self._save_supervisor(user_id, supervisor)
        
        # Log the registration
        await self._log_event(
            event_type="supervisor_registered",
            details={
                "supervisor_id": user_id,
                "role": role,
                "permissions": permissions
            }
        )
        
        return {
            "success": True,
            "message": f"Supervisor {user_id} registered successfully",
            "supervisor_id": user_id,
            "role": role,
            "permissions": permissions
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
            if supervisor["role"] == required_role
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
        if supervisor["role"] != request["required_role"]:
            return {
                "success": False,
                "message": f"Supervisor {supervisor_id} does not have the required role ({request['required_role']})",
                "supervisor_id": supervisor_id,
                "supervisor_role": supervisor["role"],
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
        if supervisor["role"] != request["required_role"]:
            return {
                "success": False,
                "message": f"Supervisor {supervisor_id} does not have the required role ({request['required_role']})",
                "supervisor_id": supervisor_id,
                "supervisor_role": supervisor["role"],
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
                    
                if self.supervisors[supervisor_id]["role"] != request["required_role"]:
                    continue
            
            pending_requests.append(request)
        
        return pending_requests
    
    async def create_notification(self, supervisor_ids: List[str], message: str, 
                                 level: str = "info", context: Optional[Dict[str, Any]] = None) -> str:
        """
        Create a notification for supervisors.
        
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