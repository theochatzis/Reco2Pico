#!/bin/bash
# ---------------------------------------------------------------------------
# TrueJES: histograms and plots of the jet response along the truth ladder.
#
# Usage:  run_truejes.sh [INPUT_DIR] [OUTPUT_TAG]
#   INPUT_DIR   directory with the run3_rawsim Picos (default: the Condor output)
#   OUTPUT_TAG  suffix of the output directories (default: none)
# Env: THREADS [8], MAX_EVENTS [-1], FILE_PATTERN [*.root]
# Needs cmsenv (PyROOT); the plotting needs mplhep/matplotlib (see base README).
# ---------------------------------------------------------------------------
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
BASE="${HERE}/../SkimRDFAnalysisBase"
INPUT="${1:-/eos/user/t/tchatzis/run3_rawsim/DYto2Mu-4Jets_Bin-MLL-50}"
TAG="${2:-}"
THREADS="${THREADS:-8}"
MAX_EVENTS="${MAX_EVENTS:--1}"
FILE_PATTERN="${FILE_PATTERN:-*.root}"
OUT="${HERE}/output${TAG}"
PLOTS="${HERE}/plots${TAG}"

python3 "${HERE}/make_histograms_yaml.py"
python3 "${BASE}/run_analysis.py" \
  --input-files-dir "${INPUT}" \
  --file-pattern "${FILE_PATTERN}" \
  --output-dir "${OUT}" \
  --output-name truejes.root \
  --histograms-defs "${HERE}/truejes_histograms.yaml" \
  --rdf-definition "${HERE}/truejes_rdf_definition.py" \
  --analysis-config "${HERE}/truejes_config.yaml" \
  --threads "${THREADS}" \
  --max-events "${MAX_EVENTS}"
python3 "${HERE}/plot_truejes.py" --input "${OUT}/truejes.root" --output-dir "${PLOTS}"
