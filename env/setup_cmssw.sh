#!/usr/bin/env bash
set -euo pipefail
source /cvmfs/cms.cern.ch/cmsset_default.sh
CMSSW_VERSION="${CMSSW_VERSION:-$(cat env/cmssw_version.txt)}"
if [ ! -d "$CMSSW_VERSION" ]; then
  cmsrel "$CMSSW_VERSION"
fi
cd "$CMSSW_VERSION/src"
cmsenv
echo "CMSSW_BASE=$CMSSW_BASE"
