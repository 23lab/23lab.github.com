IMAP Mail Client (CLI)

Simple Python IMAP CLI client using the standard library. Supports listing mailboxes, searching messages, showing headers/body, flag operations, moving and deleting messages.

Quick start

1) Ensure Python 3.9+ is installed.
2) No third-party dependencies required.

Environment variables (optional)

- IMAP_HOST
- IMAP_PORT
- IMAP_SSL ("1" or "0")
- IMAP_STARTTLS ("1" or "0")
- IMAP_USER
- IMAP_PASSWORD

Usage

List available commands:

```bash
python -m imap_client --help
```

Examples

```bash
# List mailboxes
python -m imap_client --host imap.example.com --ssl 1 --user alice --password secret mailboxes

# List unseen messages in INBOX, limiting to 20
python -m imap_client --host imap.example.com --ssl 1 --user alice --password secret list --mailbox INBOX --unseen --limit 20

# Show a message by UID with headers and text body
python -m imap_client --host imap.example.com --ssl 1 --user alice --password secret show --mailbox INBOX --uid 12345 --headers --body

# Move messages to Archive
python -m imap_client --host imap.example.com --ssl 1 --user alice --password secret move --mailbox INBOX --uids 12345,12346 --to Archive

# Delete and expunge
python -m imap_client --host imap.example.com --ssl 1 --user alice --password secret delete --mailbox INBOX --uids 12345,12346
python -m imap_client --host imap.example.com --ssl 1 --user alice --password secret expunge --mailbox INBOX
```

Security

- Prefer using app-specific passwords or environment variables. Avoid passing credentials via shell history when possible.

