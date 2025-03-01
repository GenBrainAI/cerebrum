    # open interperter
    # AutoGPT, LangGraph
    # AnythingLLM
    # https://github.com/Doriandarko/maestro
    # https://github.com/togethercomputer/MoA
    # Phi ?? 
from __future__ import annotations
from datetime import datetime, date
from typing import List, Optional, Dict, Any, Union
from pydantic import BaseModel, Field

from .message import Message

class ChatMessage(BaseModel):
    """Serializable chat message model"""
    role: str
    content: str
    file_ids: Optional[List[str]] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def to_message(self) -> Message:
        """Convert to Message object"""
        return Message(**self.dict())

    @classmethod
    def from_message(cls, message: Message) -> 'ChatMessage':
        """Create from Message object"""
        return cls(**message.dict())
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ChatMessage':
        """Create from dictionary"""
        return cls(**data)

class ChatSession(BaseModel):
    """Model for a chat session"""
    id: str
    name: Optional[str] = None
    created_at: Optional[datetime] = Field(default_factory=datetime.now)
    updated_at: Optional[datetime] = None
    messages: List[ChatMessage] = Field(default_factory=list)

    def add_message(self, message: Union[Message, Dict[str, Any], ChatMessage]) -> None:
        """Add a message to the session"""
        if isinstance(message, Message):
            self.messages.append(ChatMessage.from_message(message))
        elif isinstance(message, dict):
            self.messages.append(ChatMessage.from_dict(message))
        elif isinstance(message, ChatMessage):
            self.messages.append(message)
        else:
            raise ValueError(f"Unsupported message type: {type(message)}")
        self.updated_at = datetime.now()

    def get_messages(self) -> List[Message]:
        """Get messages as Message objects"""
        return [msg.to_message() for msg in self.messages]

    def get_messages_dict(self) -> List[Dict[str, Any]]:
        """Get messages as dictionaries"""
        return [msg.dict() for msg in self.messages]

class Task(BaseModel):
    """Task model with chat session and message support"""
    id: Optional[str] = Field(default=None)
    name: Optional[str] = Field(default=None)
    tasksmanager_id: Optional[str] = Field(default=None)
    description: Optional[str] = Field(default=None)
    status: str = Field(default="pending", description="Current status of the task (pending, running, completed, failed)")
    error: Optional[str] = Field(default=None, description="Error message if task failed")
    messages: Optional[List[Message]] = Field(default_factory=list)
    chat_sessions: Dict[str, List[Dict[str, Any]]] = Field(default_factory=dict)
    toolsets: Optional[List[str]] = Field(default_factory=list)
    curried_tools: Optional[List[str]] = Field(default_factory=list)
    curried_proxy_id: Optional[str] = Field(default=None)
    crewai_config_id: Optional[str] = Field(default=None)
    autogen_config_id: Optional[str] = Field(default=None)
    tree_flow_id: Optional[str] = Field(default=None, description="ID of the task tree flow associated with this task")
    agent_role: Optional[str] = Field(default=None, description="Role of the agent assigned to this task")
    framework: Optional[str] = Field(default="crewai", description="Framework to use for task execution (e.g. crewai, autogen)")
    created_at: Optional[datetime] = Field(default_factory=datetime.now)
    updated_at: Optional[datetime] = Field(default_factory=datetime.now)
    config: Optional[Dict[str, Any]] = Field(default_factory=dict)
    use_context: bool = Field(default=True)
    inherit_manager_context: bool = Field(default=True)
    contexts: List[Dict] = Field(default_factory=list, description="Context references for the task")
    execution_logs: Optional[List[Dict[str, Any]]] = Field(default_factory=list, description="Logs from task execution")
    input_data: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Input data for task execution")
    result: Optional[str] = Field(default=None, description="Result of task execution")

    def create_session(self, name: Optional[str] = None) -> str:
        """Create a new chat session"""
        session_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        if not hasattr(self, 'chat_sessions') or self.chat_sessions is None:
            self.chat_sessions = {}
        self.chat_sessions[session_id] = []
        return session_id

    def add_message_to_session(self, session_id: str, message: Union[Message, Dict[str, Any], 'ChatMessage']) -> None:
        """Add a message to a specific session"""
        if not hasattr(self, 'chat_sessions') or self.chat_sessions is None:
            self.chat_sessions = {}
            
        if session_id not in self.chat_sessions:
            self.chat_sessions[session_id] = []
            
        # Convert message to dict format for storage
        if isinstance(message, Message):
            message_dict = message.dict()
        elif isinstance(message, dict):
            message_dict = message
        else:
            message_dict = message.dict() if hasattr(message, 'dict') else {'role': 'user', 'content': str(message)}
            
        self.chat_sessions[session_id].append(message_dict)
        self.updated_at = datetime.now()

    def get_session_messages(self, session_id: str) -> List[Message]:
        """Get all messages for a session as Message objects"""
        if not hasattr(self, 'chat_sessions') or self.chat_sessions is None:
            self.chat_sessions = {}
            return []
            
        if session_id not in self.chat_sessions:
            return []
            
        # Convert stored dict messages back to Message objects
        return [Message(**msg) if isinstance(msg, dict) else msg 
                for msg in self.chat_sessions[session_id]]

    def get_system_messages(self) -> List[Message]:
        """Get all system messages for the task as Message objects"""
        if not self.messages:
            return []
            
        # Convert any dict messages to Message objects
        system_messages = []
        for msg in self.messages:
            if isinstance(msg, dict):
                msg = Message(**msg)
            if msg.role == 'system':
                system_messages.append(msg)
        return system_messages

    def update_context_config(
        self,
        use_context: Optional[bool] = None,
        inherit_manager_context: Optional[bool] = None
    ) -> bool:
        """Update context configuration."""
        updated = False
        if use_context is not None and use_context != self.use_context:
            self.use_context = use_context
            updated = True
        if inherit_manager_context is not None and inherit_manager_context != self.inherit_manager_context:
            self.inherit_manager_context = inherit_manager_context
            updated = True
        return updated

    def get_chat_sessions(self) -> Dict[str, List[Dict]]:
        """Get all chat sessions."""
        return self.chat_sessions or {}

    class Config:
        arbitrary_types_allowed = True
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None,
            date: lambda v: v.isoformat() if v else None,
            Message: lambda v: v.dict() if v else None
        }