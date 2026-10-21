class QualityDegradationQueries:
    INSERT_ALERT: str = (
        "INSERT INTO alert_history (alert_type, model, service, payload) "
        "VALUES (%s, %s, %s, %s);"
    )
