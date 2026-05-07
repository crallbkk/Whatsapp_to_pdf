"""
Render a list of Message objects into an HTML string using the Jinja2 template,
with optional base64-encoded image embedding for media attachments.
"""

import base64
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

from jinja2 import Environment, FileSystemLoader

_TEMPLATES_DIR = Path(__file__).parent / "templates"

_MIME_MAP = {
    ".jpg":  "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png":  "image/png",
    ".gif":  "image/gif",
    ".webp": "image/webp",
}

_IMAGE_EXTENSIONS = set(_MIME_MAP.keys())


def _embed_image(media_dir: Optional[str], filename: str):
    """
    Try to find `filename` inside `media_dir`.  If found and it is an image,
    return (base64_string, mime_type).  Otherwise return (None, None).
    """
    if not media_dir or not filename or filename == "<Media omitted>":
        return None, None

    candidate = Path(media_dir) / filename
    if not candidate.is_file():
        # Also try searching one level deep (WhatsApp sometimes nests media)
        matches = list(Path(media_dir).rglob(filename))
        if not matches:
            return None, None
        candidate = matches[0]

    ext = candidate.suffix.lower()
    if ext not in _IMAGE_EXTENSIONS:
        return None, None

    mime = _MIME_MAP[ext]
    with open(candidate, "rb") as fh:
        b64 = base64.b64encode(fh.read()).decode("ascii")
    return b64, mime


def render_html(messages: list, me: str, theme: str = "light",
                media_dir: Optional[str] = None) -> str:
    """
    Render messages to an HTML string.

    Parameters
    ----------
    messages  : list of parser.Message objects
    me        : display name of the user whose messages appear on the right
    theme     : "light" or "dark"
    media_dir : optional path to folder containing exported media files
    """
    env = Environment(
        loader=FileSystemLoader(str(_TEMPLATES_DIR)),
        autoescape=True,
    )
    template = env.get_template("chat.html")

    # Attach base64 image data directly to message objects (temporary attrs)
    for msg in messages:
        if msg.media_filename and msg.media_filename != "<Media omitted>":
            b64, mime = _embed_image(media_dir, msg.media_filename)
            msg.media_b64 = b64
            msg.mime_type = mime
        else:
            msg.media_b64 = None
            msg.mime_type = None

    html = template.render(messages=messages, me=me, theme=theme)
    return html


def render_translated_html(entries: list, me: str, theme: str = "light",
                           media_dir: Optional[str] = None) -> str:
    """
    Render a translations.json entry list as an A4-landscape dual-language HTML.

    Parameters
    ----------
    entries   : list of dicts from translations.json
    me        : display name of the user whose messages appear on the right
    theme     : "light" or "dark"
    media_dir : optional folder containing exported media files
    """
    env = Environment(
        loader=FileSystemLoader(str(_TEMPLATES_DIR)),
        autoescape=True,
    )
    template = env.get_template("translated.html")

    for e in entries:
        ts = datetime.fromisoformat(e["timestamp"])
        e["date_str"] = ts.strftime("%d %B %Y").lstrip("0")
        e["time_str"] = ts.strftime("%H:%M")

        fn = e.get("media_filename")
        if fn and fn != "<Media omitted>":
            b64, mime = _embed_image(media_dir, fn)
            e["media_b64"] = b64
            e["mime_type"] = mime
        else:
            e["media_b64"] = None
            e["mime_type"] = None

    # Derive the other person's name from the first non-system, non-me entry
    other_name = ""
    for e in entries:
        if not e.get("is_system") and e.get("sender") and e["sender"] != me:
            other_name = e["sender"]
            break

    return template.render(entries=entries, me=me, theme=theme, other_name=other_name)
