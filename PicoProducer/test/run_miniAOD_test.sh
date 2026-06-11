#!/usr/bin/env bash
set -euo pipefail

BASE=${CMSSW_BASE}/src/
INPUT_FILE="${1:-file:miniAOD.root}"
OUTPUT_FILE="${2:-pico_test.root}"
MAX_EVENTS="${3:-100}"
cmsRun ${BASE}/Reco2Pico/PicoProducer/python/workflows/miniAOD_to_pico_cfg.py inputFiles="$INPUT_FILE" output="$OUTPUT_FILE" maxEvents="$MAX_EVENTS"
#python ${BASE}/Reco2Pico/scripts/validate_branches.py "$OUTPUT_FILE" --branches nMuon Muon_pt nJet Jet_pt MET_pt
