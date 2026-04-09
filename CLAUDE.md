# WhatsApp to PDF — Project Notes

## What this does
Converts a WhatsApp `.txt` chat export to a styled PDF that mimics the real WhatsApp UI (light or dark theme), with embedded images.

## How to run

```bash
pip install -r requirements.txt
pip install playwright
python -m playwright install chromium

python convert.py whatsapp_export/_chat.txt \
  --me "Your Name" \
  --theme light \
  --media whatsapp_export \
  --output "output.pdf"
```

## Key decisions & lessons learned

### PDF renderer: Playwright/Chromium (not WeasyPrint or xhtml2pdf)
- **WeasyPrint** requires GTK3 native libraries (`libgobject`, `libpango`) which are not available on Windows without a separate runtime installer. Avoid.
- **xhtml2pdf** does not support CSS flexbox — the chat bubbles were completely unstyled (no left/right alignment, no colors).
- **Playwright + Chromium** renders the full HTML/CSS including flexbox, images, and all styling. This is the correct approach.

### Media parsing: iOS export format
WhatsApp iOS exports use this format for attachments:
```
‎[5/26/25, 2:01:05 PM] Sender: ‎<attached: 00000057-PHOTO-2025-05-26-14-01-05.jpg>
```
Key issues:
1. Lines start with an invisible Unicode LTR mark `\u200e` before the `[` — the iOS regex must include `\u200e?` at the start.
2. The attachment tag format is `<attached: filename.ext>`, not `filename (file attached)`.
3. The `\u200e` also appears before `<attached:` in the text portion and must be stripped.
4. Some messages have text *before* the `<attached:>` tag on the same line (e.g. `"Same as Nidek SE-9090 Edger System patternless ‎<attached: filename.jpg>"`). These are handled by `_strip_attached()` in `parser.py` which separates the prefix text from the media filename.

### Chat bubble tails: SVG data URI (not CSS border triangles)
CSS border-triangle tricks (`border: 8px solid transparent`) **do not render correctly in Chromium's print-to-PDF mode** — they appear as filled rectangles/boxes instead of triangles.

The fix is to use inline SVG as a `background-image` data URI:
```css
/* Received bubble tail (points left) */
background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='8' height='13'%3E%3Cpolygon points='8,0 0,0 8,13' fill='%23FFFFFF'/%3E%3C/svg%3E");

/* Sent bubble tail (points right) */
background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='8' height='13'%3E%3Cpolygon points='0,0 8,0 0,13' fill='%23DCF8C6'/%3E%3C/svg%3E");
```

Since SVG data URIs can't use CSS variables, the colors are injected at render time via Jinja2 `{% if theme == "dark" %}` in the template.

### strftime on Windows
`%-d` and `%-H` (no-padding format codes) are Linux-only and crash on Windows. Use:
- `"%d %B %Y".lstrip("0")` for dates
- `"%H:%M".lstrip("0")` for times

### Unicode print issues on Windows
The terminal on Windows uses cp1252 encoding by default. Avoid non-ASCII characters in `print()` statements (e.g. `→`, `…`) — use ASCII equivalents (`->`, `...`).

## File structure
```
convert.py          # CLI entry point, argument parsing, PDF generation via Playwright
parser.py           # Parses WhatsApp .txt export into Message objects
renderer.py         # Renders Message list to HTML string via Jinja2
templates/chat.html # Jinja2 HTML template with all CSS styling
requirements.txt    # Python deps (weasyprint listed but not used — use playwright)
whatsapp_export/    # Unzipped WhatsApp export (gitignored)
```

## Dependencies
```
playwright          # PDF generation via headless Chromium
jinja2              # HTML templating
Pillow              # Image handling
```
After installing: `python -m playwright install chromium`
