from abc import ABC, abstractmethod
from typing import Dict, Any

class ChannelAdapter(ABC):
    @abstractmethod
    async def send_message(self, user_id: str, message: str):
        """Send a message to the user on the channel."""
        pass

    @abstractmethod
    async def receive_message(self) -> Dict[str, Any]:
        """Receive a message from the channel."""
        pass

    @abstractmethod
    def start(self):
        """Start the adapter and begin listening for messages."""
        pass

    @abstractmethod
    async def shutdown(self):
        """Shutdown the adapter gracefully."""
        pass
