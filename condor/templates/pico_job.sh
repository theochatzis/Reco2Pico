#!/usr/bin/env bash
set -euo pipefail
JOB_ID="$1"
INPUT_LIST="$2"
CFG="$3"
OUTPUT_DIR="$4"
TABLES="$5"
GLOBAL_TAG="$6"
MAX_EVENTS="$7"
WORKDIR="$(pwd)"
OUTFILE="pico_${JOB_ID}.root"

if [ -z "${CMSSW_BASE:-}" ]; then
  echo "CMSSW_BASE is not set. Source cmsenv before submitting or use a site wrapper." >&2
  exit 1
fi

cd "$CMSSW_BASE/src"
eval "$(scram runtime -sh)"
cd "$WORKDIR"

INPUTS=$(python3 -c 'from pathlib import Path; import sys; files=[x.strip() for x in Path(sys.argv[1]).read_text().splitlines() if x.strip() and not x.strip().startswith("#")]; print(",".join(files))' "$INPUT_LIST")

cmsRun "$CMSSW_BASE/src/$CFG" \
  inputFiles="$INPUTS" \
  outputFile="$OUTFILE" \
  tables="$TABLES" \
  globalTag="$GLOBAL_TAG" \
  maxEvents="$MAX_EVENTS"

mkdir -p "$OUTPUT_DIR"
if command -v xrdcp >/dev/null 2>&1 && [[ "$OUTPUT_DIR" == root://* ]]; then
  xrdcp -f "$OUTFILE" "$OUTPUT_DIR/$OUTFILE"
else
  cp "$OUTFILE" "$OUTPUT_DIR/$OUTFILE"
fi
