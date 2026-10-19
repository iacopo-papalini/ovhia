"""DNS management functionality."""

import logging
import time

import dns.exception
import dns.resolver

DEFAULT_NAMESERVERS = ["8.8.8.8", "1.1.1.1", "9.9.9.9"]


class DNSManager:
    """Handles DNS operations including resolution and propagation verification."""

    def __init__(self, nameservers: list[str] | None = None):
        self.nameservers = nameservers or DEFAULT_NAMESERVERS
        self.logger = logging.getLogger(__name__)

    def resolve_domain_ip(self, domain_name: str) -> str:
        """Resolve domain to IP address, falling back across public nameservers."""
        resolver = dns.resolver.Resolver(configure=False)
        resolver.nameservers = self.nameservers
        resolver.lifetime = 15

        try:
            answers = resolver.resolve(domain_name, "A")
            return str(answers[0])
        except dns.exception.DNSException as e:
            raise RuntimeError(f"DNS query failed for {domain_name}: {e}")

    def verify_propagation(
        self, domains: list[str], expected_ip: str, timeout: int = 300
    ) -> tuple[bool, int]:
        """
        Verify DNS propagation for multiple domains.

        Args:
            domains: List of domain names to check
            expected_ip: The IP address all domains should resolve to
            timeout: Maximum time to wait in seconds

        Returns:
            Tuple of (success, elapsed_seconds)
        """
        self.logger.info("Waiting for DNS propagation (up to %d seconds)...", timeout)
        start_time = time.time()

        while time.time() - start_time < timeout:
            all_propagated = True

            for domain_name in domains:
                try:
                    dns_ip = self.resolve_domain_ip(domain_name)
                    if dns_ip != expected_ip:
                        all_propagated = False
                        break
                except RuntimeError:
                    all_propagated = False
                    break

            if all_propagated:
                elapsed = int(time.time() - start_time)
                self.logger.info(
                    "DNS propagation completed successfully after %d seconds", elapsed
                )
                return True, elapsed

            time.sleep(10)  # Check every 10 seconds

        # Timeout reached
        elapsed = int(time.time() - start_time)
        self.logger.error("DNS propagation failed - timeout after %d seconds", elapsed)
        return False, elapsed

    def check_domains(
        self, domains: list[str], current_ip: str
    ) -> tuple[list[str], list[str], list[str]]:
        """
        Check which domains need updating.

        Args:
            domains: List of domain names to check
            current_ip: Current public IP address

        Returns:
            Tuple of (domains_to_update, domain_changes, unresolved) where
            domain_changes contains formatted strings showing the IP changes and
            unresolved contains the errors for domains that could not be checked
        """
        domains_to_update = []
        domain_changes = []
        unresolved = []

        for domain_name in domains:
            try:
                dns_ip = self.resolve_domain_ip(domain_name)
                if dns_ip != current_ip:
                    domains_to_update.append(domain_name)
                    domain_changes.append(f"{domain_name}: {dns_ip} -> {current_ip}")
                    self.logger.info(
                        "%s: DNS shows %s != current IP %s; needs updating",
                        domain_name,
                        dns_ip,
                        current_ip,
                    )
                else:
                    self.logger.info(
                        "%s: DNS correctly points to %s", domain_name, current_ip
                    )

            except RuntimeError as e:
                self.logger.error("%s: %s", domain_name, e)
                unresolved.append(str(e))

        return domains_to_update, domain_changes, unresolved
