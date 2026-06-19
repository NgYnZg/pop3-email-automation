---
status: closed
type: AFK
estimate: S
domain: parsing
blockedBy:
---
## Parent

PRD: `.scratch/openclaw-mailbot/PRD.md`

## What to build

Add HTML entity unescaping to the email parser so that named and numeric character references in both the `html` and `plainText` fields are decoded to their Unicode codepoints before the payload is serialized.

Specifically:

1. Add a private module-level function `_sanitize_text(text: str) -> str` in `parser.py` that applies `html.unescape()` to decode all HTML5 named entities (e.g., `&amp;`, `&lt;`, `&gt;`, `&quot;`, `&nbsp;`) and all numeric/hex entities (e.g., `&#160;`, `&#x00A0;`).

2. Wire it into `parse_email()` immediately after `_extract_bodies()` returns — apply it to both `html` and `plainText` if they are not `None`.

3. Modify the existing test `test_html_only` (line asserting `"<b>HTML</b>"` in html) to account for unescaping if needed. Add a new fixture entity-aware test.

4. Create a new fixture `entities.eml` (add a `def entities()` generator to `tests/fixtures/generate.py`) containing a multipart/alternative email with both `text/plain` and `text/html` parts that include:
   - Named entities: `&amp;`, `&lt;`, `&gt;`, `&quot;`, `&nbsp;`, `&pound;`, `&euro;`
   - Numeric entities: `&#160;`, `&#x00A0;`
   - Regular text with no entities (to verify non-entity text passes through unchanged)
   - The HTML part should have a `<b>` tag around some content to verify structural tags survive

5. Add these test methods to `test_parser.py`:
   - `test_entities_plain_text` — opens `entities.eml`, asserts `plainText` field has decoded characters (e.g., `&amp;` → `&`, `&nbsp;` → `\u00A0`, `&pound;` → `£`)
   - `test_entities_html` — opens `entities.eml`, asserts `html` field has decoded characters alongside preserved HTML tags like `<b>`
   - `test_numeric_entities` — opens `entities.eml`, asserts `&#160;` and `&#x00A0;` both decode to `\u00A0`
   - `test_no_entities_unchanged` — opens `plain_only.eml` and `html_only.eml` (which have no entities), asserts `plainText` and `html` values match current expected output exactly (regression guard)

6. Regenerate affected fixture files by running `python tests/fixtures/generate.py`.

**Important constraints:**

- Only `src/openclaw_mailbot/parser.py` is modified. No changes to `poll.py`, `forwarder.py`, `cli.py`, `pop3.py`, `state.py`, or `config.py`.
- Use only Python stdlib — the `html` module's `unescape()` function. No third-party dependencies.
- Modify the existing `html` and `plainText` fields in-place. Do not add new fields like `htmlClean`.
- `&nbsp;` must decode to U+00A0 (non-breaking space), not U+0020 (regular space).
- Do NOT strip any HTML tags. Only decode character references.

## Acceptance criteria

- [ ] `_sanitize_text()` exists in `parser.py`, is called from `parse_email()` for both `html` and `plainText` fields
- [ ] `entities.eml` fixture exists with named and numeric entities in both MIME parts
- [ ] `test_entities_plain_text` passes: `&amp;` → `&`, `&nbsp;` → `\u00A0`, `&pound;` → `£`, `&euro;` → `€` in the plainText field
- [ ] `test_entities_html` passes: same entities decoded in html field, HTML structural tags (`<b>`, `<p>`, etc.) preserved
- [ ] `test_numeric_entities` passes: `&#160;` and `&#x00A0;` both decode to `\u00A0`
- [ ] `test_no_entities_unchanged` passes: `plain_only.eml` and `html_only.eml` output matches pre-sanitization expected values
- [ ] All existing parser tests continue to pass

## Blocked by

None — can start immediately.


---
**Batch processor update**: status changed to `closed` on 2026-06-19.
- Branch: `batch/openclaw-mailbot/openclaw-mailbot-01`
- Validation rounds: 1
- Result artifacts: `.pi\batch-processor\results\openclaw-mailbot-01`
- Summary: Added `_sanitize_text()` to `src/openclaw_mailbot/parser.py` using stdlib `html.unescape()`, wired it into `parse_email()` for both `html` and `plainText` immediately after `_extract_bodies()`, created the `entities()` fixture generator and `entities.eml` with named/numeric entities in both MIME parts, and added `test_entities_plain_text`, `test_entities_html`, `test_numeric_entities`, and `test_no_entities_unchanged` to `tests/test_parser.py`.
- Changed files: src/openclaw_mailbot/parser.py, tests/fixtures/generate.py, tests/test_parser.py, tests/fixtures/entities.eml
