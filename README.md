# OpenClaw Mailbot

A lightweight, stdlib-only Python mailbot that polls a POP3 mailbox and forwards incoming emails to an OpenClaw webhook. It leaves messages on the POP3 server, tracks already-processed messages by `UIDL`, and retries failed webhook deliveries on the next poll.

## Features

- Polls a POP3 mailbox on a cron schedule.
- Detects new messages using `UIDL` tracking across restarts.
- Leaves messages on the server (no `DELE`).
- Extracts HTML (canonical) and plain-text (fallback) bodies, stripping `<style>` and `<script>` blocks from the HTML and decoding HTML character references (e.g. `&amp;`, `&nbsp;`, `&#160;`).
- Saves attachments to local disk and references them in the webhook payload.
- Reads the POP3 password from an environment variable.
- Configurable data directory for state and attachments.

## Install

This project is managed with [`uv`](https://docs.astral.sh/uv/). Clone the repository and install dependencies:

```bash
uv sync
```

There are no runtime dependencies beyond the Python standard library.

## Configuration

Create an INI file, for example `config.example.ini`:

```ini
[pop3]
host = pop.example.com
port = 995
username = mailbot@example.com
use_ssl = true

[storage]
data_dir = /var/lib/openclaw-mailbot

[openclaw]
webhook_url = https://openclaw.example.com/hooks/email
timeout_seconds = 30
```

## Required environment variables

| Variable | Purpose |
|----------|---------|
| `POP3_PASSWORD` | Password for the POP3 account. Never store this in the INI file. |
| `MAILBOT_DATA_DIR` | Optional override for the data directory configured in `storage.data_dir`. |

Set them with `export` for a single run:

```bash
export POP3_PASSWORD="super-secret"
export MAILBOT_DATA_DIR="/var/lib/openclaw-mailbot"
uv run openclaw-mailbot --config config.example.ini poll
```

Or create a `.env` file in the project root:

```bash
cp .env.example .env
# edit .env with your POP3_PASSWORD, MAILBOT_DATA_DIR, and WEBHOOK_BEARER_TOKEN
```

The mailbot loads `.env` automatically. Already-set environment variables take precedence over `.env` values.

## Testing the POP3 connection and parser before enabling the webhook

The `test` subcommand connects to the configured POP3 server, parses each new message, prints the JSON payload to stdout, and marks messages as processed. It does **not** forward to the OpenClaw webhook and does **not** require `webhook_url`.

```bash
uv run openclaw-mailbot --config config.example.ini test
```

This is useful for verifying:

- POP3 host, port, username, and password.
- UIDL tracking and state persistence.
- Body extraction and HTML entity/style/script sanitization.
- Attachment saving paths.

Because parsed messages are marked as processed, a second `test` run will not re-fetch the same messages. Delete `<data_dir>/state.json` to re-test from scratch.

## Archiving and recovery

Every message fetched from the POP3 server is saved as a raw `.eml` file under `<data_dir>/archive/<uidl>.eml` before parsing or forwarding. This provides a local backup and makes failed webhook deliveries recoverable.

If a webhook delivery fails, the message is left unprocessed and can be re-forwarded later from the local archive:

```bash
# Re-forward all archived emails
uv run openclaw-mailbot --config config.ini recover

# Re-forward a single archived email by UIDL
uv run openclaw-mailbot --config config.ini recover --uidl <uidl>
```

Successfully recovered messages are marked as processed. Failures stop the loop so you can fix the webhook and retry.

## Cron setup

Run the mailbot every 5 minutes from the user account that owns the data directory:

```cron
*/5 * * * * cd /opt/openclaw-mailbot && POP3_PASSWORD="super-secret" MAILBOT_DATA_DIR="/var/lib/openclaw-mailbot" /usr/local/bin/uv run openclaw-mailbot --config config.example.ini poll >> /var/log/openclaw-mailbot.log 2>&1
```

Cron will email any stderr output to the user by default, making failures visible.

## Development

Run the seam tests with:

```bash
uv run pytest -v
# or
uv run python -m unittest discover -s tests -v
```

Parse a local .eml file:

```bash
uv run openclaw-mailbot parse path/to/email.eml
```

Test the full POP3 + parser path without forwarding:

```bash
export POP3_PASSWORD="super-secret"
uv run openclaw-mailbot --config config.example.ini test
```

## Project layout

- `src/openclaw_mailbot/parser.py` — RFC 2822 parsing, HTML entity decoding, and attachment extraction.
- `src/openclaw_mailbot/pop3.py` — POP3 transport and client.
- `src/openclaw_mailbot/state.py` — UIDL persistence.
- `src/openclaw_mailbot/forwarder.py` — Webhook POST.
- `src/openclaw_mailbot/poll.py` — Poll orchestration and recovery.
- `src/openclaw_mailbot/archive.py` — Raw `.eml` archiving and archive iteration.
- `src/openclaw_mailbot/cli.py` — Command-line entry point.
