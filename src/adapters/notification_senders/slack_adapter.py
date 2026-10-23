import json
import logging
import urllib.request
import urllib.error
from typing import Any
from opentelemetry import trace
from ports.slack_port import SlackPort

logger = logging.getLogger(__name__)
tracer = trace.get_tracer("alert-engine")

class SlackAdapter(SlackPort):
    def __init__(
        self,
        webhook_url: str,
        timeout_seconds: float = 5.0,
        default_channel: str | None = None,
        username: str | None = None,
        icon_emoji: str | None = None,
    ) -> None:
        self.webhook_url = webhook_url
        self.timeout_seconds = timeout_seconds
        self.default_channel = default_channel
        self.username = username
        self.icon_emoji = icon_emoji

    def _post(self, payload: dict[str, Any]) -> bool:
        if not self.webhook_url:
            logger.warning("Slack webhook URL is not configured. Suppressing notification.")
            return False

        if self.default_channel and "channel" not in payload:
            payload["channel"] = self.default_channel
        if self.username and "username" not in payload:
            payload["username"] = self.username
        if self.icon_emoji and "icon_emoji" not in payload:
            payload["icon_emoji"] = self.icon_emoji

        with tracer.start_as_current_span(
            "slack_adapter.post",
            attributes={
                "http.url": self.webhook_url,
                "slack.channel": payload.get("channel", ""),
                "slack.username": payload.get("username", "") or "",
            }
        ) as span:
            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                self.webhook_url,
                data=data,
                headers={"Content-Type": "application/json"}
            )
            try:
                with urllib.request.urlopen(req, timeout=self.timeout_seconds) as resp:
                    resp_body = resp.read()
                    span.set_attribute("http.status_code", resp.status)
                    return resp.status == 200 or resp_body == b"ok"
            except urllib.error.URLError as e:
                span.record_exception(e)
                span.set_status(trace.StatusCode.ERROR, str(e))
                logger.error("Failed to post message to Slack (%s): %s", self.webhook_url, e)
                return False

    def send_channel_message(self, channel: str, text: str) -> None:
        self._post({"channel": channel, "text": text})

    def send_direct_message(self, user: str, text: str) -> None:
        self._post({"channel": user, "text": text})

    def send_rich_message(
        self,
        channel: str,
        text: str,
        blocks: list[dict[str, Any]] | None = None,
        attachments: list[dict[str, Any]] | None = None
    ) -> bool:
        payload: dict[str, Any] = {"channel": channel, "text": text}
        if blocks:
            payload["blocks"] = blocks
        if attachments:
            payload["attachments"] = attachments
        return self._post(payload)
