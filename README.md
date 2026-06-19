# openclaw-mailbot

A lightweight Python mailbot that polls a POP3 mailbox and triggers OpenClaw workflows via webhook.

This repository is the prototype / first vertical slice. It currently parses local `.eml` files and emits the structured JSON payload that will later be forwarded to OpenClaw.

## Project setup

This project uses [`uv`](https://docs.astral.sh/uv/) and requires Python 3.11+. There are no runtime dependencies beyond the Python standard library.

```bash
uv sync
```

## Usage

Parse a local `.eml` file:

```bash
uv run openclaw-mailbot parse tests/fixtures/mixed.eml --config config.example.ini
```

The command prints a JSON payload to stdout and saves any attachments under the configured data directory.

### Configuration

Copy `config.example.ini` to `config.ini` and edit as needed:

```ini
[pop3]
host = pop.example.com
port = 995
username = mailbot@example.com

[mailbot]
data_dir = /var/lib/openclaw-mailbot

[forwarder]
webhook_url = https://openclaw.example.com/webhooks/email
timeout_seconds = 30
```

The data directory can also be overridden with the `MAILBOT_DATA_DIR` environment variable. The POP3 password is read from `POP3_PASSWORD` (not used in this slice).

## Output JSON shape

```json
{
  "event": "email.received",
  "messageId": "<abc123@sender.com>",
  "receivedAt": "2026-06-18T14:30:00Z",
  "from": { "address": "sender@example.com", "name": "Sender Name" },
  "to": [{ "address": "you@company.com", "name": "" }],
  "cc": [],
  "subject": "...",
  "date": "2026-06-18T14:28:00Z",
  "plainText": "...",
  "html": "...",
  "attachments": [
    {
      "filename": "invoice.pdf",
      "path": "/var/lib/openclaw-mailbot/attachments/20260618-143000/abc123@sender.com/invoice.pdf",
      "contentType": "application/pdf",
      "sizeBytes": 12345
    }
  ]
}
```

`html` is canonical and `plainText` is the fallback. Either field may be omitted if the corresponding body part is absent.

## Running tests

```bash
uv run python -m unittest discover -s tests -v
```

## Fixtures

The parser tests are driven by RFC 2822 fixtures in `tests/fixtures/`:

- `plain_only.eml` — text/plain body only
- `html_only.eml` — text/html body only
- `mixed.eml` — multipart/alternative with both plain and HTML
- `unicode.eml` — unicode subject and body content
- `with_attachment.eml` — mixed email with a PDF attachment

Regenerate fixtures with:

```bash
uv run python tests/fixtures/generate.py
```
