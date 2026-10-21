class CostAnomalyQueries:
    INSERT_ALERT: str = (
        "INSERT INTO alert_history "
        "(alert_type, service, model, user_id, event_type, payload, delivery_latency_ms) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s);"
    )
