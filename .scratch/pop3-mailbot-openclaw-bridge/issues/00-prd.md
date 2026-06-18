---
status: ready-for-agent
labels: ready-for-agent
---

# POP3 mailbot for OpenClaw workflow triggering

## Problem Statement

The company’s incoming email infrastructure is POP3-only, which does not support push-based ingestion. OpenClaw workflows need to be triggered automatically when emails arrive. There is currently no mechanism to bridge the POP3 mailbox to OpenClaw, so email-driven automations are blocked.

## Solution

Build a lightweight Python mailbot that polls the POP3 mailbox on a cron schedule, detects new messages using `UIDL` tracking, parses the email body and attachments, and triggers an OpenClaw workflow via webhook. The mailbot leaves messages on the POP3 server, persists only the last-seen UIDL, and retries naturally on the next poll when the webhook fails.

## User Stories

1. As an operator, I want the mailbot to check the POP3 mailbox every 5 minutes, so that emails are ingested without manual intervention.
2. As an operator, I want the mailbot to detect only new messages across restarts, so that the same email is not processed twice.
3. As an operator, I want the mailbot to leave messages on the POP3 server after reading them, so that I do not lose email history if something goes wrong.
4. As an operator, I want the mailbot to extract the HTML body of each email, so that OpenClaw receives rich content when available.
5. As an operator, I want the mailbot to include a plain-text fallback for each email, so that OpenClaw can still act when HTML is absent.
6. As an operator, I want the mailbot to save attachments to local disk and include their paths in the webhook payload, so that OpenClaw workflows can read them.
7. As an operator, I want the mailbot to forward all emails without filtering, so that no legitimate messages are silently dropped during early testing.
8. As an operator, I want the mailbot to retry failed webhook deliveries on the next poll, so that transient errors do not require manual recovery.
9. As an operator, I want the POP3 password to be read from an environment variable, so that credentials are not stored in plaintext config files.
10. As a developer, I want the project managed with `uv`, so that dependencies and the Python version are reproducible.
11. As a developer, I want the mailbot to be invoked by cron, so that scheduling is simple and familiar to operators.
12. As a developer, I want a working prototype in the current repo, so that I can validate the design before creating a dedicated repository.
13. As an operator, I want the mailbot’s data directory to be configurable via environment variable, so that I can adapt it to different machines.
14. As a developer, I want unit tests at high-level seams, so that I can refactor internals without breaking confidence.
15. As an operator, I want logs from each cron run to be visible on stdout/stderr, so that I can debug failures using cron’s default email behavior.

## Implementation Decisions

- **Trigger mechanism:** The mailbot calls an OpenClaw HTTP webhook with a JSON payload. The forwarder is a small abstraction so a file-drop or queue forwarder can be added later without changing POP3 or parsing logic.
- **Scheduling:** A cron job runs the mailbot every 5 minutes.
- **POP3 interaction:** The client uses `UIDL` to track already-processed messages and leaves messages on the server. The last seen UIDL is persisted locally.
- **Body extraction:** The parser extracts `text/html` as the canonical body and `text/plain` as a fallback. If neither exists, the body fields are omitted.
- **Attachments:** Attachments are saved under a configurable data directory with paths like `<data_dir>/attachments/<run-timestamp>/<uidl>/<filename>`. The webhook payload references these local paths.
- **Configuration:** Config is read from an `INI` file. The POP3 password is read from the `POP3_PASSWORD` environment variable. The data directory defaults to a sensible path but can be overridden via `MAILBOT_DATA_DIR`.
- **Language and packaging:** Python with stdlib only for the prototype. `uv` is used for project management. `pyproject.toml` declares no runtime dependencies.
- **Failure handling:** If the webhook POST fails, the message remains on the POP3 server and will be retried on the next poll. No dead-letter or alerting logic in the first slice.
- **Filtering:** No filtering is performed; all messages in the mailbox are candidates for forwarding.

## Testing Decisions

- Tests should exercise external behavior, not internal implementation. For example, assert that a given `.eml` input produces a specific webhook payload, not that a private function calls `poplib`.
- The parser seam will be tested with RFC 2822 `.eml` fixtures covering plain text only, HTML only, mixed, with attachments, and with unicode content.
- The POP3 client seam will be tested with a fake socket/transport that speaks the POP3 protocol so the test can assert UIDL tracking and the leave-on-server behavior.
- The state-store seam will be tested by writing a UIDL, creating a fresh store instance, and asserting the UIDL is restored.
- The webhook forwarder seam will be tested with `http.server` or a mocked `urllib` transport to assert headers, JSON body, and timeout behavior.
- The end-to-end seam will wire parser + state + webhook forwarder with a fake POP3 client and assert the complete output for a representative email.

## Out of Scope

- Webhook authentication or signature verification.
- Deleting messages from the POP3 server after successful delivery.
- Dead-letter queue or alerting for repeated failures.
- HTML-to-plaintext conversion; plain text is taken as-is from the email.
- Filtering by sender, subject, or attachment type.
- Attachment upload to object storage or generation of pre-signed URLs.
- Metrics, structured logging, or observability beyond stdout/stderr.
- Migration to a dedicated repository.

## Further Notes

- The prototype should be kept small and stdlib-only so it is easy to reason about and deploy.
- The OpenClaw webhook URL and other connection details live in config; OpenClaw itself is not part of this implementation.
- The UIDL state file is intentionally simple (plain text or a tiny SQLite) to minimize failure modes.
