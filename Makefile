.PHONY: help install setup cron clean

# Default target
help:
	@echo "Available targets:"
	@echo "  install  - Install uv if not present"
	@echo "  setup    - Install dependencies and set up the project"
	@echo "  cron     - Install cronjob (runs every 5 minutes)"
	@echo "  clean    - Remove virtual environment"

# Install uv if not already installed
install:
	@if ! command -v uv &> /dev/null; then \
		echo "Installing uv..."; \
		curl -LsSf https://astral.sh/uv/install.sh | sh; \
		echo "Please restart your shell or run: source ~/.bashrc"; \
	else \
		echo "uv is already installed"; \
	fi

# Set up the project
setup: install
	@echo "Setting up project dependencies..."
	uv sync
	@echo "Installing package in editable mode..."
	uv pip install -e .
	@echo "Project setup complete!"

# Install cronjob if not already present
cron:
	@PROJECT_DIR=$$(pwd); \
	CRON_LINE="*/5 * * * * cd $$PROJECT_DIR && uv run ovhia >> /var/log/ovhia.$$(date +\%Y-\%m-\%d).log 2>&1"; \
	CLEANUP_LINE="0 0 * * * find /var/log -name 'ovhia.*.log' -mtime +30 -delete"; \
	if ! crontab -l 2>/dev/null | grep -q "uv run ovhia"; then \
		echo "Installing cronjob..."; \
		(crontab -l 2>/dev/null; echo "$$CRON_LINE"; echo "$$CLEANUP_LINE") | crontab -; \
		echo "Cronjob installed: $$CRON_LINE"; \
		echo "Log cleanup installed: $$CLEANUP_LINE"; \
	else \
		echo "Cronjob already exists"; \
	fi

# Clean up
clean:
	@echo "Removing .venv directory..."
	@rm -rf .venv
	@echo "Clean complete!"