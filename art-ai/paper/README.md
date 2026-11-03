# ART-AI Thesis — compiling

`art-ai-thesis.tex` is self-contained (no external image files). All diagrams are
drawn in TikZ/pgfplots, so it compiles anywhere those packages exist.

## Easiest: Overleaf
1. Go to overleaf.com -> New Project -> Upload Project
2. Upload `art-ai-thesis.tex`
3. Set compiler to **pdfLaTeX** (Menu -> Compiler)
4. Recompile twice so the table of contents and cross-references resolve.

## Locally (Windows)
Install MiKTeX (https://miktex.org/download), then:

    pdflatex art-ai-thesis.tex
    pdflatex art-ai-thesis.tex     # second pass for ToC / refs

MiKTeX will offer to install missing packages on first run; accept.

## Packages used
tikz, pgfplots, booktabs, tabularx, amsmath, graphicx, xcolor, listings,
hyperref, geometry, caption, enumitem — all in a standard TeX Live / MiKTeX
installation.

## Before submitting
Fill in the title page placeholders (author, supervisor, institution) — they are
currently blank rules in the `\begin{titlepage}` block.
