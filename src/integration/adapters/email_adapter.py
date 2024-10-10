# src/integration/adapters/email_adapter.py
# To use these adapters, you'll need to set the following environment variables:


# For Email:

# EMAIL_SMTP_HOST
# EMAIL_SMTP_PORT
# EMAIL_IMAP_HOST
# EMAIL_IMAP_PORT
# EMAIL_ADDRESS
# EMAIL_PASSWORD




import os
import asyncio
import aiosmtplib
from email.message import EmailMessage
from imapclient import IMAPClient
from ..channel_adapter import ChannelAdapter

class EmailAdapter(ChannelAdapter):
    def __init__(self):
        self.smtp_host = os.environ["EMAIL_SMTP_HOST"]
        self.smtp_port = int(os.environ["EMAIL_SMTP_PORT"])
        self.imap_host = os.environ["EMAIL_IMAP_HOST"]
        self.imap_port = int(os.environ["EMAIL_IMAP_PORT"])
        self.email = os.environ["EMAIL_ADDRESS"]
        self.password = os.environ["EMAIL_PASSWORD"]
        self.process_message = None
        self.running = False

    async def send_message(self, user_id: str, message: str):
        smtp = aiosmtplib.SMTP(hostname=self.smtp_host, port=self.smtp_port, use_tls=True)
        await smtp.connect()
        await smtp.login(self.email, self.password)

        email_message = EmailMessage()
        email_message.set_content(message)
        email_message["Subject"] = "Cerebrum Response"
        email_message["From"] = self.email
        email_message["To"] = user_id

        await smtp.send_message(email_message)
        await smtp.quit()

    async def receive_message(self) -> Dict[str, Any]:
        # This method is used in the continuous polling loop
        with IMAPClient(self.imap_host) as client:
            client.login(self.email, self.password)
            client.select_folder("INBOX")
            messages = client.search(["UNSEEN"])
            for msg_id, data in client.fetch(messages, ["ENVELOPE", "RFC822"]).items():
                envelope = data[b"ENVELOPE"]
                rfc822 = data[b"RFC822"]
                return {
                    "user_id": envelope.from_[0].mailbox.decode() + "@" + envelope.from_[0].host.decode(),
                    "subject": envelope.subject.decode(),
                    "body": rfc822.decode()
                }
        return None

    def start(self):
        self.running = True
        asyncio.create_task(self._poll_emails())

    async def _poll_emails(self):
        while self.running:
            message = await self.receive_message()
            if message:
                await self.process_message("email", message["user_id"], message["body"])
            await asyncio.sleep(60)  # Poll every 60 seconds

    async def shutdown(self):
        self.running = False
        # Add any necessary cleanup for email connections