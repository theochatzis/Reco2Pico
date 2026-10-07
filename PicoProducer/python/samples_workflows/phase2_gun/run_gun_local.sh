#!/bin/bash
# ---------------------------------------------------------------------------
# Local end-to-end test of the Phase-2 single-hadron gun chain
#   step1 GEN-SIM -> step2 DIGI-RAW-HLT -> step3 RECO -> step4 NANO:@HGCALVal
#
# Run from a shell where cmsenv has been done.
#
# Usage:  run_gun_local.sh [NEVENTS] [PDGID]        (defaults: 10 211)
#
# Environment overrides:
#   TESTDIR    [$CMSSW_BASE/src/gun_local_test]  where cfgs and outputs go
#   plus everything make_gun_cfgs.sh understands (GEOM, ERA, GT, PU, PUINPUT, ...)
# ---------------------------------------------------------------------------
set -euo pipefail

NEVENTS="${1:-10}"
PDGID="${2:-211}"

log() { echo "[run_gun_local] $*"; }

if [ -z "${CMSSW_BASE:-}" ]; then
  log "ERROR: CMSSW_BASE is not set; run cmsenv first"
  exit 1
fi

GUNDIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TESTDIR="${TESTDIR:-${CMSSW_BASE}/src/gun_local_test}"
mkdir -p "${TESTDIR}"
log "building cfgs in ${TESTDIR}/cfgs"
bash "${GUNDIR}/make_gun_cfgs.sh" "${TESTDIR}/cfgs"

cd "${TESTDIR}"

run_step() {
  local n="$1"; shift
  log "step ${n}: cmsRun -j step${n}.xml $*"
  cmsRun -j "step${n}.xml" "$@" 2>&1 | tee "step${n}.log" | grep -v "^%MSG" || true
  test "${PIPESTATUS[0]}" -eq 0
}

run_step 1 cfgs/step1_GENSIM_cfg.py inputFiles=gun://job000 maxEvents="${NEVENTS}" skipEvents=0 \
  output=step1.root pdgId="${PDGID}" pMin=1 pMax=200 etaMin=1.6 etaMax=2.9
test -s step1.root

run_step 2 cfgs/step2_DIGIRAW_cfg.py inputFiles=file:step1.root maxEvents=-1 skipEvents=0 output=step2.root
test -s step2.root

run_step 3 cfgs/step3_RECO_cfg.py inputFiles=file:step2.root maxEvents=-1 skipEvents=0 output=step3.root
test -s step3.root

run_step 4 cfgs/step4_NANO_cfg.py inputFiles=file:step3.root maxEvents=-1 skipEvents=0 output=step4_nano.root
test -s step4_nano.root

log "inspecting step4_nano.root"
python3 - <<'PYEOF'
import sys
import ROOT
ROOT.gROOT.SetBatch(True)
f = ROOT.TFile.Open('step4_nano.root')
if not f or f.IsZombie():
    print('ERROR: cannot open step4_nano.root'); sys.exit(1)
tree = f.Get('Events')
if not tree:
    print('ERROR: no Events tree in step4_nano.root'); sys.exit(1)
names = [b.GetName() for b in tree.GetListOfBranches()]
status = 0
for prefix in ('ticlTrackstersCLUE3DHigh', 'ticlSimTrackstersfromCPs', 'TICLCandidates', 'GeneralTrack', 'hgcalLayerClusters'):
    hits = [n for n in names if n.startswith(prefix) or n.startswith('n' + prefix)]
    print('{:8s} {:28s} ({} branches)'.format('OK' if hits else 'MISSING', prefix, len(hits)))
    if not hits:
        status = 1
print('events:', tree.GetEntries())
sys.exit(status)
PYEOF
log "done (outputs in ${TESTDIR})"
