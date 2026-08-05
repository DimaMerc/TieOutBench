#!/usr/bin/env python3
"""
paper/build_docx.py -- render tieoutbench-v1.md to Word (.docx) via pandoc.

The paper's figure placements are markers like:
    **Figure 4 here** (`figures/f7-blast-radius`) -- *caption text.*
(sometimes spanning two lines). This script replaces each marker with a real
image embed + italic caption so the .docx shows the charts, then runs pandoc.

Run: python paper/build_docx.py        ->  paper/tieoutbench-v1.docx
"""
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "tieoutbench-v1.md")
TMP = os.path.join(HERE, "_tieoutbench-v1.docx.md")
# optional argv[1] = output basename (lets a rebuild land beside a .docx that is open in Word)
OUT = os.path.join(HERE, sys.argv[1] if len(sys.argv) > 1 else "tieoutbench-v1.docx")

text = open(SRC, encoding="utf-8").read()

# Match the full marker even when the caption wraps across lines: it ends at
# the first *...* caption's closing "*" before a blank line or the next marker.
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
    sys.exit(f"expected 7 figure markers, replaced {n} — check the markers in {SRC}")

open(TMP, "w", encoding="utf-8").write(new)
try:
    subprocess.run(
        ["pandoc", TMP, "-o", OUT, "--from", "markdown", "--to", "docx",
         "--resource-path", HERE, "--toc", "--toc-depth", "2",
         "--metadata", "title="],  # title comes from the H1, not metadata
        check=True, cwd=HERE,
    )
finally:
    os.remove(TMP)
print("wrote", OUT)
