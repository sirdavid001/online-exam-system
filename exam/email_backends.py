import json
from email.utils import getaddresses
from urllib import error as urllib_error
from urllib import request as urllib_request

from django.conf import settings
from django.core.mail.backends.base import BaseEmailBackend


class BrevoAPIEmailBackend(BaseEmailBackend):
    """
    Send transactional emails via Brevo API using BREVO_API_KEY.
    """

    api_url = "https://api.brevo.com/v3/smtp/email"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.api_key = (getattr(settings, "BREVO_API_KEY", "") or "").strip()
        self.sender_name = (getattr(settings, "BREVO_SENDER_NAME", "") or "").strip()
        self.timeout = getattr(settings, "EMAIL_TIMEOUT", 20)

    def send_messages(self, email_messages):
        if not email_messages:
            return 0

        if not self.api_key:
            if self.fail_silently:
                return 0
            raise ValueError("BREVO_API_KEY is not configured.")

        sent_count = 0
        for message in email_messages:
            try:
                if self._send(message):
                    sent_count += 1
            except Exception:
                if not self.fail_silently:
                    raise
        return sent_count

    def _send(self, message):
        recipients = message.recipients()
        if not recipients:
            return False

        parsed_recipients = getaddresses(recipients)
        to_entries = [{"email": addr, "name": name} if name else {"email": addr} for name, addr in parsed_recipients if addr]
        if not to_entries:
            return False

        from_email = message.from_email or settings.DEFAULT_FROM_EMAIL
        sender = {"email": from_email}
        if self.sender_name:
            sender["name"] = self.sender_name

        payload = {
            "sender": sender,
            "to": to_entries,
            "subject": message.subject or "",
            "textContent": "",
        }

        if message.content_subtype == "html":
            payload["htmlContent"] = message.body or ""
        else:
            payload["textContent"] = message.body or ""

        for alternative, mimetype in getattr(message, "alternatives", []):
            if mimetype == "text/html":
                payload["htmlContent"] = alternative

        request = urllib_request.Request(
            self.api_url,
            data=json.dumps(payload).encode("utf-8"),
            method="POST",
        )
        request.add_header("accept", "application/json")
        request.add_header("content-type", "application/json")
        request.add_header("api-key", self.api_key)

        try:
            with urllib_request.urlopen(request, timeout=self.timeout) as response:
                return response.status in (200, 201, 202)
        except urllib_error.HTTPError as exc:
            if self.fail_silently:
                return False
            body = exc.read().decode("utf-8", errors="ignore")
            raise RuntimeError(f"Brevo API email request failed ({exc.code}): {body}") from exc
