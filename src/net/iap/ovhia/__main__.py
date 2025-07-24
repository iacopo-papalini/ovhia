"""Main entry point for OVHIA DNS updater."""

import logging

from .ovh_updater import OVHDNSUpdater


def main():
    """Main function to run the DNS updater."""
    # Configure logging
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
    )

    # Create and run the updater
    updater = OVHDNSUpdater()
    updater.run()


if __name__ == "__main__":
    main()
