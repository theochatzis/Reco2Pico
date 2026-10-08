#!/bin/bash
# ---------------------------------------------------------------------------
# Create (and optionally submit) HTCondor jobs for the Phase-2 single-hadron
# gun chain with Reco2Pico's bdriver, one job area per species.
#
# Usage:  submit_gun_bdriver.sh [--submit] [--dry-run]
#
# Environment overrides (defaults in brackets):
#   JOBS           [200]        jobs per species
#   EVENTS_PER_JOB [500]        events per job
#   PMIN PMAX      [1] [200]    |p| range [GeV]
#   ETAMIN ETAMAX  [1.6] [2.9]
#   SPECIES        ["211 -211 321 -321 2212 -2212"]  labels: pip pim Kp Km p pbar
#   NTUPLE         [hgcalval-nano]  ntuple definition (../common/ntuples/); the
#                               cfgs must have been built with the same NTUPLE
#   FINAL_OUTPUT   [/eos/user/t/tchatzis/phase2_gun]  EOS destination of the ntuples
#   JOBAREA        [<this dir>/jobs]  bdriver -o (bdriver mirrors it under AFS when it is on /eos)
#   OS             [el9]        bdriver --os
#   RUNTIME        [20:00:00]   bdriver -t (+MaxRuntime); bdriver's default is 01:00:00
#   CFGDIR         [<this dir>/cfgs]                 cfg location (make_gun_cfgs.sh output)
#   SAMPLE_STEPS   [<this dir>/steps_gun_chain.json] sample steps manifest (2-3)
#   TAGSUFFIX      []           appended to the job tag, e.g. _pu200
#   DATASETS       [<this dir>/datasets]  where dataset JSONs and composed manifests go
#   SEED           []           when set, passed as seed=$SEED to all steps
#
# The bdriver manifest is composed per run: SAMPLE_STEPS + cfgs/ntuple_<NTUPLE>_cfg.py
# (datasets/steps_<tag>.json). The generic part lives in ../common/submit_bdriver_chain.sh.
# ---------------------------------------------------------------------------
set -euo pipefail
SW_LOG=submit_gun_bdriver
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
# shellcheck disable=SC1091
source "${SCRIPT_DIR}/../common/chain_lib.sh"
sw_require_cmssw

PASS=()
for arg in "$@"; do
  case "${arg}" in
    --submit|--dry-run) PASS+=("${arg}") ;;
    -h|--help) sed -n '3,/^# ----/p' "${BASH_SOURCE[0]}" | sed '$d'; exit 0 ;;
    *) sw_die "unknown argument: ${arg}" ;;
  esac
done

JOBS="${JOBS:-200}"
EVENTS_PER_JOB="${EVENTS_PER_JOB:-500}"
PMIN="${PMIN:-1}"
PMAX="${PMAX:-200}"
ETAMIN="${ETAMIN:-1.6}"
ETAMAX="${ETAMAX:-2.9}"
SPECIES="${SPECIES:-211 -211 321 -321 2212 -2212}"
NTUPLE="${NTUPLE:-hgcalval-nano}"
FINAL_OUTPUT="${FINAL_OUTPUT:-/eos/user/t/tchatzis/phase2_gun}"
JOBAREA="${JOBAREA:-${SCRIPT_DIR}/jobs}"
OS="${OS:-el9}"
RUNTIME="${RUNTIME:-20:00:00}"
CFGDIR="${CFGDIR:-${SCRIPT_DIR}/cfgs}"
SAMPLE_STEPS="${SAMPLE_STEPS:-${SCRIPT_DIR}/steps_gun_chain.json}"
TAGSUFFIX="${TAGSUFFIX:-}"
DATASETS="${DATASETS:-${SCRIPT_DIR}/datasets}"
SEED="${SEED:-}"

sw_load_ntuple "${NTUPLE}"
STEP1_CFG="${CFGDIR}/step1_GENSIM_cfg.py"
NTUPLE_CFG="${CFGDIR}/$(sw_ntuple_cfg_name)"
for f in "${STEP1_CFG}" "${NTUPLE_CFG}" "${SAMPLE_STEPS}"; do
  [ -f "${f}" ] || sw_die "missing ${f}; run NTUPLE=${NTUPLE} make_gun_cfgs.sh ${CFGDIR}"
done

species_label() {
  case "$1" in
    211)   echo pip ;;
    -211)  echo pim ;;
    321)   echo Kp ;;
    -321)  echo Km ;;
    2212)  echo p ;;
    -2212) echo pbar ;;
    *)     local v="$1"; echo "pdg${v//-/m}" ;;
  esac
}

mkdir -p "${DATASETS}"
EXTRA_ARGS=("pMin=${PMIN}" "pMax=${PMAX}" "etaMin=${ETAMIN}" "etaMax=${ETAMAX}")
[ -n "${SEED}" ] && EXTRA_ARGS+=("seed=${SEED}")

for pdg in ${SPECIES}; do
  label="$(species_label "${pdg}")"
  tag="${label}_p${PMIN}to${PMAX}${TAGSUFFIX}"
  json="${DATASETS}/gun_${label}_p${PMIN}to${PMAX}.json"
  steps="${DATASETS}/steps_${tag}_${NTUPLE}.json"

  python3 "${SCRIPT_DIR}/make_gun_dataset.py" \
    --name "gun_${label}_p${PMIN}to${PMAX}" --jobs "${JOBS}" --events-per-job "${EVENTS_PER_JOB}" -o "${json}"
  sw_compose_steps "${steps}" "${SAMPLE_STEPS}" "${NTUPLE_CFG}"

  bash "${SCRIPT_DIR}/../common/submit_bdriver_chain.sh" "${PASS[@]}" \
    --dataset "${json}" --step1 "${STEP1_CFG}" --steps "${steps}" \
    --jobarea "${JOBAREA}/${tag}" --final-output "${FINAL_OUTPUT}/${tag}" \
    --name "gun_${tag}" --events-per-job "${EVENTS_PER_JOB}" \
    --parents 0 --runtime "${RUNTIME}" --os "${OS}" --memory 4G --cpus 1 --disk-mb 8000 --job-flavour tomorrow \
    -- "pdgId=${pdg}" "${EXTRA_ARGS[@]}"
done
sw_log "done"
