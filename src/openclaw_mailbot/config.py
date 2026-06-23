"""Configuration loading for the OpenClaw mailbot."""

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
        """Load configuration from an INI file, a ``.env`` file, and environment variables.

        Environment variables take precedence over ``.env`` values, which take
        precedence over the INI file.

        The POP3 password is intentionally read from ``POP3_PASSWORD`` and is
        not part of the returned object.

        ``MAILBOT_DATA_DIR`` overrides any data_dir value from the INI file.
        """
        _load_dotenv()

        parser = ConfigParser()
        if path:
            parser.read(path, encoding="utf-8")

        data_dir = os.environ.get("MAILBOT_DATA_DIR")
        if not data_dir:
            data_dir = parser.get("storage", "data_dir", fallback="./mailbot-data")

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


def _load_dotenv(dotenv_path: Path | str | None = ".env") -> None:
    """Load KEY=VALUE pairs from a ``.env`` file into ``os.environ``.

    Already-set environment variables are not overwritten. Lines starting with
    ``#`` and blank lines are ignored. Values may be quoted with single or
    double quotes; surrounding whitespace is stripped.
    """
    if dotenv_path is None:
        return

    path = Path(dotenv_path)
    if not path.is_file():
        return

    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if "=" not in stripped:
            continue
        key, _, value = stripped.partition("=")
        key = key.strip()
        if not key or key in os.environ:
            continue
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in ('"', "'"):
            value = value[1:-1]
        os.environ[key] = value
