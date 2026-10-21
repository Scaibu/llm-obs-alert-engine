from __future__ import annotations

from opentelemetry import trace

SERVICE_NAME = "alert-engine"
tracer = trace.get_tracer(SERVICE_NAME)

def get_tracer() -> trace.Tracer:
    return tracer
