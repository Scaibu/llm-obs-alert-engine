import json
import logging
import urllib.request
import urllib.error
from typing import Any
from opentelemetry import trace
from ports.slack_port import SlackPort

logger = logging.getLogger(__name__)
tracer = trace.get_tracer("alert-engine")

class TeamsAdapter(SlackPort):
    def __init__(
        self,
        webhook_url: str,
        timeout_seconds: float = 5.0,
    ) -> None:
        self.webhook_url = webhook_url
        self.timeout_seconds = timeout_seconds

    def _post(self, title: str, text: str) -> bool:
        if not self.webhook_url:
            logger.warning("Microsoft Teams webhook URL is not configured.")
            return False

        payload = {
            "type": "message",
            "attachments": [
                {
                    "contentType": "application/vnd.microsoft.card.adaptive",
                    "contentUrl": None,
                    "content": {
                        "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
                        "type": "AdaptiveCard",
                        "version": "1.4",
                        "body": [
                            {
                                "type": "TextBlock",
                                "text": title,
                                "weight": "Bolder",
                                "size": "Medium",
                            },
                            {
                                "type": "TextBlock",
                                "text": text,
                                "wrap": True,
                            }
                        ]
                    }
                }
            ]
        }

        with tracer.start_as_current_span(
            "teams_adapter.post",
            attributes={
                "http.url": self.webhook_url,
                "teams.title": title,
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
                    span.set_attribute("http.status_code", resp.status)
                    return resp.status in (200, 202)
            except urllib.error.URLError as e:
                span.record_exception(e)
                span.set_status(trace.StatusCode.ERROR, str(e))
                logger.error("Failed to post message to Teams: %s", e)
                return False

    def send_channel_message(self, channel: str, text: str) -> None:
        self._post(title=f"Alert: {channel}", text=text)

    def send_direct_message(self, user: str, text: str) -> None:
        self._post(title=f"Notification for {user}", text=text)
