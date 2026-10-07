#!/bin/bash
# ---------------------------------------------------------------------------
# Create (and optionally submit) HTCondor jobs for the Phase-2 single-hadron
# gun chain with Reco2Pico's bdriver, one job area per species.
#
# Usage:  submit_gun_bdriver.sh [--submit]
#
# Environment overrides (defaults in brackets):
#   JOBS           [200]        jobs per species
#   EVENTS_PER_JOB [500]        events per job
#   PMIN PMAX      [1] [200]    |p| range [GeV]
#   ETAMIN ETAMAX  [1.6] [2.9]
#   SPECIES        ["211 -211 321 -321 2212 -2212"]  labels: pip pim Kp Km p pbar
#   FINAL_OUTPUT   [/eos/user/t/tchatzis/phase2_gun]  EOS destination of the NANO files
#   JOBAREA        [<this dir>/jobs]  bdriver -o (bdriver mirrors it under AFS when it is on /eos)
#   OS             [el9]        bdriver --os
#   RUNTIME        [20:00:00]   bdriver -t (+MaxRuntime); bdriver's default is 01:00:00
#   CFGDIR         [<this dir>/cfgs]                 step-1 cfg location
#   STEPS          [<this dir>/steps_gun_chain.json] steps manifest (2-4)
#   TAGSUFFIX      []           appended to the job tag, e.g. _pu200
#   DATASETS       [<this dir>/datasets]  where the dataset JSONs are written
#   SEED           []           when set, passed as seed=$SEED to all steps
#
# -p 0 (no secondary input files) is required: the dataset entries have empty
# parentFiles lists and bdriver's default -p 2 refuses empty secondary inputs.
# Never pass --customize-cfg: it sets process.source.fileNames on the EmptySource
# of the GEN step; gun_varparsing_tail.py already handles all driver arguments.
# ---------------------------------------------------------------------------
set -euo pipefail

SUBMIT=""
for arg in "$@"; do
  case "${arg}" in
    --submit) SUBMIT="--submit" ;;
    -h|--help) sed -n '3,/^# ----/p' "${BASH_SOURCE[0]}" | sed '$d'; exit 0 ;;
    *) echo "[submit_gun_bdriver] unknown argument: ${arg}" >&2; exit 1 ;;
  esac
done

if [ -z "${CMSSW_BASE:-}" ]; then
  echo "[submit_gun_bdriver] ERROR: CMSSW_BASE is not set; run cmsenv first" >&2
  exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
JOBS="${JOBS:-200}"
EVENTS_PER_JOB="${EVENTS_PER_JOB:-500}"
PMIN="${PMIN:-1}"
PMAX="${PMAX:-200}"
ETAMIN="${ETAMIN:-1.6}"
ETAMAX="${ETAMAX:-2.9}"
SPECIES="${SPECIES:-211 -211 321 -321 2212 -2212}"
FINAL_OUTPUT="${FINAL_OUTPUT:-/eos/user/t/tchatzis/phase2_gun}"
JOBAREA="${JOBAREA:-${SCRIPT_DIR}/jobs}"
OS="${OS:-el9}"
RUNTIME="${RUNTIME:-20:00:00}"
CFGDIR="${CFGDIR:-${SCRIPT_DIR}/cfgs}"
STEPS="${STEPS:-${SCRIPT_DIR}/steps_gun_chain.json}"
TAGSUFFIX="${TAGSUFFIX:-}"
SEED="${SEED:-}"

BDRIVER="${CMSSW_BASE}/src/Reco2Pico/PicoProducer/scripts/bdriver"
STEP1_CFG="${CFGDIR}/step1_GENSIM_cfg.py"
DATASETS="${DATASETS:-${SCRIPT_DIR}/datasets}"

for f in "${BDRIVER}" "${STEP1_CFG}" "${STEPS}"; do
  [ -f "${f}" ] || { echo "[submit_gun_bdriver] ERROR: missing ${f}" >&2; exit 1; }
done
grep -q "phase2_gun: VarParsing tail" "${STEP1_CFG}" || {
  echo "[submit_gun_bdriver] ERROR: ${STEP1_CFG} has no VarParsing tail; run make_gun_cfgs.sh" >&2; exit 1; }

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
EXTRA_ARGS=()
[ -n "${SEED}" ] && EXTRA_ARGS+=("seed=${SEED}")

for pdg in ${SPECIES}; do
  label="$(species_label "${pdg}")"
  tag="${label}_p${PMIN}to${PMAX}${TAGSUFFIX}"
  json="${DATASETS}/gun_${label}_p${PMIN}to${PMAX}.json"

  python3 "${SCRIPT_DIR}/make_gun_dataset.py" \
    --name "gun_${label}_p${PMIN}to${PMAX}" --jobs "${JOBS}" --events-per-job "${EVENTS_PER_JOB}" -o "${json}"

  cmd=(python3 "${BDRIVER}"
       -c "${STEP1_CFG}"
       --steps "${STEPS}"
       -d "${json}"
       -o "${JOBAREA}/${tag}"
       -fo "${FINAL_OUTPUT}/${tag}"
       -n "${EVENTS_PER_JOB}"
       -p 0
       --name "gun_${tag}"
       --JobFlavour tomorrow
       -t "${RUNTIME}"
       --memory 4G
       --cpus 1
       --disk-mb 8000
       --os "${OS}")
  [ -n "${SUBMIT}" ] && cmd+=("${SUBMIT}")
  cmd+=("pdgId=${pdg}" "pMin=${PMIN}" "pMax=${PMAX}" "etaMin=${ETAMIN}" "etaMax=${ETAMAX}")
  [ ${#EXTRA_ARGS[@]} -gt 0 ] && cmd+=("${EXTRA_ARGS[@]}")

  echo "[submit_gun_bdriver] ${tag}:"
  printf '  %q' "${cmd[@]}"; echo
  "${cmd[@]}"
done
echo "[submit_gun_bdriver] done${SUBMIT:+ (submitted)}"
