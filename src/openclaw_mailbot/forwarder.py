"""OpenClaw webhook forwarder."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Protocol


class WebhookForwarder(Protocol):
    """Protocol for a webhook forwarder implementation."""

    def send(self, payload: dict) -> "ForwardResult":
        """Send *payload* to the configured webhook.

        Returns a ``ForwardResult`` indicating success or failure.
        """
        ...


@dataclass(frozen=True)
class ForwardResult:
    """Result of a webhook delivery attempt."""

    ok: bool
    status_code: int | None = None
    error: str | None = None


class UrllibWebhookForwarder:
    """Forwarder that POSTs JSON via :mod:`urllib`."""

    def __init__(self, webhook_url: str, timeout_seconds: float = 30.0) -> None:
        self._webhook_url = webhook_url
        self._timeout_seconds = timeout_seconds

    def send(self, payload: dict) -> ForwardResult:
        """POST *payload* as JSON to the webhook URL."""
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        request = urllib.request.Request(
            self._webhook_url,
            data=body,
            headers={
                "Content-Type": "application/json; charset=utf-8",
                "Accept": "application/json",
                "User-Agent": "openclaw-mailbot/0.1.0",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(
                request, timeout=self._timeout_seconds
            ) as response:
                status = response.getcode()
                if 200 <= status < 300:
                    return ForwardResult(ok=True, status_code=status)
                return ForwardResult(
                    ok=False, status_code=status, error=f"HTTP {status}"
                )
        except urllib.error.HTTPError as exc:
            return ForwardResult(
                ok=False, status_code=exc.code, error=f"HTTP {exc.code}"
            )
        except Exception as exc:
            return ForwardResult(ok=False, error=str(exc))


class RecordingWebhookForwarder:
    """Forwarder that records payloads without making network calls."""

    def __init__(self) -> None:
        self.payloads: list[dict] = []
        self.results: list[ForwardResult] = []

    def set_results(self, results: list[ForwardResult]) -> None:
        """Configure the results to return for successive calls."""
        self.results = list(results)
        self.payloads = []

    def send(self, payload: dict) -> ForwardResult:
        self.payloads.append(payload)
        if self.results:
            return self.results.pop(0)
        return ForwardResult(ok=True)
