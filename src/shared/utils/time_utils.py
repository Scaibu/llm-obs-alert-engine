from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional


def compute_delivery_latency_ms(
    timestamp: Optional[str],
    now: Optional[datetime] = None,
) -> Optional[int]:
    if not timestamp:
        return None
    current_time = now or datetime.now(timezone.utc)
    try:
        normalized = timestamp.replace("Z", "+00:00")
        dt = datetime.fromisoformat(normalized)
        diff = (current_time - dt).total_seconds() * 1000
        return max(0, int(diff))
    except Exception:
        return None


def get_current_utc_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()
