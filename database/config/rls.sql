ALTER TABLE alert_history ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS alert_history_tenant_isolation_policy ON alert_history;

CREATE POLICY alert_history_tenant_isolation_policy ON alert_history
    FOR ALL
    USING (tenant_id = current_setting('app.current_tenant_id', true))
    WITH CHECK (tenant_id = current_setting('app.current_tenant_id', true));
