import pytest
from config.config import AppConfigLoader, ValidationError, WorkerConfig, load_config
from worker.config import load_config as worker_load_config

def test_load_config_defaults() -> None:
    config = load_config({})
    assert isinstance(config, WorkerConfig)
    assert config.kafka_consumer_group == "alert-engine-group"
    assert config.prometheus_metrics_port == 9464
    assert config.health_check_port == 8001
    assert "alerts.budget" in config.kafka_topics

def test_load_config_custom_env() -> None:
    custom_env = {
        "KAFKA_BOOTSTRAP_SERVERS": "custom-kafka:9092",
        "KAFKA_CONSUMER_GROUP": "custom-group",
        "KAFKA_TOPICS": "topic1, topic2",
        "REDIS_URL": "redis://custom-redis:6379/1",
        "POSTGRES_DSN": "postgresql://user:pass@custom-pg:5432/db",
        "SLACK_WEBHOOK_URL": "http://custom-slack",
        "PAGERDUTY_ROUTING_KEY": "custom-pd",
        "SERVICE_OWNERS_FILE_PATH": "custom_owners.yaml",
        "PROMETHEUS_METRICS_PORT": "9999",
        "HEALTH_CHECK_PORT": "8888",
    }
    config = load_config(custom_env)
    assert config.kafka_bootstrap_servers == "custom-kafka:9092"
    assert config.kafka_consumer_group == "custom-group"
    assert config.kafka_topics == ["topic1", "topic2"]
    assert config.redis_url == "redis://custom-redis:6379/1"
    assert config.postgres_dsn == "postgresql://user:pass@custom-pg:5432/db"
    assert config.slack_webhook_url == "http://custom-slack"
    assert config.pagerduty_routing_key == "custom-pd"
    assert config.service_owners_file_path == "custom_owners.yaml"
    assert config.prometheus_metrics_port == 9999
    assert config.health_check_port == 8888

def test_load_config_invalid_integer() -> None:
    with pytest.raises(ValidationError, match="PROMETHEUS_METRICS_PORT must be an integer"):
        load_config({"PROMETHEUS_METRICS_PORT": "not_an_int"})

    with pytest.raises(ValidationError, match="HEALTH_CHECK_PORT must be an integer"):
        load_config({"HEALTH_CHECK_PORT": "invalid"})

def test_app_config_loader_reads_declarative_yamls() -> None:
    cfg = AppConfigLoader.load_config()
    assert isinstance(cfg, dict)
    assert "server" in cfg

    endpoints = AppConfigLoader.load_endpoints()
    assert isinstance(endpoints, dict)
    assert "endpoints" in endpoints

    flags = AppConfigLoader.load_feature_flags()
    assert isinstance(flags, dict)
    assert "flags" in flags

def test_worker_config_reexport_compatibility() -> None:
    config = worker_load_config({})
    assert isinstance(config, WorkerConfig)
