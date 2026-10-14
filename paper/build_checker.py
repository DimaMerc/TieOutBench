#!/usr/bin/env python3
"""
paper/build_checker.py -- render tieoutbench-checker-v1.md to Word (.docx) and to the canonical PDF.

Same pipeline as build_docx.py / build_pdf.py for the first report: figure markers of the form
    **Figure N here** (`figures/stem`) — *caption*
become image embeds with italic captions, then pandoc -> .docx, and pandoc -> standalone HTML with
the print stylesheet -> headless Edge --print-to-pdf. Three figure markers are expected.

Run: python paper/build_checker.py            ->  paper/tieoutbench-checker-v1.docx and .pdf
     python paper/build_checker.py docx|pdf   ->  one of them
"""
import os
import re
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
STEM = "tieoutbench-checker-v1"
SRC = os.path.join(HERE, STEM + ".md")
EDGE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
N_FIGURES = 3


def find_pandoc() -> str:
    hit = shutil.which("pandoc")
    if hit:
        return hit
    for c in (os.path.expandvars(r"%LOCALAPPDATA%\Pandoc\pandoc.exe"),
              os.path.expandvars(r"%ProgramFiles%\Pandoc\pandoc.exe")):
        if os.path.exists(c):
            return c
    sys.exit("pandoc not found")


PANDOC = find_pandoc()

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

PAT = re.compile(r"\*\*Figure (\d+) here\*\*\s*\(`figures/([a-z0-9-]+)`\)\s*—\s*\*(.*?)\*", re.DOTALL)


def embed_figures(text: str) -> str:
    def repl(m):
        num, stem, caption = m.group(1), m.group(2), " ".join(m.group(3).split())
        img = os.path.join(HERE, "figures", stem + ".png")
        if not os.path.exists(img):
            sys.exit(f"missing figure file: {img}")
        return f"![Figure {num}. {caption}](figures/{stem}.png)"
    new, n = PAT.subn(repl, text)
    if n != N_FIGURES:
        sys.exit(f"expected {N_FIGURES} figure markers, replaced {n}")
    return new


def build_docx(md: str) -> str:
    tmp = os.path.join(HERE, f"_{STEM}.docx.md")
    out = os.path.join(HERE, STEM + ".docx")
    open(tmp, "w", encoding="utf-8").write(md)
    try:
        subprocess.run([PANDOC, tmp, "-o", out, "--from", "markdown", "--to", "docx",
                        "--resource-path", HERE, "--toc", "--toc-depth", "2", "--metadata", "title="],
                       check=True, cwd=HERE)
    finally:
        os.remove(tmp)
    return out


def build_pdf(md: str) -> str:
    tmp_md = os.path.join(HERE, f"_{STEM}.pdf.md")
    tmp_html = os.path.join(HERE, f"_{STEM}.pdf.html")
    tmp_css = os.path.join(HERE, "_checker_print.css")
    out = os.path.join(HERE, STEM + ".pdf")
    profile = os.path.join(HERE, "_edge_profile_tmp_checker")
    open(tmp_md, "w", encoding="utf-8").write(md)
    open(tmp_css, "w", encoding="utf-8").write(CSS)
    try:
        subprocess.run([PANDOC, tmp_md, "-o", tmp_html, "--from", "markdown", "--to", "html5",
                        "--standalone", "--embed-resources", "--resource-path", HERE,
                        "--css", tmp_css, "--metadata", "pagetitle=TieOutBench checker report"],
                       check=True, cwd=HERE)
        subprocess.run([EDGE, "--headless", "--disable-gpu", "--no-first-run", "--disable-extensions",
                        f"--user-data-dir={profile}", "--no-pdf-header-footer",
                        f"--print-to-pdf={out}", tmp_html], check=True, cwd=HERE)
        data = open(out, "rb").read()
        n_pages = data.count(b"/Type /Page") - data.count(b"/Type /Pages")
        if len(data) < 120_000 or n_pages < 8 or b"ERR_FILE_NOT_FOUND" in data:
            sys.exit(f"PDF looks broken: {len(data)} bytes, ~{n_pages} pages")
        print(f"pdf: {len(data)} bytes, ~{n_pages} pages")
    finally:
        for p in (tmp_md, tmp_html, tmp_css):
            if os.path.exists(p):
                os.remove(p)
        shutil.rmtree(profile, ignore_errors=True)
    return out


if __name__ == "__main__":
    what = sys.argv[1] if len(sys.argv) > 1 else "both"
    md = embed_figures(open(SRC, encoding="utf-8").read())
    if what in ("docx", "both"):
        print("wrote", build_docx(md))
    if what in ("pdf", "both"):
        print("wrote", build_pdf(md))
