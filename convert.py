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
        "--date-format",
        choices=["auto", "dmy", "mdy"],
        default="auto",
        help="How to interpret ambiguous dates like 5/12/2025. "
             "'auto' (default) detects from the file and prompts if unclear. "
             "'dmy' treats it as 5 December; 'mdy' treats it as May 12.",
    )
    parser.add_argument(
        "--media",
        default=None,
        metavar="DIR",
        help="Folder containing exported media files. "
             "Images found here will be embedded in the PDF.",
    )
    parser.add_argument(
        "--translations",
        default=None,
        metavar="FILE",
        help="Path to translations.json; generates a dual-language A4 landscape PDF.",
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
        from playwright.sync_api import sync_playwright
    except ImportError:
        print(
            "Error: playwright is not installed.\n"
            "Run: pip install playwright && python -m playwright install chromium",
            file=sys.stderr,
        )
        sys.exit(1)

    from renderer import render_html, render_translated_html

    # --- Dual-language mode ---
    if args.translations:
        import json
        trans_path = Path(args.translations)
        if not trans_path.is_file():
            print(f"Error: translations file not found: {trans_path}", file=sys.stderr)
            sys.exit(1)
        entries = json.loads(trans_path.read_text(encoding="utf-8"))
        print(f"Loaded {len(entries)} entries from {trans_path}")
        print(f"Rendering dual-language HTML ({args.theme} theme) ...")
        html_content = render_translated_html(
            entries=entries,
            me=me,
            theme=args.theme,
            media_dir=args.media,
        )
        pdf_format = "A4"
        pdf_landscape = True
        pdf_margin = {"top": "6mm", "bottom": "16mm", "left": "8mm", "right": "8mm"}
    else:
        from parser import parse_file, detect_date_format

        # --- Resolve date format ---
        date_format = args.date_format
        if date_format == "auto":
            detected = detect_date_format(str(input_path))
            if detected == "ambiguous":
                print(
                    "Date format is ambiguous in this export "
                    "(no day > 12 found to disambiguate)."
                )
                choice = input(
                    "Are dates D/M/Y (e.g. 5/12 = 5 December) "
                    "or M/D/Y (e.g. 5/12 = May 12)? [dmy/mdy] "
                ).strip().lower()
                date_format = "mdy" if choice.startswith("m") else "dmy"
            else:
                date_format = detected
                print(f"Detected date format: {date_format.upper()}")

        print(f"Parsing {input_path} ...")
        messages = parse_file(str(input_path), date_format=date_format)
        print(f"  {len(messages)} messages found.")

        print(f"Rendering HTML ({args.theme} theme) ...")
        html_content = render_html(
            messages=messages,
            me=me,
            theme=args.theme,
            media_dir=args.media,
        )
        pdf_format = "A4"
        pdf_landscape = False
        pdf_margin = {"top": "10mm", "bottom": "10mm", "left": "8mm", "right": "8mm"}

    # Write HTML to a temp file so Chromium can resolve relative paths
    import tempfile
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", suffix=".html", delete=False
    ) as tmp:
        tmp.write(html_content)
        tmp_path = tmp.name

    # Locate Chromium — try default install first, then known fallback path
    _CHROMIUM_FALLBACK = "/opt/pw-browsers/chromium-1194/chrome-linux/chrome"

    print(f"Generating PDF -> {output_path} ...")
    try:
        with sync_playwright() as p:
            launch_kwargs = {}
            import os as _os
            if _os.path.isfile(_CHROMIUM_FALLBACK):
                launch_kwargs["executable_path"] = _CHROMIUM_FALLBACK
            browser = p.chromium.launch(**launch_kwargs)
            page = browser.new_page()
            page.goto(f"file:///{tmp_path.replace(os.sep, '/')}")
            page.wait_for_load_state("networkidle")
            pdf_kwargs = dict(
                path=str(output_path),
                format=pdf_format,
                landscape=pdf_landscape,
                margin=pdf_margin,
                print_background=True,
            )
            if args.translations:
                # Phone-bottom bezel rendered in every page's bottom margin.
                # Layout matches the table column widths in templates/translated.html
                # (50% - 10px | 20px gap | 50% - 10px).
                footer_html = (
                    '<style>'
                    '* { box-sizing: border-box; margin: 0; padding: 0; '
                    '-webkit-print-color-adjust: exact; print-color-adjust: exact; }'
                    '</style>'
                    '<div style="width:100%; height:100%; display:flex; '
                    'background:#d0d0d0; font-size:0; line-height:0;">'
                    + (
                        '<div style="flex:1; background:#1a1a1a; '
                        'padding:0 10px 10px; '
                        'border-radius:0 0 38px 38px; '
                        'box-sizing:border-box;">'
                        '<div style="background:#ECE5DD; '
                        'border-radius:0 0 28px 28px; '
                        'height:100%; display:flex; '
                        'justify-content:center; align-items:flex-end; '
                        'padding-bottom:6px;">'
                        '<div style="width:110px; height:4px; '
                        'background:#888; border-radius:2px;"></div>'
                        '</div></div>'
                    ) * 1
                    + '<div style="width:20px; background:#d0d0d0;"></div>'
                    + (
                        '<div style="flex:1; background:#1a1a1a; '
                        'padding:0 10px 10px; '
                        'border-radius:0 0 38px 38px; '
                        'box-sizing:border-box;">'
                        '<div style="background:#ECE5DD; '
                        'border-radius:0 0 28px 28px; '
                        'height:100%; display:flex; '
                        'justify-content:center; align-items:flex-end; '
                        'padding-bottom:6px;">'
                        '<div style="width:110px; height:4px; '
                        'background:#888; border-radius:2px;"></div>'
                        '</div></div>'
                    )
                    + '</div>'
                )
                pdf_kwargs["display_header_footer"] = True
                pdf_kwargs["header_template"] = "<div></div>"
                pdf_kwargs["footer_template"] = footer_html
            page.pdf(**pdf_kwargs)
            browser.close()
    finally:
        os.unlink(tmp_path)

    print(f"Done. PDF saved to: {output_path}")


if __name__ == "__main__":
    main()
