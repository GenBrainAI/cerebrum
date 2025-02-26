"""
Prompt Transformer for Task Flows

This module provides a flexible way to transform prompts between tasks in a task flow.
It allows for custom transformations to be applied to the output of one task before
it's passed as input to the next task.
"""

from typing import Dict, Any, List, Optional, Callable, Union
from src.server.models.task import Task, Message

class PromptTransformer:
    """
    A flexible transformer for modifying prompts between tasks in a task flow.
    
    This class provides a way to transform the output of one task before it's passed
    as input to the next task. It supports both simple string transformations and
    more complex transformations that can modify the entire message structure.
    """
    
    def __init__(
        self, 
        transform_func: Optional[Callable] = None,
        instructions: Optional[str] = None,
        prefix: Optional[str] = None,
        suffix: Optional[str] = None
    ):
        """
        Initialize a PromptTransformer with transformation options.
        
        Args:
            transform_func: A custom function that takes a task result and returns a transformed prompt
            instructions: Instructions to prepend to the prompt (e.g., "Add date and time to this text")
            prefix: Text to add before the prompt content
            suffix: Text to add after the prompt content
        """
        self.transform_func = transform_func
        self.instructions = instructions
        self.prefix = prefix
        self.suffix = suffix
        
    def transform(
        self, 
        task_result: Union[str, Dict[str, Any]], 
        target_task: Optional[Task] = None
    ) -> Union[str, List[Message]]:
        """
        Transform the result of a task into a prompt for the next task.
        
        Args:
            task_result: The result from the previous task (string or dict with 'response' key)
            target_task: Optional target task to customize the transformation
            
        Returns:
            Either a transformed string prompt or a list of messages for the next task
        """
        # Extract the response from the task result
        if isinstance(task_result, dict) and "response" in task_result:
            content = task_result["response"]
        elif isinstance(task_result, str):
            content = task_result
        else:
            content = str(task_result)
            
        # Apply custom transformation function if provided
        if self.transform_func:
            return self.transform_func(content, target_task)
            
        # Apply standard transformations
        if self.instructions:
            content = f"{self.instructions}: {content}"
            
        if self.prefix:
            content = f"{self.prefix}{content}"
            
        if self.suffix:
            content = f"{content}{self.suffix}"
            
        return content
        
    def create_messages(
        self, 
        task_result: Union[str, Dict[str, Any]], 
        target_task: Task,
        role: str = "user"
    ) -> List[Message]:
        """
        Create a list of messages for the next task based on the transformed prompt.
        
        Args:
            task_result: The result from the previous task
            target_task: The target task that will receive the messages
            role: The role for the new message (default: "user")
            
        Returns:
            A list of messages including system messages and the transformed prompt
        """
        print(f"\n🔍 DEBUG - PromptTransformer.create_messages")
        print(f"  task_result type: {type(task_result)}")
        print(f"  task_result: {task_result}")
        print(f"  target_task: {target_task.name if hasattr(target_task, 'name') else 'Unknown'}")
        
        # Get system messages from the target task
        messages = target_task.get_system_messages() if target_task else []
        print(f"  system messages count: {len(messages)}")
        print(f"  system messages types: {[type(m) for m in messages]}")
        
        # Transform the prompt
        transformed_content = self.transform(task_result, target_task)
        print(f"  transformed_content: {transformed_content[:50]}...")
        
        # Add the transformed content as a new message
        new_message = Message(role=role, content=transformed_content)
        print(f"  new_message type: {type(new_message)}")
        messages.append(new_message)
        
        print(f"  final messages count: {len(messages)}")
        print(f"  final messages types: {[type(m) for m in messages]}")
        
        return messages


class MessageTransformer:
    """
    A transformer for modifying message structures between tasks.
    
    This class provides more advanced transformations that can modify
    the entire message structure, not just the content.
    """
    
    def __init__(
        self,
        transform_func: Optional[Callable] = None,
        include_system_messages: bool = True,
        include_history: bool = False,
        max_history: Optional[int] = None
    ):
        """
        Initialize a MessageTransformer with transformation options.
        
        Args:
            transform_func: A custom function that takes messages and returns transformed messages
            include_system_messages: Whether to include system messages from the target task
            include_history: Whether to include message history from the source task
            max_history: Maximum number of history messages to include
        """
        self.transform_func = transform_func
        self.include_system_messages = include_system_messages
        self.include_history = include_history
        self.max_history = max_history
        
    def transform(
        self,
        source_task: Task,
        target_task: Task,
        session_id: Optional[str] = None,
        additional_content: Optional[str] = None,
        role: str = "user"
    ) -> List[Message]:
        """
        Transform messages from the source task for use in the target task.
        
        Args:
            source_task: The task that produced the output
            target_task: The task that will receive the transformed messages
            session_id: Optional session ID for retrieving chat history
            additional_content: Optional content to add to the messages
            role: The role for any new messages
            
        Returns:
            A list of transformed messages for the target task
        """
        messages = []
        
        # Include system messages from target task if requested
        if self.include_system_messages:
            messages.extend(target_task.get_system_messages())
            
        # Include history from source task if requested
        if self.include_history and session_id:
            history = source_task.get_session_messages(session_id)
            if self.max_history and len(history) > self.max_history:
                history = history[-self.max_history:]
            messages.extend(history)
            
        # Get the latest response from the source task
        latest_response = None
        if session_id:
            session_messages = source_task.get_session_messages(session_id)
            if session_messages:
                # Find the last assistant message
                for msg in reversed(session_messages):
                    if msg.role == "assistant":
                        latest_response = msg.content
                        break
                        
        # Create a new message with the latest response and any additional content
        if latest_response:
            content = latest_response
            if additional_content:
                content = f"{additional_content}: {content}"
            messages.append(Message(role=role, content=content))
        elif additional_content:
            messages.append(Message(role=role, content=additional_content))
            
        # Apply custom transformation if provided
        if self.transform_func:
            return self.transform_func(messages, source_task, target_task)
            
        return messages 