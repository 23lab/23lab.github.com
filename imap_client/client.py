import imaplib
import ssl
import os
import re
from typing import Iterable, List, Optional, Tuple, Dict, Any
from email import message_from_bytes
from email.header import decode_header
from email.message import Message


def decode_mime_words(value: Optional[str]) -> str:
    if not value:
        return ""
    decoded_parts: List[str] = []
    for bytes_or_str, encoding in decode_header(value):
        if isinstance(bytes_or_str, bytes):
            try:
                decoded_parts.append(bytes_or_str.decode(encoding or "utf-8", errors="replace"))
            except LookupError:
                decoded_parts.append(bytes_or_str.decode("utf-8", errors="replace"))
        else:
            decoded_parts.append(bytes_or_str)
    return "".join(decoded_parts)


def sanitize_filename(filename: str) -> str:
    # Remove directory separators and control chars
    filename = re.sub(r"[\\/\0\r\n\t]", "_", filename)
    filename = filename.strip() or "attachment.bin"
    return filename


class IMAPClient:
    """Thin wrapper around imaplib for common IMAP operations."""

    def __init__(
        self,
        host: str,
        port: int,
        username: str,
        password: str,
        use_ssl: bool = True,
        starttls: bool = False,
        timeout: Optional[int] = None,
        debug: bool = False,
    ) -> None:
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.use_ssl = use_ssl
        self.starttls = starttls
        self.timeout = timeout
        self.debug = debug
        self._conn: Optional[imaplib.IMAP4] = None

    # Context manager support
    def __enter__(self) -> "IMAPClient":
        return self.connect()

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    # Connection management
    def connect(self) -> "IMAPClient":
        if self._conn is not None:
            return self
        if self.use_ssl:
            context = ssl.create_default_context()
            conn = imaplib.IMAP4_SSL(self.host, self.port, ssl_context=context, timeout=self.timeout)
        else:
            conn = imaplib.IMAP4(self.host, self.port, timeout=self.timeout)
            if self.starttls:
                context = ssl.create_default_context()
                conn.starttls(ssl_context=context)
        if self.debug:
            conn.debug = 4
        conn.login(self.username, self.password)
        self._conn = conn
        return self

    def close(self) -> None:
        if self._conn is None:
            return
        try:
            try:
                self._conn.close()
            except Exception:
                # Might already be closed or no mailbox selected
                pass
            self._conn.logout()
        finally:
            self._conn = None

    # Helpers
    def _ensure_conn(self) -> imaplib.IMAP4:
        if self._conn is None:
            raise RuntimeError("Not connected. Call connect() first.")
        return self._conn

    def select_mailbox(self, mailbox: str, readonly: bool = True) -> int:
        conn = self._ensure_conn()
        status, data = conn.select(mailbox, readonly=readonly)
        if status != "OK":
            raise RuntimeError(f"Failed to select mailbox {mailbox}: {status}")
        try:
            return int(data[0])
        except Exception:
            return 0

    def list_mailboxes(self) -> List[str]:
        conn = self._ensure_conn()
        status, data = conn.list()
        if status != "OK":
            raise RuntimeError("Failed to list mailboxes")
        names: List[str] = []
        if data is None:
            return names
        for raw in data:
            if not raw:
                continue
            # raw example: b'(\\HasNoChildren) "/" "INBOX"'
            line = raw.decode("utf-8", errors="replace")
            # Extract last quoted string
            match = re.search(r'"((?:\\.|[^"\\])*)"\s*$', line)
            if match:
                mailbox = match.group(1).encode("utf-8").decode("unicode_escape")
                names.append(mailbox)
            else:
                # Fallback to last token
                parts = line.split(" ")
                names.append(parts[-1].strip('"'))
        return names

    def search_uids(self, mailbox: str, criteria: str = "ALL") -> List[int]:
        conn = self._ensure_conn()
        self.select_mailbox(mailbox, readonly=True)
        status, data = conn.uid("search", None, criteria)
        if status != "OK" or not data:
            return []
        ids_str = data[0].decode("utf-8", errors="replace").strip()
        if not ids_str:
            return []
        return [int(x) for x in ids_str.split()]

    def fetch_overview(self, mailbox: str, uids: Iterable[int]) -> List[Dict[str, Any]]:
        uids_list = list(uids)
        if not uids_list:
            return []
        conn = self._ensure_conn()
        self.select_mailbox(mailbox, readonly=True)
        set_str = ",".join(str(u) for u in uids_list)
        status, data = conn.uid(
            "fetch",
            set_str,
            "(FLAGS BODY.PEEK[HEADER.FIELDS (SUBJECT FROM DATE MESSAGE-ID)])",
        )
        if status != "OK" or not data:
            return []
        # Parse alternating tuples in data
        results: List[Dict[str, Any]] = []
        current: Dict[str, Any] = {}
        for item in data:
            if item is None:
                continue
            if isinstance(item, tuple) and len(item) == 2:
                meta_bytes, payload = item
                meta = meta_bytes.decode("utf-8", errors="replace")
                # Extract UID
                m = re.search(r"UID (\d+)", meta)
                if m:
                    uid = int(m.group(1))
                    current = {"uid": uid, "flags": [], "subject": "", "from": "", "date": ""}
                    # Parse header
                    msg = message_from_bytes(payload)
                    current["subject"] = decode_mime_words(msg.get("Subject"))
                    current["from"] = decode_mime_words(msg.get("From"))
                    current["date"] = msg.get("Date", "")
                    results.append(current)
                else:
                    # FLAGS-only or unexpected chunk
                    if "FLAGS" in meta and results:
                        flags_match = re.search(r"FLAGS \(([^)]*)\)", meta)
                        if flags_match:
                            flags_raw = flags_match.group(1).strip()
                            results[-1]["flags"] = flags_raw.split() if flags_raw else []
            elif isinstance(item, bytes):
                # Some servers interleave FLAGS bytes lines. Attach to last.
                meta = item.decode("utf-8", errors="replace")
                if "FLAGS" in meta and results:
                    flags_match = re.search(r"FLAGS \(([^)]*)\)", meta)
                    if flags_match:
                        flags_raw = flags_match.group(1).strip()
                        results[-1]["flags"] = flags_raw.split() if flags_raw else []
        return results

    def fetch_message(self, mailbox: str, uid: int) -> Message:
        conn = self._ensure_conn()
        self.select_mailbox(mailbox, readonly=True)
        status, data = conn.uid("fetch", str(uid), "(RFC822)")
        if status != "OK" or not data or not isinstance(data[0], tuple):
            raise RuntimeError(f"Failed to fetch message UID {uid}")
        raw = data[0][1]
        return message_from_bytes(raw)

    def download_attachments(
        self, mailbox: str, uid: int, dest_dir: str, only_substr: Optional[str] = None
    ) -> List[str]:
        os.makedirs(dest_dir, exist_ok=True)
        msg = self.fetch_message(mailbox, uid)
        saved_paths: List[str] = []
        for part in msg.walk():
            content_disposition = part.get_content_disposition()
            if content_disposition not in ("attachment", "inline"):
                continue
            filename = part.get_filename()
            if not filename:
                # Derive from content type
                maintype, subtype = (part.get_content_type() or "application/octet-stream").split("/", 1)
                filename = f"attachment.{subtype}"
            filename = decode_mime_words(filename)
            filename = sanitize_filename(filename)
            if only_substr and only_substr.lower() not in filename.lower():
                continue
            payload = part.get_payload(decode=True)
            if payload is None:
                continue
            full_path = os.path.join(dest_dir, filename)
            # Avoid overwrite by appending (n)
            base, ext = os.path.splitext(full_path)
            counter = 1
            candidate = full_path
            while os.path.exists(candidate):
                candidate = f"{base} ({counter}){ext}"
                counter += 1
            with open(candidate, "wb") as f:
                f.write(payload)
            saved_paths.append(candidate)
        return saved_paths

    def set_flags(
        self,
        mailbox: str,
        uid: int,
        seen: Optional[bool] = None,
        flagged: Optional[bool] = None,
    ) -> None:
        if seen is None and flagged is None:
            return
        conn = self._ensure_conn()
        self.select_mailbox(mailbox, readonly=False)
        if seen is not None:
            flag = r"(\\Seen)"
            if seen:
                conn.uid("store", str(uid), "+FLAGS.SILENT", flag)
            else:
                conn.uid("store", str(uid), "-FLAGS.SILENT", flag)
        if flagged is not None:
            flag = r"(\\Flagged)"
            if flagged:
                conn.uid("store", str(uid), "+FLAGS.SILENT", flag)
            else:
                conn.uid("store", str(uid), "-FLAGS.SILENT", flag)