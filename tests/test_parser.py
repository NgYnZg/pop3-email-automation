"""Tests for the mailbot parser seam."""

from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path

from openclaw_mailbot.config import Config
from openclaw_mailbot.parser import parse_email, parse_email_json


FIXTURES = Path(__file__).with_name("fixtures")


class ParserTests(unittest.TestCase):
    """High-level parser tests driven by .eml fixtures."""

    def setUp(self) -> None:
        self.data_dir = Path(tempfile.mkdtemp())

    def tearDown(self) -> None:
        import shutil

        shutil.rmtree(self.data_dir, ignore_errors=True)

    def test_plain_text_only(self) -> None:
        payload = parse_email(FIXTURES / "plain_only.eml", self.data_dir, "20260618-143000")

        self.assertEqual(payload["from"], {"address": "sender@example.com", "name": "Sender Name"})
        self.assertEqual(payload["to"], [{"address": "you@company.com", "name": ""}])
        self.assertEqual(payload["cc"], [])
        self.assertEqual(payload["subject"], "Plain text email")
        self.assertEqual(payload["date"], "2026-06-18T14:28:00Z")
        self.assertNotIn("html", payload)
        self.assertIn("plainText", payload)
        self.assertEqual(payload["plainText"].strip(), "This is the plain text body.")
        self.assertEqual(payload["attachments"], [])

    def test_html_only(self) -> None:
        payload = parse_email(FIXTURES / "html_only.eml", self.data_dir, "20260618-143000")

        self.assertIn("html", payload)
        self.assertNotIn("plainText", payload)
        self.assertIn("<b>HTML</b>", payload["html"])
        self.assertEqual(payload["attachments"], [])

    def test_mixed(self) -> None:
        payload = parse_email(FIXTURES / "mixed.eml", self.data_dir, "20260618-143000")

        self.assertIn("html", payload)
        self.assertIn("plainText", payload)
        self.assertIn("<b>HTML</b>", payload["html"])
        self.assertEqual(payload["plainText"].strip(), "This is the plain text fallback.")
        self.assertEqual(payload["cc"], [{"address": "cc@company.com", "name": ""}])
        self.assertEqual(payload["attachments"], [])

    def test_unicode(self) -> None:
        payload = parse_email(FIXTURES / "unicode.eml", self.data_dir, "20260618-143000")

        self.assertIn("🌍", payload["subject"])
        self.assertIn("こんにちは", payload["plainText"])
        self.assertIn("тестовое", payload["plainText"])

    def test_with_attachment(self) -> None:
        payload = parse_email(FIXTURES / "with_attachment.eml", self.data_dir, "20260618-143000")

        self.assertIn("plainText", payload)
        self.assertEqual(len(payload["attachments"]), 1)
        attachment = payload["attachments"][0]
        self.assertEqual(attachment["filename"], "invoice.pdf")
        self.assertEqual(attachment["contentType"], "application/pdf")
        self.assertEqual(attachment["sizeBytes"], 37)
        self.assertTrue(str(attachment["path"]).startswith(str(self.data_dir)))
        self.assertTrue(Path(attachment["path"]).exists())

    def test_json_output_is_valid(self) -> None:
        json_text = parse_email_json(FIXTURES / "mixed.eml", self.data_dir, "20260618-143000")
        payload = json.loads(json_text)
        self.assertEqual(payload["event"], "email.received")
        self.assertIn("html", payload)
        self.assertIn("plainText", payload)


class ConfigTests(unittest.TestCase):
    """Config loading tests."""

    def test_load_from_ini(self) -> None:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".ini", delete=False) as fh:
            fh.write("""
[pop3]
host = pop.example.com
port = 110
username = user
use_ssl = false

[storage]
data_dir = /tmp/mailbot-data

[openclaw]
webhook_url = https://example.com/webhook
timeout_seconds = 10
""")
            path = Path(fh.name)
        try:
            config = Config.load(path)
            self.assertEqual(config.pop3_host, "pop.example.com")
            self.assertEqual(config.pop3_port, 110)
            self.assertEqual(config.pop3_username, "user")
            self.assertFalse(config.pop3_use_ssl)
            self.assertEqual(config.data_dir, Path("/tmp/mailbot-data").resolve())
            self.assertEqual(config.webhook_url, "https://example.com/webhook")
            self.assertEqual(config.webhook_timeout_seconds, 10.0)
        finally:
            path.unlink(missing_ok=True)

    def test_mailbot_data_dir_env_overrides_ini(self) -> None:
        with tempfile.TemporaryDirectory() as env_dir:
            with tempfile.NamedTemporaryFile(mode="w", suffix=".ini", delete=False) as fh:
                fh.write("""
[storage]
data_dir = /ini/data/dir
""")
                path = Path(fh.name)
            try:
                old_env = os.environ.get("MAILBOT_DATA_DIR")
                os.environ["MAILBOT_DATA_DIR"] = env_dir
                try:
                    config = Config.load(path)
                    self.assertEqual(config.data_dir, Path(env_dir).resolve())
                finally:
                    if old_env is None:
                        os.environ.pop("MAILBOT_DATA_DIR", None)
                    else:
                        os.environ["MAILBOT_DATA_DIR"] = old_env
            finally:
                path.unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
