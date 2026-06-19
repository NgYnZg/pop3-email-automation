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

Example for a single run:

```bash
export POP3_PASSWORD="super-secret"
export MAILBOT_DATA_DIR="/var/lib/openclaw-mailbot"
uv run openclaw-mailbot --config config.example.ini poll
```

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

## Project layout

- `src/openclaw_mailbot/parser.py` — RFC 2822 parsing, HTML entity decoding, and attachment extraction.
- `src/openclaw_mailbot/pop3.py` — POP3 transport and client.
- `src/openclaw_mailbot/state.py` — UIDL persistence.
- `src/openclaw_mailbot/forwarder.py` — Webhook POST.
- `src/openclaw_mailbot/poll.py` — Poll orchestration.
- `src/openclaw_mailbot/cli.py` — Command-line entry point.
