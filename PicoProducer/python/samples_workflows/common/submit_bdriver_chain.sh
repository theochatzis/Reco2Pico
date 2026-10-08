#!/bin/bash
# ---------------------------------------------------------------------------
# samples_workflows/common/submit_bdriver_chain.sh
# One bdriver job area for one dataset of a chained sample workflow.
#
# Usage:
#   submit_bdriver_chain.sh [--submit] \
#     --dataset DATASET.json --step1 STEP1_CFG --steps STEPS.json \
#     --jobarea DIR --final-output DIR --name NAME --events-per-job N \
#     [--parents 0] [--runtime 20:00:00] [--os el9] [--memory 4G] [--cpus 1] \
#     [--disk-mb 8000] [--job-flavour tomorrow] [--dry-run] \
#     [-- key=value ...]            extra cmsRun arguments passed to every step
#
# STEPS.json is the full manifest (sample steps + ntuple step), e.g. the output
# of sw_compose_steps. STEP1_CFG must carry the VarParsing tail (see
# common/varparsing.py); bdriver appends inputFiles=/output=/... itself.
# --parents 0 (default) is for datasets without parent files (e.g. particle
# guns); bdriver's own default -p 2 refuses an empty secondary-file list.
# Never pass --customize-cfg to bdriver: it sets process.source.fileNames on the
# EmptySource of a GEN step; the tail handles all driver arguments.
# ---------------------------------------------------------------------------
set -euo pipefail
SW_LOG=submit_bdriver_chain
# shellcheck disable=SC1091
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)/chain_lib.sh"

SUBMIT="" DRYRUN=""
DATASET="" STEP1="" STEPS="" JOBAREA="" FINAL_OUTPUT="" NAME="" EVENTS_PER_JOB=""
PARENTS=0 RUNTIME="20:00:00" OS="el9" MEMORY="4G" CPUS=1 DISK_MB=8000 JOB_FLAVOUR="tomorrow"
EXTRA_ARGS=()
while [ $# -gt 0 ]; do
  case "$1" in
    --submit) SUBMIT="--submit"; shift ;;
    --dry-run) DRYRUN=1; shift ;;
    --dataset) DATASET="$2"; shift 2 ;;
    --step1) STEP1="$2"; shift 2 ;;
    --steps) STEPS="$2"; shift 2 ;;
    --jobarea) JOBAREA="$2"; shift 2 ;;
    --final-output) FINAL_OUTPUT="$2"; shift 2 ;;
    --name) NAME="$2"; shift 2 ;;
    --events-per-job) EVENTS_PER_JOB="$2"; shift 2 ;;
    --parents) PARENTS="$2"; shift 2 ;;
    --runtime) RUNTIME="$2"; shift 2 ;;
    --os) OS="$2"; shift 2 ;;
    --memory) MEMORY="$2"; shift 2 ;;
    --cpus) CPUS="$2"; shift 2 ;;
    --disk-mb) DISK_MB="$2"; shift 2 ;;
    --job-flavour) JOB_FLAVOUR="$2"; shift 2 ;;
    --) shift; EXTRA_ARGS=("$@"); break ;;
    -h|--help) sed -n '3,/^# ----/p' "${BASH_SOURCE[0]}" | sed '$d'; exit 0 ;;
    *) sw_die "unknown argument: $1" ;;
  esac
done

sw_require_cmssw
for v in DATASET STEP1 STEPS JOBAREA FINAL_OUTPUT NAME EVENTS_PER_JOB; do
  [ -n "${!v}" ] || sw_die "--$(tr 'A-Z_' 'a-z-' <<<"${v}") is required"
done
BDRIVER="${CMSSW_BASE}/src/Reco2Pico/PicoProducer/scripts/bdriver"
for f in "${BDRIVER}" "${DATASET}" "${STEP1}" "${STEPS}"; do
  [ -f "${f}" ] || sw_die "missing ${f}"
done
grep -q "${SW_TAIL_MARKER}" "${STEP1}" || sw_die "${STEP1} has no VarParsing tail; regenerate the cfgs"
python3 - "${STEPS}" <<'PYEOF'
import json, os, sys
steps = json.load(open(sys.argv[1]))
base = os.path.dirname(os.path.abspath(sys.argv[1]))
missing = [s['cfg'] for s in steps if not os.path.isfile(os.path.join(base, s['cfg']))]
if missing:
    sys.exit('steps manifest references missing cfgs: ' + ', '.join(missing))
PYEOF

cmd=(python3 "${BDRIVER}"
     -c "${STEP1}"
     --steps "${STEPS}"
     -d "${DATASET}"
     -o "${JOBAREA}"
     -fo "${FINAL_OUTPUT}"
     -n "${EVENTS_PER_JOB}"
     -p "${PARENTS}"
     --name "${NAME}"
     --JobFlavour "${JOB_FLAVOUR}"
     -t "${RUNTIME}"
     --memory "${MEMORY}"
     --cpus "${CPUS}"
     --disk-mb "${DISK_MB}"
     --os "${OS}")
[ -n "${SUBMIT}" ] && cmd+=("${SUBMIT}")
[ ${#EXTRA_ARGS[@]} -gt 0 ] && cmd+=("${EXTRA_ARGS[@]}")

sw_log "${NAME}:"
printf '  %q' "${cmd[@]}"; echo
[ -n "${DRYRUN}" ] && { sw_log "dry run, not executing"; exit 0; }
"${cmd[@]}"
