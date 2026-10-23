import logging
import smtplib
from email.message import EmailMessage
from opentelemetry import trace

logger = logging.getLogger(__name__)
tracer = trace.get_tracer("alert-engine")

class EmailSmtpAdapter:
    def __init__(
        self,
        smtp_host: str,
        smtp_port: int,
        smtp_user: str,
        smtp_password: str,
        from_email: str,
        use_tls: bool = True,
        timeout_seconds: float = 10.0,
    ) -> None:
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.smtp_user = smtp_user
        self.smtp_password = smtp_password
        self.from_email = from_email
        self.use_tls = use_tls
        self.timeout_seconds = timeout_seconds

    def send_email(self, to_email: str, subject: str, content: str, is_html: bool = False) -> bool:
        if not self.smtp_host or not self.from_email:
            logger.warning("SMTP host or from_email not configured.")
            return False

        with tracer.start_as_current_span(
            "email_smtp_adapter.send_email",
            attributes={"email.to": to_email, "email.subject": subject}
        ) as span:
            msg = EmailMessage()
            msg["Subject"] = subject
            msg["From"] = self.from_email
            msg["To"] = to_email
            if is_html:
                msg.set_content(content, subtype="html")
            else:
                msg.set_content(content)

            try:
                with smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=self.timeout_seconds) as server:
                    if self.use_tls:
                        server.starttls()
                    if self.smtp_user and self.smtp_password:
                        server.login(self.smtp_user, self.smtp_password)
                    server.send_message(msg)
                    return True
            except Exception as e:
                span.record_exception(e)
                span.set_status(trace.StatusCode.ERROR, str(e))
                logger.error("Failed to send SMTP email to %s: %s", to_email, e)
                return False
