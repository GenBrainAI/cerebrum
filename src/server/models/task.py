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
    """Task model.
    
    Attributes:
        id: Unique identifier for the task
        name: Name of the task
        tasksmanager_id: ID of the task manager
        description: Description of the task
        status: Current status of the task
        error: Error message if any
        messages: List of messages for the task
        chat_sessions: Dictionary of chat sessions
        toolsets: List of toolset IDs
        curried_tools: List of curried tool IDs
        curried_proxy_id: ID of the curried proxy
        crewai_config_id: ID of the CrewAI config
        autogen_config_id: ID of the Autogen config
        tree_flow_id: ID of the tree flow
        agent_role: Role of the agent
        framework: Framework to use
        model: Model to use
        created_at: When the task was created
        updated_at: When the task was last updated
        config: Configuration for the task
        use_context: Whether to use context
        inherit_manager_context: Whether to inherit context from manager
        contexts: List of contexts
        execution_logs: List of execution logs
        input_data: Input data for the task
        input_from_tasks: List of task IDs to take input from
        output_to_tasks: List of task IDs to send output to
        output_data: Output data from the task
        result: Result of the task
        last_response: Last response from the task
        data: Additional data for the task (used for handover)
    """
    
    id: str = Field(default=None)
    name: str = Field(default=None)
    tasksmanager_id: str = Field(default=None)
    description: Optional[str] = Field(default=None)
    status: Optional[str] = Field(default="pending")
    error: Optional[str] = Field(default=None)
    messages: Optional[List[Union[Dict[str, Any], Message]]] = Field(default=[])
    chat_sessions: Optional[Dict[str, List[Dict[str, Any]]]] = Field(default={})
    toolsets: Optional[List[str]] = Field(default=[])
    curried_tools: Optional[List[str]] = Field(default=[])
    curried_proxy_id: Optional[str] = Field(default=None)
    crewai_config_id: Optional[str] = Field(default=None)
    autogen_config_id: Optional[str] = Field(default=None)
    tree_flow_id: Optional[str] = Field(default=None)
    agent_role: Optional[str] = Field(default=None)
    framework: Optional[str] = Field(default="crewai")
    model: Optional[str] = Field(default=None)
    created_at: Optional[datetime] = Field(default_factory=datetime.now)
    updated_at: Optional[datetime] = Field(default_factory=datetime.now)
    config: Optional[Dict[str, Any]] = Field(default={})
    use_context: Optional[bool] = Field(default=True)
    inherit_manager_context: Optional[bool] = Field(default=False)
    contexts: Optional[List[Dict[str, Any]]] = Field(default=[])
    execution_logs: Optional[List[Dict[str, Any]]] = Field(default=[])
    input_data: Optional[Dict[str, Any]] = Field(default={})
    result: Optional[Any] = Field(default=None)
    last_response: Optional[Any] = Field(default=None)
    input_from_tasks: Optional[List[str]] = Field(default=[])
    output_to_tasks: Optional[List[str]] = Field(default=[])
    output_data: Optional[Dict[str, Any]] = Field(default={})
    data: Optional[Dict[str, Any]] = Field(default={})
    
    def __init__(self, **data: Any):
        """Initialize a Task object with automatic message normalization."""
        super().__init__(**data)
        # Ensure all messages are normalized on initialization
        self.normalize_messages()
    
    def normalize_messages(self) -> None:
        """
        Ensure all messages in the task are proper Message objects.
        This fixes issues with dict messages causing errors during task updates.
        """
        if self.messages is None:
            self.messages = []
            return
            
        normalized_messages = []
        for msg in self.messages:
            if isinstance(msg, dict):
                try:
                    # Convert dict to Message object
                    normalized_messages.append(Message(**msg))
                except Exception as e:
                    # If conversion fails, create a basic system message as fallback
                    print(f"Error normalizing message, creating fallback: {str(e)}")
                    normalized_messages.append(Message(
                        role="system", 
                        content=msg.get('content', "No content") if isinstance(msg, dict) else "Invalid message"
                    ))
            elif isinstance(msg, Message):
                # Already a Message object
                normalized_messages.append(msg)
            else:
                # Unsupported type, create fallback
                print(f"Unsupported message type: {type(msg)}, creating fallback")
                normalized_messages.append(Message(
                    role="system",
                    content="Invalid message format"
                ))
                
        # Replace messages with normalized version
        self.messages = normalized_messages

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
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None,
            date: lambda v: v.isoformat() if v else None,
            Message: lambda v: v.dict() if v else None
        }