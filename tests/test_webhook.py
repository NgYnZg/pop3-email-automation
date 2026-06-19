"""Tests for the OpenClaw webhook forwarder and polling integration."""

from __future__ import annotations

import json
import threading
from email.message import EmailMessage
from email.utils import make_msgid
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any

import pytest

from openclaw_mailbot.config import Config
from openclaw_mailbot.forwarder import ForwardResult, UrllibWebhookForwarder
from openclaw_mailbot.poll import poll
from openclaw_mailbot.pop3 import FakePop3Client
from openclaw_mailbot.state import StateStore


class _WebhookHandler(BaseHTTPRequestHandler):
    """HTTP request handler that records webhook requests."""

    status_code: int = 200
    requests: list[dict[str, Any]] = []

    def do_POST(self) -> None:
        content_length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(content_length)
        self.requests.append(
            {
                "path": self.path,
                "headers": dict(self.headers.items()),
                "body": body,
            }
        )
        self.send_response(self.status_code)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(b'{"ok": true}')

    def log_message(self, format: str, *args: Any) -> None:
        pass


class _MockServer:
    def __init__(self, status_code: int = 200) -> None:
        self.status_code = status_code
        self.requests: list[dict[str, Any]] = []

    def __enter__(self) -> "_MockServer":
        _WebhookHandler.status_code = self.status_code
        _WebhookHandler.requests = self.requests
        self._server = HTTPServer(("127.0.0.1", 0), _WebhookHandler)
        self.port = self._server.server_address[1]
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()
        return self

    def __exit__(self, *exc: Any) -> None:
        self._server.shutdown()
        self._server.server_close()

    @property
    def url(self) -> str:
        return f"http://127.0.0.1:{self.port}/openclaw/webhook"


@pytest.fixture
def data_dir(tmp_path: Path) -> Path:
    return tmp_path


@pytest.fixture
def config(data_dir: Path) -> Config:
    return Config(
        data_dir=data_dir,
        pop3_host="pop.example.com",
        pop3_port=995,
        pop3_username="user@example.com",
        pop3_use_ssl=True,
        webhook_url="http://example.com/webhook",
        webhook_timeout_seconds=5.0,
    )


def _build_message(subject: str = "Test") -> bytes:
    msg = EmailMessage()
    msg["Message-Id"] = make_msgid(domain="sender.com")
    msg["From"] = "Sender Name <sender@example.com>"
    msg["To"] = "you@company.com"
    msg["Subject"] = subject
    msg["Date"] = "Wed, 18 Jun 2026 14:28:00 +0000"
    msg.set_content("Plain fallback")
    msg.add_alternative("<h1>Hello OpenClaw</h1>", subtype="html")
    return msg.as_bytes()


def _build_message_with_attachment(subject: str = "With attachment") -> bytes:
    from email.mime.application import MIMEApplication
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText

    msg = MIMEMultipart("mixed")
    msg["Message-Id"] = make_msgid(domain="sender.com")
    msg["From"] = "Sender Name <sender@example.com>"
    msg["To"] = "you@company.com"
    msg["Subject"] = subject
    msg["Date"] = "Wed, 18 Jun 2026 14:28:00 +0000"

    alt = MIMEMultipart("alternative")
    alt.attach(MIMEText("Plain fallback", "plain", "utf-8"))
    alt.attach(MIMEText("<h1>Hello OpenClaw</h1>", "html", "utf-8"))
    msg.attach(alt)

    att = MIMEApplication(b"PDF-content", _subtype="pdf")
    att.add_header("Content-Disposition", "attachment", filename="invoice.pdf")
    msg.attach(att)
    return msg.as_bytes()


def test_urllib_forwarder_posts_json_headers_and_body(config: Config) -> None:
    with _MockServer(status_code=200) as server:
        forwarder = UrllibWebhookForwarder(server.url, timeout_seconds=5.0)
        payload = {"event": "email.received", "uidl": "uidl-1"}
        result = forwarder.send(payload)

        assert result.ok is True
        assert result.status_code == 200
        assert len(server.requests) == 1

        request = server.requests[0]
        assert request["path"] == "/openclaw/webhook"
        headers = {k.lower(): v for k, v in request["headers"].items()}
        assert headers["content-type"] == "application/json; charset=utf-8"
        assert headers["accept"] == "application/json"
        assert "openclaw-mailbot" in headers["user-agent"]
        assert json.loads(request["body"]) == payload


def test_urllib_forwarder_returns_false_on_non_2xx(config: Config) -> None:
    with _MockServer(status_code=500) as server:
        forwarder = UrllibWebhookForwarder(server.url, timeout_seconds=5.0)
        result = forwarder.send({"event": "email.received"})

        assert result.ok is False
        assert result.status_code == 500
        assert len(server.requests) == 1


def test_poll_forwards_new_message_and_advances_state(config: Config, data_dir: Path) -> None:
    with _MockServer(status_code=200) as server:
        config = Config(
            data_dir=data_dir,
            pop3_host="pop.example.com",
            pop3_port=995,
            pop3_username="user@example.com",
            pop3_use_ssl=True,
            webhook_url=server.url,
            webhook_timeout_seconds=5.0,
        )
        raw = _build_message_with_attachment()
        pop3 = FakePop3Client({1: ("uidl-1", raw)})
        state = StateStore(data_dir)
        forwarder = UrllibWebhookForwarder(server.url, timeout_seconds=5.0)

        results = poll(config, state, pop3, forwarder, run_timestamp="20260618-143000")

        assert len(results) == 1
        assert results[0].ok is True
        assert state.is_processed("uidl-1")

        assert len(server.requests) == 1
        payload = json.loads(server.requests[0]["body"])
        assert payload["event"] == "email.received"
        assert payload["uidl"] == "uidl-1"
        assert payload["html"] == "<h1>Hello OpenClaw</h1>"
        assert payload["plainText"] == "Plain fallback"
        assert payload["from"] == {"name": "Sender Name", "address": "sender@example.com"}
        assert payload["to"] == [{"name": "", "address": "you@company.com"}]
        assert len(payload["attachments"]) == 1
        attachment = payload["attachments"][0]
        assert attachment["filename"] == "invoice.pdf"
        assert attachment["contentType"] == "application/pdf"
        assert attachment["sizeBytes"] == len(b"PDF-content")
        assert Path(attachment["path"]).exists()


def test_poll_retry_on_webhook_failure(data_dir: Path) -> None:
    with _MockServer(status_code=500) as server:
        config = Config(
            data_dir=data_dir,
            pop3_host="pop.example.com",
            pop3_port=995,
            pop3_username="user@example.com",
            pop3_use_ssl=True,
            webhook_url=server.url,
            webhook_timeout_seconds=5.0,
        )
        raw = _build_message()
        pop3 = FakePop3Client({1: ("uidl-1", raw)})
        state = StateStore(data_dir)
        forwarder = UrllibWebhookForwarder(server.url, timeout_seconds=5.0)

        results = poll(config, state, pop3, forwarder)

        assert len(results) == 1
        assert results[0].ok is False
        assert not state.is_processed("uidl-1")


def test_poll_stops_after_failure_and_later_messages_retry(data_dir: Path) -> None:
    with _MockServer(status_code=500) as server:
        config = Config(
            data_dir=data_dir,
            pop3_host="pop.example.com",
            pop3_port=995,
            pop3_username="user@example.com",
            pop3_use_ssl=True,
            webhook_url=server.url,
            webhook_timeout_seconds=5.0,
        )
        raw1 = _build_message(subject="First")
        raw2 = _build_message(subject="Second")
        pop3 = FakePop3Client({1: ("uidl-1", raw1), 2: ("uidl-2", raw2)})
        state = StateStore(data_dir)
        forwarder = UrllibWebhookForwarder(server.url, timeout_seconds=5.0)

        results = poll(config, state, pop3, forwarder)

        assert len(results) == 1
        assert results[0].ok is False
        assert not state.is_processed("uidl-1")
        assert not state.is_processed("uidl-2")

        # When the server recovers, both messages are re-delivered in order.
        server.status_code = 200
        _WebhookHandler.status_code = 200
        pop3 = FakePop3Client({1: ("uidl-1", raw1), 2: ("uidl-2", raw2)})

        results = poll(config, state, pop3, forwarder)

        assert len(results) == 2
        assert all(r.ok for r in results)
        assert state.is_processed("uidl-1")
        assert state.is_processed("uidl-2")


def test_poll_second_run_with_unchanged_uidls_is_no_op(data_dir: Path) -> None:
    with _MockServer(status_code=200) as server:
        config = Config(
            data_dir=data_dir,
            pop3_host="pop.example.com",
            pop3_port=995,
            pop3_username="user@example.com",
            pop3_use_ssl=True,
            webhook_url=server.url,
            webhook_timeout_seconds=5.0,
        )
        raw = _build_message()
        pop3 = FakePop3Client({1: ("uidl-1", raw)})
        state = StateStore(data_dir)
        forwarder = UrllibWebhookForwarder(server.url, timeout_seconds=5.0)

        poll(config, state, pop3, forwarder)
        assert len(server.requests) == 1

        pop3 = FakePop3Client({1: ("uidl-1", raw)})
        poll(config, state, pop3, forwarder)
        assert len(server.requests) == 1
