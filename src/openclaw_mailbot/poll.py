"""Polling loop that bridges POP3 to the OpenClaw webhook."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

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

    try:
        uidl_map = pop3_client.uidl()
    except Exception:
        logger.exception("Failed to list messages from POP3 server")
        return results

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
                data_dir=config.data_dir,
                uidl=uidl,
                run_timestamp=run_timestamp,
            )
        except Exception:
            logger.exception("Failed to parse message %d (uidl=%s)", msg_num, uidl)
            break

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
