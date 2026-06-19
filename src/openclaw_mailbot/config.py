"""Configuration loading for the mailbot."""

from __future__ import annotations

import os
from configparser import ConfigParser
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Config:
    """Mailbot configuration."""

    data_dir: Path
    pop3_host: str = ""
    pop3_port: int = 995
    pop3_username: str = ""
    pop3_use_ssl: bool = True
    webhook_url: str = ""
    webhook_timeout_seconds: float = 30.0

    @classmethod
    def load(cls, path: Path | str | None = None) -> "Config":
        """Load configuration from an INI file and environment variables.

        The POP3 password is intentionally read from the ``POP3_PASSWORD``
        environment variable and is not part of the returned object.

        ``MAILBOT_DATA_DIR`` overrides any data_dir value from the INI file.
        """
        parser = ConfigParser()
        if path:
            parser.read(path, encoding="utf-8")

        data_dir = os.environ.get("MAILBOT_DATA_DIR")
        if not data_dir:
            data_dir = parser.get("storage", "data_dir", fallback=None)
        if not data_dir:
            data_dir = parser.get("mailbot", "data_dir", fallback="./mailbot-data")

        return cls(
            data_dir=Path(data_dir).expanduser().resolve(),
            pop3_host=parser.get("pop3", "host", fallback=""),
            pop3_port=parser.getint("pop3", "port", fallback=995),
            pop3_username=parser.get("pop3", "username", fallback=""),
            pop3_use_ssl=parser.getboolean("pop3", "use_ssl", fallback=True),
            webhook_url=parser.get("openclaw", "webhook_url", fallback=""),
            webhook_timeout_seconds=parser.getfloat(
                "openclaw", "timeout_seconds", fallback=30.0
            ),
        )

    @property
    def pop3_password(self) -> str:
        """Return the POP3 password from the environment."""
        return os.environ.get("POP3_PASSWORD", "")
