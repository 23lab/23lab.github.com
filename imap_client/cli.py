import argparse
import getpass
import os
import sys
from typing import List, Optional

from .client import IMAPClient


def positive_int(value: str) -> int:
    try:
        ivalue = int(value)
    except Exception:
        raise argparse.ArgumentTypeError("must be an integer")
    if ivalue <= 0:
        raise argparse.ArgumentTypeError("must be > 0")
    return ivalue


def add_common_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--host", required=True, help="IMAP server host")
    parser.add_argument("--port", type=int, default=993, help="IMAP server port (default 993)")
    parser.add_argument("--user", required=True, help="Username")
    parser.add_argument("--password", help="Password (use IMAP_PASSWORD env or prompt if omitted)")
    parser.add_argument("--no-ssl", action="store_true", help="Disable SSL (use IMAP on 143)")
    parser.add_argument("--starttls", action="store_true", help="Use STARTTLS after connecting (when --no-ssl)")
    parser.add_argument("--timeout", type=int, default=None, help="Socket timeout seconds")
    parser.add_argument("--debug", action="store_true", help="Enable imaplib debug output")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="imap_client",
        description="Simple IMAP client CLI",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # list-mailboxes
    p_list_mbx = subparsers.add_parser("list-mailboxes", help="List mailboxes")
    add_common_args(p_list_mbx)

    # list
    p_list = subparsers.add_parser("list", help="List messages in a mailbox")
    add_common_args(p_list)
    p_list.add_argument("--mailbox", default="INBOX", help="Mailbox name (default INBOX)")
    p_list.add_argument("--criteria", default="ALL", help="IMAP SEARCH criteria (default ALL)")
    p_list.add_argument("--limit", type=positive_int, default=50, help="Max messages to show (default 50)")

    # show
    p_show = subparsers.add_parser("show", help="Show one message headers")
    add_common_args(p_show)
    p_show.add_argument("--mailbox", default="INBOX")
    p_show.add_argument("--uid", type=int, required=True, help="Message UID")

    # download
    p_dl = subparsers.add_parser("download", help="Download attachments")
    add_common_args(p_dl)
    p_dl.add_argument("--mailbox", default="INBOX")
    p_dl.add_argument("--uid", type=int, required=True)
    p_dl.add_argument("--out", default=".", help="Destination directory")
    p_dl.add_argument("--name-contains", default=None, help="Only save attachments whose name contains substring")

    # mark
    p_mark = subparsers.add_parser("mark", help="Set flags on a message")
    add_common_args(p_mark)
    p_mark.add_argument("--mailbox", default="INBOX")
    p_mark.add_argument("--uid", type=int, required=True)
    p_mark.add_argument("--seen", choices=["true", "false"], help="Mark seen/unseen")
    p_mark.add_argument("--flagged", choices=["true", "false"], help="Mark flagged/unflagged")

    return parser


def get_password(args_password: Optional[str]) -> str:
    if args_password:
        return args_password
    env = os.getenv("IMAP_PASSWORD")
    if env:
        return env
    return getpass.getpass("IMAP password: ")


def make_client(args: argparse.Namespace) -> IMAPClient:
    password = get_password(args.password)
    return IMAPClient(
        host=args.host,
        port=args.port,
        username=args.user,
        password=password,
        use_ssl=not args.no_ssl,
        starttls=args.starttls,
        timeout=args.timeout,
        debug=args.debug,
    )


def cmd_list_mailboxes(args: argparse.Namespace) -> int:
    with make_client(args) as client:
        names = client.list_mailboxes()
        for name in names:
            print(name)
    return 0


def cmd_list(args: argparse.Namespace) -> int:
    with make_client(args) as client:
        uids = client.search_uids(args.mailbox, args.criteria)
        if not uids:
            return 0
        # Show latest first
        uids_sorted = sorted(uids, reverse=True)[: args.limit]
        items = client.fetch_overview(args.mailbox, uids_sorted)
        # Sort by the same order as uids_sorted
        order = {uid: i for i, uid in enumerate(uids_sorted)}
        items.sort(key=lambda x: order.get(x.get("uid", 0), 0))
        for it in items:
            uid = it.get("uid")
            flags = " ".join(it.get("flags", []))
            subj = it.get("subject", "")
            frm = it.get("from", "")
            date = it.get("date", "")
            print(f"{uid}\t{date}\t{frm}\t{subj}\t{flags}")
    return 0


def cmd_show(args: argparse.Namespace) -> int:
    from email import policy
    from email.parser import BytesParser

    with make_client(args) as client:
        msg = client.fetch_message(args.mailbox, args.uid)
        # Headers summary
        print(f"UID: {args.uid}")
        for key in ["From", "To", "Cc", "Date", "Subject"]:
            val = msg.get(key)
            if val:
                print(f"{key}: {val}")
        # Show text/plain part (if any)
        text = None
        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_type() == "text/plain":
                    text = part.get_payload(decode=True)
                    charset = part.get_content_charset() or "utf-8"
                    try:
                        print()
                        print(text.decode(charset, errors="replace"))
                    except Exception:
                        print()
                        print(text.decode("utf-8", errors="replace"))
                    break
        else:
            if msg.get_content_type() == "text/plain":
                text = msg.get_payload(decode=True)
                charset = msg.get_content_charset() or "utf-8"
                print()
                print(text.decode(charset, errors="replace"))
    return 0


def cmd_download(args: argparse.Namespace) -> int:
    with make_client(args) as client:
        saved = client.download_attachments(args.mailbox, args.uid, args.out, args.name_contains)
        for path in saved:
            print(path)
    return 0


def cmd_mark(args: argparse.Namespace) -> int:
    seen = None if args.seen is None else (args.seen == "true")
    flagged = None if args.flagged is None else (args.flagged == "true")
    with make_client(args) as client:
        client.set_flags(args.mailbox, args.uid, seen=seen, flagged=flagged)
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "list-mailboxes":
            return cmd_list_mailboxes(args)
        if args.command == "list":
            return cmd_list(args)
        if args.command == "show":
            return cmd_show(args)
        if args.command == "download":
            return cmd_download(args)
        if args.command == "mark":
            return cmd_mark(args)
        parser.error("unknown command")
        return 2
    except KeyboardInterrupt:
        print("Interrupted", file=sys.stderr)
        return 130
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())