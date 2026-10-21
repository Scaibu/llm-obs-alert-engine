-- Invariant Queries for Continuous Integrity Verification (05-db-writing-rules.md Section 10)

-- FLOW_CHECK_ALERT_HISTORY_INVALID_ALERT_TYPE
SELECT id, alert_type 
FROM alert_history 
WHERE alert_type NOT IN (
    'latency_slo',
    'latency_ttft_regression',
    'budget',
    'cost_anomaly',
    'quality_degradation',
    'toxicity'
);

-- FLOW_CHECK_ALERT_HISTORY_INVALID_PAYLOAD
SELECT id, payload 
FROM alert_history 
WHERE jsonb_typeof(payload) <> 'object';

-- FLOW_CHECK_ALERT_HISTORY_NEGATIVE_LATENCY
SELECT id, delivery_latency_ms 
FROM alert_history 
WHERE delivery_latency_ms < 0;

-- FLOW_CHECK_ALERT_HISTORY_UNTRIMMED_TEXT
SELECT id, service, model, user_id 
FROM alert_history 
WHERE (service IS NOT NULL AND service <> btrim(service))
   OR (model IS NOT NULL AND model <> btrim(model))
   OR (user_id IS NOT NULL AND user_id <> btrim(user_id));

-- FLOW_CHECK_ALERT_HISTORY_DUPLICATE_EXTERNAL_ID
SELECT tenant_id, source, external_id, count(*) 
FROM alert_history 
GROUP BY tenant_id, source, external_id 
HAVING count(*) > 1;
