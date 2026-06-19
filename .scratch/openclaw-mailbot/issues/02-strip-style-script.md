---
status: ready-for-agent
type: AFK
estimate: S
domain: parsing
blockedBy: ["openclaw-mailbot-01"]
---

## Parent

PRD: `.scratch/openclaw-mailbot/PRD.md`

## What to build

Add style/script block removal to the HTML sanitization pipeline so that the contents of `<style>...</style>` and `<script>...</script>` tags are stripped from the `html` field before entity unescaping.

Specifically:

1. Add a private module-level function `_strip_style_script(html: str) -> str` in `parser.py` that removes the contents (but not the tags themselves) of `<style>` and `<script>` blocks using a non-greedy regex with `re.IGNORECASE | re.DOTALL`:

   ```python
   _STYLE_SCRIPT_RE = re.compile(
       r'<style[^>]*>.*?</style>|<script[^>]*>.*?</script>',
       re.IGNORECASE | re.DOTALL,
   )
   ```

   The replacement should be the empty string `""`, effectively removing the entire tag pair including its contents.

2. Create a new function `_sanitize_html(text: str) -> str` that chains style/script stripping **before** entity unescaping:

   ```python
   def _sanitize_html(text: str) -> str:
       text = _strip_style_script(text)
       return _sanitize_text(text)
   ```

   (Where `_sanitize_text` is the entity unescaping function from issue 01.)

3. In `parse_email()`, change the `html` field sanitization path to use `_sanitize_html()` instead of `_sanitize_text()`:

   ```python
   if html is not None:
       html = _sanitize_html(html)
   if plain is not None:
       plain = _sanitize_text(plain)
   ```

4. Create a new fixture `style_script.eml` (add a `def style_script()` generator to `tests/fixtures/generate.py`) containing a `text/html` email with:
   - A `<style>` block with CSS rules (e.g., `.body { color: red; font-size: 14px; }`)
   - A `<script>` block with JS (e.g., `console.log("hello");`)
   - Visible HTML content around and between the blocks (e.g., `<p>Hello <b>world</b></p>`)
   - An HTML entity inside visible content (e.g., `&amp;`) to verify that entity unescaping still applies after stripping
   - Content-Type: text/html

5. Add these test methods to `test_parser.py`:
   - `test_style_script_stripped` — opens `style_script.eml`, asserts that the `html` field does NOT contain CSS source text or JS source text (e.g., `"color: red"` not present, `"console.log"` not present)
   - `test_html_structure_preserved` — opens `style_script.eml`, asserts that visible HTML structure survives — e.g., `<p>`, `<b>world</b>` are present in the output html
   - `test_style_script_entities` — opens `style_script.eml`, asserts that entities in non-style/script content are still decoded (`&amp;` → `&`)
   - `test_style_script_absent` — opens `mixed.eml` (no style/script blocks), asserts that the html field is unchanged by stripping (regression)

6. Regenerate affected fixture files by running `python tests/fixtures/generate.py`.

**Important constraints:**

- Only `parser.py` and test files are modified. No other modules.
- The regex matches the full `<style>...</style>` and `<script>...</script>` element including contents. The entire element is removed — both the tags and their contents — leaving the surrounding HTML structurally intact.
- Style/script stripping is NOT applied to `plainText`. Only entity unescaping (from issue 01) applies to plainText.
- Style/script removal happens BEFORE entity unescaping in the pipeline, so that entities inside CSS/JS source text don't need to be decoded before being dropped.

## Acceptance criteria

- [ ] `_strip_style_script()` and `_sanitize_html()` exist in `parser.py`
- [ ] `parse_email()` calls `_sanitize_html()` for the `html` field and `_sanitize_text()` for the `plainText` field
- [ ] `style_script.eml` fixture exists with CSS and JS blocks
- [ ] `test_style_script_stripped` passes: style/script block contents are absent from output html
- [ ] `test_html_structure_preserved` passes: non-style/script HTML tags survive
- [ ] `test_style_script_entities` passes: entities in visible content are still decoded
- [ ] `test_style_script_absent` passes: emails without style/script blocks are unaffected
- [ ] All existing parser tests continue to pass (including those from issue 01)

## Blocked by

- **openclaw-mailbot-01** — depends on `_sanitize_text()` being available and on the entity unescaping fixture infrastructure
