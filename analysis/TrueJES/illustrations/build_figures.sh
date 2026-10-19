#!/bin/bash
# ---------------------------------------------------------------------------
# Build the TikZ figures (make), render each as PNG for the Markdown write-up,
# and copy the PDFs and PNGs that docs/TrueJES.md embeds into docs/figures.
#
# Usage:  build_figures.sh [FIGURE ...]     (default: every figure of the Makefile)
#   build_figures.sh                        all figures + TrueJES_illustrations.pdf
#   build_figures.sh attribution_samples    one figure (name without .tex)
# Env: DPI [110] resolution of the PNGs; DOCS_FIGURES [../../../docs/figures]
# Needs pdflatex (TikZ, preview) and pdftoppm (poppler).
# ---------------------------------------------------------------------------
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
DPI="${DPI:-110}"
DOCS_FIGURES="${DOCS_FIGURES:-${HERE}/../../../docs/figures}"
cd "${HERE}"

if [ $# -gt 0 ]; then
  FIGS=("$@")
  make "${FIGS[@]/%/.pdf}"
else
  read -r -a FIGS <<< "$(sed -n 's/^FIGS = //p' Makefile)"
  make
fi

for f in "${FIGS[@]}"; do
  pdftoppm -png -r "${DPI}" -singlefile "${f}.pdf" "${f}"
  # the write-up embeds the figures that already have a copy in docs/figures
  if [ -d "${DOCS_FIGURES}" ] && [ -e "${DOCS_FIGURES}/${f}.pdf" -o -e "${DOCS_FIGURES}/${f}.png" ]; then
    cp "${f}.pdf" "${f}.png" "${DOCS_FIGURES}/"
    echo "${f}: built, PNG rendered, copied to docs/figures"
  else
    echo "${f}: built, PNG rendered"
  fi
done
