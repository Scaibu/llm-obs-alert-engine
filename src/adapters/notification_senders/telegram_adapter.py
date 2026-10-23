import json
import logging
import urllib.request
import urllib.error
from typing import Any
from opentelemetry import trace

logger = logging.getLogger(__name__)
tracer = trace.get_tracer("alert-engine")

class TelegramAdapter:
    def __init__(
        self,
        bot_token: str,
        chat_id: str,
        endpoint_template: str,
        timeout_seconds: float = 5.0,
    ) -> None:
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.endpoint_template = endpoint_template
        self.timeout_seconds = timeout_seconds

    def send_message(self, text: str, parse_mode: str = "Markdown") -> bool:
        if not self.bot_token or not self.chat_id or not self.endpoint_template:
            logger.warning("Telegram bot_token, chat_id, or endpoint_template not configured.")
            return False

        endpoint = self.endpoint_template.replace("{bot_token}", self.bot_token)
        with tracer.start_as_current_span(
            "telegram_adapter.send_message",
            attributes={"telegram.chat_id": self.chat_id, "http.url": endpoint}
        ) as span:
            payload = {
                "chat_id": self.chat_id,
                "text": text,
                "parse_mode": parse_mode,
            }
            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                endpoint,
                data=data,
                headers={"Content-Type": "application/json"}
            )
            try:
                with urllib.request.urlopen(req, timeout=self.timeout_seconds) as resp:
                    span.set_attribute("http.status_code", resp.status)
                    return resp.status == 200
            except urllib.error.URLError as e:
                span.record_exception(e)
                span.set_status(trace.StatusCode.ERROR, str(e))
                logger.error("Failed to post message to Telegram: %s", e)
                return False
