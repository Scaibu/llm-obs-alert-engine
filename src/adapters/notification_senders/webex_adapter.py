import json
import logging
import urllib.request
import urllib.error
from typing import Any
from opentelemetry import trace

logger = logging.getLogger(__name__)
tracer = trace.get_tracer("alert-engine")

class WebexAdapter:
    def __init__(
        self,
        bot_token: str,
        room_id: str,
        endpoint: str,
        timeout_seconds: float = 5.0,
    ) -> None:
        self.bot_token = bot_token
        self.room_id = room_id
        self.endpoint = endpoint
        self.timeout_seconds = timeout_seconds

    def send_message(self, markdown_text: str) -> bool:
        if not self.bot_token or not self.room_id or not self.endpoint:
            logger.warning("Cisco Webex bot_token, room_id, or endpoint not configured.")
            return False

        with tracer.start_as_current_span(
            "webex_adapter.send_message",
            attributes={"webex.room_id": self.room_id, "http.url": self.endpoint}
        ) as span:
            payload = {
                "roomId": self.room_id,
                "markdown": markdown_text,
            }
            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                self.endpoint,
                data=data,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.bot_token}",
                }
            )
            try:
                with urllib.request.urlopen(req, timeout=self.timeout_seconds) as resp:
                    span.set_attribute("http.status_code", resp.status)
                    return resp.status == 200
            except urllib.error.URLError as e:
                span.record_exception(e)
                span.set_status(trace.StatusCode.ERROR, str(e))
                logger.error("Failed to post message to Webex: %s", e)
                return False
