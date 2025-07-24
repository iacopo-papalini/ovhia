# OVHIA - Dynamic DNS Updater

This is a Python tool that automatically updates OVH DNS records to point to your current public IP address. It's designed to run as a cron job for home network dynamic DNS management.

## Project Structure
- **Language**: Python 3.13.5
- **Package Manager**: uv
- **Configuration**: pyproject.toml + conf.toml
- **Main Module**: `src/net/iap/ovhia/__main__.py`

## Setup & Dependencies

### Installation
```bash
# Install dependencies using uv
uv sync
```

### Configuration
1. Copy `conf.toml.example` to `conf.toml` (if example exists)
2. Configure your OVH API credentials:
   ```toml
   [ovh]
   endpoint="ovh-eu"
   application_key="your_key"
   application_secret="your_secret"  
   consumer_key="your_consumer_key"

   [dns]
   zoneName="your_domain.com"
   subdomains=["subdomain1", "subdomain2"]
   ttl=60
   ```

## Running the Project

### Development
```bash
# Run with uv (recommended)
uv run ovhia

# Or run directly with Python
python -m net.iap.ovhia
```

### Production (Cron Job)
Add to crontab for periodic execution:
```bash
# Check and update DNS every 5 minutes
*/5 * * * * cd /path/to/ovhia && uv run ovhia
```

## Code Quality & Standards

### Linting & Formatting
- **Tool**: ruff (configured for pre-commit hooks)
- **Python Version Target**: 3.13
- **Rules**: UP (pyupgrade), I (isort), F (pyflakes), E (pycodestyle), T, G, PIE
- **Ignored**: E501 (line length), UP046

### Pre-commit Setup
```bash
# Install pre-commit
pip install pre-commit

# Install hooks
pre-commit install

# Run manually
pre-commit run --all-files
```

### Pre-commit Configuration
```yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.12.3
    hooks:
      - id: ruff
        args:
          - --select
          - UP,I,F,E,T,G,PIE
          - --ignore
          - E501,UP046
          - --fix
          - --target-version=py313
        stages: [pre-commit]
        files: ^src/
      - id: ruff-format
        stages: [pre-commit]
        files: ^(src|test)/
```

### Logging Standards
- **No f-strings in logging**: Use `%` formatting or logger parameters instead
  ```python
  # ❌ Incorrect  
  logger.info(f"Processing {item_count} items")
  
  # ✅ Correct
  logger.info("Processing %d items", item_count)
  logger.info("Processing %s items", item_count)
  ```

### Exception Handling
- Avoid catching generic 'Exception'
- Use specific exception types when possible

## Testing
Currently no testing framework is configured. Tests may be added in the future using pytest.

## Modernization Goals
- [x] Migrate from requirements.txt to pyproject.toml
- [x] Use uv for dependency management
- [x] Update to Python 3.13.5
- [x] Add console script entry point (`uv run ovhia`)
- [x] Implement ruff with pre-commit hooks
- [ ] Add proper logging instead of print statements
- [ ] Add tests (pytest framework when implemented)

## Security Notes
- Keep `conf.toml` out of version control (contains API credentials)
- OVH API credentials should be properly secured
- This tool only performs defensive DNS updates for your own domains