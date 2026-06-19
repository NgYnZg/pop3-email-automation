# Design Context: Filter Wasteful HTML Entities/Tags from Email Parser Output

## 1. Domain Terms and Definitions

| Term | Current Definition | Source |
|------|-------------------|--------|
| **Webhook payload** | A JSON dict with keys: `event`, `messageId`, `uidl`, `receivedAt`, `from`, `to`, `cc`, `subject`, `date`, `plainText` (optional), `html` (optional), `attachments` | `parser.py:parse_email()` |
| **Body extraction** | Raw bytes decoded to text with the part's charset (fallback `utf-8`). No sanitization, normalization, or entity unescaping. HTML is stored as-is. | `parser.py:_extract_bodies()` |
| **UIDL tracking** | POP3 UIDL unique-ID per message, persisted in a local state file to deduplicate across polls. | `state.py`, `poll.py` |
| **Forwarder** | POSTs the full parser payload as JSON to an OpenClaw webhook URL. | `forwarder.py` |
| **OpenClaw** | An external workflow engine; not part of this repo. The mailbot's only interaction is via HTTP webhook. | `README.md` |
| **Attachment** | Any MIME part not matching `text/plain`, `text/html`, `multipart/*` or lacking an `attachment` disposition. Saved to local disk; path referenced in payload. | `parser.py:_is_attachment()` |
| **Stdlib-only constraint** | Zero runtime dependencies beyond Python 3.11+. The parser uses `email.message_from_binary_file`, `html.parser` would be the natural choice for HTML sanitization. | `pyproject.toml` |

## 2. Existing Architectural Decisions (ADRs)

**No ADRs exist.** The repo has `docs/agents/domain.md` describing a single-context layout with `CONTEXT.md` + `docs/adr/`, but neither file exists yet. The only documented decisions are in the prior PRD (`.scratch/pop3-mailbot-openclaw-bridge/PRD.md`), which explicitly lists:

- **No HTML-to-plaintext conversion** — plain text is taken as-is from the email (PRD Out of Scope). This was intentional.
- **No filtering** — all messages are forwarded without filtering (PRD Out of Scope).
- **Stdlib-only** — no runtime deps, for easy reasoning and deployment.
- **Forwarder is thin** — a small abstraction so different transports can be swapped.

These decisions constrain this feature: we cannot add an external HTML sanitizer library.

## 3. Likely Modules/Files That Will Change

| File | Change Reason |
|------|---------------|
| `src/openclaw_mailbot/parser.py` | The primary module. `_extract_bodies()` returns raw HTML/plain text. A new function is needed to strip/escape wasteful HTML entities (`&nbsp;`, `&amp;`, etc.) and optionally strip HTML tags in the plain text output. The HTML output may also be cleaned. |
| `tests/test_parser.py` | New test cases for the sanitization function with .eml fixtures containing HTML entities. |
| `tests/fixtures/` | New fixture `.eml` files containing HTML entities (`&nbsp;`, `&lt;`, `<style>` blocks, etc.) and other wasteful tag patterns. |
| `tests/fixtures/generate.py` | A new generator function for the entity-rich fixture. |

**Unchanged:** `poll.py`, `forwarder.py`, `cli.py`, `pop3.py`, `state.py`, `config.py` — no contract changes to the payload shape or delivery mechanism.

## 4. Gaps, Contradictions, and Open Questions

### 4.1 Gap: No CONTEXT.md or ADRs exist
The project instructions reference `CONTEXT.md` and `docs/adr/` as the canonical decision store, but neither exists. The prior PRD is the only decision artifact. This feature should be recorded as the first ADR.

### 4.2 Contradiction: Prior "no filtering" decision vs. this request
The prior PRD explicitly listed "Filtering by sender, subject, or attachment type" as Out of Scope. This feature *is* filtering — but of HTML entities in body text, not of headers. This is a substantively different axis (content quality vs. message routing) and should be clarified as in-scope for this feature.

### 4.3 Gap: What exactly constitutes "wasteful characters"?
The request mentions `&nbsp;` and "other tags" but doesn't specify:
- Should HTML tags be *stripped* from the `html` field, or only entities unescaped?
- Should the `plainText` field have HTML tags stripped away? (Currently it comes from the email's `text/plain` MIME part, which may also contain HTML entities.)
- Should `&nbsp;`, `&amp;`, `&lt;`, `&gt;`, `&quot;`, `&#160;` (numeric entities) all be handled?
- What about `<style>`, `<script>` blocks — stripped entirely?

### 4.4 Gap: Html.parser vs. regex tradeoff
The stdlib-only constraint means:
- `html.parser.HTMLParser` can unescape entities but cannot parse malformed real-world HTML.
- `re` can strip tags but is fragile with edge cases (attribute values containing `>`).
- A hybrid approach using `html.parser` for entity unescaping and `re` for tag stripping is the pragmatic stdlib route.

### 4.5 Gap: Plain text body may also contain HTML entities
Real-world emails sometimes include `text/plain` alternatives that still contain HTML entities (e.g., `&nbsp;` for spacing in mail clients that generate both parts). The sanitization should apply to *both* `html` and `plainText` fields if present.

### 4.6 Gap: Performance on large HTML bodies
Entity unescaping and tag stripping on a multi-megabyte HTML email (common with newsletters) could be slow with `html.parser`. No streaming approach exists in the current code — bodies are fully decoded into memory first. This is acceptable for a cron-based tool processing one-at-a-time.

### 4.7 The feature could add value at two levels
1. **Entity unescaping** (convert `&amp;` → `&`, `&nbsp;` → `\xa0`, etc.) — purely mechanical, lossless for downstream consumers.
2. **Tag stripping** (remove `<style>`, `<script>`, and their contents; flatten other tags to text) — opinionated, potentially destructive if the OpenClaw workflow expects HTML markup.

The PRD's prior "no HTML-to-plaintext conversion" decision suggests OpenClaw workflows expect raw HTML. So entity unescaping is likely the right scope; tag stripping may break existing downstream expectations.
