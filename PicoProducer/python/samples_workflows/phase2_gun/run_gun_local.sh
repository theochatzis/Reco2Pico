#!/bin/bash
# ---------------------------------------------------------------------------
# Local end-to-end test of the Phase-2 single-hadron gun chain
#   step1 GEN-SIM -> step2 DIGI-RAW-HLT -> step3 RECO -> step4 ntuple (NTUPLE)
#
# Run from a shell where cmsenv has been done.
#
# Usage:  run_gun_local.sh [NEVENTS] [PDGID]        (defaults: 10 211)
#
# Environment overrides:
#   TESTDIR    [<this dir>/local_test]  where cfgs and outputs go (not versioned)
#   CLEAN      [ask]  what to do when TESTDIR already exists:
#                     ask -> prompt (y: wipe it, n: abort); abort if no tty
#                     yes -> wipe it without asking;  no -> keep it and abort
#   NTUPLE     [hgcalval-nano]  ntuple definition (../common/ntuples/)
#   plus everything make_gun_cfgs.sh understands (GEOM, ERA, GT, PU, PUINPUT, ...)
#
# A stale TESTDIR is the usual cause of
#   Fatal Root Error: @SUB=TStorageFactorySystem::Unlink Unsupported
# (cmsRun recreates its output and the storage adaptor refuses to unlink).
# ---------------------------------------------------------------------------
set -euo pipefail
SW_LOG=run_gun_local
GUNDIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
# shellcheck disable=SC1091
source "${GUNDIR}/../common/chain_lib.sh"
sw_require_cmssw

NEVENTS="${1:-10}"
PDGID="${2:-211}"
TESTDIR="${TESTDIR:-${GUNDIR}/local_test}"
CLEAN="${CLEAN:-ask}"
export NTUPLE="${NTUPLE:-hgcalval-nano}"

sw_prepare_testdir "${TESTDIR}" "${CLEAN}"
sw_log "building cfgs in ${TESTDIR}/cfgs"
bash "${GUNDIR}/make_gun_cfgs.sh" "${TESTDIR}/cfgs"
sw_load_ntuple "${NTUPLE}"
NTUPLE_CFG="cfgs/$(sw_ntuple_cfg_name)"

cd "${TESTDIR}"

sw_run_step 1 cfgs/step1_GENSIM_cfg.py inputFiles=gun://job000 maxEvents="${NEVENTS}" skipEvents=0 \
  output=step1.root pdgId="${PDGID}" pMin=1 pMax=200 etaMin=1.6 etaMax=2.9
test -s step1.root

sw_run_step 2 cfgs/step2_DIGIRAW_cfg.py inputFiles=file:step1.root maxEvents=-1 skipEvents=0 output=step2.root
test -s step2.root

sw_run_step 3 cfgs/step3_RECO_cfg.py inputFiles=file:step2.root maxEvents=-1 skipEvents=0 output=step3.root
test -s step3.root

sw_run_step 4 "${NTUPLE_CFG}" inputFiles=file:step3.root maxEvents=-1 skipEvents=0 output=step4_ntuple.root
test -s step4_ntuple.root

sw_log "inspecting step4_ntuple.root (${NTUPLE})"
# shellcheck disable=SC2086
sw_inspect_nano step4_ntuple.root ${NTUPLE_INSPECT:-}
sw_make_ntuple_doc step4_ntuple.root "doc_${NTUPLE}.html" "phase2_gun ${NTUPLE} (${NEVENTS} events, pdgId ${PDGID})"
sw_log "done (outputs in ${TESTDIR}; variable documentation: ${TESTDIR}/doc_${NTUPLE}.html)"
