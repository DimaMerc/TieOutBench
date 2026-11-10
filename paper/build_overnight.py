#!/usr/bin/env python3
"""
paper/build_overnight.py -- render etf-overnight-reference-value-v1.md to Word (.docx) and to the canonical PDF.

Same pipeline as build_checker.py (pandoc -> .docx; pandoc -> standalone HTML with the print stylesheet ->
headless Edge --print-to-pdf). This report has no figures; its tables are markdown tables.

Run: python paper/build_overnight.py            ->  paper/etf-overnight-reference-value-v1.docx and .pdf
     python paper/build_overnight.py docx|pdf   ->  one of them
"""
import os
import shutil
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from build_checker import CSS, find_pandoc  # noqa: E402  (the shared print stylesheet and pandoc lookup)

STEM = "etf-overnight-reference-value-v1"
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
    tmp_css = os.path.join(HERE, "_overnight_print.css")
    out = os.path.join(HERE, STEM + ".pdf")
    profile = os.path.join(HERE, "_edge_profile_tmp_overnight")
    open(tmp_md, "w", encoding="utf-8").write(md)
    open(tmp_css, "w", encoding="utf-8").write(CSS)
    try:
        subprocess.run([PANDOC, tmp_md, "-o", tmp_html, "--from", "markdown", "--to", "html5",
                        "--standalone", "--embed-resources", "--resource-path", HERE,
                        "--css", tmp_css, "--metadata", "pagetitle=After the Close: overnight ETF reference value report"],
                       check=True, cwd=HERE)
        # Print to a fresh file and wait for it. With another Edge window open the launcher can return
        # before the page is printed (or without printing at all); validating the old PDF at `out` would
        # then report success on a stale file, which happened on 2026-11-10.
        fresh = os.path.join(HERE, f"_{STEM}.fresh.pdf")
        if os.path.exists(fresh):
            os.remove(fresh)
        subprocess.run([EDGE, "--headless", "--disable-gpu", "--no-first-run", "--disable-extensions",
                        f"--user-data-dir={profile}", "--no-pdf-header-footer",
                        f"--print-to-pdf={fresh}", tmp_html], check=True, cwd=HERE)
        deadline, last = time.time() + 90, -1
        while time.time() < deadline:
            size = os.path.getsize(fresh) if os.path.exists(fresh) else 0
            if size > 0 and size == last:
                break
            last = size
            time.sleep(1.5)
        else:
            sys.exit("Edge did not write the PDF within 90 seconds. Close the Edge windows and run "
                     "'python paper/build_overnight.py pdf' again; the existing PDF was left untouched.")
        data = open(fresh, "rb").read()
        n_pages = data.count(b"/Type /Page") - data.count(b"/Type /Pages")
        if len(data) < 60_000 or n_pages < 6 or b"ERR_FILE_NOT_FOUND" in data:
            sys.exit(f"PDF looks broken: {len(data)} bytes, ~{n_pages} pages")
        try:
            os.replace(fresh, out)
        except PermissionError:
            # the PDF is open in a viewer, which locks it: keep the new build beside it and say so
            out = os.path.join(HERE, STEM + ".rebuilt.pdf")
            os.replace(fresh, out)
            print(f"NOTE: {STEM}.pdf is open in another program and could not be replaced. The new build is "
                  f"{os.path.basename(out)}; close the viewer and run the pdf step again to replace the original.")
        print(f"pdf: {len(data)} bytes, ~{n_pages} pages")
    finally:
        fresh_left = os.path.join(HERE, f"_{STEM}.fresh.pdf")
        if os.path.exists(fresh_left):
            os.remove(fresh_left)
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
