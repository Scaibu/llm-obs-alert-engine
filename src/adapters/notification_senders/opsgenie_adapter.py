import json
import logging
import urllib.request
import urllib.error
from typing import Any
from opentelemetry import trace

logger = logging.getLogger(__name__)
tracer = trace.get_tracer("alert-engine")

class OpsgenieAdapter:
    def __init__(
        self,
        api_key: str,
        endpoint: str,
        timeout_seconds: float = 5.0,
    ) -> None:
        self.api_key = api_key
        self.endpoint = endpoint
        self.timeout_seconds = timeout_seconds

    def create_alert(
        self,
        message: str,
        alias: str,
        priority: str,
        description: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> bool:
        if not self.api_key or not self.endpoint:
            logger.warning("Opsgenie API key or endpoint not set. Suppressing alert.")
            return False

        with tracer.start_as_current_span(
            "opsgenie_adapter.create_alert",
            attributes={
                "http.url": self.endpoint,
                "opsgenie.alias": alias,
                "opsgenie.priority": priority,
            }
        ) as span:
            payload: dict[str, Any] = {
                "message": message,
                "alias": alias,
                "priority": priority,
                "description": description or message,
                "details": details or {},
                "source": "alert-engine",
            }

            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                self.endpoint,
                data=data,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"GenieKey {self.api_key}",
                }
            )
            try:
                with urllib.request.urlopen(req, timeout=self.timeout_seconds) as resp:
                    span.set_attribute("http.status_code", resp.status)
                    return resp.status in (200, 201, 202)
            except urllib.error.URLError as e:
                span.record_exception(e)
                span.set_status(trace.StatusCode.ERROR, str(e))
                logger.error("Failed to send alert to Opsgenie: %s", e)
                return False

    def close_alert(self, alias: str) -> bool:
        if not self.api_key or not self.endpoint:
            return False

        close_endpoint = f"{self.endpoint.rstrip('/')}/{alias}/close?identifierType=alias"
        with tracer.start_as_current_span(
            "opsgenie_adapter.close_alert",
            attributes={
                "http.url": close_endpoint,
                "opsgenie.alias": alias,
            }
        ) as span:
            payload = {"source": "alert-engine"}
            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                close_endpoint,
                data=data,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"GenieKey {self.api_key}",
                }
            )
            try:
                with urllib.request.urlopen(req, timeout=self.timeout_seconds) as resp:
                    span.set_attribute("http.status_code", resp.status)
                    return resp.status in (200, 202)
            except urllib.error.URLError as e:
                span.record_exception(e)
                span.set_status(trace.StatusCode.ERROR, str(e))
                logger.error("Failed to close Opsgenie alert (%s): %s", alias, e)
                return False
