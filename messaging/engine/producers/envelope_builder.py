import json
import uuid
from datetime import datetime, timezone
from typing import Any

class EnvelopeBuilder:
    @staticmethod
    def build_envelope(
        event_name: str,
        payload: dict[str, Any],
        correlation_id: str | None = None,
        tenant_id: str | None = None,
    ) -> dict[str, Any]:
        return {
            "id": str(uuid.uuid4()),
            "event_name": event_name,
            "tenant_id": tenant_id or "default",
            "correlation_id": correlation_id or str(uuid.uuid4()),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "payload": payload,
        }
