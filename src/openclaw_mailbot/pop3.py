"""POP3 client wrapper for the mailbot."""

from __future__ import annotations

import poplib
from dataclasses import dataclass
from typing import Protocol


class Pop3Client(Protocol):
    """Protocol for a POP3 client implementation."""

    def uidl(self) -> dict[int, str]:
        """Return a mapping of message number to UIDL."""
        ...

    def retr(self, msg_num: int) -> bytes:
        """Fetch and return the raw message bytes for *msg_num*."""
        ...

    def quit(self) -> None:
        """Close the connection gracefully."""
        ...


@dataclass
class Pop3Config:
    host: str
    port: int
    username: str
    password: str
    use_ssl: bool = True


class Pop3LibClient:
    """Production POP3 client backed by :mod:`poplib`."""

    def __init__(self, config: Pop3Config) -> None:
        self._config = config
        self._client: poplib.POP3_SSL | poplib.POP3 | None = None

    def _connect(self) -> poplib.POP3_SSL | poplib.POP3:
        if self._config.use_ssl:
            client = poplib.POP3_SSL(self._config.host, self._config.port)
        else:
            client = poplib.POP3(self._config.host, self._config.port)
        client.user(self._config.username)
        client.pass_(self._config.password)
        return client

    def uidl(self) -> dict[int, str]:
        client = self._connect()
        self._client = client
        response, items, _ = client.uidl()
        result: dict[int, str] = {}
        for item in items:
            line = item.decode("utf-8", errors="replace")
            parts = line.split(None, 1)
            if len(parts) == 2:
                result[int(parts[0])] = parts[1]
        return result

    def retr(self, msg_num: int) -> bytes:
        client = self._client or self._connect()
        response, lines, octets = client.retr(msg_num)
        return b"\r\n".join(lines)

    def quit(self) -> None:
        if self._client is not None:
            try:
                self._client.quit()
            except Exception:
                pass
            self._client = None


class FakePop3Client:
    """In-memory POP3 client for tests and local development."""

    def __init__(self, messages: dict[int, tuple[str, bytes]]) -> None:
        self._messages = messages
        self._quitted = False

    def uidl(self) -> dict[int, str]:
        return {num: uidl for num, (uidl, _data) in self._messages.items()}

    def retr(self, msg_num: int) -> bytes:
        try:
            return self._messages[msg_num][1]
        except KeyError as exc:
            raise poplib.error_proto(f"message {msg_num} not found") from exc

    def quit(self) -> None:
        self._quitted = True
