#!/usr/bin/env python3
"""
paper/build_options.py -- render tieoutbench-options-redemption-v1.md to Word (.docx) and to the canonical PDF.

Same pipeline as build_checker.py (pandoc -> .docx; pandoc -> standalone HTML with the print stylesheet ->
headless Edge --print-to-pdf). This report has no figures; its tables are markdown tables.

Run: python paper/build_options.py            ->  paper/tieoutbench-options-redemption-v1.docx and .pdf
     python paper/build_options.py docx|pdf   ->  one of them
"""
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from build_checker import CSS, find_pandoc  # noqa: E402  (the shared print stylesheet and pandoc lookup)

STEM = "tieoutbench-options-redemption-v1"
SRC = os.path.join(HERE, STEM + ".md")
EDGE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
PANDOC = find_pandoc()


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
    tmp_css = os.path.join(HERE, "_options_print.css")
    out = os.path.join(HERE, STEM + ".pdf")
    profile = os.path.join(HERE, "_edge_profile_tmp_options")
    open(tmp_md, "w", encoding="utf-8").write(md)
    open(tmp_css, "w", encoding="utf-8").write(CSS)
    try:
        subprocess.run([PANDOC, tmp_md, "-o", tmp_html, "--from", "markdown", "--to", "html5",
                        "--standalone", "--embed-resources", "--resource-path", HERE,
                        "--css", tmp_css, "--metadata", "pagetitle=TieOutBench options-redemption report"],
                       check=True, cwd=HERE)
        subprocess.run([EDGE, "--headless", "--disable-gpu", "--no-first-run", "--disable-extensions",
                        f"--user-data-dir={profile}", "--no-pdf-header-footer",
                        f"--print-to-pdf={out}", tmp_html], check=True, cwd=HERE)
        data = open(out, "rb").read()
        n_pages = data.count(b"/Type /Page") - data.count(b"/Type /Pages")
        if len(data) < 60_000 or n_pages < 6 or b"ERR_FILE_NOT_FOUND" in data:
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
    md = open(SRC, encoding="utf-8").read()
    if what in ("docx", "both"):
        print("wrote", build_docx(md))
    if what in ("pdf", "both"):
        print("wrote", build_pdf(md))
