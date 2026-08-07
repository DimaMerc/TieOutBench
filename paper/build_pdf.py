#!/usr/bin/env python3
"""
paper/build_pdf.py -- render tieoutbench-v1.md to the canonical PDF.

Pipeline: figure markers -> real image embeds (same as build_docx.py), pandoc -> standalone
HTML with the print stylesheet below, then headless Edge --print-to-pdf (no LaTeX needed).
White/navy brand, serif body for print, A4-ish letter geometry.

Run: python paper/build_pdf.py            ->  paper/tieoutbench-v1.pdf
     python paper/build_pdf.py out.pdf    ->  paper/out.pdf
"""
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "tieoutbench-v1.md")
TMP_MD = os.path.join(HERE, "_tieoutbench-v1.pdf.md")
TMP_HTML = os.path.join(HERE, "_tieoutbench-v1.pdf.html")
TMP_CSS = os.path.join(HERE, "_paper_print.css")
OUT = os.path.join(HERE, sys.argv[1] if len(sys.argv) > 1 else "tieoutbench-v1.pdf")
EDGE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"

CSS = """
@page { size: Letter; margin: 22mm 20mm; }
html { -webkit-print-color-adjust: exact; }
body { font-family: Cambria, Georgia, 'Times New Roman', serif; font-size: 10.5pt;
       line-height: 1.45; color: #1a2233; max-width: 100%; margin: 0; }
h1 { font-family: 'Segoe UI', Arial, sans-serif; color: #16243B; font-size: 19pt;
     line-height: 1.25; margin: 0 0 4pt 0; }
h3:first-of-type { margin-top: 2pt; }
h2 { font-family: 'Segoe UI', Arial, sans-serif; color: #16243B; font-size: 13.5pt;
     border-bottom: 1px solid #C9D3DE; padding-bottom: 3pt; margin: 18pt 0 8pt;
     page-break-after: avoid; }
h3 { font-family: 'Segoe UI', Arial, sans-serif; color: #16243B; font-size: 11.5pt;
     margin: 13pt 0 5pt; page-break-after: avoid; }
p { margin: 0 0 7pt; text-align: justify; }
em { color: inherit; }
strong { color: #16243B; }
a { color: #16243B; text-decoration: none; border-bottom: 1px dotted #6B7785; }
code { font-family: Consolas, 'DejaVu Sans Mono', monospace; font-size: 9pt;
       background: #F4F7FB; padding: 0 2px; }
pre { background: #F4F7FB; border: 1px solid #C9D3DE; padding: 7pt 9pt; font-size: 8.8pt;
      line-height: 1.35; overflow-x: hidden; white-space: pre-wrap; page-break-inside: avoid; }
pre code { background: none; padding: 0; }
table { border-collapse: collapse; margin: 9pt auto; font-size: 8.8pt;
        font-family: 'Segoe UI', Arial, sans-serif; page-break-inside: avoid; }
th { background: #16243B; color: #fff; padding: 4pt 7pt; text-align: left; }
td { border-bottom: 1px solid #C9D3DE; padding: 3.5pt 7pt; }
tr:nth-child(even) td { background: #F7F9FC; }
img { max-width: 100%; display: block; margin: 10pt auto 3pt; page-break-inside: avoid; }
figure { margin: 10pt 0; page-break-inside: avoid; }
figcaption { font-size: 8.8pt; color: #6B7785; text-align: center; margin: 3pt 14mm 10pt;
             font-family: 'Segoe UI', Arial, sans-serif; }
blockquote { border-left: 3px solid #C9D3DE; margin: 8pt 0; padding: 1pt 12pt; color: #444f60; }
hr { border: none; border-top: 1px solid #C9D3DE; margin: 14pt 0; }
li { margin-bottom: 3pt; }
h2 + p > em:first-child { color: #6B7785; }
"""

text = open(SRC, encoding="utf-8").read()

pat = re.compile(
    r"\*\*Figure (\d+) here\*\*\s*\(`figures/([a-z0-9-]+)`\)\s*—\s*\*(.*?)\*",
    re.DOTALL,
)

def repl(m):
    num, stem, caption = m.group(1), m.group(2), " ".join(m.group(3).split())
    img = os.path.join(HERE, "figures", stem + ".png")
    if not os.path.exists(img):
        sys.exit(f"missing figure file: {img}")
    return f"![Figure {num} — {caption}](figures/{stem}.png)"

new, n = pat.subn(repl, text)
if n != 7:
    sys.exit(f"expected 7 figure markers, replaced {n}")

open(TMP_MD, "w", encoding="utf-8").write(new)
open(TMP_CSS, "w", encoding="utf-8").write(CSS)
try:
    subprocess.run(
        ["pandoc", TMP_MD, "-o", TMP_HTML, "--from", "markdown", "--to", "html5",
         "--standalone", "--embed-resources", "--resource-path", HERE,
         "--css", TMP_CSS, "--metadata", "pagetitle=TieOutBench"],
        check=True, cwd=HERE,
    )
    # A dedicated --user-data-dir keeps headless Edge from DELEGATING to an already-running
    # browser instance (which returns immediately, races the temp-file cleanup, and prints a
    # "File not found" error page to the PDF — this happened).
    profile = os.path.join(HERE, "_edge_profile_tmp")
    subprocess.run(
        [EDGE, "--headless", "--disable-gpu", "--no-first-run", "--disable-extensions",
         f"--user-data-dir={profile}", "--no-pdf-header-footer",
         f"--print-to-pdf={OUT}", TMP_HTML],
        check=True, cwd=HERE,
    )
    # Validate the output — a broken build must fail loudly, never write garbage.
    data = open(OUT, "rb").read()
    n_pages = data.count(b"/Type /Page") - data.count(b"/Type /Pages")
    if len(data) < 300_000 or n_pages < 10 or b"ERR_FILE_NOT_FOUND" in data:
        sys.exit(f"PDF looks broken: {len(data)} bytes, ~{n_pages} pages — build FAILED")
finally:
    import shutil
    for p in (TMP_MD, TMP_HTML, TMP_CSS):
        if os.path.exists(p):
            os.remove(p)
    shutil.rmtree(os.path.join(HERE, "_edge_profile_tmp"), ignore_errors=True)
print("wrote", OUT, "(validated)")
