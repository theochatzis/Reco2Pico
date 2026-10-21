#!/bin/bash
# Make one navigator page per Pico tier, with every table group the tier
# supports switched on (MC). Run inside cmsenv:
#
#   ./make_all_pico_navigators.sh [output directory, default ./out]
#
# The input files are never opened; they only satisfy the configurations'
# argument checks (a /mc/ path makes the MiniAOD configuration pick MC).

if [ -z "$CMSSW_BASE" ]; then
    echo "Run inside a CMSSW environment (cmsenv)." >&2
    exit 1
fi

HERE=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
OUT=$(mkdir -p "${1:-$HERE/out}" && cd "${1:-$HERE/out}" && pwd)
WORKFLOWS=$CMSSW_BASE/src/Reco2Pico/PicoProducer/python/workflows
MC_FILE=file:/store/mc/navigator/dummy.root

# name | focus module | configuration | configuration arguments
PAGES=(
    "miniAOD_to_pico|picoJetTable|miniAOD_to_pico_cfg.py|inputFiles=$MC_FILE tables=event,pfRhoStrip,vertices,muons,electrons,jets,met,pfcands,user_jets,custom_objects rerunPUPPI=True reApplyJEC=True"
    "AOD_to_pico|picoJetTable|AOD_to_pico_cfg.py|isMC=true inputFiles=$MC_FILE tables=event,muons,electrons,jets,pfcands,tracks,vertices,rechits,genparts,sim,simcalo,recojets"
    "RECO_to_pico|picoPFJetGenMatchTable|RECO_to_pico_cfg.py|isMC=true inputFiles=$MC_FILE secondaryInputFiles=$MC_FILE tables=event,muons,electrons,jets,pfcands,tracks,vertices,pfclusters,rechits,pfblocks,genparts,sim,simcalo,recojets,calodigis"
)

cd "$WORKFLOWS" || exit 1
failed=0
for page in "${PAGES[@]}"; do
    IFS='|' read -r name focus cfg args <<< "$page"
    # shellcheck disable=SC2086  # args is a list of cfg arguments
    if python3 "$HERE/navigator.py" -o "$OUT/$name.html" --focus "$focus" "$cfg" $args > "$OUT/$name.log" 2>&1; then
        echo "$(tail -n 1 "$OUT/$name.log")"
    else
        echo "FAILED $name, see $OUT/$name.log" >&2
        failed=1
    fi
done
exit $failed
