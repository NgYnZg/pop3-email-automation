"""Tests for the UIDL state store."""

from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from openclaw_mailbot.state import StateStore


class StateStoreTests(unittest.TestCase):

    def setUp(self):
        self.tmpdir = TemporaryDirectory()
        self.data_dir = Path(self.tmpdir.name)

    def tearDown(self):
        self.tmpdir.cleanup()

    def test_new_store_has_no_processed_uidls(self):
        store = StateStore(self.data_dir)
        store.load()
        self.assertFalse(store.is_processed("uidl-1"))

    def test_mark_processed_and_is_processed(self):
        store = StateStore(self.data_dir)
        store.load()
        store.mark_processed("uidl-1")
        self.assertTrue(store.is_processed("uidl-1"))

    def test_persistence_across_instances(self):
        store1 = StateStore(self.data_dir)
        store1.load()
        store1.mark_processed("uidl-1")
        store1.mark_processed("uidl-2")

        store2 = StateStore(self.data_dir)
        store2.load()
        self.assertTrue(store2.is_processed("uidl-1"))
        self.assertTrue(store2.is_processed("uidl-2"))

    def test_mark_already_processed_is_idempotent(self):
        store = StateStore(self.data_dir)
        store.load()
        store.mark_processed("uidl-1")
        store.mark_processed("uidl-1")  # no-op
        self.assertTrue(store.is_processed("uidl-1"))

    def test_multiple_uidls(self):
        store = StateStore(self.data_dir)
        store.load()
        for i in range(10):
            store.mark_processed(f"uidl-{i}")
        for i in range(10):
            self.assertTrue(store.is_processed(f"uidl-{i}"))


if __name__ == "__main__":
    unittest.main()
