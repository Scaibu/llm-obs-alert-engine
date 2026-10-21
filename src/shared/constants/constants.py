from __future__ import annotations

HEADER_TRACEPARENT = "traceparent"
HEADER_X_REQUEST_ID = "x-request-id"
HEADER_X_CORRELATION_ID = "x-correlation-id"
HEADER_X_IDEMPOTENCY_KEY = "x-idempotency-key"

TOPIC_ALERTS_BUDGET = "alerts.budget"
TOPIC_ALERTS_COST_ANOMALY = "alerts.cost.anomaly"
TOPIC_ALERTS_LATENCY_SLO = "alerts.latency.slo"
TOPIC_ALERTS_LATENCY_TTFT_REGRESSION = "alerts.latency.ttft_regression"
TOPIC_ALERTS_QUALITY_DEGRADATION = "alerts.quality.degradation"
TOPIC_LLM_TOXICITY_FLAGGED = "llm.toxicity.flagged"

CHANNEL_LLM_LATENCY_ALERTS = "#llm-latency-alerts"
CHANNEL_LLM_COST_ALERTS = "#llm-cost-alerts"
CHANNEL_LLM_QUALITY_ALERTS = "#llm-quality-alerts"
CHANNEL_LLM_SAFETY_REVIEW = "#llm-safety-review"

DEFAULT_PAGE_RATE_LIMIT_TTL = 900
DEFAULT_INCIDENT_TTL = 86400
DEFAULT_TTFT_RATE_LIMIT_TTL = 21600
DEFAULT_COST_ANOMALY_RATE_LIMIT_TTL = 3600
DEFAULT_TOXICITY_RATE_LIMIT_TTL = 300
