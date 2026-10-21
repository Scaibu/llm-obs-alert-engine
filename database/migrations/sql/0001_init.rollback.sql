-- migration:      0001
-- description:    rollback create alert_history table
-- author:         reliability-platform
-- date:           2026-10-21
-- depends_on:     none
-- reversible:     YES
-- lock_risk:      LOW
-- rows_affected:  schema only
-- reason:         revert initial schema setup for alert_history table

DROP TABLE IF EXISTS alert_history CASCADE;
