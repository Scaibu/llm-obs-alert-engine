from unittest.mock import MagicMock
from handlers.alerts_toxicity.handler import ToxicityAlertHandler
from ports.redis_port import RedisPort
from ports.slack_port import SlackPort

def test_scenario_toxicity_surge_and_rate_limiting() -> None:
    redis = MagicMock(spec=RedisPort)
    slack = MagicMock(spec=SlackPort)

    call_count = [0]
    def rate_limit_limiter(key: str, ttl_seconds: int) -> bool:
        call_count[0] += 1
        return call_count[0] <= 3

    redis.acquire_rate_limit.side_effect = rate_limit_limiter

    handler = ToxicityAlertHandler(
        redis_port=redis,
        slack_port=slack,
    )

    for i in range(1, 6):
        handler.handle({
            "span_id": f"span-{i}",
            "toxicity_score": 0.85,
            "user_id": f"usr-surge",
            "model": "gpt-4",
            "endpoint": "/v1/chat",
        })

    assert redis.acquire_rate_limit.call_count == 5
    assert slack.send_channel_message.call_count == 3
