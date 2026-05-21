#!/usr/bin/env bash
set -euo pipefail
INPUT_FILE="${1:-file:miniAOD.root}"
OUTPUT_FILE="${2:-pico_test.root}"
MAX_EVENTS="${3:-100}"
cmsRun Reco2Pico/python/workflows/miniAOD_to_pico_cfg.py inputFiles="$INPUT_FILE" outputFile="$OUTPUT_FILE" maxEvents="$MAX_EVENTS"
python Reco2Pico/scripts/validate_branches.py "$OUTPUT_FILE" --branches nMuon Muon_pt nJet Jet_pt MET_pt
