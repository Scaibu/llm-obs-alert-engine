import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:
    yaml = None

class ValidationError(Exception):
    pass

@dataclass(frozen=True)
class WorkerConfig:
    kafka_bootstrap_servers: str
    kafka_consumer_group: str
    kafka_topics: list[str]
    redis_url: str
    postgres_dsn: str
    slack_webhook_url: str
    pagerduty_routing_key: str
    service_owners_file_path: str
    prometheus_metrics_port: int
    health_check_port: int
    slack_timeout_seconds: float = 5.0
    pagerduty_endpoint: str = ""
    pagerduty_timeout_seconds: float = 5.0
    teams_webhook_url: str = ""
    opsgenie_api_key: str = ""
    opsgenie_endpoint: str = ""
    generic_webhook_url: str = ""

class AppConfigLoader:
    _cached_config: dict[str, Any] | None = None
    _cached_endpoints: dict[str, Any] | None = None
    _cached_flags: dict[str, Any] | None = None

    @classmethod
    def get_config_dir(cls) -> Path:
        return Path(__file__).resolve().parents[2] / "config"

    @classmethod
    def read_yaml_file(cls, filename: str) -> dict[str, Any]:
        file_path = cls.get_config_dir() / filename
        if file_path.exists() and yaml is not None:
            try:
                content = file_path.read_text(encoding="utf-8")
                parsed = yaml.safe_load(content)
                if isinstance(parsed, dict):
                    return parsed
            except Exception:
                pass
        return {}

    @classmethod
    def load_config(cls) -> dict[str, Any]:
        if cls._cached_config is not None:
            return cls._cached_config
        data = cls.read_yaml_file("default.yaml")
        app_env = os.environ.get("APP_ENV", os.environ.get("ENVIRONMENT", "development")).lower()
        if app_env in ("production", "prod"):
            prod_overrides = cls.read_yaml_file("production.yaml")
            data = cls._deep_merge(data, prod_overrides)
        elif app_env in ("test", "testing"):
            test_overrides = cls.read_yaml_file("test.yaml")
            data = cls._deep_merge(data, test_overrides)
        cls._cached_config = data
        return data

    @classmethod
    def load_endpoints(cls) -> dict[str, Any]:
        if cls._cached_endpoints is not None:
            return cls._cached_endpoints
        cls._cached_endpoints = cls.read_yaml_file("endpoints.yaml")
        return cls._cached_endpoints

    @classmethod
    def load_feature_flags(cls) -> dict[str, Any]:
        if cls._cached_flags is not None:
            return cls._cached_flags
        cls._cached_flags = cls.read_yaml_file("feature-flags.yaml")
        return cls._cached_flags

    @classmethod
    def _deep_merge(cls, base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
        merged = dict(base)
        for key, val in override.items():
            if key in merged and isinstance(merged[key], dict) and isinstance(val, dict):
                merged[key] = cls._deep_merge(merged[key], val)
            else:
                merged[key] = val
        return merged

def _int_val(raw: str, key: str) -> int:
    try:
        return int(raw)
    except ValueError as exc:
        raise ValidationError(f"{key} must be an integer") from exc

def load_config(env: dict[str, str] | None = None) -> WorkerConfig:
    source = env if env is not None else os.environ

    yaml_cfg: dict[str, Any] = {}
    if env is None:
        yaml_cfg = AppConfigLoader.load_config()

    server_cfg = yaml_cfg.get("server", {})
    kafka_cfg = yaml_cfg.get("kafka", {})
    postgres_cfg = yaml_cfg.get("postgres", {})
    redis_cfg = yaml_cfg.get("redis", {})
    integrations_cfg = yaml_cfg.get("integrations", {})

    postgres_user = source.get("POSTGRES_USER", str(postgres_cfg.get("user", "postgres")))
    postgres_password = source.get("POSTGRES_PASSWORD", str(postgres_cfg.get("password", "postgres")))
    postgres_host = source.get("POSTGRES_HOST", str(postgres_cfg.get("host", "localhost")))
    postgres_port = source.get("POSTGRES_PORT", str(postgres_cfg.get("port", "5439")))
    postgres_db = source.get("POSTGRES_DB", str(postgres_cfg.get("db", "ewma_db")))

    computed_dsn = f"postgresql://{postgres_user}:{postgres_password}@{postgres_host}:{postgres_port}/{postgres_db}"
    postgres_dsn = source.get("POSTGRES_DSN", computed_dsn)

    default_topics_list = kafka_cfg.get("topics")
    if isinstance(default_topics_list, list) and default_topics_list:
        default_topics = ",".join(str(t) for t in default_topics_list)
    else:
        default_topics = "alerts.budget,alerts.cost.anomaly,llm.toxicity.flagged,alerts.quality.degradation,alerts.latency.slo,alerts.latency.ttft_regression"

    topics_raw = source.get("KAFKA_TOPICS", default_topics)
    kafka_topics = [t.strip() for t in topics_raw.split(",") if t.strip()]

    default_kafka_bootstrap = str(kafka_cfg.get("bootstrap_servers", "localhost:9099"))
    default_kafka_group = str(kafka_cfg.get("consumer_group", "alert-engine-group"))
    default_redis_url = str(redis_cfg.get("url", "redis://localhost:6389/0"))
    default_slack_url = str(integrations_cfg.get("slack_webhook_url", ""))
    default_pagerduty_key = str(integrations_cfg.get("pagerduty_routing_key", ""))
    default_service_owners = str(integrations_cfg.get("service_owners_file", "config/service_owners.yaml"))
    default_slack_timeout = float(integrations_cfg.get("slack_timeout_seconds", 5.0))
    default_pd_endpoint = str(integrations_cfg.get("pagerduty_endpoint", ""))
    default_pd_timeout = float(integrations_cfg.get("pagerduty_timeout_seconds", 5.0))
    default_metrics_port = str(server_cfg.get("prometheus_metrics_port", "9464"))
    default_health_port = str(server_cfg.get("health_check_port", "8001"))

    try:
        slack_timeout = float(source.get("SLACK_TIMEOUT_SECONDS", default_slack_timeout))
    except (ValueError, TypeError):
        slack_timeout = default_slack_timeout

    try:
        pd_timeout = float(source.get("PAGERDUTY_TIMEOUT_SECONDS", default_pd_timeout))
    except (ValueError, TypeError):
        pd_timeout = default_pd_timeout

    return WorkerConfig(
        kafka_bootstrap_servers=source.get("KAFKA_BOOTSTRAP_SERVERS", default_kafka_bootstrap),
        kafka_consumer_group=source.get("KAFKA_CONSUMER_GROUP", default_kafka_group),
        kafka_topics=kafka_topics,
        redis_url=source.get("REDIS_URL", default_redis_url),
        postgres_dsn=postgres_dsn,
        slack_webhook_url=source.get("SLACK_WEBHOOK_URL", default_slack_url),
        pagerduty_routing_key=source.get("PAGERDUTY_ROUTING_KEY", default_pagerduty_key),
        service_owners_file_path=source.get("SERVICE_OWNERS_FILE_PATH", default_service_owners),
        prometheus_metrics_port=_int_val(source.get("PROMETHEUS_METRICS_PORT", default_metrics_port), "PROMETHEUS_METRICS_PORT"),
        health_check_port=_int_val(source.get("HEALTH_CHECK_PORT", default_health_port), "HEALTH_CHECK_PORT"),
        slack_timeout_seconds=slack_timeout,
        pagerduty_endpoint=source.get("PAGERDUTY_ENDPOINT", default_pd_endpoint),
        pagerduty_timeout_seconds=pd_timeout,
        teams_webhook_url=source.get("TEAMS_WEBHOOK_URL", str(integrations_cfg.get("teams_webhook_url", ""))),
        opsgenie_api_key=source.get("OPSGENIE_API_KEY", str(integrations_cfg.get("opsgenie_api_key", ""))),
        opsgenie_endpoint=source.get("OPSGENIE_ENDPOINT", str(integrations_cfg.get("opsgenie_endpoint", ""))),
        generic_webhook_url=source.get("GENERIC_WEBHOOK_URL", str(integrations_cfg.get("generic_webhook_url", ""))),
    )
