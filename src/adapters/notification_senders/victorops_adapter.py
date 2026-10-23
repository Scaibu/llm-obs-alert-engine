import json
import logging
import urllib.request
import urllib.error
from typing import Any
from opentelemetry import trace

logger = logging.getLogger(__name__)
tracer = trace.get_tracer("alert-engine")

class VictorOpsAdapter:
    def __init__(
        self,
        routing_url: str,
        timeout_seconds: float = 5.0,
    ) -> None:
        self.routing_url = routing_url
        self.timeout_seconds = timeout_seconds

    def trigger_incident(
        self,
        entity_id: str,
        message_type: str,
        state_message: str,
        details: dict[str, Any] | None = None,
    ) -> bool:
        if not self.routing_url:
            logger.warning("VictorOps routing URL not configured.")
            return False

        with tracer.start_as_current_span(
            "victorops_adapter.trigger_incident",
            attributes={"victorops.entity_id": entity_id, "victorops.message_type": message_type}
        ) as span:
            payload = {
                "message_type": message_type,
                "entity_id": entity_id,
                "state_message": state_message,
                "monitoring_tool": "alert-engine",
                "data": details or {},
            }
            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                self.routing_url,
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
                logger.error("Failed to post incident to VictorOps: %s", e)
                return False
