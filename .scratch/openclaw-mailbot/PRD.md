---
status: ready-for-agent
labels: ready-for-agent
---

# Sanitize HTML Entities and Non-Content Blocks from Email Parser Output

**Summary:** Add content-level sanitization to the email parser that unescapes HTML character references (e.g., `&nbsp;`, `&amp;`, `&#160;`) in both the `html` and `plainText` payload fields, and strips `<style>` / `<script>` block contents from the `html` field — reducing token waste before delivery to OpenClaw workflows.

## Problem Statement

When OpenClaw workflows receive email payloads from the mailbot, the `html` and `plainText` fields may contain thousands of HTML character references such as `&nbsp;`, `&amp;`, `&lt;`, and numeric entities like `&#160;`. Each entity expands to 5–8 ASCII characters in the JSON payload but encodes only a single Unicode codepoint. A marketing email with 200 `&nbsp;` instances wastes ~1200 characters in the payload — tokens consumed by the LLM for no informational value.

Additionally, real-world HTML emails routinely embed large `<style>` and `<script>` blocks that account for 60–80% of the raw HTML size. CSS source text and JavaScript code are not document content; they inflate the payload with data that downstream workflows cannot use.

The current `_extract_bodies()` function returns raw decoded text verbatim — no entity unescaping, no cleanup. Every email delivers the full weight of its source formatting into LLM context windows, costing tokens and reducing effective context capacity.

## Solution

The mailbot's parser applies two lightweight sanitization passes to the `html` and `plainText` fields before the payload is serialized to JSON:

1. **HTML entity unescaping** — All HTML5 named character references (e.g., `&nbsp;`, `&amp;`, `&lt;`, `&gt;`, `&quot;`) and numeric/hex entities (e.g., `&#160;`, `&#x00A0;`) are decoded to their Unicode codepoints using the stdlib `html.unescape()` function. This applies to **both** `html` and `plainText` fields because real-world emails often embed entities in both MIME alternatives.

2. **Style/script block removal** — The contents of `<style>...</style>` and `<script>...</script>` tags are removed from the `html` field. The tags themselves and the surrounding HTML structure remain intact. This is not "HTML-to-plaintext conversion" (which strips all tags) — it removes non-content data regions that are never rendered as visible text.

The sanitization is applied unconditionally (no configuration flag) and modifies the existing `html` / `plainText` fields in-place (no new fields). The payload contract is otherwise unchanged — `event`, `messageId`, `subject`, `from`, `to`, `attachments`, and all other fields pass through unmodified.

## User Stories

1. As an operator, I want `&nbsp;` characters in the email body to be decoded to non-breaking spaces (U+00A0), so that downstream LLM workflows do not waste tokens on encoded whitespace markup.

2. As an operator, I want `&amp;`, `&lt;`, `&gt;`, and `&quot;` in both HTML and plain text bodies to be decoded to their actual characters, so that workflow text processing sees the intended content.

3. As an operator, I want numeric and hex HTML entities (e.g., `&#160;`, `&#x00A0;`) to be decoded alongside named entities, so that no entity-based token waste remains regardless of encoding style.

4. As an operator, I want the contents of `<style>` and `<script>` blocks stripped from the `html` field, so that CSS and JS source text (which accounts for most of a newsletter's HTML size) does not consume LLM context.

5. As an operator, I want entity unescaping to apply to the `plainText` field as well, so that newsletters that embed `&nbsp;` in the text/plain alternative are also cleaned.

6. As an operator, I want sanitization to be unconditional — no config flag to forget or mis-set — so that every payload benefits from token reduction without setup.

7. As a developer, I want the sanitization to use only Python stdlib (`html.unescape()`), so that the project's zero-runtime-dependency constraint is maintained.

8. As a developer, I want the sanitization to happen inside `_extract_bodies()` or immediately after it in `parse_email()`, so that the forwarder and CLI layers are not affected.

9. As a developer, I want existing tests to continue passing with sanitized output, so that no regressions are introduced in unrelated parsing behavior.

10. As an operator, I want to be able to inspect the original raw `.eml` file on disk if I need to debug what the email actually contained before sanitization, so that sanitization bugs are diagnosable.

## Implementation Decisions

### Sanitization Scope: Both `html` and `plainText`

The `plainText` field comes from the email's own `text/plain` MIME part, not from HTML-to-text conversion. Real-world email senders (especially marketing platforms) auto-generate the plain-text alternative with `&nbsp;` and other entities intact. Sanitizing only `html` would leave half the token-waste problem unsolved. Both fields get the same entity-unescape treatment.

### Entity Unescaping Only — No Tag Stripping

HTML tags like `<div>`, `<span>`, `<b>`, `<a>` are structural markup that OpenClaw workflows may depend on for their own rendering or extraction logic. Stripping all tags would violate the prior PRD's "No HTML-to-plaintext conversion" decision and break workflow expectations. Only **character references** (entities) are decoded — tags are preserved.

The one exception is `<style>` and `<script>` blocks, whose contents are CSS/JS source code — not structural markup and not visible document content. Removing them reduces payload size by 60–80% on marketing emails without affecting visible HTML structure.

### Stdlib Implementation: `html.unescape()`

```python
from html import unescape

def _sanitize_html(text: str) -> str:
    """Unescape HTML character references and strip style/script block contents."""
    # Strip style/script blocks first so entities inside them don't need decoding
    text = _strip_style_script(text)
    return unescape(text)
```

`html.parser.HTMLParser.unescape()` (aliased as `html.unescape()` since Python 3.4) is in the stdlib, handles all HTML5 named entities and all numeric/hex entities correctly, and is O(n) with well-tested CPython internals. A regex-based replacement would be slower, more error-prone, and harder to maintain. This is a one-line import with zero additional dependencies.

### Style/Script Block Removal

The removal targets only the **contents** between `<style>` and `</style>` (and `<script>`/`</script>`), not the tags themselves. A simple regex or `html.parser.HTMLParser` subclass can drop these regions. The surrounding HTML remains structurally valid because the tags are left in place (as empty elements).

```python
import re

_STYLE_SCRIPT_RE = re.compile(
    r'<style[^>]*>.*?</style>|<script[^>]*>.*?</script>',
    re.IGNORECASE | re.DOTALL,
)

def _strip_style_script(html: str) -> str:
    return _STYLE_SCRIPT_RE.sub("", html)
```

### In-Place Modification, No New Fields

The sanitization modifies `html` and `plainText` in `parse_email()` before the payload dict is assembled. No `htmlClean` / `plainTextClean` fields are added. This is a prototype with no production OpenClaw workflows yet; keeping the payload simple is correct. If backward compatibility becomes necessary later, a `sanitized: true` field or `parserVersion` can be added.

### Unconditional Application, No Config Flag

Adding a configuration flag introduces config-surface complexity (INI parsing, documentation, testing) that delays the core feature. The sanitization is simple and well-understood — the risk of introducing a bug is low. Operators who need to inspect raw HTML can look at the original `.eml` files on disk in the POP3 mailbox or add a debug flag in a follow-up issue.

### Module Changed: `parser.py`

Only `src/openclaw_mailbot/parser.py` is modified. The new functions `_sanitize_html()` and `_strip_style_script()` are private module-level functions called from `parse_email()` after `_extract_bodies()` returns. The payload assembly code changes from:

```python
html, plain = _extract_bodies(message)
# ... becomes:
html, plain = _extract_bodies(message)
if html is not None:
    html = _sanitize_html(html)
if plain is not None:
    plain = _sanitize_plain(plain)  # entity unescape only, no style/script stripping
```

### Unchanged Modules

`poll.py`, `forwarder.py`, `cli.py`, `pop3.py`, `state.py`, `config.py` — no contract changes to the payload shape, webhook delivery, or CLI interface.

## Testing Decisions

### What Makes a Good Test

- **Fixture-driven.** New `.eml` fixture files containing HTML entities (`&nbsp;`, `&amp;`, `&#160;`), style blocks, script blocks, and mixed content in both HTML and plain text MIME parts. The test asserts the expected decoded output, not the internal function calls.
- **Behavioral, not implementation.** Tests assert that `parse_email()` returns a payload with correctly sanitized `html` and `plainText` fields. They do not import `_sanitize_html` directly.
- **Edge cases covered:**
  - Plain text with entities (e.g., `text/plain: "Price: &pound;10 &amp; &euro;5"`)
  - HTML with nested style/script blocks
  - Numeric entities (`&#160;`, `&#x00A0;`)
  - Mixed named and numeric entities
  - Email with no entities (regression — output should match current behavior)
  - Email with no HTML or no plain text (sanitization should be a no-op on absent fields)

### Modules to Test

| Test | What It Covers |
|------|----------------|
| `test_entities_plain_text` | Entities in `text/plain` MIME part are unescaped |
| `test_entities_html` | Entities in `text/html` MIME part are unescaped |
| `test_style_script_stripped` | `<style>` and `<script>` block contents removed from `html` |
| `test_html_structure_preserved` | Non-style/script HTML tags survive sanitization |
| `test_no_entities_unchanged` | Payload without entities matches current output |
| `test_numeric_entities` | `&#160;`, `&#x00A0;` are decoded |

### Prior Art in the Codebase

Tests live in `tests/test_parser.py` and use fixture `.eml` files from `tests/fixtures/`. New fixtures should follow the same pattern and can be generated using `tests/fixtures/generate.py`.

## Out of Scope

- **HTML tag stripping** — Only character references are decoded; `<div>`, `<span>`, `<b>`, `<a>` and all other structural tags remain intact. This is not HTML-to-plaintext conversion.
- **Message-level filtering** — No filtering by sender, subject, or attachment type. The prior PRD's "no filtering" exclusion applies to message routing, not content-level sanitization.
- **Configuration flag** — No `sanitize_html = true/false` option. Unconditional application keeps the surface small.
- **New payload fields** — No `htmlClean` or `plainTextClean`. Existing fields are modified in-place.
- **Style/script stripping from plainText** — The `plainText` field gets entity unescaping only. Style/script blocks are HTML concepts that do not appear in `text/plain` MIME parts.
- **Performance optimization** — No streaming parser, no chunked processing. Bodies are fully decoded into memory before sanitization, which is acceptable for a cron-based tool processing one message at a time.
- **Raw HTML debugging endpoint** — No `--verbose` flag or alternate output mode for raw (unsanitized) payloads in this slice. Operators can inspect `.eml` files on disk.

## Further Notes

- This is the first decision recorded against the project that should be captured as an ADR. Consider writing `docs/adr/001-html-entity-sanitization.md` documenting the scope, rationale, and constraints established here.
- The `html.unescape()` function correctly decodes `&nbsp;` to U+00A0 (non-breaking space), not U+0020 (regular space). This preserves semantic intent; downstream consumers that need ASCII-space normalization can apply it themselves.
- Style/script block removal uses a non-greedy regex with the DOTALL flag. This handles the common case (well-formed tags) but will not handle deeply nested `<script>` tags with escaped HTML inside them — a pathological edge case that does not occur in real-world email HTML.
- If an operator discovers that sanitization breaks an existing workflow, the escape hatch is to inspect the original `.eml` file. A future issue can add a `--raw` CLI flag or a `sanitized: true` field to the payload.
