import json
import logging
import urllib.request
import urllib.error
from typing import Any
from opentelemetry import trace

logger = logging.getLogger(__name__)
tracer = trace.get_tracer("alert-engine")

class DiscordAdapter:
    def __init__(
        self,
        webhook_url: str,
        timeout_seconds: float = 5.0,
    ) -> None:
        self.webhook_url = webhook_url
        self.timeout_seconds = timeout_seconds

    def send_message(self, content: str, embeds: list[dict[str, Any]] | None = None) -> bool:
        if not self.webhook_url:
            logger.warning("Discord webhook URL not configured.")
            return False

        with tracer.start_as_current_span(
            "discord_adapter.send_message",
            attributes={"http.url": self.webhook_url}
        ) as span:
            payload: dict[str, Any] = {"content": content}
            if embeds:
                payload["embeds"] = embeds

            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                self.webhook_url,
                data=data,
                headers={"Content-Type": "application/json"}
            )
            try:
                with urllib.request.urlopen(req, timeout=self.timeout_seconds) as resp:
                    span.set_attribute("http.status_code", resp.status)
                    return resp.status in (200, 204)
            except urllib.error.URLError as e:
                span.record_exception(e)
                span.set_status(trace.StatusCode.ERROR, str(e))
                logger.error("Failed to post message to Discord: %s", e)
                return False
