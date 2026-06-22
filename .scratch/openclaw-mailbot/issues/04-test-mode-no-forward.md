---
status: closed
type: AFK
estimate: XS
domain: cli
blockedBy:
  - openclaw-mailbot-01
  - openclaw-mailbot-02
  - openclaw-mailbot-03
---

## Parent

PRD: `.scratch/openclaw-mailbot/PRD.md`

## What to build

Add a `test` CLI subcommand that connects to the configured POP3 server, parses all new messages through the normal `parse_email()` pipeline, prints the JSON payloads to stdout, and marks messages as processed — without forwarding anything to the OpenClaw webhook.

This gives operators a safe way to verify mail server connectivity, UIDL tracking, body extraction, and HTML sanitization before enabling live webhook forwarding.

## Implementation

1. Add a `parse_only()` function in `src/openclaw_mailbot/poll.py` that mirrors `poll()` but:
   - Does not require or use a webhook URL / forwarder.
   - Prints each parsed payload as formatted JSON to stdout (or accepts an `output` callable for testability).
   - Marks each successfully parsed message as processed in `StateStore`.
   - Stops on fetch/parse errors, matching `poll()`'s failure semantics.

2. Wire a `test` subcommand in `src/openclaw_mailbot/cli.py` that:
   - Loads the config.
   - Requires `[pop3] host` but does **not** require `[openclaw] webhook_url`.
   - Creates a `StateStore` and POP3 client and calls `parse_only()`.

## Usage

```bash
export POP3_PASSWORD="super-secret"
uv run openclaw-mailbot --config config.ini test
```

## Acceptance criteria

- [x] `openclaw-mailbot test` subcommand exists and runs without requiring `webhook_url`.
- [x] It connects to the configured POP3 server, fetches new messages, parses them, and prints JSON payloads.
- [x] It does not forward to OpenClaw.
- [x] Parsed messages are marked as processed so they are not re-fetched.
- [x] Existing `poll` subcommand behavior is unchanged.
- [x] Existing tests continue to pass.
- [x] README documents the `test` subcommand and its purpose.
