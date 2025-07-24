"""Email notification functionality."""

import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any


class EmailNotifier:
    """Handles email notifications for DNS update events."""

    def __init__(self, smtp_config: dict[str, Any]):
        self.smtp_config = smtp_config
        self.logger = logging.getLogger(__name__)

    def send_email(self, subject: str, body: str) -> None:
        """Send email notification"""
        try:
            msg = MIMEMultipart()
            msg["From"] = self.smtp_config["user"]
            msg["To"] = ", ".join(self.smtp_config["to"])
            msg["Subject"] = subject

            msg.attach(MIMEText(body, "plain"))

            server = smtplib.SMTP_SSL(
                self.smtp_config["server"], self.smtp_config["ssl_port"]
            )
            server.login(self.smtp_config["user"], self.smtp_config["password"])
            server.send_message(msg)
            server.quit()

            self.logger.info("Email notification sent: %s", subject)
        except Exception as e:
            self.logger.error("Failed to send email notification: %s", e)

    def send_success_notification(
        self, zone_name: str, changed_domains: list[str], elapsed_seconds: int
    ) -> None:
        """Send success notification when DNS updates complete successfully."""
        subject = f"DNS Update Success - {zone_name}"
        body = f"DNS records updated successfully for {zone_name}:\n\n"
        body += "\n".join(changed_domains)
        body += f"\n\nPropagation completed in {elapsed_seconds} seconds."

        self.send_email(subject, body)

    def send_timeout_notification(
        self, zone_name: str, changed_domains: list[str], elapsed_seconds: int
    ) -> None:
        """Send notification when DNS propagation times out."""
        subject = f"DNS Update Timeout - {zone_name}"
        body = f"DNS records were updated but propagation timed out after {elapsed_seconds} seconds for {zone_name}:\n\n"
        body += "\n".join(changed_domains)
        body += "\n\nPlease check DNS propagation manually."

        self.send_email(subject, body)

    def send_error_notification(self, zone_name: str, error_message: str) -> None:
        """Send notification when an error occurs during DNS update process."""
        subject = f"DNS Update Error - {zone_name}"
        body = f"An error occurred during DNS update process for {zone_name}:\n\n{error_message}"

        self.send_email(subject, body)
