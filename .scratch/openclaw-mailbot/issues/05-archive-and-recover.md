---
status: closed
type: AFK
estimate: S
domain: reliability
blockedBy:
  - openclaw-mailbot-04
---

## Parent

PRD: `.scratch/openclaw-mailbot/PRD.md`

## What to build

Persist a copy of every raw message received from POP3 so that failed webhook deliveries can be retried later, and add a `recover` CLI command to replay archived messages.

## Implementation

1. Add `src/openclaw_mailbot/archive.py`:
   - `save_raw_email(data_dir, uidl, raw)` writes raw bytes to `<data_dir>/archive/<uidl>.eml`.
   - `iter_archived_emls(data_dir)` lists all archived files.
   - Filenames are sanitized to be filesystem-safe.

2. Update `src/openclaw_mailbot/poll.py`:
   - `_iter_messages()` calls `save_raw_email()` immediately after fetching each message, before parsing.
   - Add `recover()` function that re-parses archived `.eml` files and forwards them via the configured webhook.
   - `recover()` supports `--uidl` to recover a single message; otherwise recovers all archived messages.
   - Successfully recovered messages are marked as processed.

3. Update `src/openclaw_mailbot/cli.py`:
   - Add `recover` subcommand with optional `--uidl` argument.

## Usage

All future `poll` and `test` runs automatically archive raw `.eml` files to `mailbot-data/archive/`.

Replay everything that failed or was missed:

```bash
uv run openclaw-mailbot --config config.ini recover
```

Replay a single message:

```bash
uv run openclaw-mailbot --config config.ini recover --uidl <uidl-from-archive>
```

## Acceptance criteria

- [x] Raw `.eml` files are saved to `<data_dir>/archive/<uidl>.eml` during POP3 fetch.
- [x] `recover` subcommand exists and re-forwards archived messages.
- [x] `--uidl` option supports single-message recovery.
- [x] Recovered messages are marked processed on success.
- [x] README documents archiving and recovery.
- [x] Existing tests continue to pass.
