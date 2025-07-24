"""OVH DNS updater main orchestration class."""

import logging
import tomllib
from typing import Any

import ovh
import whatismyip as whatismyip

from .dns_manager import DNSManager
from .email_notifier import EmailNotifier


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

    def run(self) -> None:
        """Main execution method."""
        try:
            current_ip = whatismyip.whatismyipv4()
            domain_names = self._get_domain_names()

            # Check which domains need updating
            domains_to_update, domain_changes = self.dns_manager.check_domains(
                domain_names, current_ip
            )

            if not domains_to_update:
                self.logger.info("All DNS records are up to date")
                return

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

            if propagation_success:
                self.email_notifier.send_success_notification(
                    self.zone_name, domain_changes, elapsed_seconds
                )
            else:
                self.email_notifier.send_timeout_notification(
                    self.zone_name, domain_changes, elapsed_seconds
                )
                raise RuntimeError(
                    "DNS propagation timeout - changes may not be fully propagated"
                )

        except Exception as e:
            self.email_notifier.send_error_notification(self.zone_name, str(e))
            raise
