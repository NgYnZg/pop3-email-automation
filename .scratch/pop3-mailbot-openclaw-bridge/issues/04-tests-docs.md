---
status: closed
labels: ready-for-agent
---

## Parent

`issues/00-prd.md`

## What to build

Add focused seam tests and deployment documentation. Tests should exercise external behavior, not internal implementation. Also add a `README.md` with install, configuration, and cron setup instructions.

## Acceptance criteria

- [ ] Parser tests cover plain-text-only, HTML-only, mixed, with attachments, and unicode `.eml` fixtures.
- [ ] State-store test verifies persistence across instances.
- [ ] POP3 transport test verifies UIDL tracking and leave-on-server behavior.
- [ ] Webhook forwarder test verifies headers, JSON body, and timeout behavior.
- [ ] End-to-end test wires fake POP3 + mock webhook and asserts the complete output for a representative email.
- [ ] README includes project overview, `uv` install steps, config example, required env vars (`POP3_PASSWORD`, `MAILBOT_DATA_DIR`), and cron line (`*/5 * * * *`).

## Blocked by

- `issues/03-webhook.md`
