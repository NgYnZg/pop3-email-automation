---
status: ready-for-human
type: HITL
estimate: XS
domain: documentation
blockedBy: ["openclaw-mailbot-01", "openclaw-mailbot-02"]
---

## Parent

PRD: `.scratch/openclaw-mailbot/PRD.md`

## What to build

Write an Architecture Decision Record (ADR) documenting the HTML entity sanitization and style/script stripping decisions established in the PRD and implemented in issues 01 and 02.

Create the file at `docs/adr/001-html-entity-sanitization.md`.

The ADR must cover:

1. **Context**: Why entity unescaping and style/script stripping are needed (token waste in LLM contexts, real-world email analysis showing `&nbsp;` density and CSS/JS size in marketing emails).

2. **Decision**: 
   - Entity unescaping applies to both `html` and `plainText` fields
   - Only HTML character references are decoded — tags are not stripped
   - Exception: `<style>` and `<script>` block contents are removed from the `html` field
   - Style/script removal targets the entire element (tags + contents), not just contents
   - Implementation uses `html.unescape()` from Python stdlib (no third-party deps)
   - Style/script stripping uses a non-greedy regex with `re.DOTALL | re.IGNORECASE`
   - Sanitization is applied unconditionally (no config flag) to existing fields in-place

3. **Rationale**: For each decision point, explain the alternatives considered and why this choice was made (referencing the domain context responses that informed the decisions).

4. **Consequences**: 
   - Payload contract: `html` and `plainText` fields now contain decoded characters
   - Backward compatibility: breaking change for any client that expects raw entities (none exist yet at time of writing)
   - Debugging: operators can inspect original `.eml` files for unsanitized content
   - Performance: O(n) pass over body strings, acceptable for cron-based single-message processing

5. **Status**: Accepted

Use the standard ADR format (Michael Nygard's template, which is the convention in this project).

## Acceptance criteria

- [ ] `docs/adr/001-html-entity-sanitization.md` exists and is well-formatted
- [ ] All five ADR sections (Context, Decision, Rationale, Consequences, Status) are present
- [ ] Each decision point includes the alternatives considered and the reasoning for the choice
- [ ] References the domain context questions that informed the decisions (e.g., sanitization scope, entity-only vs tag stripping, stdlib vs regex, unconditional vs configurable)
- [ ] A human reviewer can read and understand the architectural decisions without reading the PRD or implementation code

## Blocked by

- **openclaw-mailbot-01** — sanitize entities implementation must be accepted so the ADR reflects final code behavior
- **openclaw-mailbot-02** — style/script stripping implementation must be accepted for the same reason
