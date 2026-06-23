"""Raw email archival and recovery helpers."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import BinaryIO

logger = logging.getLogger(__name__)


def archive_dir(data_dir: Path) -> Path:
    """Return the directory where raw ``.eml`` files are archived."""
    return data_dir / "archive"


def archive_path(data_dir: Path, uidl: str) -> Path:
    """Return the filesystem path for a given UIDL archive file."""
    # UIDLs can contain characters unsafe for filenames; sanitize aggressively.
    safe_uidl = "".join(c if c.isalnum() or c in "-_@.+" else "_" for c in uidl)
    return archive_dir(data_dir) / f"{safe_uidl}.eml"


def save_raw_email(data_dir: Path, uidl: str, raw: bytes) -> Path:
    """Persist raw message bytes to ``<data_dir>/archive/<uidl>.eml``.

    Overwrites any existing file with the same UIDL so replays always use the
    latest captured source.
    """
    path = archive_path(data_dir, uidl)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(raw)
    logger.debug("Archived raw email to %s", path)
    return path


def iter_archived_emls(data_dir: Path) -> list[tuple[str, Path]]:
    """Return all archived ``(uidl, path)`` pairs, sorted by filename."""
    directory = archive_dir(data_dir)
    if not directory.exists():
        return []
    items: list[tuple[str, Path]] = []
    for path in directory.iterdir():
        if path.is_file() and path.suffix.lower() == ".eml":
            uidl = path.stem
            items.append((uidl, path))
    items.sort(key=lambda item: item[1].name)
    return items
