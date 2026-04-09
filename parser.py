"""
Parse WhatsApp .txt chat exports into a list of Message objects.

Supports both Android and iOS export formats, 12/24-hour time,
multi-line messages, system messages, and media attachment lines.
"""

import re
from dataclasses import dataclass, field
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

# iOS: "[23/04/2021, 14:23:45] Sender: text"  (optional leading LTR mark \u200e)
_IOS_RE = re.compile(
    r"^\u200e?\[(\d{1,2}/\d{1,2}/\d{2,4}),\s"
    r"(\d{1,2}:\d{2}(?::\d{2})?(?:\s?[AP]M)?)\]\s"
    r"(.+?):\s(.*)$"
)

# iOS system message
_IOS_SYS_RE = re.compile(
    r"^\u200e?\[(\d{1,2}/\d{1,2}/\d{2,4}),\s"
    r"(\d{1,2}:\d{2}(?::\d{2})?(?:\s?[AP]M)?)\]\s(.+)$"
)

# Media filename pattern: "IMG-20210101-WA0001.jpg (file attached)"
_MEDIA_ATTACHED_RE = re.compile(
    r"^(.+\.(jpg|jpeg|png|gif|webp|mp4|mp3|opus|pdf|doc|docx))\s*\(file attached\)$",
    re.IGNORECASE,
)

# iOS export format: "<attached: filename.jpg>"
_MEDIA_ATTACHED_IOS_RE = re.compile(
    r"^(?:.*\u200e)?\s*<attached:\s*(.+\.(jpg|jpeg|png|gif|webp|mp4|mp3|opus|pdf|doc|docx))>\s*$",
    re.IGNORECASE,
)

_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}


def _parse_timestamp(date_str: str, time_str: str) -> datetime:
    """Try several date/time format combos and return the first that works."""
    time_str = time_str.strip()
    date_str = date_str.strip()

    formats = [
        "%d/%m/%Y %H:%M:%S",
        "%d/%m/%Y %H:%M",
        "%d/%m/%y %H:%M:%S",
        "%d/%m/%y %H:%M",
        "%m/%d/%Y %H:%M:%S",
        "%m/%d/%Y %H:%M",
        "%m/%d/%y %H:%M:%S",
        "%m/%d/%y %H:%M",
        "%d/%m/%Y %I:%M:%S %p",
        "%d/%m/%Y %I:%M %p",
        "%d/%m/%y %I:%M:%S %p",
        "%d/%m/%y %I:%M %p",
        "%m/%d/%Y %I:%M:%S %p",
        "%m/%d/%Y %I:%M %p",
        "%m/%d/%y %I:%M:%S %p",
        "%m/%d/%y %I:%M %p",
    ]
    combined = f"{date_str} {time_str}"
    for fmt in formats:
        try:
            return datetime.strptime(combined, fmt)
        except ValueError:
            continue
    # Fallback — return epoch so parsing doesn't crash
    return datetime(1970, 1, 1)


def _detect_media(text: str) -> Optional[str]:
    """Return the media filename if the text is a media line, else None."""
    stripped = text.strip()
    if stripped == "<Media omitted>" or stripped == "\u200e<Media omitted>":
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
    # Find <attached: ...> anywhere in the text
    pattern = re.compile(
        r"\u200e?<attached:\s*(.+\.(jpg|jpeg|png|gif|webp|mp4|mp3|opus|pdf|doc|docx))>",
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


def parse_file(path: str) -> list:
    """
    Parse a WhatsApp export .txt file and return a list of Message objects.
    """
    messages: list[Message] = []

    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        lines = fh.readlines()

    # Strip BOM if present
    if lines and lines[0].startswith("\ufeff"):
        lines[0] = lines[0][1:]

    for raw_line in lines:
        line = raw_line.rstrip("\n")

        # Try Android message
        m = _ANDROID_RE.match(line)
        if m:
            ts = _parse_timestamp(m.group(1), m.group(2))
            sender = m.group(3)
            text = m.group(4)
            media = _detect_media(text)
            if media is None:
                text, media = _strip_attached(text)
            else:
                text = "" if media else text
            messages.append(Message(
                timestamp=ts,
                sender=sender,
                text=text,
                media_filename=media,
            ))
            continue

        # Try iOS message
        m = _IOS_RE.match(line)
        if m:
            ts = _parse_timestamp(m.group(1), m.group(2))
            sender = m.group(3)
            text = m.group(4).lstrip("\u200e")
            media = _detect_media(text)
            if media is None:
                text, media = _strip_attached(text)
            else:
                text = "" if media else text
            messages.append(Message(
                timestamp=ts,
                sender=sender,
                text=text,
                media_filename=media,
            ))
            continue

        # Try Android system message
        m = _ANDROID_SYS_RE.match(line)
        if m:
            ts = _parse_timestamp(m.group(1), m.group(2))
            messages.append(Message(
                timestamp=ts,
                sender="",
                text=m.group(3),
                is_system=True,
            ))
            continue

        # Try iOS system message
        m = _IOS_SYS_RE.match(line)
        if m:
            ts = _parse_timestamp(m.group(1), m.group(2))
            messages.append(Message(
                timestamp=ts,
                sender="",
                text=m.group(3),
                is_system=True,
            ))
            continue

        # Continuation line (multi-line message)
        if messages and not messages[-1].is_system:
            messages[-1].text += "\n" + line
        # Ignore leading lines before any message is parsed

    return messages
