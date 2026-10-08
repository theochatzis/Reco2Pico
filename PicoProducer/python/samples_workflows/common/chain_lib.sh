#!/bin/bash
# ---------------------------------------------------------------------------
# samples_workflows/common/chain_lib.sh
# Shell helpers shared by every sample chain (source it, do not execute it).
#
#   SW_LOG                  log prefix used by sw_log (default: samples_workflows)
#   sw_log MSG              / sw_die MSG
#   sw_require_cmssw        abort unless cmsenv was done
#   sw_gtgen GT             echo GT_13TeV when that autoCond alias exists, else GT
#                           (the relval GenSimHLBeamSpot step uses it: HL-LHC
#                           SimBeamSpot payload for --beamspot DBrealisticHLLHC)
#   sw_run_driver ARGS...   echo + cmsDriver.py ARGS
#   sw_append_tail CFG TAILFILE
#                           append TAILFILE to CFG unless the marker is present
#   sw_load_ntuple NAME     source ntuples/NAME.sh (NTUPLE_* variables, see there)
#   sw_ntuple_cfg_name      echo the cfg file name of the loaded ntuple
#   sw_make_ntuple_cfg OUTDIR FILEIN -- CMSDRIVER_COMMON_ARGS...
#                           write OUTDIR/<sw_ntuple_cfg_name> for the loaded ntuple
#   sw_compose_steps OUT.json SAMPLE_STEPS.json NTUPLE_CFG
#                           bdriver manifest = sample steps (made absolute) + ntuple
#   sw_prepare_testdir DIR CLEAN   (CLEAN = ask | yes | no)
#   sw_run_step N CFG ARGS...      cmsRun -j stepN.xml, log stepN.log, exit on failure
#   sw_inspect_nano FILE PREFIX... OK/EMPTY/MISSING per table prefix + event count
#   sw_make_ntuple_doc FILE [OUT.html] [TITLE]
#                           variable documentation HTML (+ CSV) via make_ntuple_doc.py
# ---------------------------------------------------------------------------

SW_COMMON_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
SW_TAIL_MARKER="samples_workflows: VarParsing tail"

sw_log() { echo "[${SW_LOG:-samples_workflows}] $*"; }
sw_die() { sw_log "ERROR: $*" >&2; exit 1; }

sw_require_cmssw() {
  [ -n "${CMSSW_BASE:-}" ] || sw_die "CMSSW_BASE is not set; run cmsenv first"
}

sw_gtgen() {
  local gt="$1"
  if [[ "${gt}" == auto:* ]] && python3 - "${gt#auto:}" <<'PYEOF'
import sys
from Configuration.AlCa.autoCond import autoCond
sys.exit(0 if sys.argv[1] + '_13TeV' in autoCond else 1)
PYEOF
  then echo "${gt}_13TeV"; else echo "${gt}"; fi
}

sw_run_driver() {
  sw_log "cmsDriver.py $*"
  cmsDriver.py "$@"
}

sw_append_tail() {
  local cfg="$1" tail="$2"
  [ -f "${cfg}" ] || sw_die "sw_append_tail: no such cfg ${cfg}"
  [ -f "${tail}" ] || sw_die "sw_append_tail: no such tail ${tail}"
  if grep -q "${SW_TAIL_MARKER}" "${cfg}"; then
    sw_log "$(basename "${cfg}"): VarParsing tail already present"
  else
    cat "${tail}" >> "${cfg}"
    sw_log "$(basename "${cfg}"): VarParsing tail appended"
  fi
}

# --- ntuple definitions ------------------------------------------------------
sw_load_ntuple() {
  local name="$1" def="${SW_COMMON_DIR}/ntuples/$1.sh"
  [ -f "${def}" ] || sw_die "unknown ntuple '${name}'; available: $(ls "${SW_COMMON_DIR}/ntuples" | sed 's/\.sh$//' | tr '\n' ' ')"
  unset NTUPLE_KIND NTUPLE_STEP NTUPLE_EVENTCONTENT NTUPLE_DATATIER NTUPLE_CUSTOMISE NTUPLE_CFG NTUPLE_INSPECT NTUPLE_DESCRIPTION
  # shellcheck disable=SC1090
  source "${def}"
  NTUPLE_NAME="${name}"
  case "${NTUPLE_KIND:-}" in
    cmsdriver)
      [ -n "${NTUPLE_STEP:-}" ] || sw_die "ntuple ${name}: NTUPLE_STEP not set"
      local key
      key="$(sed -nE 's/.*NANO:@([A-Za-z0-9]+).*/\1/p' <<<"${NTUPLE_STEP}")"
      if [ -n "${key}" ] && ! python3 - "${key}" <<'PYEOF'
import sys
from PhysicsTools.NanoAOD.autoNANO import autoNANO
sys.exit(0 if sys.argv[1] in autoNANO else 1)
PYEOF
      then
        sw_die "ntuple ${name}: NANO flavour '@${key}' is not defined in PhysicsTools.NanoAOD.autoNANO of ${CMSSW_VERSION:-this release}; available: $(python3 -c 'from PhysicsTools.NanoAOD.autoNANO import autoNANO; print(" ".join(sorted(autoNANO)))')"
      fi ;;
    cfg)
      [ -f "${CMSSW_BASE}/src/${NTUPLE_CFG:-/nonexistent}" ] || sw_die "ntuple ${name}: NTUPLE_CFG not found: ${CMSSW_BASE}/src/${NTUPLE_CFG:-}" ;;
    *) sw_die "ntuple ${name}: NTUPLE_KIND must be cmsdriver or cfg (got '${NTUPLE_KIND:-}')" ;;
  esac
  sw_log "ntuple ${name}: ${NTUPLE_DESCRIPTION:-}"
}

sw_ntuple_cfg_name() { echo "ntuple_${NTUPLE_NAME}_cfg.py"; }

sw_make_ntuple_cfg() {
  local outdir="$1" filein="$2"; shift 2
  [ "${1:-}" = "--" ] && shift
  [ -n "${NTUPLE_NAME:-}" ] || sw_die "sw_make_ntuple_cfg: call sw_load_ntuple first"
  local cfg="${outdir}/$(sw_ntuple_cfg_name)"
  case "${NTUPLE_KIND}" in
    cmsdriver)
      local cust=()
      [ -n "${NTUPLE_CUSTOMISE:-}" ] && cust=(--customise "${NTUPLE_CUSTOMISE}")
      sw_run_driver ntuple "$@" \
        --step "${NTUPLE_STEP}" --eventcontent "${NTUPLE_EVENTCONTENT}" --datatier "${NTUPLE_DATATIER}" \
        "${cust[@]}" \
        --filein "${filein}" --fileout file:ntuple.root \
        --python_filename "${cfg}" ;;
    cfg)
      cp "${CMSSW_BASE}/src/${NTUPLE_CFG}" "${cfg}"
      sw_log "copied ${NTUPLE_CFG} -> ${cfg}" ;;
  esac
}

sw_compose_steps() {
  local out="$1" sample="$2" ntuple_cfg="$3"
  python3 - "${out}" "${sample}" "${ntuple_cfg}" <<'PYEOF'
import json, os, sys
out, sample, ntuple = sys.argv[1:4]
base = os.path.dirname(os.path.abspath(sample))
steps = json.load(open(sample))
if not isinstance(steps, list) or not steps:
    sys.exit('sw_compose_steps: %s must be a non-empty JSON list' % sample)
for s in steps:
    s['cfg'] = os.path.normpath(os.path.join(base, s['cfg']))
steps.append({'cfg': os.path.abspath(ntuple)})
for s in steps:
    if not os.path.isfile(s['cfg']):
        sys.exit('sw_compose_steps: missing cfg %s' % s['cfg'])
os.makedirs(os.path.dirname(os.path.abspath(out)) or '.', exist_ok=True)
json.dump(steps, open(out, 'w'), indent=2)
open(out, 'a').write('\n')
print('[samples_workflows] steps manifest %s: %s' % (out, ' -> '.join(os.path.basename(s['cfg']) for s in steps)))
PYEOF
}

# --- local test ----------------------------------------------------------------
sw_prepare_testdir() {
  local dir="$1" clean="${2:-ask}"
  if [ -e "${dir}" ]; then
    case "${clean}" in
      yes) ;;
      no)  sw_die "${dir} exists and CLEAN=no; remove it or set TESTDIR" ;;
      ask)
        [ -t 0 ] || sw_die "${dir} exists and no terminal to ask; rerun with CLEAN=yes or CLEAN=no"
        echo "[${SW_LOG:-samples_workflows}] ${dir} exists (leftover of a previous run):"
        ls -la "${dir}" | sed 's/^/    /'
        local ans
        read -r -p "[${SW_LOG:-samples_workflows}] remove it and start clean? [y/N] " ans
        case "${ans}" in y|Y|yes|YES) ;; *) sw_die "aborting; set TESTDIR=... to use another directory" ;; esac ;;
      *) sw_die "CLEAN must be ask, yes or no (got '${clean}')" ;;
    esac
    sw_log "removing ${dir}"
    rm -rf "${dir}"
  fi
  mkdir -p "${dir}"
}

# cmsRun output files are opened in "recreate" mode; an existing file makes the
# CMSSW storage adaptor fail with "TStorageFactorySystem::Unlink Unsupported"
# (notably on EOS fuse), which is why sw_prepare_testdir wipes the directory.
sw_run_step() {
  local n="$1"; shift
  local rc
  sw_log "step ${n}: cmsRun -j step${n}.xml $*"
  # "|| true" must not follow the pipeline: under pipefail it would run on a
  # cmsRun failure and overwrite PIPESTATUS, letting the chain carry on.
  set +e
  cmsRun -j "step${n}.xml" "$@" 2>&1 | tee "step${n}.log" | grep -v "^%MSG"
  rc="${PIPESTATUS[0]}"
  set -e
  if [ "${rc}" -ne 0 ]; then
    sw_die "step ${n} failed (exit ${rc}); see $(pwd)/step${n}.log"
  fi
}

sw_inspect_nano() {
  local file="$1"; shift
  python3 - "${file}" "$@" <<'PYEOF'
import sys
import ROOT
ROOT.gROOT.SetBatch(True)
fname, prefixes = sys.argv[1], sys.argv[2:]
f = ROOT.TFile.Open(fname)
if not f or f.IsZombie():
    sys.exit('ERROR: cannot open ' + fname)
tree = f.Get('Events')
if not tree:
    sys.exit('ERROR: no Events tree in ' + fname)
names = [b.GetName() for b in tree.GetListOfBranches()]
n = tree.GetEntries()
status = 0
for prefix in prefixes:
    hits = [x for x in names if x.startswith(prefix + '_') or x == prefix or x == 'n' + prefix]
    if not hits:
        print('{:8s} {:28s} (no branches)'.format('MISSING', prefix)); status = 1; continue
    total = ''
    if 'n' + prefix in names:
        total = int(sum(tree.GetEntry(i) * 0 + int(getattr(tree, 'n' + prefix)) for i in range(n)))
        if total == 0:
            print('{:8s} {:28s} ({} branches, 0 entries in {} events)'.format('EMPTY', prefix, len(hits), n)); status = 1; continue
    print('{:8s} {:28s} ({} branches{})'.format('OK', prefix, len(hits), '' if total == '' else ', {} entries'.format(total)))
print('events: {}  branches: {}'.format(n, len(names)))
sys.exit(status)
PYEOF
}

sw_make_ntuple_doc() {
  local file="$1" out="${2:-}" title="${3:-}"
  local args=("${file}")
  [ -n "${out}" ] && args+=(-o "${out}" --csv "${out%.html}.csv")
  [ -n "${title}" ] && args+=(--title "${title}")
  python3 "${SW_COMMON_DIR}/make_ntuple_doc.py" "${args[@]}"
}
