# Triage labels

This repo uses the default canonical triage role strings.

| Role | String | Meaning |
|------|--------|---------|
| Needs triage | `needs-triage` | Maintainer still needs to evaluate the issue |
| Needs info | `needs-info` | Waiting on the reporter for more information |
| Ready for agent | `ready-for-agent` | Fully specified and AFK-ready; an agent can pick it up with no human context |
| Ready for human | `ready-for-human` | Needs a human to implement |
| Won't fix | `wontfix` | Will not be actioned |

For local markdown issues, represent the current state in the frontmatter of `.scratch/<feature>/issue.md`:

```yaml
---
status: ready-for-agent
---
```
