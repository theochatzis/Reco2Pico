#!/bin/bash

NEVENTS=500
cmsRun miniAOD_to_pico_cfg.py \
	inputFiles=/store/data/Run2025G/ZeroBias/MINIAOD/PromptReco-v1/000/397/867/00000/00310bcb-a164-4d17-aeb8-9a7bae912bf3.root \
	output=test_pico_data.root \
	maxEvents=${NEVENTS} \
	tables=event,pfRhoStrip,vertices,jets,met,muons,electrons,pfcands

size=$(du -b test_pico.root | awk '{print $1}')
sizeInKB=$((size / 1024))
echo "size is $sizeInKB KB"
sizePerEvent=$((sizeInKB / ${NEVENTS}))
echo "size (KB) per event: $sizePerEvent"

python3 make_workbook.py

#inputFiles=/store/mc/RunIII2024Summer24MiniAODv6/SingleNeutrino_Par-E-10_gun/MINIAODSIM/FlatPU0to120_150X_mcRun3_2024_realistic_v2-v2/120000/7324e590-b0e6-4c31-90f7-b24c9a13d2a1.root
