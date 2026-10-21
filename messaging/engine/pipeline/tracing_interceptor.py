from typing import Any
from opentelemetry.context import Context
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator

class TracingInterceptor:
    @staticmethod
    def extract_context(headers: Any) -> Context | None:
        if not headers:
            return None
        carrier: dict[str, str] = {}
        for item in headers:
            if not isinstance(item, (tuple, list)) or len(item) < 2:
                continue
            key, value = item[0], item[1]
            if value is None:
                continue
            decoded = value.decode("utf-8") if isinstance(value, bytes) else str(value)
            if key in ("traceparent", "tracestate"):
                carrier[key] = decoded
        if not carrier:
            return None
        propagator = TraceContextTextMapPropagator()
        return propagator.extract(carrier)
