-- migration:      0001
-- description:    create alert_history table
-- author:         reliability-platform
-- date:           2026-10-21
-- depends_on:     none
-- reversible:     YES
-- lock_risk:      LOW
-- rows_affected:  schema only
-- reason:         initial schema setup for alert_history table with 5-role identifiers and audit columns
-- nullable_columns:
--   service: optional originating service identifier
--   model: optional LLM model identifier for model-specific alerts
--   user_id: optional user identifier associated with the alert event
--   event_type: optional sub-category or trigger type of the alert event
--   delivery_latency_ms: optional metric recorded only when outbound dispatch latency is measured
--   deleted_at: optional timestamp populated only upon soft deletion

CREATE TABLE alert_history (
    id BIGINT GENERATED ALWAYS AS IDENTITY,
    public_id VARCHAR(64) NOT NULL DEFAULT ('alt_' || substr(md5(random()::text), 1, 26)),
    tenant_id VARCHAR(64) NOT NULL DEFAULT 'default',
    source VARCHAR(64) NOT NULL DEFAULT 'alert-engine',
    external_id VARCHAR(128) NOT NULL DEFAULT ('ext_' || substr(md5(random()::text), 1, 26)),
    correlation_id VARCHAR(64) NOT NULL DEFAULT ('cor_' || substr(md5(random()::text), 1, 26)),
    alert_type VARCHAR(50) NOT NULL,
    service VARCHAR(255),
    model VARCHAR(255),
    user_id VARCHAR(255),
    event_type VARCHAR(50),
    payload JSONB NOT NULL,
    delivery_latency_ms INTEGER,
    version BIGINT NOT NULL DEFAULT 1,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMPTZ,
    CONSTRAINT alert_history_pkey PRIMARY KEY (id),
    CONSTRAINT alert_history_tenant_id_id_uk UNIQUE (tenant_id, id),
    CONSTRAINT alert_history_public_id_uk UNIQUE (public_id),
    CONSTRAINT alert_history_tenant_source_ext_uk UNIQUE (tenant_id, source, external_id),
    CONSTRAINT alert_history_public_id_ck CHECK (public_id = btrim(public_id) AND length(public_id) > 0),
    CONSTRAINT alert_history_tenant_id_ck CHECK (tenant_id = btrim(tenant_id) AND length(tenant_id) > 0),
    CONSTRAINT alert_history_source_ck CHECK (source = btrim(source) AND length(source) > 0),
    CONSTRAINT alert_history_external_id_ck CHECK (external_id = btrim(external_id) AND length(external_id) > 0),
    CONSTRAINT alert_history_correlation_id_ck CHECK (correlation_id = btrim(correlation_id) AND length(correlation_id) > 0),
    CONSTRAINT alert_history_alert_type_ck CHECK (
        alert_type IN (
            'latency_slo',
            'latency_ttft_regression',
            'budget',
            'cost_anomaly',
            'quality_degradation',
            'toxicity'
        )
    ),
    CONSTRAINT alert_history_service_ck CHECK (service IS NULL OR (service = btrim(service) AND length(service) > 0)),
    CONSTRAINT alert_history_model_ck CHECK (model IS NULL OR (model = btrim(model) AND length(model) > 0)),
    CONSTRAINT alert_history_user_id_ck CHECK (user_id IS NULL OR (user_id = btrim(user_id) AND length(user_id) > 0)),
    CONSTRAINT alert_history_event_type_ck CHECK (event_type IS NULL OR (event_type = btrim(event_type) AND length(event_type) > 0)),
    CONSTRAINT alert_history_payload_ck CHECK (jsonb_typeof(payload) = 'object'),
    CONSTRAINT alert_history_delivery_latency_ms_ck CHECK (delivery_latency_ms IS NULL OR delivery_latency_ms >= 0),
    CONSTRAINT alert_history_version_ck CHECK (version >= 1)
);

CREATE INDEX alert_history_tenant_alert_type_created_idx ON alert_history (tenant_id, alert_type, created_at DESC);
CREATE INDEX alert_history_correlation_id_idx ON alert_history (correlation_id);
