"""Email notification functionality."""

import logging
import smtplib
import socket
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any


class EmailNotifier:
    """Handles email notifications for DNS update events."""

    def __init__(self, smtp_config: dict[str, Any]):
        self.smtp_config = smtp_config
        self.logger = logging.getLogger(__name__)
        self.host = socket.gethostname()

    def send_email(self, subject: str, body: str) -> bool:
        """Send email notification. Returns whether it was sent."""
        try:
            msg = MIMEMultipart()
            msg["From"] = self.smtp_config["user"]
            msg["To"] = ", ".join(self.smtp_config["to"])
            msg["Subject"] = f"[ovhia@{self.host}] {subject}"

            msg.attach(MIMEText(body, "plain"))

            with smtplib.SMTP_SSL(
                self.smtp_config["server"], self.smtp_config["ssl_port"], timeout=30
            ) as server:
                server.login(self.smtp_config["user"], self.smtp_config["password"])
                server.send_message(msg)

            self.logger.info("Email notification sent: %s", subject)
            return True
        except (OSError, smtplib.SMTPException) as e:
            self.logger.error("Failed to send email notification: %s", e)
            return False

    def send_success_notification(
        self, zone_name: str, changed_domains: list[str], elapsed_seconds: int
    ) -> bool:
        """Send success notification when DNS updates complete successfully."""
        subject = f"DNS updated - {zone_name}"
        body = f"DNS records updated successfully for {zone_name}:\n\n"
        body += "\n".join(changed_domains)
        body += f"\n\nPropagation completed in {elapsed_seconds} seconds."

        return self.send_email(subject, body)

    def send_failure_notification(
        self,
        zone_name: str,
        failures: int,
        since: str,
        error_details: str,
        reminder: bool,
    ) -> bool:
        """Send notification that the updater is failing (first alert or reminder)."""
        status = "STILL FAILING" if reminder else "FAILING"
        subject = f"{status} - DNS updater for {zone_name}"
        body = (
            f"The DNS updater for {zone_name} is failing.\n\n"
            f"Consecutive failed runs: {failures}\n"
            f"Failing since: {since}\n\n"
            "While this lasts, a change of public IP will NOT be propagated to DNS.\n"
            "You will get a RECOVERED email once a run succeeds.\n\n"
            f"Latest error:\n\n{error_details}"
        )

        return self.send_email(subject, body)

    def send_recovery_notification(
        self, zone_name: str, failures: int, since: str, current_ip: str
    ) -> bool:
        """Send notification that the updater works again after failing."""
        subject = f"RECOVERED - DNS updater for {zone_name}"
        body = (
            f"The DNS updater for {zone_name} is working again.\n\n"
            f"Failed runs: {failures}\n"
            f"Failing since: {since}\n"
            f"All records verified to point to {current_ip}.\n"
        )

        return self.send_email(subject, body)
