"""Command-line entry point for the OpenClaw mailbot."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from openclaw_mailbot.config import Config
from openclaw_mailbot.parser import parse_email_json
from openclaw_mailbot.poll import create_forwarder, create_pop3_client, parse_only, poll, recover
from openclaw_mailbot.state import StateStore


def _cmd_parse(args: argparse.Namespace) -> int:
    """Handle the ``parse`` subcommand."""
    config = Config.load(args.config)
    if not args.eml_path.exists():
        print(f"Error: file not found: {args.eml_path}", file=sys.stderr)
        return 1
    print(parse_email_json(args.eml_path, config.data_dir))
    return 0


def _cmd_poll(args: argparse.Namespace) -> int:
    """Handle the ``poll`` subcommand."""
    config = Config.load(args.config)
    if not config.webhook_url:
        logging.getLogger(__name__).error("Missing [openclaw] webhook_url in config")
        return 1
    if not config.pop3_host:
        logging.getLogger(__name__).error("Missing [pop3] host in config")
        return 1

    state_store = StateStore(config.data_dir)
    pop3_client = create_pop3_client(config)
    forwarder = create_forwarder(config)
    poll(config, state_store, pop3_client, forwarder)
    return 0


def _cmd_test(args: argparse.Namespace) -> int:
    """Handle the ``test`` subcommand."""
    config = Config.load(args.config)
    if not config.pop3_host:
        logging.getLogger(__name__).error("Missing [pop3] host in config")
        return 1

    state_store = StateStore(config.data_dir)
    pop3_client = create_pop3_client(config)
    parse_only(config, state_store, pop3_client)
    return 0


def _cmd_recover(args: argparse.Namespace) -> int:
    """Handle the ``recover`` subcommand."""
    config = Config.load(args.config)
    if not config.webhook_url:
        logging.getLogger(__name__).error("Missing [openclaw] webhook_url in config")
        return 1

    state_store = StateStore(config.data_dir)
    forwarder = create_forwarder(config)
    recover(config, state_store, forwarder, uidl=args.uidl)
    return 0


def main(argv: list[str] | None = None) -> int:
    """Run the mailbot CLI."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    # Ensure stdout can emit UTF-8 payloads on all platforms.
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    parser = argparse.ArgumentParser(
        prog="openclaw-mailbot",
        description="POP3 mailbot that bridges incoming email to OpenClaw webhooks",
    )
    parser.add_argument(
        "--config",
        "-c",
        type=Path,
        default=None,
        help="Path to the INI configuration file",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    parse_cmd = subparsers.add_parser(
        "parse",
        help="Parse a local .eml file and emit the structured JSON payload",
    )
    parse_cmd.add_argument(
        "eml_path",
        type=Path,
        help="Path to the .eml file to parse",
    )
    parse_cmd.set_defaults(func=_cmd_parse)

    poll_cmd = subparsers.add_parser("poll", help="Poll the POP3 mailbox once")
    poll_cmd.set_defaults(func=_cmd_poll)

    test_cmd = subparsers.add_parser(
        "test",
        help="Connect to the POP3 server, parse all messages, and print payloads without forwarding",
    )
    test_cmd.set_defaults(func=_cmd_test)

    recover_cmd = subparsers.add_parser(
        "recover",
        help="Re-forward archived raw .eml files to the webhook",
    )
    recover_cmd.add_argument(
        "--uidl",
        type=str,
        default=None,
        help="Recover only the archived email with this UIDL (default: all archived emails)",
    )
    recover_cmd.set_defaults(func=_cmd_recover)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
