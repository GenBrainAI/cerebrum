# src/integration/adapters/slack_adapter.py

import os
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from ..channel_adapter import ChannelAdapter

class SlackAdapter(ChannelAdapter):
    def __init__(self):
        self.app = App(token=os.environ["SLACK_BOT_TOKEN"])
        self.handler = SocketModeHandler(self.app, os.environ["SLACK_APP_TOKEN"])

    async def send_message(self, user_id: str, message: str):
        await self.app.client.chat_postMessage(channel=user_id, text=message)

    async def receive_message(self):
        # This method won't be used directly, as Slack uses an event-based model
        pass

    def start(self):
        @self.app.event("message")
        async def handle_message(body, say, logger):
            user_id = body["event"]["user"]
            text = body["event"]["text"]
            channel = body["event"]["channel"]
            
            # Process the message through the Cerebrum Integration Layer
            await self.process_message(channel, user_id, text)

        # Start the Socket Mode handler
        self.handler.start()

    async def process_message(self, channel: str, user_id: str, message: str):
        # This method should be set by the CerebrumIntegrationLayer
        pass

# Usage example
if __name__ == "__main__":
    slack_adapter = SlackAdapter()
    slack_adapter.start()
