# ADR 001: HTML Entity Sanitization and Style/Script Stripping in Email Parser

## Status

Accepted

## Context

The OpenClaw mailbot parses RFC 2822 MIME email messages and forwards a JSON payload to downstream workflows. Two fields produced by the parser, `html` and `plainText`, frequently contain large amounts of non-content data that wastes tokens in LLM context windows:

- **HTML character references** such as `&nbsp;`, `&amp;`, `&lt;`, and numeric forms like `&#160;` / `&#x00A0;` expand to 5–8 ASCII characters in the JSON payload while encoding a single Unicode codepoint. Real-world marketing emails can contain hundreds of these references, turning whitespace and punctuation into unnecessary token volume.
- **`<style>` and `<script>` blocks** routinely account for 60–80% of the raw HTML body in marketing and newsletter emails. CSS rules and JavaScript source text are not visible document content, yet they pass through into the payload and consume context-window capacity that downstream workflows cannot use.

A forward-looking concern is format consistency: a later parser extension (e.g., `.msg` support) must feed its extracted bodies into the same sanitization pipeline so that both `.eml` and `.msg` sources produce the same payload contract. Establishing the pipeline as a first-class, documented decision makes that extension easier to reason about.

The project also operates under a **stdlib-only runtime** constraint (`pyproject.toml` declares zero runtime dependencies), so any solution must avoid third-party HTML libraries.

## Decision

We add two small, unconditional sanitization passes to `parse_email()` in `src/openclaw_mailbot/parser.py`, applied after body extraction and before payload assembly:

1. **HTML entity unescaping** is applied to both the `html` and `plainText` fields.
   - Named HTML5 character references (e.g., `&nbsp;`, `&amp;`, `&pound;`) and numeric/hex references (e.g., `&#160;`, `&#x00A0;`) are decoded to their Unicode codepoints.
   - Only **character references** are decoded; HTML structural tags (`<div>`, `<span>`, `<b>`, `<a>`, etc.) are preserved.
   - `&nbsp;` decodes to U+00A0 (non-breaking space), not U+0020 (regular space), preserving semantic intent.

2. **Style and script block removal** is applied only to the `html` field.
   - The entire `<style>...</style>` and `<script>...</script>` elements (opening tag, contents, and closing tag) are removed.
   - The surrounding HTML structure is left intact.
   - This pass runs **before** entity unescaping, so entities inside CSS/JS source text do not need to be decoded before being dropped.

Implementation details:

- Entity unescaping uses `html.unescape()` from the Python standard library.
- Style/script stripping uses a single compiled regular expression with `re.IGNORECASE | re.DOTALL` and non-greedy matching:
  ```python
  _STYLE_SCRIPT_RE = re.compile(
      r'<style[^>]*>.*?</style>|<script[^>]*>.*?</script>',
      re.IGNORECASE | re.DOTALL,
  )
  ```
- Sanitization modifies the existing `html` and `plainText` fields in-place; no new fields such as `htmlClean` or `plainTextClean` are introduced.
- Sanitization is applied unconditionally; there is no configuration flag to enable or disable it.

## Rationale

### Sanitization scope: both `html` and `plainText`

- **Alternative considered:** Unescape entities only in the `html` field.
- **Reasoning:** The `plainText` field comes from the email's `text/plain` MIME part, not from HTML-to-text conversion. Real-world senders — especially marketing platforms — often generate the plain-text alternative with `&nbsp;` and other entities intact. Cleaning only `html` would leave roughly half the entity waste in place. Both fields therefore receive the same `_sanitize_text()` pass.

### Entity unescaping only, no tag stripping

- **Alternative considered:** Strip all HTML tags and convert `html` to plain text.
- **Reasoning:** A prior product decision explicitly rejected HTML-to-text conversion. Structural tags such as `<b>`, `<a>`, `<div>`, and `<span>` may be relied on by downstream workflows for rendering hints, link extraction, or section boundaries. Decoding only character references preserves that structure while eliminating encoding overhead.

### Remove `<style>` and `<script>` blocks from `html`

- **Alternative considered:** Leave style/script blocks in place, or strip all tags indiscriminately.
- **Reasoning:** Style and script blocks are not visible document content and routinely dominate payload size. Removing them yields a large token reduction without affecting visible HTML structure. Removing only these two block types keeps the decision narrow and predictable, avoiding the broader behavioral change of full tag stripping.

### Remove the entire element, not just the contents

- **Alternative considered:** Replace only the block contents with an empty string while leaving the tags (`<style></style>`).
- **Reasoning:** Leaving empty tags adds no structural value and still carries a small amount of payload weight. Removing the full element produces a cleaner result and is simpler to express with a single regex substitution. The surrounding HTML remains structurally valid for downstream consumers.

### Use `html.unescape()` from the Python standard library

- **Alternatives considered:** A custom regex replacement; a third-party library such as `html5lib` or `BeautifulSoup`.
- **Reasoning:** `html.unescape()` correctly handles all HTML5 named entities and numeric/hex forms, is maintained inside CPython, runs in O(n) time, and requires no new dependencies. A custom regex would be slower, more fragile, and harder to maintain. Adding a third-party package would violate the project's stdlib-only constraint.

### Use a regex for style/script stripping

- **Alternative considered:** A subclass of `html.parser.HTMLParser` that drops tokens inside these blocks.
- **Reasoning:** A regex is sufficient for the common case of well-formed email HTML. The parser subclass would be more robust against pathological nesting, but real-world marketing emails do not contain nested or escaped `<script>` tags. The regex keeps the implementation small, stdlib-only, and easy to audit.

### Strip before unescaping

- **Alternative considered:** Unescape entities first, then strip style/script blocks.
- **Reasoning:** Running the strip first avoids decoding entities that live inside CSS/JS source text only to throw the decoded text away. This saves a small amount of work and avoids creating transient decoded strings that contain content we never intend to keep.

### Modify existing fields in-place, no new fields

- **Alternative considered:** Add `htmlClean` / `plainTextClean` fields alongside the originals.
- **Reasoning:** The mailbot is still a prototype and no downstream consumers depend on raw entity output. Adding parallel fields would enlarge the payload and the mental model for operators. If backward compatibility becomes necessary later, a `parserVersion` or `sanitized` flag can be added as a follow-up.

### Unconditional application, no config flag

- **Alternative considered:** Add a `sanitize_html = true/false` option in `config.ini`.
- **Reasoning:** The sanitization is simple, well-understood, and low-risk. A configuration flag would introduce parsing, documentation, and testing surface without adding meaningful flexibility. Operators who need unsanitized content can inspect the original `.eml` file on disk.

## Consequences

- **Payload contract:** The `html` and `plainText` fields now contain decoded Unicode characters rather than raw HTML entities. Consumers that previously parsed raw entities must be updated, although none existed at the time of this decision.
- **Backward compatibility:** This is a breaking change for any client expecting raw entities. Because the mailbot has no production consumers yet, the breaking change is acceptable and avoids carrying parallel fields.
- **Debugging:** Sanitization is lossy with respect to the raw message text. Operators can still inspect the original `.eml` file in the mailbox or on disk to see the pre-sanitization content. A future issue may add a `--raw` CLI flag or a `sanitized: true` payload marker if operational needs arise.
- **Performance:** Sanitization performs an O(n) pass over each body string. This is acceptable for a cron-based tool that processes one message at a time and does not stream bodies.
- **Format consistency:** The sanitization pipeline is explicitly documented as a shared stage after body extraction. Any future body source (for example, a `.msg` parser) can feed its output into the same `_sanitize_text()` / `_sanitize_html()` functions to guarantee identical payload behavior across input formats.
- **Edge-case behavior:** The regex-based style/script stripper handles well-formed tags but may behave unexpectedly on pathological input such as nested `<script>` blocks with escaped HTML. This is considered acceptable for real-world email HTML.
