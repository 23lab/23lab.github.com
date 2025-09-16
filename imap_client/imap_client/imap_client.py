from __future__ import annotations

import contextlib
import email
import email.policy
import imaplib
import os
import re
import socket
import ssl
from dataclasses import dataclass
from typing import Iterable, List, Optional, Sequence, Tuple


@dataclass
class ImapConfig:
    host: str
    port: int = 993
    use_ssl: bool = True
    use_starttls: bool = False
    username: Optional[str] = None
    password: Optional[str] = None
    timeout_seconds: int = 30


class ImapError(RuntimeError):
    pass


class ImapClient:
    def __init__(self, config: ImapConfig) -> None:
        self.config = config
        self._conn: Optional[imaplib.IMAP4] = None

    # ----- Connection management -----
    def connect(self) -> None:
        try:
            socket.setdefaulttimeout(self.config.timeout_seconds)
            if self.config.use_ssl:
                self._conn = imaplib.IMAP4_SSL(self.config.host, self.config.port)
            else:
                self._conn = imaplib.IMAP4(self.config.host, self.config.port)
                if self.config.use_starttls:
                    self._conn.starttls(ssl_context=ssl.create_default_context())

            if self.config.username:
                self.login(self.config.username, self.config.password or "")
        except (imaplib.IMAP4.error, socket.timeout, OSError) as exc:
            raise ImapError(f"Failed to connect/login: {exc}") from exc

    def login(self, username: str, password: str) -> None:
        self._ensure_conn()
        try:
            assert self._conn is not None
            typ, _ = self._conn.login(username, password)
            if typ != "OK":
                raise ImapError("Login failed")
        except imaplib.IMAP4.error as exc:
            raise ImapError(f"Login failed: {exc}") from exc

    def logout(self) -> None:
        if self._conn is not None:
            with contextlib.suppress(Exception):
                self._conn.logout()
            self._conn = None

    def _ensure_conn(self) -> None:
        if self._conn is None:
            raise ImapError("Not connected")

    # ----- Mailboxes -----
    def list_mailboxes(self) -> List[str]:
        self._ensure_conn()
        assert self._conn is not None
        typ, data = self._conn.list()
        if typ != "OK":
            raise ImapError("LIST failed")
        mailboxes: List[str] = []
        for line in data or []:
            if not line:
                continue
            decoded = line.decode(errors="ignore")
            # Format: (* FLAGS) "/" "INBOX"
            m = re.search(r"\"([^\"]+)\"\s*$", decoded)
            if m:
                mailboxes.append(m.group(1))
            else:
                # Fallback to last token
                mailboxes.append(decoded.split()[-1].strip('"'))
        return mailboxes

    def ensure_selected(self, mailbox: str) -> Tuple[str, List[bytes]]:
        self._ensure_conn()
        assert self._conn is not None
        typ, data = self._conn.select(mailbox, readonly=False)
        if typ != "OK":
            raise ImapError(f"SELECT {mailbox} failed")
        return typ, data

    # ----- Search / List -----
    def search(self, mailbox: str, criteria: Sequence[str]) -> List[int]:
        self.ensure_selected(mailbox)
        assert self._conn is not None
        typ, data = self._conn.search(None, *criteria)
        if typ != "OK":
            raise ImapError(f"SEARCH failed: {' '.join(criteria)}")
        if not data or not data[0]:
            return []
        uids = [int(x) for x in data[0].split()]
        return uids

    def list_messages(
        self,
        mailbox: str,
        limit: Optional[int] = None,
        unseen: bool = False,
        since: Optional[str] = None,
        before: Optional[str] = None,
    ) -> List[int]:
        criteria: List[str] = ["UID", "1:*"]
        if unseen:
            criteria.append("UNSEEN")
        if since:
            criteria.extend(["SINCE", since])
        if before:
            criteria.extend(["BEFORE", before])
        uids = self.search(mailbox, criteria)
        uids.sort(reverse=True)
        if limit is not None:
            uids = uids[:limit]
        uids.sort()
        return uids

    # ----- Fetch -----
    def fetch_headers(self, mailbox: str, uid: int) -> str:
        self.ensure_selected(mailbox)
        assert self._conn is not None
        typ, data = self._conn.uid("FETCH", str(uid), "(BODY.PEEK[HEADER])")
        if typ != "OK" or not data or not isinstance(data[0], tuple):
            raise ImapError("FETCH headers failed")
        raw = data[0][1]
        msg = email.message_from_bytes(raw, policy=email.policy.default)
        return msg.as_string()

    def fetch_body_text(self, mailbox: str, uid: int) -> str:
        self.ensure_selected(mailbox)
        assert self._conn is not None
        typ, data = self._conn.uid("FETCH", str(uid), "(BODY.PEEK[])")
        if typ != "OK" or not data or not isinstance(data[0], tuple):
            raise ImapError("FETCH body failed")
        raw = data[0][1]
        msg = email.message_from_bytes(raw, policy=email.policy.default)

        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                disposition = part.get_content_disposition()
                if disposition == "attachment":
                    continue
                if content_type == "text/plain":
                    return part.get_content()
            # Fallback to first non-attachment part
            for part in msg.walk():
                if part.get_content_disposition() == "attachment":
                    continue
                try:
                    return part.get_content()
                except Exception:
                    continue
            return ""
        else:
            return msg.get_content()

    # ----- Flags / Move / Delete -----
    def add_flags(self, mailbox: str, uids: Iterable[int], flags: Sequence[str]) -> None:
        self.ensure_selected(mailbox)
        assert self._conn is not None
        uid_set = ",".join(str(u) for u in uids)
        flag_list = "(" + " ".join(flags) + ")"
        typ, _ = self._conn.uid("STORE", uid_set, "+FLAGS.SILENT", flag_list)
        if typ != "OK":
            raise ImapError("ADD flags failed")

    def remove_flags(self, mailbox: str, uids: Iterable[int], flags: Sequence[str]) -> None:
        self.ensure_selected(mailbox)
        assert self._conn is not None
        uid_set = ",".join(str(u) for u in uids)
        flag_list = "(" + " ".join(flags) + ")"
        typ, _ = self._conn.uid("STORE", uid_set, "-FLAGS.SILENT", flag_list)
        if typ != "OK":
            raise ImapError("REMOVE flags failed")

    def move(self, mailbox: str, uids: Iterable[int], destination_mailbox: str) -> None:
        self.ensure_selected(mailbox)
        assert self._conn is not None
        uid_set = ",".join(str(u) for u in uids)
        # Try MOVE extension
        typ, _ = self._conn.uid("MOVE", uid_set, destination_mailbox)
        if typ == "OK":
            return
        # Fallback: COPY + delete + expunge
        typ, _ = self._conn.uid("COPY", uid_set, destination_mailbox)
        if typ != "OK":
            raise ImapError("COPY failed during move")
        self.add_flags(mailbox, [int(u) for u in uid_set.split(",")], ["\\Deleted"])
        self.expunge(mailbox)

    def delete(self, mailbox: str, uids: Iterable[int]) -> None:
        self.ensure_selected(mailbox)
        self.add_flags(mailbox, uids, ["\\Deleted"])

    def expunge(self, mailbox: str) -> None:
        self.ensure_selected(mailbox)
        assert self._conn is not None
        typ, _ = self._conn.expunge()
        if typ != "OK":
            raise ImapError("EXPUNGE failed")


def load_config_from_env(overrides: Optional[dict] = None) -> ImapConfig:
    cfg = ImapConfig(
        host=os.environ.get("IMAP_HOST", ""),
        port=int(os.environ.get("IMAP_PORT", "993")),
        use_ssl=os.environ.get("IMAP_SSL", "1") == "1",
        use_starttls=os.environ.get("IMAP_STARTTLS", "0") == "1",
        username=os.environ.get("IMAP_USER"),
        password=os.environ.get("IMAP_PASSWORD"),
        timeout_seconds=int(os.environ.get("IMAP_TIMEOUT", "30")),
    )
    if overrides:
        for key, value in overrides.items():
            if hasattr(cfg, key):
                setattr(cfg, key, value)
    return cfg

