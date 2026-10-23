import json
import logging
import urllib.request
import urllib.error
from typing import Any
from opentelemetry import trace

logger = logging.getLogger(__name__)
tracer = trace.get_tracer("alert-engine")

class WebhookAdapter:
    def __init__(
        self,
        webhook_url: str,
        timeout_seconds: float = 5.0,
        headers: dict[str, str] | None = None,
    ) -> None:
        self.webhook_url = webhook_url
        self.timeout_seconds = timeout_seconds
        self.headers = headers or {"Content-Type": "application/json"}

    def send_event(self, event_type: str, data: dict[str, Any]) -> bool:
        if not self.webhook_url:
            logger.warning("Generic webhook URL is not configured.")
            return False

        payload = {
            "event_type": event_type,
            "data": data,
        }

        with tracer.start_as_current_span(
            "webhook_adapter.send_event",
            attributes={
                "http.url": self.webhook_url,
                "event.type": event_type,
            }
        ) as span:
            encoded_data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                self.webhook_url,
                data=encoded_data,
                headers=self.headers
            )
            try:
                with urllib.request.urlopen(req, timeout=self.timeout_seconds) as resp:
                    span.set_attribute("http.status_code", resp.status)
                    return resp.status in (200, 201, 202, 204)
            except urllib.error.URLError as e:
                span.record_exception(e)
                span.set_status(trace.StatusCode.ERROR, str(e))
                logger.error("Failed to post event to generic webhook (%s): %s", self.webhook_url, e)
                return False
