"""Polling loop that bridges POP3 to the OpenClaw webhook."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Callable, Iterator

from pathlib import Path

from .config import Config
from .forwarder import ForwardResult, UrllibWebhookForwarder
from .parser import parse_email
from .pop3 import Pop3Client, Pop3LibClient
from .state import StateStore

logger = logging.getLogger(__name__)


def create_pop3_client(config: Config) -> Pop3Client:
    """Create a production POP3 client from configuration."""
    return Pop3LibClient(
        host=config.pop3_host,
        port=config.pop3_port,
        username=config.pop3_username,
        password=config.pop3_password,
        use_ssl=config.pop3_use_ssl,
    )


def create_forwarder(config: Config) -> UrllibWebhookForwarder:
    """Create a production webhook forwarder from configuration."""
    return UrllibWebhookForwarder(
        webhook_url=config.webhook_url,
        timeout_seconds=config.webhook_timeout_seconds,
    )


def _iter_messages(
    pop3_client: Pop3Client,
    state_store: StateStore,
    data_dir: Path,
    run_timestamp: str,
) -> Iterator[tuple[int, str, dict]]:
    """Fetch and parse new messages, yielding (msg_num, uidl, payload)."""
    try:
        uidl_map = pop3_client.uidl()
    except Exception:
        logger.exception("Failed to list messages from POP3 server")
        return

    for msg_num in sorted(uidl_map):
        uidl = uidl_map[msg_num]
        if state_store.is_processed(uidl):
            continue

        try:
            raw = pop3_client.retr(msg_num)
        except Exception:
            logger.exception("Failed to fetch message %d (uidl=%s)", msg_num, uidl)
            break

        try:
            payload = parse_email(
                source=raw,
                data_dir=data_dir,
                uidl=uidl,
                run_timestamp=run_timestamp,
            )
        except Exception:
            logger.exception("Failed to parse message %d (uidl=%s)", msg_num, uidl)
            break

        yield msg_num, uidl, payload


def parse_only(
    config: Config,
    state_store: StateStore,
    pop3_client: Pop3Client,
    output: Callable[[str], None] | None = None,
    run_timestamp: str | None = None,
) -> list[dict]:
    """Poll the POP3 mailbox, parse messages, and print payloads without forwarding.

    Useful for testing mail server connectivity and parser output before enabling
    the real webhook. Messages are marked as processed so they are not re-fetched
    on the next run.
    """
    if run_timestamp is None:
        run_timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")

    state_store.load()
    payloads: list[dict] = []
    emit = output if output is not None else print

    for msg_num, uidl, payload in _iter_messages(
        pop3_client, state_store, config.data_dir, run_timestamp
    ):
        payloads.append(payload)
        emit(json.dumps(payload, indent=2, ensure_ascii=False))
        state_store.mark_processed(uidl)
        logger.info("Parsed message %d (uidl=%s)", msg_num, uidl)

    try:
        pop3_client.quit()
    except Exception:
        logger.exception("Error closing POP3 connection")

    return payloads


def poll(
    config: Config,
    state_store: StateStore,
    pop3_client: Pop3Client,
    forwarder: UrllibWebhookForwarder,
    run_timestamp: str | None = None,
) -> list[ForwardResult]:
    """Poll the POP3 mailbox and forward new messages.

    Messages are processed in POP3 message-number order. After each successful
    webhook delivery the UIDL is marked as processed. If a delivery fails, the
    loop stops so the unprocessed message (and any later messages) are retried
    on the next poll.

    Returns the list of forward results, one per delivery attempt.
    """
    if run_timestamp is None:
        run_timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")

    state_store.load()
    results: list[ForwardResult] = []

    for msg_num, uidl, payload in _iter_messages(
        pop3_client, state_store, config.data_dir, run_timestamp
    ):
        result = forwarder.send(payload)
        results.append(result)

        if result.ok:
            state_store.mark_processed(uidl)
            logger.info("Forwarded message %d (uidl=%s)", msg_num, uidl)
        else:
            logger.warning(
                "Webhook failed for message %d (uidl=%s): %s",
                msg_num,
                uidl,
                result.error or f"HTTP {result.status_code}",
            )
            break

    try:
        pop3_client.quit()
    except Exception:
        logger.exception("Error closing POP3 connection")

    return results
