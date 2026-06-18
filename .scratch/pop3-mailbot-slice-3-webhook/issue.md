---
status: ready-for-agent
labels: ready-for-agent
---

## Parent

`pop3-mailbot-openclaw-bridge` (PRD issue)

## What to build

Add the webhook forwarder and integrate it into the polling loop. For each new message discovered by the POP3 poller, the bot POSTs the structured JSON payload to the configured OpenClaw webhook URL. If the POST fails, the message is treated as unprocessed so it is retried on the next poll.

## Acceptance criteria

- [ ] Webhook forwarder POSTs JSON to `[openclaw] webhook_url` from config.
- [ ] Payload follows the schema agreed in the PRD, with `html` canonical and `plainText` fallback.
- [ ] Attachment paths in the payload point to files on local disk saved by slice 1.
- [ ] On webhook failure (non-2xx or exception), the UIDL state is not advanced, so the message is retried on the next poll.
- [ ] On webhook success, the UIDL state is advanced normally.
- [ ] A mock HTTP server fixture can verify headers, JSON body, and retry behavior in tests.

## Blocked by

- Slice 2: Poll POP3 mailbox and print new payloads to stdout
