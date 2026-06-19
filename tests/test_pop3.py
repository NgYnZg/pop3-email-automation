"""Tests for the POP3 client seam using FakePop3Client."""

from __future__ import annotations

import poplib
import unittest

from openclaw_mailbot.pop3 import FakePop3Client, Pop3Client

SAMPLE_EML = b"From: sender@example.com\r\nTo: you@company.com\r\nSubject: Test\r\n\r\nHello World\r\n"


class FakePop3ClientTests(unittest.TestCase):

    def test_uidl_returns_message_map(self):
        client = FakePop3Client({1: ("uidl-a", SAMPLE_EML), 2: ("uidl-b", SAMPLE_EML)})
        self.assertEqual(client.uidl(), {1: "uidl-a", 2: "uidl-b"})

    def test_retr_returns_message_bytes(self):
        client = FakePop3Client({1: ("uidl-a", SAMPLE_EML)})
        self.assertEqual(client.retr(1), SAMPLE_EML)

    def test_retr_raises_on_unknown_message(self):
        client = FakePop3Client({1: ("uidl-a", SAMPLE_EML)})
        with self.assertRaises(poplib.error_proto):
            client.retr(999)

    def test_quit_sets_quitted_flag(self):
        client = FakePop3Client({})
        self.assertFalse(client._quitted)
        client.quit()
        self.assertTrue(client._quitted)

    def test_no_delete_method_exists(self):
        """Verify FakePop3Client has no dele method (leave-on-server)."""
        client = FakePop3Client({})
        with self.assertRaises(AttributeError):
            client.dele(1)  # type: ignore[attr-defined]

    def test_satisfies_pop3_client_protocol(self):
        """Verify FakePop3Client implements Pop3Client protocol."""
        client: Pop3Client = FakePop3Client({})
        self.assertTrue(hasattr(client, "uidl"))
        self.assertTrue(hasattr(client, "retr"))
        self.assertTrue(hasattr(client, "quit"))


if __name__ == "__main__":
    unittest.main()
