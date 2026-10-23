from __future__ import annotations

import json
import logging
import urllib.request
import urllib.error
from typing import Any
from opentelemetry import trace
from ports.pagerduty_port import PagerDutyPort

logger = logging.getLogger(__name__)
tracer = trace.get_tracer("alert-engine")

class PagerDutyAdapter(PagerDutyPort):
    def __init__(
        self,
        routing_key: str,
        endpoint: str,
        timeout_seconds: float = 5.0,
    ) -> None:
        self.routing_key = routing_key
        self.endpoint = endpoint
        self.timeout_seconds = timeout_seconds

    def trigger_incident(
        self,
        summary: str,
        severity: str,
        source: str,
        custom_details: dict[str, Any] | None = None
    ) -> str | None:
        if not self.routing_key or not self.endpoint:
            logger.warning("PagerDuty routing key or endpoint not set. Suppressing incident trigger.")
            return None

        with tracer.start_as_current_span(
            "pagerduty_adapter.trigger_incident",
            attributes={
                "http.url": self.endpoint,
                "pagerduty.summary": summary,
                "pagerduty.severity": severity,
                "pagerduty.source": source,
            }
        ) as span:
            dedup_key = None
            if custom_details:
                model = custom_details.get("model")
                endpoint = custom_details.get("endpoint")
                if model and endpoint:
                    dedup_key = f"latency_slo:{model}:{endpoint}".replace("/", "_")

            payload = {
                "routing_key": self.routing_key,
                "event_action": "trigger",
                "payload": {
                    "summary": summary,
                    "severity": severity,
                    "source": source,
                    "custom_details": custom_details or {}
                }
            }
            if dedup_key:
                payload["dedup_key"] = dedup_key

            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                self.endpoint,
                data=data,
                headers={"Content-Type": "application/json"}
            )
            try:
                with urllib.request.urlopen(req, timeout=self.timeout_seconds) as resp:
                    resp_data = json.loads(resp.read().decode("utf-8"))
                    returned_dedup = resp_data.get("dedup_key")
                    return returned_dedup or dedup_key
            except urllib.error.URLError as e:
                span.record_exception(e)
                span.set_status(trace.StatusCode.ERROR, str(e))
                logger.error("Failed to trigger PagerDuty incident: %s", e)
                return dedup_key

    def resolve_incident(
        self,
        dedup_key: str
    ) -> None:
        if not self.routing_key or not self.endpoint:
            return

        with tracer.start_as_current_span(
            "pagerduty_adapter.resolve_incident",
            attributes={
                "http.url": self.endpoint,
                "pagerduty.dedup_key": dedup_key,
            }
        ) as span:
            payload = {
                "routing_key": self.routing_key,
                "event_action": "resolve",
                "dedup_key": dedup_key
            }
            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                self.endpoint,
                data=data,
                headers={"Content-Type": "application/json"}
            )
            try:
                with urllib.request.urlopen(req, timeout=self.timeout_seconds) as resp:
                    resp.read()
            except urllib.error.URLError as e:
                span.record_exception(e)
                span.set_status(trace.StatusCode.ERROR, str(e))
                logger.error("Failed to resolve PagerDuty incident (%s): %s", dedup_key, e)
