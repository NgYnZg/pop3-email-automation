# Issue tracker

This repo uses a **local markdown** issue tracker.

## Where issues live

Issues are stored as markdown files under `.scratch/<feature>/`.

- Each feature or bug-fix gets its own directory under `.scratch/`.
- Each directory contains:
  - `issue.md` — the main issue description.
  - Optional supporting files (`notes.md`, `repro.md`, etc.).
- Use the directory name as the issue identifier.

## Creating an issue

Create a new directory under `.scratch/<feature>/` and write the issue to `issue.md`. Use a short kebab-case feature name.

## Listing issues

List all issue directories under `.scratch/`.

## Reading an issue

Read `.scratch/<feature>/issue.md`.

## Updating an issue

Edit the markdown files in `.scratch/<feature>/` directly.
