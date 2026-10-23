import json
import logging
import urllib.request
import urllib.error
from typing import Any
from opentelemetry import trace

logger = logging.getLogger(__name__)
tracer = trace.get_tracer("alert-engine")

class GrafanaOnCallAdapter:
    def __init__(
        self,
        webhook_url: str,
        timeout_seconds: float = 5.0,
    ) -> None:
        self.webhook_url = webhook_url
        self.timeout_seconds = timeout_seconds

    def trigger_alert(
        self,
        title: str,
        message: str,
        state: str = "alerting",
        link_to_upstream_details: str | None = None,
    ) -> bool:
        if not self.webhook_url:
            logger.warning("Grafana OnCall webhook URL not configured.")
            return False

        with tracer.start_as_current_span(
            "grafana_oncall_adapter.trigger_alert",
            attributes={"http.url": self.webhook_url}
        ) as span:
            payload: dict[str, Any] = {
                "title": title,
                "message": message,
                "state": state,
            }
            if link_to_upstream_details:
                payload["link_to_upstream_details"] = link_to_upstream_details

            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                self.webhook_url,
                data=data,
                headers={"Content-Type": "application/json"}
            )
            try:
                with urllib.request.urlopen(req, timeout=self.timeout_seconds) as resp:
                    span.set_attribute("http.status_code", resp.status)
                    return resp.status in (200, 201, 202)
            except urllib.error.URLError as e:
                span.record_exception(e)
                span.set_status(trace.StatusCode.ERROR, str(e))
                logger.error("Failed to post alert to Grafana OnCall: %s", e)
                return False
