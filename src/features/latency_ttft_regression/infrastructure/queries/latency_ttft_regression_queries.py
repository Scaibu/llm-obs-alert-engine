"""
Blueprint:
- Named parameterized SQL queries for latency_ttft_regression alert persistence.
- Follows canonical role (12) queries with FLOW_{VERB}_{ENTITY}_{CRITERIA} convention.
- 100% comment-free function and class bodies per rule (6).
"""

FLOW_INSERT_LATENCY_TTFT_REGRESSION_ALERT = """
INSERT INTO alert_history (alert_type, service, model, user_id, event_type, payload, delivery_latency_ms, created_at)
VALUES (:alert_type, :service, :model, :user_id, :event_type, :payload, :delivery_latency_ms, NOW());
"""

FLOW_SELECT_LATENCY_TTFT_REGRESSION_ALERTS_BY_MODEL = """
SELECT id, alert_type, service, model, user_id, event_type, payload, delivery_latency_ms, created_at
FROM alert_history
WHERE alert_type = 'latency_ttft_regression' AND model = :model
ORDER BY created_at DESC
LIMIT :limit;
"""
