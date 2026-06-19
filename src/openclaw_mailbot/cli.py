"""Command-line interface for the OpenClaw mailbot."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .config import Config
from .parser import parse_email_json


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="openclaw-mailbot",
        description="Bridge POP3 email to OpenClaw webhooks.",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=None,
        help="Path to an INI configuration file.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    parse_cmd = subparsers.add_parser(
        "parse",
        help="Parse a local .eml file and emit the structured JSON payload.",
    )
    parse_cmd.add_argument(
        "eml_path",
        type=Path,
        help="Path to the .eml file to parse.",
    )

    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the CLI and return an exit code."""
    # Ensure stdout can emit UTF-8 payloads on all platforms.
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    args = _build_parser().parse_args(argv)

    config = Config.load(args.config)

    if args.command == "parse":
        if not args.eml_path.exists():
            print(f"Error: file not found: {args.eml_path}", file=sys.stderr)
            return 1
        print(parse_email_json(args.eml_path, config.data_dir))
        return 0

    return 2


if __name__ == "__main__":
    raise SystemExit(main())
