class ToxicityQueries:
    INSERT_ALERT: str = (
        "INSERT INTO alert_history "
        "(alert_type, user_id, service, model, payload) "
        "VALUES (%s, %s, %s, %s, %s);"
    )
