"""UIDL state store for the mailbot."""

from __future__ import annotations

from pathlib import Path


class StateStore:
    """Persists the set of processed POP3 UIDLs.

    The store keeps a plain-text file at ``<data_dir>/state/uidl.db`` with one
    processed UIDL per line. Advancing state means adding a UIDL to the set; a
    failed message is simply not added so it is retried on the next poll.
    """

    def __init__(self, data_dir: Path) -> None:
        self._data_dir = data_dir
        self._path = data_dir / "state" / "uidl.db"
        self._processed: set[str] = set()

    def load(self) -> None:
        """Load processed UIDLs from disk."""
        if not self._path.exists():
            self._processed = set()
            return
        try:
            text = self._path.read_text(encoding="utf-8")
        except FileNotFoundError:
            self._processed = set()
            return
        self._processed = {line.strip() for line in text.splitlines() if line.strip()}

    def is_processed(self, uidl: str) -> bool:
        """Return whether the given UIDL has already been processed."""
        return uidl in self._processed

    def mark_processed(self, uidl: str) -> None:
        """Mark a UIDL as processed and persist the change."""
        if uidl in self._processed:
            return
        self._processed.add(uidl)
        self._persist()

    def last_processed(self) -> str | None:
        """Return the most recently processed UIDL, or None."""
        if not self._processed:
            return None
        return max(self._processed)

    def _persist(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        lines = sorted(self._processed)
        self._path.write_text("\n".join(lines) + "\n", encoding="utf-8")
