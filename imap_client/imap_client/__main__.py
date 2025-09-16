from __future__ import annotations

import argparse
import os
import sys
from typing import List

from .imap_client import ImapClient, ImapConfig, ImapError, load_config_from_env


def parse_uids(uids_csv: str) -> List[int]:
    if not uids_csv:
        return []
    return [int(x) for x in uids_csv.split(',') if x.strip()]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="imap-client", description="IMAP mail client CLI")
    parser.add_argument("--host", default=os.environ.get("IMAP_HOST"), help="IMAP host")
    parser.add_argument("--port", type=int, default=int(os.environ.get("IMAP_PORT", "993")), help="IMAP port")
    parser.add_argument("--ssl", type=int, choices=[0, 1], default=int(os.environ.get("IMAP_SSL", "1")), help="Use SSL (default 1)")
    parser.add_argument("--starttls", type=int, choices=[0, 1], default=int(os.environ.get("IMAP_STARTTLS", "0")), help="Use STARTTLS")
    parser.add_argument("--user", default=os.environ.get("IMAP_USER"), help="Username")
    parser.add_argument("--password", default=os.environ.get("IMAP_PASSWORD"), help="Password")
    parser.add_argument("--timeout", type=int, default=int(os.environ.get("IMAP_TIMEOUT", "30")), help="Socket timeout seconds")

    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("mailboxes", help="List mailboxes")

    list_p = sub.add_parser("list", help="List message UIDs in a mailbox")
    list_p.add_argument("--mailbox", default="INBOX")
    list_p.add_argument("--limit", type=int, default=50)
    list_p.add_argument("--unseen", action="store_true")
    list_p.add_argument("--since", help="Since date in format 01-Jan-2024")
    list_p.add_argument("--before", help="Before date in format 01-Jan-2024")

    show_p = sub.add_parser("show", help="Show message headers/body")
    show_p.add_argument("--mailbox", default="INBOX")
    show_p.add_argument("--uid", type=int, required=True)
    show_p.add_argument("--headers", action="store_true")
    show_p.add_argument("--body", action="store_true")

    flags_add = sub.add_parser("flag-add", help="Add flags to messages")
    flags_add.add_argument("--mailbox", default="INBOX")
    flags_add.add_argument("--uids", required=True, help="CSV of UIDs")
    flags_add.add_argument("--flags", required=True, help="Space-separated flags, e.g. \\Seen \\Flagged")

    flags_rm = sub.add_parser("flag-remove", help="Remove flags from messages")
    flags_rm.add_argument("--mailbox", default="INBOX")
    flags_rm.add_argument("--uids", required=True)
    flags_rm.add_argument("--flags", required=True)

    move_p = sub.add_parser("move", help="Move messages to another mailbox")
    move_p.add_argument("--mailbox", default="INBOX")
    move_p.add_argument("--uids", required=True)
    move_p.add_argument("--to", required=True, dest="destination")

    del_p = sub.add_parser("delete", help="Mark messages as deleted")
    del_p.add_argument("--mailbox", default="INBOX")
    del_p.add_argument("--uids", required=True)

    expunge_p = sub.add_parser("expunge", help="Permanently remove messages marked as deleted")
    expunge_p.add_argument("--mailbox", default="INBOX")

    return parser


def create_client_from_args(args: argparse.Namespace) -> ImapClient:
    overrides = {
        "host": args.host,
        "port": args.port,
        "use_ssl": bool(args.ssl),
        "use_starttls": bool(args.starttls),
        "username": args.user,
        "password": args.password,
        "timeout_seconds": args.timeout,
    }
    cfg = load_config_from_env(overrides)
    if not cfg.host:
        raise SystemExit("--host is required (or set IMAP_HOST)")
    return ImapClient(cfg)


def main(argv: List[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    client = create_client_from_args(args)
    try:
        client.connect()

        if args.command == "mailboxes":
            for m in client.list_mailboxes():
                print(m)
            return 0

        if args.command == "list":
            uids = client.list_messages(
                mailbox=args.mailbox,
                limit=args.limit,
                unseen=args.unseen,
                since=args.since,
                before=args.before,
            )
            for u in uids:
                print(u)
            return 0

        if args.command == "show":
            if args.headers:
                print(client.fetch_headers(args.mailbox, args.uid))
            if args.body:
                print(client.fetch_body_text(args.mailbox, args.uid))
            if not args.headers and not args.body:
                print(client.fetch_headers(args.mailbox, args.uid))
                print()
                print(client.fetch_body_text(args.mailbox, args.uid))
            return 0

        if args.command == "flag-add":
            client.add_flags(args.mailbox, parse_uids(args.uids), args.flags.split())
            return 0

        if args.command == "flag-remove":
            client.remove_flags(args.mailbox, parse_uids(args.uids), args.flags.split())
            return 0

        if args.command == "move":
            client.move(args.mailbox, parse_uids(args.uids), args.destination)
            return 0

        if args.command == "delete":
            client.delete(args.mailbox, parse_uids(args.uids))
            return 0

        if args.command == "expunge":
            client.expunge(args.mailbox)
            return 0

        parser.error("Unknown command")
        return 2

    except ImapError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    finally:
        client.logout()


if __name__ == "__main__":
    raise SystemExit(main())

