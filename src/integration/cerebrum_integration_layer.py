import asyncio
import logging
from typing import Dict, Any, List
from datetime import datetime, timedelta
from .channel_adapter import ChannelAdapter
from .adapters.slack_adapter import SlackAdapter
from .adapters.whatsapp_adapter import WhatsAppAdapter
from .adapters.email_adapter import EmailAdapter

from src.server.models.task import Task
from src.server.models.message import Message
from src.server.controllers.task_runner import TaskRunner
from src.server.persistence.persistence_model_factory import PersistenceModelFactory

class UserSession:
    def __init__(self, user_id: str, tasksmanager_id: str, task_id: str, model: str):
        self.user_id = user_id
        self.tasksmanager_id = tasksmanager_id
        self.task_id = task_id
        self.model = model
        self.messages: List[Message] = []
        self.last_interaction: datetime = datetime.utcnow()

    def add_message(self, message: Message):
        self.messages.append(message)
        self.last_interaction = datetime.utcnow()

    def is_expired(self, expiration_minutes: int) -> bool:
        return datetime.utcnow() - self.last_interaction > timedelta(minutes=expiration_minutes)

class CerebrumIntegrationLayer:
    def __init__(self):
        self.channel_adapters: Dict[str, ChannelAdapter] = {}
        self.message_queue = asyncio.Queue()
        self.running = False
        self.persistence_model = PersistenceModelFactory.persistence_model("inmemory")
        self.task_runner = TaskRunner(self.persistence_model)
        self.user_sessions: Dict[str, UserSession] = {}
        self.session_expiration_minutes = 60  # Sessions expire after 60 minutes of inactivity
        self.logger = logging.getLogger(__name__)

    def register_adapter(self, channel: str, adapter: ChannelAdapter):
        self.channel_adapters[channel] = adapter
        adapter.process_message = self.process_incoming_message
        self.logger.info(f"Registered adapter for channel: {channel}")

    async def process_incoming_message(self, channel: str, user_id: str, message: str):
        await self.message_queue.put({
            "channel": channel,
            "user_id": user_id,
            "message": message
        })
        self.logger.debug(f"Received message from {user_id} on {channel}")

    def initialize_adapters(self):
        slack_adapter = SlackAdapter()
        self.register_adapter("slack", slack_adapter)
        slack_adapter.start()

        whatsapp_adapter = WhatsAppAdapter()
        self.register_adapter("whatsapp", whatsapp_adapter)
        whatsapp_adapter.start()

        email_adapter = EmailAdapter()
        self.register_adapter("email", email_adapter)
        email_adapter.start()

        self.logger.info("All adapters initialized and started")

    async def process_with_cerebrum(self, message: Dict[str, Any]) -> str:
        channel = message["channel"]
        user_id = message["user_id"]
        content = message["message"]

        try:
            # Get or create user session
            session = self.get_or_create_session(user_id)

            # Create a new message
            new_message = Message(role="user", content=content)

            # Add the new message to the session
            session.add_message(new_message)

            # Process the message with Cerebrum
            response = await self.task_runner.completion(
                tasksmanager_id=session.tasksmanager_id,
                task_id=session.task_id,
                messages=session.messages,
                model=session.model
            )

            # Add the response to the session
            session.add_message(Message(role="assistant", content=response))

            # Trim the session messages if they exceed a certain length
            if len(session.messages) > 20:  # Adjust this number as needed
                session.messages = session.messages[-20:]

            self.logger.info(f"Processed message for user {user_id} on {channel}")
            return response

        except Exception as e:
            self.logger.error(f"Error processing message for user {user_id} on {channel}: {str(e)}")
            return "I apologize, but I encountered an error while processing your request. Please try again later."

    def get_or_create_session(self, user_id: str) -> UserSession:
        try:
            session = self.user_sessions.get(user_id)
            if session and not session.is_expired(self.session_expiration_minutes):
                self.logger.debug(f"Retrieved existing session for user {user_id}")
                return session
            
            # Create a new session if it doesn't exist or has expired
            tasksmanager = self.persistence_model.tasksmanagers.create({
                "name": f"Session for user {user_id}",
                "model": "gpt-4",  # Or whichever model you prefer
                "description": f"TasksManager for user {user_id}'s session"
            })

            task = self.persistence_model.tasks.create(Task(
                name=f"Conversation with user {user_id}",
                description="Handle ongoing conversation with the user",
                tasksmanager_id=tasksmanager.id,
                messages=[
                    Message(
                        role="system",
                        content="You are an AI assistant capable of handling a wide range of tasks and queries. Maintain a helpful and friendly demeanor throughout the conversation."
                    )
                ]
            ))

            new_session = UserSession(
                user_id=user_id,
                tasksmanager_id=tasksmanager.id,
                task_id=task.id,
                model="gpt-4"  # Or whichever model you prefer
            )
            new_session.messages = task.messages
            self.user_sessions[user_id] = new_session
            self.logger.info(f"Created new session for user {user_id}")
            return new_session

        except Exception as e:
            self.logger.error(f"Error creating session for user {user_id}: {str(e)}")
            raise

    async def run(self):
        self.running = True
        self.initialize_adapters()

        while self.running:
            try:
                message = await asyncio.wait_for(self.message_queue.get(), timeout=1.0)
                response = await self.process_with_cerebrum(message)
                await self.channel_adapters[message["channel"]].send_message(
                    message["user_id"],
                    response
                )
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                self.logger.error(f"Error in main run loop: {str(e)}")
            
            # Periodically clean up expired sessions
            await self.cleanup_expired_sessions()

    async def cleanup_expired_sessions(self):
        try:
            expired_users = [user_id for user_id, session in self.user_sessions.items() 
                            if session.is_expired(self.session_expiration_minutes)]
            for user_id in expired_users:
                del self.user_sessions[user_id]
                self.logger.info(f"Cleaned up expired session for user {user_id}")
        except Exception as e:
            self.logger.error(f"Error cleaning up expired sessions: {str(e)}")

    async def shutdown(self):
        self.running = False
        for adapter in self.channel_adapters.values():
            try:
                await adapter.shutdown()
            except Exception as e:
                self.logger.error(f"Error shutting down adapter: {str(e)}")
        
        # Clean up user sessions
        for session in self.user_sessions.values():
            # You might want to save the session state or perform other cleanup
            pass
        self.user_sessions.clear()
        self.logger.info("CerebrumIntegrationLayer shut down successfully")