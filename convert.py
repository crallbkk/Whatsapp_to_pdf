#!/usr/bin/env python3
"""
WhatsApp to PDF converter.

Usage:
    python convert.py chat.txt --me "Alice" --theme dark --media ./WhatsApp_Images/
"""

import argparse
import os
import sys
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(
        description="Convert a WhatsApp .txt chat export to a styled PDF.",
    )
    parser.add_argument(
        "input",
        help="Path to the WhatsApp .txt export file.",
    )
    parser.add_argument(
        "--me",
        default=None,
        help="Your display name in the chat (the right-side bubbles). "
             "If omitted you will be prompted.",
    )
    parser.add_argument(
        "--theme",
        choices=["light", "dark"],
        default="light",
        help="Color theme for the PDF (default: light).",
    )
    parser.add_argument(
        "--media",
        default=None,
        metavar="DIR",
        help="Folder containing exported media files. "
             "Images found here will be embedded in the PDF.",
    )
    parser.add_argument(
        "--output",
        default=None,
        metavar="FILE",
        help="Output PDF file path (default: same name as input with .pdf extension).",
    )

    args = parser.parse_args()

    # --- Validate input file ---
    input_path = Path(args.input)
    if not input_path.is_file():
        print(f"Error: input file not found: {input_path}", file=sys.stderr)
        sys.exit(1)

    # --- Determine output path ---
    output_path = Path(args.output) if args.output else input_path.with_suffix(".pdf")

    # --- Ask for name if not provided ---
    me = args.me
    if not me:
        try:
            me = input("Your name in this chat (as it appears in the export): ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nAborted.", file=sys.stderr)
            sys.exit(1)
        if not me:
            print("Error: a name is required to identify your messages.", file=sys.stderr)
            sys.exit(1)

    # --- Import here so startup is fast even if deps are missing ---
    try:
        from weasyprint import HTML
    except ImportError:
        print(
            "Error: weasyprint is not installed.\n"
            "Run: pip install -r requirements.txt",
            file=sys.stderr,
        )
        sys.exit(1)

    from parser import parse_file
    from renderer import render_html

    print(f"Parsing {input_path} …")
    messages = parse_file(str(input_path))
    print(f"  {len(messages)} messages found.")

    print(f"Rendering HTML ({args.theme} theme) …")
    html_content = render_html(
        messages=messages,
        me=me,
        theme=args.theme,
        media_dir=args.media,
    )

    print(f"Generating PDF → {output_path} …")
    HTML(string=html_content, base_url=str(input_path.parent)).write_pdf(str(output_path))

    print(f"Done. PDF saved to: {output_path}")


if __name__ == "__main__":
    main()
