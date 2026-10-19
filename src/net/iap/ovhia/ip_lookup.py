"""Public IPv4 address lookup."""

import ipaddress
import logging
import urllib.request

# Plain-text "what is my IP" services, tried in order until one answers.
# Plain HTTPS on an ephemeral port: no fixed source port to collide with.
PROVIDERS = [
    "https://api.ipify.org",
    "https://ipv4.icanhazip.com",
    "https://v4.ident.me",
    "https://ifconfig.me/ip",
]

logger = logging.getLogger(__name__)


def get_public_ipv4(timeout: float = 5) -> str:
    """Return the public IPv4 address, trying each provider in turn."""
    errors = []
    for url in PROVIDERS:
        try:
            with urllib.request.urlopen(url, timeout=timeout) as response:
                text = response.read(64).decode().strip()
            return str(ipaddress.IPv4Address(text))
        except (OSError, ValueError) as e:
            logger.warning("Public IP lookup via %s failed: %s", url, e)
            errors.append(f"{url}: {e}")

    raise RuntimeError("Could not determine public IP:\n  " + "\n  ".join(errors))
