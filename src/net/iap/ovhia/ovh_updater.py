"""OVH DNS updater main orchestration class."""

import logging
import tomllib
import traceback
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import ovh

from .dns_manager import DNSManager
from .email_notifier import EmailNotifier
from .ip_lookup import get_public_ipv4
from .run_state import RunState


class OVHDNSUpdater:
    """Main class that orchestrates the DNS update process."""

    def __init__(self, config_path: str = "./conf.toml"):
        self.config_path = config_path
        self.logger = logging.getLogger(__name__)

        # Initialize components
        self.dns_manager = DNSManager()
        self.config = self._load_config()
        self.ovh_client = ovh.Client(**self.config["ovh"])
        self.email_notifier = EmailNotifier(self.config["smtp"])

        # Configuration shortcuts
        self.zone_name = self.config["dns"]["zoneName"]
        self.subdomains = self.config["dns"]["subdomains"]
        self.ttl = self.config["dns"]["ttl"]

        notify = self.config.get("notify", {})
        self.reminder_interval = timedelta(hours=notify.get("reminder_hours", 2))
        self.state_path = Path(config_path).parent / notify.get(
            "state_file", "state.json"
        )

    def _load_config(self) -> dict[str, Any]:
        """Load configuration from TOML file."""
        with open(self.config_path, "rb") as conf_file:
            return tomllib.load(conf_file)

    def _get_domain_names(self) -> list[str]:
        """Get full domain names from subdomains."""
        return [f"{subdomain}.{self.zone_name}" for subdomain in self.subdomains]

    def _update_dns_record(self, subdomain: str, current_ip: str) -> None:
        """Update a single DNS record via OVH API."""
        params = {
            "zoneName": self.zone_name,
            "subdomain": subdomain,
            "ttl": self.ttl,
        }

        # Find the record ID
        result = self.ovh_client.get(
            "/domain/zone/{zoneName}/record?subDomain={subdomain}&fieldType=A".format(
                **params
            )
        )

        match len(result):
            case 0:
                raise RuntimeError(
                    "No zones found for {subdomain}.{zoneName}".format(**params)
                )
            case 1:
                zone_id = result[0]
            case _:
                raise RuntimeError(
                    "Too many zones found for {subdomain}.{zoneName}".format(**params)
                )

        # Update the record
        zone_url = "/domain/zone/{zoneName}/record/{zone_id}".format(
            **params, zone_id=zone_id
        )
        self.ovh_client.put(
            zone_url, target=current_ip, subDomain=subdomain, ttl=self.ttl
        )

        domain_name = f"{subdomain}.{self.zone_name}"
        self.logger.info("%s: Updated DNS record to %s", domain_name, current_ip)

    def _refresh_soa(self) -> None:
        """Refresh the SOA record to propagate changes."""
        self.logger.info("Refreshing SOA for %s", self.zone_name)
        self.ovh_client.post(f"/domain/zone/{self.zone_name}/refresh")

    def _update(self) -> str:
        """Bring DNS records in line with the public IP. Returns the public IP."""
        current_ip = get_public_ipv4()
        domain_names = self._get_domain_names()

        # Check which domains need updating
        domains_to_update, domain_changes, unresolved = self.dns_manager.check_domains(
            domain_names, current_ip
        )

        if domains_to_update:
            # Update DNS records
            for domain_name in domains_to_update:
                # Extract subdomain from full domain name
                subdomain = domain_name.replace(f".{self.zone_name}", "")
                self._update_dns_record(subdomain, current_ip)

            # Refresh SOA
            self._refresh_soa()

            # Verify propagation
            propagation_success, elapsed_seconds = self.dns_manager.verify_propagation(
                domain_names, current_ip, timeout=300
            )
            if not propagation_success:
                raise RuntimeError(
                    f"DNS records were updated but propagation timed out after {elapsed_seconds} seconds:\n  "
                    + "\n  ".join(domain_changes)
                )

            self.email_notifier.send_success_notification(
                self.zone_name, domain_changes, elapsed_seconds
            )

        if unresolved:
            # Never report "up to date" for records we could not actually check
            raise RuntimeError(
                "Could not verify DNS records:\n  " + "\n  ".join(unresolved)
            )

        if not domains_to_update:
            self.logger.info("All DNS records are up to date")
        return current_ip

    def run(self) -> None:
        """Main execution method: update DNS and alert on failure/recovery."""
        state = RunState.load(self.state_path)
        now = datetime.now(UTC)

        try:
            current_ip = self._update()
        except Exception as e:  # top-level boundary: any failure must be reported
            state.consecutive_failures += 1
            state.first_failure_at = state.first_failure_at or now.isoformat(
                timespec="seconds"
            )
            state.last_error = f"{type(e).__name__}: {e}"
            self.logger.error(
                "Run failed (%d consecutive): %s",
                state.consecutive_failures,
                state.last_error,
            )

            reminder = state.last_alert_at is not None
            due = not reminder or (
                now - datetime.fromisoformat(state.last_alert_at)
                >= self.reminder_interval
            )
            if due and self.email_notifier.send_failure_notification(
                self.zone_name,
                state.consecutive_failures,
                state.first_failure_at,
                traceback.format_exc(),
                reminder,
            ):
                state.last_alert_at = now.isoformat(timespec="seconds")

            state.save(self.state_path)
            raise

        if state.last_alert_at is not None:
            if not self.email_notifier.send_recovery_notification(
                self.zone_name,
                state.consecutive_failures,
                state.first_failure_at,
                current_ip,
            ):
                # Keep the failure state so the recovery email is retried next run
                return
        elif state.consecutive_failures:
            self.logger.info(
                "Recovered after %d failed runs (no alert had been sent)",
                state.consecutive_failures,
            )

        state = RunState(last_success_at=now.isoformat(timespec="seconds"))
        state.save(self.state_path)
