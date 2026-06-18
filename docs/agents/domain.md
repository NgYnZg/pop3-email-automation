# Domain docs

## Layout

This repo uses a **single-context** layout.

- `CONTEXT.md` at the repo root describes the project's domain language and boundaries.
- `docs/adr/` contains architecture decision records.

## Consumer rules

When a skill needs domain context:

1. Read `CONTEXT.md` at the repo root.
2. If the request touches an architectural decision, read the relevant ADRs in `docs/adr/`.
3. Prefer the language and boundaries defined in `CONTEXT.md` when proposing changes.
