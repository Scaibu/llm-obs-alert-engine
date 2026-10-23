import base64
import logging
import urllib.request
import urllib.error
import urllib.parse
from opentelemetry import trace

logger = logging.getLogger(__name__)
tracer = trace.get_tracer("alert-engine")

class TwilioSmsAdapter:
    def __init__(
        self,
        account_sid: str,
        auth_token: str,
        from_number: str,
        endpoint_template: str,
        timeout_seconds: float = 5.0,
    ) -> None:
        self.account_sid = account_sid
        self.auth_token = auth_token
        self.from_number = from_number
        self.endpoint_template = endpoint_template
        self.timeout_seconds = timeout_seconds

    def send_sms(self, to_number: str, body: str) -> bool:
        if not self.account_sid or not self.auth_token or not self.from_number or not self.endpoint_template:
            logger.warning("Twilio credentials, from_number, or endpoint_template not configured.")
            return False

        endpoint = self.endpoint_template.replace("{account_sid}", self.account_sid)
        with tracer.start_as_current_span(
            "twilio_sms_adapter.send_sms",
            attributes={"twilio.to": to_number, "http.url": endpoint}
        ) as span:
            data = urllib.parse.urlencode({
                "To": to_number,
                "From": self.from_number,
                "Body": body,
            }).encode("utf-8")

            auth_str = f"{self.account_sid}:{self.auth_token}"
            b64_auth = base64.b64encode(auth_str.encode("utf-8")).decode("ascii")

            req = urllib.request.Request(
                endpoint,
                data=data,
                headers={
                    "Content-Type": "application/x-www-form-urlencoded",
                    "Authorization": f"Basic {b64_auth}",
                }
            )
            try:
                with urllib.request.urlopen(req, timeout=self.timeout_seconds) as resp:
                    span.set_attribute("http.status_code", resp.status)
                    return resp.status in (200, 201)
            except urllib.error.URLError as e:
                span.record_exception(e)
                span.set_status(trace.StatusCode.ERROR, str(e))
                logger.error("Failed to send Twilio SMS: %s", e)
                return False
