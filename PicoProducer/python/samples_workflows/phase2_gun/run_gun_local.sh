#!/bin/bash
# ---------------------------------------------------------------------------
# Local end-to-end test of the Phase-2 single-hadron gun chain
#   step1 GEN-SIM -> step2 DIGI-RAW-HLT -> step3 RECO -> step4 NANO:@HGCALVal
#
# Usage:  run_gun_local.sh [NEVENTS] [PDGID]        (defaults: 10 211)
#
# Environment overrides:
#   WORKAREA   [/eos/user/t/tchatzis/reco2pico]  parent of the CMSSW release area
#   RELEASE    [CMSSW_16_1_0_pre2]
#   SCRAM_ARCH [taken from "scram list -c CMSSW" when unset]
#   REPO       [https://github.com/theochatzis/Reco2Pico.git]
#   TESTDIR    [$CMSSW_BASE/src/gun_local_test]
#   plus everything make_gun_cfgs.sh understands (GEOM, ERA, GT, PU, PUINPUT, ...)
# ---------------------------------------------------------------------------
set -euo pipefail

NEVENTS="${1:-10}"
PDGID="${2:-211}"
WORKAREA="${WORKAREA:-/eos/user/t/tchatzis/reco2pico}"
RELEASE="${RELEASE:-CMSSW_16_1_0_pre2}"
REPO="${REPO:-https://github.com/theochatzis/Reco2Pico.git}"

log() { echo "[run_gun_local] $*"; }

source /cvmfs/cms.cern.ch/cmsset_default.sh

if [ -z "${SCRAM_ARCH:-}" ]; then
  # "scram list -c CMSSW" prints: CMSSW  <release>  /cvmfs/cms.cern.ch/<arch>/cms/cmssw/<release>
  SCRAM_ARCH="$(scram list -c CMSSW 2>/dev/null | awk -v r="${RELEASE}" '$2==r {print $3}' | head -n1 \
                | sed -E 's#^/cvmfs/cms.cern.ch/([^/]+)/.*#\1#')"
  if [ -z "${SCRAM_ARCH}" ]; then
    log "ERROR: could not determine SCRAM_ARCH for ${RELEASE} from 'scram list -c CMSSW'; export SCRAM_ARCH explicitly"
    exit 1
  fi
  export SCRAM_ARCH
fi
log "SCRAM_ARCH=${SCRAM_ARCH} RELEASE=${RELEASE} WORKAREA=${WORKAREA}"

mkdir -p "${WORKAREA}"
cd "${WORKAREA}"
if [ ! -d "${RELEASE}/src" ]; then
  log "creating release area ${WORKAREA}/${RELEASE}"
  scram project CMSSW "${RELEASE}"
fi
cd "${RELEASE}/src"
eval "$(scram runtime -sh)"
log "CMSSW_BASE=${CMSSW_BASE}"

if [ ! -d Reco2Pico/.git ]; then
  log "cloning ${REPO}"
  git clone "${REPO}" Reco2Pico
fi

GUNDIR="${CMSSW_BASE}/src/Reco2Pico/PicoProducer/python/samples_workflows/phase2_gun"
touch "${GUNDIR}/../__init__.py" "${GUNDIR}/__init__.py"

log "scram b"
scram b -j 8 > "${CMSSW_BASE}/src/gun_local_scram.log" 2>&1 || { tail -n 40 "${CMSSW_BASE}/src/gun_local_scram.log"; exit 1; }

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
