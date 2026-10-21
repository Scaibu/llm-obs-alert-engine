from opentelemetry import trace
from ports.redis_port import RedisPort

tracer = trace.get_tracer("alert-engine")

def check_and_acquire_rate_limit(
    redis_port: RedisPort,
    rate_limit_key: str,
    ttl_seconds: int,
    span_name: str = "check_rate_limit"
) -> bool:
    with tracer.start_as_current_span(span_name) as sub_span:
        sub_span.set_attribute("rate_limit.key", rate_limit_key)
        sub_span.set_attribute("rate_limit.ttl", ttl_seconds)
        acquired = redis_port.acquire_rate_limit(rate_limit_key, ttl_seconds)
        sub_span.set_attribute("rate_limit.acquired", acquired)
        return acquired
