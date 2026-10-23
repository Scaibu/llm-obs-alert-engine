import json
import logging
import urllib.request
import urllib.error
from typing import Any
from opentelemetry import trace

logger = logging.getLogger(__name__)
tracer = trace.get_tracer("alert-engine")

class NewRelicAdapter:
    def __init__(
        self,
        insert_key: str,
        endpoint: str,
        timeout_seconds: float = 5.0,
    ) -> None:
        self.insert_key = insert_key
        self.endpoint = endpoint
        self.timeout_seconds = timeout_seconds

    def send_event(self, event_type: str, attributes: dict[str, Any]) -> bool:
        if not self.endpoint or not self.insert_key:
            logger.warning("New Relic endpoint or insert_key not configured.")
            return False

        with tracer.start_as_current_span(
            "newrelic_adapter.send_event",
            attributes={"newrelic.event_type": event_type, "http.url": self.endpoint}
        ) as span:
            payload = [{"eventType": event_type, **attributes}]
            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                self.endpoint,
                data=data,
                headers={
                    "Content-Type": "application/json",
                    "X-Insert-Key": self.insert_key,
                }
            )
            try:
                with urllib.request.urlopen(req, timeout=self.timeout_seconds) as resp:
                    span.set_attribute("http.status_code", resp.status)
                    return resp.status in (200, 202)
            except urllib.error.URLError as e:
                span.record_exception(e)
                span.set_status(trace.StatusCode.ERROR, str(e))
                logger.error("Failed to post event to New Relic: %s", e)
                return False
