"""Small transactional SMTP adapter; blocking I/O runs off the event loop."""

import smtplib
import ssl
from email.message import EmailMessage

from anyio import to_thread

from app.integrations.base import ProviderUnavailable


class SMTPEmailNotifier:
    def __init__(
        self, host: str, port: int, username: str, password: str, sender: str, starttls: bool
    ) -> None:
        self._host = host
        self._port = port
        self._username = username
        self._password = password
        self._sender = sender
        self._starttls = starttls

    async def send(self, recipient: str, subject: str, body: str) -> bool:
        message = EmailMessage()
        message["From"] = self._sender
        message["To"] = recipient
        message["Subject"] = subject
        message.set_content(body)

        def deliver() -> None:
            with smtplib.SMTP(self._host, self._port, timeout=10) as smtp:
                smtp.ehlo()
                if self._starttls:
                    smtp.starttls(context=ssl.create_default_context())
                    smtp.ehlo()
                smtp.login(self._username, self._password)
                smtp.send_message(message)

        try:
            await to_thread.run_sync(deliver)
        except (OSError, smtplib.SMTPException):
            raise ProviderUnavailable("Email delivery failed") from None
        return True
