# Design Context: .msg Compatible Parser

## 1. Domain Terms and Definitions

| Term | Current Definition | Source |
|------|-------------------|--------|
| **Parser** | The module responsible for turning a raw email source into the OpenClaw webhook payload dict. Currently assumes RFC 2822 MIME messages only. | `src/openclaw_mailbot/parser.py` |
| **Webhook payload** | A JSON-serializable dict with keys: `event`, `messageId`, `uidl`, `receivedAt`, `from`, `to`, `cc`, `subject`, `date`, optional `plainText`, optional `html`, and `attachments`. | `parser.py:parse_email()` |
| **.eml** | RFC 2822 / MIME message text format. The only format currently supported by the mailbot. | `README.md`, `parser.py` |
| **.msg** | Microsoft Outlook OLE Compound Document format (also called CFBF / Compound File Binary Format). A binary container format, structurally unrelated to RFC 2822. | External domain knowledge |
| **Attachment** | Any non-body MIME part saved to disk under `<data_dir>/attachments/<run-timestamp>/<identifier>/<filename>`, referenced in the payload by path. | `parser.py:_extract_attachments()` |
| **EmailParseError** | Custom `ValueError` raised when a source cannot be parsed. | `parser.py` |
| **Source parameter** | `parse_email()` accepts `BinaryIO \| Path \| str \| bytes`, all routed through `email.message_from_binary_file()`. | `parser.py:parse_email()` |
| **Stdlib-only constraint** | `pyproject.toml` declares `dependencies = []`. No third-party packages are allowed at runtime. | `pyproject.toml` |
| **POP3 transport** | Delivers raw RFC 2822 message bytes via `RETR`. .msg files do not arrive over standard POP3. | `src/openclaw_mailbot/pop3.py` |

## 2. Existing Architectural Decisions and Constraints

**No ADRs exist yet.** The repo has `docs/agents/domain.md` describing a single-context layout with `CONTEXT.md` + `docs/adr/`, but neither file exists. The only documented decisions are in the prior PRDs:

- **Stdlib-only runtime** — `pyproject.toml` declares zero runtime dependencies. The parser uses `email.message_from_binary_file`, `email.utils.parseaddr`, etc. This is a hard project constraint.
- **Payload contract** — The shape produced by `parse_email()` is fixed and consumed by `forwarder.py` and downstream OpenClaw workflows. Any new parser must produce the same keys and value types.
- **Source abstraction** — `parse_email()` already accepts bytes, paths, and file-like objects. This is the natural seam for adding .msg support.
- **CLI `parse` subcommand** — Currently named `parse` with an argument called `eml_path` and help text "Path to the .eml file to parse". It calls `parse_email_json()` directly.
- **Attachment storage** — Attachments are saved to local disk and referenced by path in the payload. The same behavior is expected for .msg attachments.
- **Leave-on-server / UIDL tracking** — POP3 fetches RFC 2822 bytes. .msg parsing is irrelevant to the POP3 poll path unless the source of messages changes.
- **HTML entity sanitization (pending)** — There is an in-flight PRD/issue set (`openclaw-mailbot`) to add HTML entity unescaping and style/script stripping. Any .msg parser work should consider whether it runs before or after that sanitization pipeline.

## 3. Likely Modules/Files That Will Change

| File | Change Reason |
|------|---------------|
| `src/openclaw_mailbot/parser.py` | Core change. The function must detect .msg vs .eml input and dispatch to a .msg parser implementation. It must still produce the same payload contract from Outlook properties and attachment streams. |
| `src/openclaw_mailbot/cli.py` | The `parse` subcommand argument is currently called `eml_path` and documented as .eml-only. Rename/generalize (e.g., `email_path`) and update help text. |
| `tests/test_parser.py` | Add tests for .msg fixture parsing: headers, body extraction, attachments, error handling for malformed .msg files. |
| `tests/fixtures/` | Add sample `.msg` fixture files (plain, HTML, mixed, with attachment, unicode). |
| `README.md` | Update "Parse a local .eml file" section to mention .msg support and any caveats. |
| `pyproject.toml` | If the project relaxes the stdlib-only constraint, a dependency would be added here. This is a major decision, not a trivial edit. |

**Unchanged (probably):** `poll.py`, `forwarder.py`, `pop3.py`, `state.py`, `config.py` — unless .msg support changes the ingestion transport (e.g., reading from a filesystem drop instead of POP3).

## 4. Gaps, Contradictions, and Open Questions

### 4.1 Contradiction: .msg cannot be parsed with the Python stdlib
The most significant constraint is the project's **stdlib-only** policy (`pyproject.toml: dependencies = []`). The .msg format is the Microsoft Outlook OLE Compound Document (CFBF) binary format. It requires parsing:

- Compound file header
- FAT and miniFAT allocation tables
- Directory entries (storage / stream tree)
- Named property streams (`__properties_version1.0`)
- Attachment objects (`__attach_version1.0_*`)
- Optional MIME conversion stream (`__substg1.0_3701000D`)

None of this is supported by the Python standard library. A correct, full-featured .msg parser is a large undertaking and would effectively become a runtime dependency shipped inside the repo.

### 4.2 Gap: POP3 does not deliver .msg files
The mailbot's primary purpose is polling a POP3 mailbox. POP3 `RETR` returns RFC 2822 messages. .msg files do not arrive via POP3. Adding .msg parsing makes sense only if:

1. The mailbot will also read .msg files from a local directory or filesystem drop, or
2. A different ingestion transport will be added later, or
3. The `parse` CLI subcommand is being promoted from a debugging helper to a general-purpose converter.

The request says "as well," which suggests option 3 (extend the parser/CLI), but this is ambiguous.

### 4.3 Gap: No dependency infrastructure exists
If the project relaxes the stdlib-only rule, there is no established process for choosing, pinning, or auditing dependencies. `uv.lock` currently only contains pytest and build tooling. Adding a .msg library (e.g., `extract_msg`, `msg-parser`, `compoundfiles`) would be the first runtime dependency.

### 4.4 Gap: The payload contract is built around MIME semantics
Current helpers (`_extract_bodies`, `_is_attachment`, `_extract_attachments`) assume an `email.message.Message` object. .msg uses a property-based model (MAPI / OLE properties like `PR_SUBJECT`, `PR_BODY`, `PR_HTML`, `PR_ATTACH_FILENAME`). Reusing the existing helpers is not possible without first converting .msg into a MIME-like structure or rewriting the extraction logic to operate on a normalized intermediate model.

### 4.5 Gap: Attachment handling differs between .eml and .msg
In RFC 2822, attachments are MIME parts with `Content-Disposition: attachment`. In .msg, attachments are separate storage objects inside the compound file with their own property streams. The current `_sanitized_filename()` and disk-write logic can likely be reused, but the traversal logic must be rewritten.

### 4.6 Open question: How should .msg detection work?
Options include:

- File extension sniffing (`.msg`)
- Magic-number / OLE header detection (`D0 CF 11 E0 A1 B1 1A E1`)
- Attempting RFC 2822 parse first, falling back to .msg parser

Extension sniffing is fragile; magic-number detection is more robust and matches the binary nature of the format.

### 4.7 Open question: What level of .msg fidelity is required?
Outlook .msg files can contain:

- Plain text body (`PR_BODY`)
- HTML body (`PR_HTML`)
- RTF body (`PR_RTF_COMPRESSED`)
- Named and resolved recipients (`PR_DISPLAY_TO`, `PR_DISPLAY_CC`, `PR_EMAIL_ADDRESS`)
- Multiple attachments with nested .msg attachments
- Embedded messages
- Transport headers when originally converted from MIME

A minimal parser can target plain/HTML bodies, top-level recipients, subject, date, and top-level attachments. A complete parser is substantially larger.

### 4.8 Open question: Relationship to pending HTML sanitization
The `openclaw-mailbot` PRD/issues add `_sanitize_text()` and `_sanitize_html()` to `parser.py`. If .msg parsing lands in the same module, the .msg body extraction must feed into the same sanitization pipeline so both formats receive identical treatment.

### 4.9 Contradiction: "As well" implies transparent dual-format support
The request is short: "Create a .msg compatible parser as well." This implies `parse_email()` should accept .msg input and produce the same payload. However, the CLI currently calls the argument `eml_path`, and the README says "Parse a local .eml file." These are minor naming/doc inconsistencies, but they signal that .msg was not in the original design.

## 5. Recommended Clarifications to Resolve

Before writing a PRD or implementation issues, the following questions should be answered:

1. **Ingestion scope:** Is .msg support for the CLI debugging path only, or will the mailbot also read .msg files from disk during polling?
2. **Dependency policy:** Can the project accept a third-party .msg parsing library, or must the solution remain stdlib-only?
3. **Minimum viable fidelity:** Which .msg features must work in the first slice (plain body, HTML body, attachments, recipients, CC, date, message ID)?
4. **Detection strategy:** Should detection be by file extension, OLE magic number, or both?
5. **Sequencing:** Should this wait until the pending HTML entity sanitization issues are merged so both formats share one sanitization pipeline?
