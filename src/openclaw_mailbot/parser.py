"""RFC 2822 email parsing and attachment extraction."""

from __future__ import annotations

import html
import json
import re
from datetime import datetime, timezone
from email import message_from_binary_file, policy
from email.message import Message
from email.utils import parseaddr, parsedate_to_datetime
from pathlib import Path
from typing import BinaryIO


class EmailParseError(ValueError):
    """Raised when an email cannot be parsed."""


def _clean_address(raw: str) -> dict[str, str]:
    """Return {name, address} for a raw RFC 2822 address header."""
    name, address = parseaddr(raw)
    return {"name": name or "", "address": address or ""}


def _clean_address_list(raw: str | None) -> list[dict[str, str]]:
    """Return a list of {name, address} objects from a comma-separated header."""
    if not raw:
        return []
    parts = [p.strip() for p in raw.split(",") if p.strip()]
    return [_clean_address(part) for part in parts]


def _parse_date(raw: str | None) -> str | None:
    """Convert an RFC 2822 date string to ISO 8601 UTC, or None."""
    if not raw:
        return None
    try:
        dt = parsedate_to_datetime(raw)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    except Exception:
        return None


def _is_attachment(part: Message) -> bool:
    """Heuristic: is this part an attachment rather than a body part?"""
    content_type = part.get_content_type()
    content_disposition = part.get_content_disposition() or ""
    if "attachment" in content_disposition:
        return True
    if content_type in {"text/plain", "text/html", "multipart/alternative", "multipart/mixed", "multipart/related"}:
        return False
    return True


def _sanitized_filename(raw: str | None) -> str:
    """Return a safe filename, generating one if missing."""
    if raw:
        # Replace path separators and null bytes; keep basename only.
        name = Path(raw).name
        name = name.replace("\x00", "")
        if name:
            return name
    return "unnamed-attachment"


def _identifier(message: Message, uidl: str = "") -> str:
    """Return a stable identifier for the message."""
    if uidl:
        return re.sub(r"[^\w@.+-]+", "_", uidl).strip("._")
    message_id = message.get("Message-Id", "")
    if message_id:
        return re.sub(r"[^\w@.+-]+", "_", message_id.strip("<>")).strip("._")
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-%f")
    return f"no-message-id-{timestamp}"


def _sanitize_text(text: str) -> str:
    """Decode HTML character references to their Unicode codepoints."""
    return html.unescape(text)


def _extract_bodies(message: Message) -> tuple[str | None, str | None]:
    """Return (html, plain_text) extracted from the message."""
    html: str | None = None
    plain: str | None = None

    if message.is_multipart():
        for part in message.walk():
            if part.is_multipart():
                continue
            content_type = part.get_content_type()
            try:
                payload = part.get_payload(decode=True)
                if payload is None:
                    continue
                charset = part.get_content_charset() or "utf-8"
                text = payload.decode(charset, errors="replace")
            except Exception:
                continue
            if content_type == "text/html" and html is None:
                html = text
            elif content_type == "text/plain" and plain is None:
                plain = text
    else:
        content_type = message.get_content_type()
        try:
            payload = message.get_payload(decode=True)
            if payload is not None:
                charset = message.get_content_charset() or "utf-8"
                text = payload.decode(charset, errors="replace")
                if content_type == "text/html":
                    html = text
                elif content_type == "text/plain":
                    plain = text
        except Exception:
            pass

    return html, plain


def _extract_attachments(
    message: Message,
    attachments_dir: Path,
) -> list[dict[str, str | int]]:
    """Save attachments to disk and return metadata."""
    attachments: list[dict[str, str | int]] = []

    if not message.is_multipart():
        return attachments

    for part in message.walk():
        if part.is_multipart() or not _is_attachment(part):
            continue

        filename = _sanitized_filename(part.get_filename())
        content_type = part.get_content_type()
        payload = part.get_payload(decode=True)
        if payload is None:
            continue

        attachment_path = attachments_dir / filename
        attachment_path.parent.mkdir(parents=True, exist_ok=True)
        attachment_path.write_bytes(payload)

        attachments.append(
            {
                "filename": filename,
                "path": str(attachment_path),
                "contentType": content_type,
                "sizeBytes": len(payload),
            }
        )

    return attachments


def parse_email(
    source: BinaryIO | Path | str | bytes,
    data_dir: Path,
    run_timestamp: str | None = None,
    uidl: str = "",
) -> dict:
    """Parse an email and return the OpenClaw payload dict.

    Args:
        source: A file-like object opened in binary mode, bytes, or a path.
        data_dir: Base directory for saving attachments.
        run_timestamp: Timestamp directory for this run (defaults to now).
        uidl: The POP3 UIDL for this message (used as directory identifier).
    """
    if run_timestamp is None:
        run_timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")

    if isinstance(source, bytes):
        from io import BytesIO
        message = message_from_binary_file(BytesIO(source), policy=policy.default)
    elif isinstance(source, (str, Path)):
        with Path(source).open("rb") as fh:
            message = message_from_binary_file(fh, policy=policy.default)
    else:
        message = message_from_binary_file(source, policy=policy.default)

    if not isinstance(message, Message):
        raise EmailParseError("Parsed message is not a Message instance")

    html, plain = _extract_bodies(message)
    if html is not None:
        html = _sanitize_text(html)
    if plain is not None:
        plain = _sanitize_text(plain)
    identifier = _identifier(message, uidl)
    attachments_dir = data_dir / "attachments" / run_timestamp / identifier
    attachments = _extract_attachments(message, attachments_dir)

    result: dict[str, object] = {
        "event": "email.received",
        "messageId": message.get("Message-Id", ""),
        "uidl": uidl or identifier,
        "receivedAt": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "from": _clean_address(message.get("From", "")),
        "to": _clean_address_list(message.get("To", "")),
        "cc": _clean_address_list(message.get("Cc", "")),
        "subject": message.get("Subject", ""),
        "date": _parse_date(message.get("Date")),
    }

    if plain is not None:
        result["plainText"] = plain
    if html is not None:
        result["html"] = html

    result["attachments"] = attachments

    return result


def parse_email_json(
    source: BinaryIO | Path | str | bytes,
    data_dir: Path,
    run_timestamp: str | None = None,
    uidl: str = "",
) -> str:
    """Parse an email and return the payload as JSON."""
    payload = parse_email(source, data_dir, run_timestamp, uidl)
    return json.dumps(payload, indent=2, ensure_ascii=False)
