"""Persistent state between cron runs, used to decide when to alert."""

import json
import logging
from dataclasses import asdict, dataclass
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class RunState:
    consecutive_failures: int = 0
    first_failure_at: str | None = None
    last_alert_at: str | None = None
    last_error: str | None = None
    last_success_at: str | None = None

    @classmethod
    def load(cls, path: Path) -> "RunState":
        try:
            return cls(**json.loads(path.read_text()))
        except FileNotFoundError:
            return cls()
        except (OSError, ValueError, TypeError) as e:
            logger.warning("Ignoring unreadable state file %s: %s", path, e)
            return cls()

    def save(self, path: Path) -> None:
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(asdict(self), indent=2))
        tmp.replace(path)
