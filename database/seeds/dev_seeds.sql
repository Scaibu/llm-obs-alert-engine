INSERT INTO alert_history (alert_type, service, model, user_id, event_type, payload, delivery_latency_ms)
VALUES 
    ('latency_slo', 'llm-gateway', 'gpt-4o', 'usr-seed-01', 'breach', '{"p95_latency_ms": 3200, "threshold_ms": 2500}'::jsonb, 45),
    ('toxicity', 'chat-service', 'claude-3-5-sonnet', 'usr-seed-02', 'flagged', '{"toxicity_score": 0.88, "flagged": true}'::jsonb, 30);
