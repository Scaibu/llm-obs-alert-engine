from unittest.mock import MagicMock
from adapters.redis.redis_adapter import RedisAdapter
from shared.utils.rate_limiter import check_and_acquire_rate_limit

def test_redis_sliding_rate_limit_integration() -> None:
    adapter = RedisAdapter("redis://localhost:6379/0")
    store: dict[str, str] = {}

    def mock_set(key: str, val: str, nx: bool = False, ex: int | None = None) -> bool | None:
        if nx and key in store:
            return None
        store[key] = val
        return True

    adapter.client = MagicMock()
    adapter.client.set.side_effect = mock_set

    key = "rate_limit:alerts_budget:usr-456"
    first_acquired = adapter.acquire_rate_limit(key, 60)
    assert first_acquired is True
    assert key in store

    second_acquired = adapter.acquire_rate_limit(key, 60)
    assert second_acquired is False

def test_shared_rate_limiter_utility_integration() -> None:
    mock_redis_port = MagicMock()
    mock_redis_port.acquire_rate_limit.return_value = True

    acquired = check_and_acquire_rate_limit(
        redis_port=mock_redis_port,
        rate_limit_key="rate_limit:toxicity:usr-123",
        ttl_seconds=30,
        span_name="test_span",
    )
    assert acquired is True
    mock_redis_port.acquire_rate_limit.assert_called_once_with(
        "rate_limit:toxicity:usr-123",
        30,
    )

    mock_redis_port.acquire_rate_limit.return_value = False
    throttled = check_and_acquire_rate_limit(
        redis_port=mock_redis_port,
        rate_limit_key="rate_limit:toxicity:usr-123",
        ttl_seconds=30,
    )
    assert throttled is False

def test_redis_incident_state_tracking_integration() -> None:
    adapter = RedisAdapter("redis://localhost:6379/0")
    cache: dict[str, str] = {}

    adapter.client = MagicMock()
    adapter.client.get.side_effect = lambda k: cache.get(k)
    adapter.client.setex.side_effect = lambda k, ttl, v: cache.update({k: v})
    adapter.client.delete.side_effect = lambda k: cache.pop(k, None)

    assert adapter.get_open_incident("gpt-4", "/v1/chat") is None

    adapter.set_open_incident("gpt-4", "/v1/chat", "inc_98765", 600)
    assert adapter.get_open_incident("gpt-4", "/v1/chat") == "inc_98765"

    adapter.delete_open_incident("gpt-4", "/v1/chat")
    assert adapter.get_open_incident("gpt-4", "/v1/chat") is None
