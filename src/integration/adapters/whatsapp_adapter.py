# src/integration/adapters/whatsapp_adapter.py
# To use these adapters, you'll need to set the following environment variables:

# For WhatsApp:

# WHATSAPP_PHONE_NUMBER_ID
# WHATSAPP_ACCESS_TOKEN
# WHATSAPP_WEBHOOK_PORT (optional, defaults to 8001)




import os
import asyncio
from typing import Dict, Any
from ..channel_adapter import ChannelAdapter
from whatsapp_business_api import WhatsAppClient  # This is a hypothetical library

class WhatsAppAdapter(ChannelAdapter):
    def __init__(self):
        self.client = WhatsAppClient(
            phone_number_id=os.environ["WHATSAPP_PHONE_NUMBER_ID"],
            access_token=os.environ["WHATSAPP_ACCESS_TOKEN"]
        )
        self.webhook_port = int(os.environ.get("WHATSAPP_WEBHOOK_PORT", 8001))
        self.process_message = None
        self.running = False

    async def send_message(self, user_id: str, message: str):
        await self.client.send_message(user_id, message)

    async def receive_message(self) -> Dict[str, Any]:
        # This method won't be used directly as WhatsApp uses webhooks
        pass

    def start(self):
        self.running = True
        asyncio.create_task(self._run_webhook_server())

    async def _run_webhook_server(self):
        from aiohttp import web

        async def webhook_handler(request):
            if request.method == "POST":
                data = await request.json()
                # Process incoming WhatsApp message
                if 'entry' in data and data['entry'][0]['changes'][0]['value'].get('messages'):
                    message = data['entry'][0]['changes'][0]['value']['messages'][0]
                    user_id = message['from']
                    text = message['text']['body']
                    await self.process_message("whatsapp", user_id, text)
            return web.Response(text="OK")

        app = web.Application()
        app.router.add_post('/webhook', webhook_handler)

        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, 'localhost', self.webhook_port)
        await site.start()

        while self.running:
            await asyncio.sleep(1)

        await runner.cleanup()

    async def shutdown(self):
        self.running = False
        # Add any necessary cleanup for the WhatsApp client
