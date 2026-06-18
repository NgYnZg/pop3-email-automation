---
status: ready-for-agent
labels: ready-for-agent
---

## Parent

`issues/00-prd.md`

## What to build

Add POP3 polling to the mailbot. The bot connects to a POP3 server, lists messages via `UIDL`, fetches only messages not seen in previous runs, parses them, and prints their payloads to stdout. Messages are left on the server. The last-seen UIDL is persisted to a state file under the configured data directory.

This slice wires the parser from slice 1 to a POP3 client and a state store. It still does not call the webhook.

## Acceptance criteria

- [ ] UIDL state store reads and writes the highest processed UIDL to `<data_dir>/state/uidl.db` (plain text or SQLite).
- [ ] POP3 client uses `UIDL` to identify new messages and fetches them with `RETR`.
- [ ] Fetched messages are left on the POP3 server (no `DELE` is issued).
- [ ] A fake POP3 server fixture can drive the client in tests.
- [ ] Second poll with unchanged UIDLs produces no output.
- [ ] Config includes `[pop3] host`, `port`, `username`, `use_ssl`, plus `[storage] data_dir`; password is read from `POP3_PASSWORD` env var.
- [ ] CLI entry point works as a cron-invokable script: `uv run mailbot poll`.

## Blocked by

- `issues/01-parse-eml.md`
