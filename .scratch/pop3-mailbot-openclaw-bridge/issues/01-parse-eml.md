---
status: closed
labels: ready-for-agent
---

## Parent

`issues/00-prd.md`

## What to build

Build the first vertical slice of the POP3 mailbot: parse a local `.eml` file and emit the structured JSON payload to stdout. This slice establishes the project skeleton, config loading, RFC 2822 parsing, and attachment extraction. It does not yet touch POP3 or the webhook.

The output JSON shape (from prototype discussion):

```json
{
  "event": "email.received",
  "messageId": "<abc123@sender.com>",
  "uidl": "pop3-uidl-abc",
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
      "path": "/var/lib/openclaw-mailbot/attachments/20260618-143000/uidl-abc/invoice.pdf",
      "contentType": "application/pdf",
      "sizeBytes": 12345
    }
  ]
}
```

For this slice, `uidl` may be omitted or mocked because POP3 integration is not yet built. HTML is canonical; plain text is fallback. Attachments are written under the configured data directory and referenced by local filesystem path.

## Acceptance criteria

- [ ] `uv` project scaffold exists (`pyproject.toml`, no runtime dependencies beyond stdlib).
- [ ] Running the CLI with a local `.eml` path prints valid JSON to stdout.
- [ ] The JSON contains `html` (canonical), `plainText` (fallback), `from`, `to`, `cc`, `subject`, `date`, and `attachments`.
- [ ] Attachments from the `.eml` are saved under `<data_dir>/attachments/<run-timestamp>/<identifier>/` and referenced by local path.
- [ ] Config is loaded from an INI file; `POP3_PASSWORD` is ignored in this slice (no POP3 yet), but `MAILBOT_DATA_DIR` is honored.
- [ ] Parser handles plain-text-only, HTML-only, mixed, and unicode `.eml` fixtures correctly.

## Blocked by

None - can start immediately.
