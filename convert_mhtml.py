#!/usr/bin/env python3
"""Convert Index.mhtml -> index.html for GitHub Pages.

The source is a Chromium-saved MHTML archive: the HTML body plus an
embedded stylesheet (referenced via cid:...@mhtml.blink) and embedded
base64 PNG brand-mark images. None of that renders when served as a flat
file, so we:

  1. Decode the HTML part (quoted-printable -> utf-8).
  2. Inline the embedded stylesheet by replacing the cid: <link> with a
     <style> block.
  3. Replace the two brand-mark <img> tags with a text wordmark.
  4. Strip any leftover base64 data URLs.

Output: ./index.html, suitable for GitHub Pages.
"""
from __future__ import annotations

import quopri
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "Index.mhtml"
DST = ROOT / "index.html"

BOUNDARY = b"------MultipartBoundary--aJ4ECgjpe1EuhqfmCXrwwoKSaK01Gw0tjFChE8BsEn----"


def split_header_body(part: bytes) -> bytes:
    sep_crlf = part.find(b"\r\n\r\n")
    sep_lf = part.find(b"\n\n")
    if sep_crlf != -1 and (sep_lf == -1 or sep_crlf < sep_lf):
        body = part[sep_crlf + 4 :]
    elif sep_lf != -1:
        body = part[sep_lf + 2 :]
    else:
        body = part
    return body.rstrip(b"-\r\n ")


def main() -> int:
    raw = SRC.read_bytes()
    parts = raw.split(BOUNDARY)
    if len(parts) < 3:
        sys.exit(f"unexpected MHTML structure: {len(parts)} parts")

    html_qp = parts[0]
    main_css_part = parts[2]
    css_body = split_header_body(main_css_part)

    html = quopri.decodestring(html_qp).decode("utf-8", errors="replace")
    css = quopri.decodestring(css_body).decode("utf-8", errors="replace")

    link_re = re.compile(
        r'<link\s+rel="stylesheet"\s+type="text/css"\s+href="cid:css-[^"]+@mhtml\.blink"\s*/?>',
        re.IGNORECASE,
    )
    html, n = link_re.subn("<style>\n" + css + "\n</style>", html, count=1)
    if n != 1:
        sys.exit("could not find embedded stylesheet <link>")

    brand_mark_re = re.compile(
        r'<div class="brand-mark"><img class="bm-light"[^>]*><img class="bm-dark"[^>]*></div>'
    )
    text_logo = (
        '<div class="brand-mark"><span class="bm-text">BrandStudios'
        '<span class="bm-dot">.</span>AI</span></div>'
    )
    html, n = brand_mark_re.subn(text_logo, html)
    if n < 1:
        sys.exit("could not find brand-mark <img> pair")

    text_logo_css = (
        "\n.brand-mark .bm-text { font-family: var(--font-body); font-weight: 800; "
        "font-size: clamp(13px, 1.7vh, 18px); letter-spacing: 0.01em; "
        "color: var(--ink); transition: color 200ms; line-height: 1; white-space: nowrap; }\n"
        ".brand-mark .bm-text .bm-dot { color: var(--orange); }\n"
        "body.is-dark .brand-mark .bm-text { color: var(--bg); }\n"
    )
    html = html.replace("</style>", text_logo_css + "</style>", 1)

    data_url_re = re.compile(r"data:image/[a-zA-Z0-9.+-]+;base64,[A-Za-z0-9+/=]+")
    html = data_url_re.sub("", html)

    DST.write_text(html, encoding="utf-8")
    print(f"Wrote {DST} ({DST.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
