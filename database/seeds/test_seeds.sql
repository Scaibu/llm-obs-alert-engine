INSERT INTO alert_history (alert_type, service, model, user_id, event_type, payload, delivery_latency_ms)
VALUES 
    ('budget', 'billing-service', 'gpt-4', 'usr-test-01', 'threshold_exceeded', '{"threshold": 1000, "current": 1250}'::jsonb, 12);
