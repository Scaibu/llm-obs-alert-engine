import json
import logging
import urllib.request
import urllib.error
from typing import Any
from opentelemetry import trace

logger = logging.getLogger(__name__)
tracer = trace.get_tracer("alert-engine")

class DatadogAdapter:
    def __init__(
        self,
        api_key: str,
        endpoint: str,
        timeout_seconds: float = 5.0,
    ) -> None:
        self.api_key = api_key
        self.endpoint = endpoint
        self.timeout_seconds = timeout_seconds

    def send_event(
        self,
        title: str,
        text: str,
        alert_type: str = "error",
        tags: list[str] | None = None,
    ) -> bool:
        if not self.api_key or not self.endpoint:
            logger.warning("Datadog API key or endpoint not configured.")
            return False

        with tracer.start_as_current_span(
            "datadog_adapter.send_event",
            attributes={"datadog.title": title, "http.url": self.endpoint}
        ) as span:
            payload: dict[str, Any] = {
                "title": title,
                "text": text,
                "alert_type": alert_type,
                "tags": tags or ["service:alert-engine"],
            }
            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                self.endpoint,
                data=data,
                headers={
                    "Content-Type": "application/json",
                    "DD-API-KEY": self.api_key,
                }
            )
            try:
                with urllib.request.urlopen(req, timeout=self.timeout_seconds) as resp:
                    span.set_attribute("http.status_code", resp.status)
                    return resp.status in (200, 202)
            except urllib.error.URLError as e:
                span.record_exception(e)
                span.set_status(trace.StatusCode.ERROR, str(e))
                logger.error("Failed to post event to Datadog: %s", e)
                return False
