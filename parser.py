"""
Parse WhatsApp .txt chat exports into a list of Message objects.

Supports both Android and iOS export formats, 12/24-hour time,
multi-line messages, system messages, and media attachment lines.
"""

import re
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class Message:
    timestamp: datetime
    sender: str                         # empty string for system messages
    text: str
    is_system: bool = False
    media_filename: Optional[str] = None  # filename if line is a media attachment


# ---------------------------------------------------------------------------
# Regex patterns
# ---------------------------------------------------------------------------

# Android: "23/04/2021, 14:23 - Sender: text"
#          "4/23/21, 2:23 PM - Sender: text"
_ANDROID_RE = re.compile(
    r"^(\d{1,2}/\d{1,2}/\d{2,4}),\s"
    r"(\d{1,2}:\d{2}(?::\d{2})?(?:\s?[AP]M)?)"
    r"\s-\s"
    r"(.+?):\s(.*)$"
)

# Android system message (no "Sender: " part)
_ANDROID_SYS_RE = re.compile(
    r"^(\d{1,2}/\d{1,2}/\d{2,4}),\s"
    r"(\d{1,2}:\d{2}(?::\d{2})?(?:\s?[AP]M)?)"
    r"\s-\s(.+)$"
)

# iOS: "[23/04/2021, 14:23:45] Sender: text"  (optional leading LTR mark ‎)
_IOS_RE = re.compile(
    r"^‎?\[(\d{1,2}/\d{1,2}/\d{2,4}),\s"
    r"(\d{1,2}:\d{2}(?::\d{2})?(?:\s?[AP]M)?)\]\s"
    r"(.+?):\s(.*)$"
)

# iOS system message
_IOS_SYS_RE = re.compile(
    r"^‎?\[(\d{1,2}/\d{1,2}/\d{2,4}),\s"
    r"(\d{1,2}:\d{2}(?::\d{2})?(?:\s?[AP]M)?)\]\s(.+)$"
)

# Media filename pattern: "IMG-20210101-WA0001.jpg (file attached)"
_MEDIA_ATTACHED_RE = re.compile(
    r"^(.+\.(jpg|jpeg|png|gif|webp|mp4|mp3|opus|pdf|doc|docx))\s*\(file attached\)$",
    re.IGNORECASE,
)

# iOS export format: "<attached: filename.jpg>"
_MEDIA_ATTACHED_IOS_RE = re.compile(
    r"^(?:.*‎)?\s*<attached:\s*(.+\.(jpg|jpeg|png|gif|webp|mp4|mp3|opus|pdf|doc|docx))>\s*$",
    re.IGNORECASE,
)

_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}

# Phrases that identify a line as a system/info notice rather than a real message,
# even when the export attributes them to a sender.
_SYSTEM_KEYWORDS = (
    "end-to-end encrypted",
    "missed voice call",
    "missed video call",
    "your security code with",
    "changed their phone number",
    "created group",
    "added you",
)


# ---------------------------------------------------------------------------
# Date format helpers
# ---------------------------------------------------------------------------

def _split_date(date_str: str):
    """Return (a, b, c) integers from "a/b/c" or None on failure."""
    parts = date_str.split("/")
    if len(parts) != 3:
        return None
    try:
        return int(parts[0]), int(parts[1]), int(parts[2])
    except ValueError:
        return None


def detect_date_format(path: str) -> str:
    """
    Scan a WhatsApp export and return 'dmy', 'mdy', or 'ambiguous'.

    Looks at every parsed timestamp line. If any first-position number > 12,
    it can't be a month — format must be D/M. If any second-position number > 12,
    that slot must be the day — format must be M/D. If both signals appear
    something is wrong; we report ambiguous.
    """
    saw_dmy = False  # first slot > 12 → first slot is the day → DMY
    saw_mdy = False  # second slot > 12 → second slot is the day → MDY

    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        for raw_line in fh:
            line = raw_line.rstrip("\n").lstrip("﻿")
            for pattern in (_ANDROID_RE, _ANDROID_SYS_RE, _IOS_RE, _IOS_SYS_RE):
                m = pattern.match(line)
                if m:
                    parts = _split_date(m.group(1))
                    if parts:
                        a, b, _ = parts
                        if a > 12:
                            saw_dmy = True
                        if b > 12:
                            saw_mdy = True
                    break

    if saw_dmy and not saw_mdy:
        return "dmy"
    if saw_mdy and not saw_dmy:
        return "mdy"
    return "ambiguous"


def _parse_timestamp(date_str: str, time_str: str, date_format: str) -> datetime:
    """Parse a date/time pair using the given date_format ('dmy' or 'mdy')."""
    date_str = date_str.strip()
    time_str = time_str.strip()

    if date_format == "mdy":
        date_patterns = ["%m/%d/%Y", "%m/%d/%y"]
    else:
        date_patterns = ["%d/%m/%Y", "%d/%m/%y"]

    time_patterns = [
        "%H:%M:%S",
        "%H:%M",
        "%I:%M:%S %p",
        "%I:%M %p",
    ]

    combined = f"{date_str} {time_str}"
    for dp in date_patterns:
        for tp in time_patterns:
            try:
                return datetime.strptime(combined, f"{dp} {tp}")
            except ValueError:
                continue
    return datetime(1970, 1, 1)


# ---------------------------------------------------------------------------
# Media + system content detection
# ---------------------------------------------------------------------------

def _detect_media(text: str) -> Optional[str]:
    """Return the media filename if the text is a media line, else None."""
    stripped = text.strip()
    if stripped == "<Media omitted>" or stripped == "‎<Media omitted>":
        return "<Media omitted>"
    m = _MEDIA_ATTACHED_RE.match(stripped)
    if m:
        return m.group(1)
    m = _MEDIA_ATTACHED_IOS_RE.match(stripped)
    if m:
        return m.group(1)
    return None


def _strip_attached(text: str) -> tuple:
    """
    If text contains an <attached: ...> tag (possibly with a prefix message),
    return (prefix_text, filename). Otherwise return (text, None).
    """
    pattern = re.compile(
        r"‎?<attached:\s*(.+\.(jpg|jpeg|png|gif|webp|mp4|mp3|opus|pdf|doc|docx))>",
        re.IGNORECASE,
    )
    m = pattern.search(text)
    if m:
        prefix = text[:m.start()].strip()
        return prefix, m.group(1)
    return text, None


def _is_image(filename: str) -> bool:
    import os
    _, ext = os.path.splitext(filename)
    return ext.lower() in _IMAGE_EXTENSIONS


def _is_system_content(text: str) -> bool:
    """True if text contains a known system-notice phrase."""
    lower = text.lower()
    return any(kw in lower for kw in _SYSTEM_KEYWORDS)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def parse_file(path: str, date_format: str = "dmy") -> list:
    """
    Parse a WhatsApp export .txt file.

    Parameters
    ----------
    path        : path to the .txt export
    date_format : 'dmy' (default) or 'mdy' — controls how ambiguous dates
                  like "5/12/2025" are interpreted.
    """
    messages: list[Message] = []

    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        lines = fh.readlines()

    # Strip BOM if present
    if lines and lines[0].startswith("﻿"):
        lines[0] = lines[0][1:]

    def _append_regular(ts, sender, text):
        media = _detect_media(text)
        if media is None:
            text, media = _strip_attached(text)
        else:
            text = "" if media else text
        # Promote to system message if the content matches a known system phrase,
        # even when the export attributes it to a sender.
        if media is None and _is_system_content(text):
            messages.append(Message(
                timestamp=ts,
                sender="",
                text=text,
                is_system=True,
            ))
            return
        messages.append(Message(
            timestamp=ts,
            sender=sender,
            text=text,
            media_filename=media,
        ))

    for raw_line in lines:
        line = raw_line.rstrip("\n")

        # Try Android message
        m = _ANDROID_RE.match(line)
        if m:
            ts = _parse_timestamp(m.group(1), m.group(2), date_format)
            _append_regular(ts, m.group(3), m.group(4))
            continue

        # Try iOS message
        m = _IOS_RE.match(line)
        if m:
            ts = _parse_timestamp(m.group(1), m.group(2), date_format)
            text = m.group(4).lstrip("‎")
            _append_regular(ts, m.group(3), text)
            continue

        # Try Android system message
        m = _ANDROID_SYS_RE.match(line)
        if m:
            text = m.group(3).strip()
            # Skip empty "Sender:" placeholder lines (appear before media bursts)
            if re.match(r"^[A-Za-z][\w\s]*:$", text):
                continue
            ts = _parse_timestamp(m.group(1), m.group(2), date_format)
            messages.append(Message(
                timestamp=ts,
                sender="",
                text=text,
                is_system=True,
            ))
            continue

        # Try iOS system message
        m = _IOS_SYS_RE.match(line)
        if m:
            text = m.group(3).strip()
            if re.match(r"^[A-Za-z][\w\s]*:$", text):
                continue
            ts = _parse_timestamp(m.group(1), m.group(2), date_format)
            messages.append(Message(
                timestamp=ts,
                sender="",
                text=text,
                is_system=True,
            ))
            continue

        # Continuation line (multi-line message)
        if messages and not messages[-1].is_system:
            messages[-1].text += "\n" + line
        # Ignore leading lines before any message is parsed

    return messages
