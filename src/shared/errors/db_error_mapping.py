from typing import Mapping
from shared.errors.application_error import ValidationError, ConflictError, ApplicationError

CONSTRAINT_ERROR_MAP: Mapping[str, type[ApplicationError]] = {
    "alert_history_alert_type_ck": ValidationError,
    "alert_history_payload_ck": ValidationError,
    "alert_history_delivery_latency_ms_ck": ValidationError,
    "alert_history_public_id_ck": ValidationError,
    "alert_history_tenant_id_ck": ValidationError,
    "alert_history_source_ck": ValidationError,
    "alert_history_external_id_ck": ValidationError,
    "alert_history_correlation_id_ck": ValidationError,
    "alert_history_service_ck": ValidationError,
    "alert_history_model_ck": ValidationError,
    "alert_history_user_id_ck": ValidationError,
    "alert_history_event_type_ck": ValidationError,
    "alert_history_version_ck": ValidationError,
    "alert_history_public_id_uk": ConflictError,
    "alert_history_tenant_id_id_uk": ConflictError,
    "alert_history_tenant_source_ext_uk": ConflictError,
}

def map_db_constraint_error(constraint_name: str, message: str) -> ApplicationError:
    error_cls = CONSTRAINT_ERROR_MAP.get(constraint_name)
    if error_cls is None:
        return ApplicationError(message=f"Database constraint violation: {constraint_name}")
    return error_cls(message=f"Constraint violation on {constraint_name}: {message}")
