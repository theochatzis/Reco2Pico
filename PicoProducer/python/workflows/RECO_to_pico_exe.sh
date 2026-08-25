#!/bin/bash

NEVENTS=100
cmsRun RECO_to_pico_cfg.py \
	inputFiles=/store/mc/Run3Winter25Reco/SingleNeutrino_E-10_gun/GEN-SIM-RECO/FlatPU0to120_142X_mcRun3_2025_realistic_v9-v3/2810000/23a8510e-33fa-420e-b3fa-917cd823ebd6.root \
	output=test_pico.root \
	maxEvents=${NEVENTS} \
	tables=event,pfcands,tracks,vertices,pfclusters,jets,muons,electrons #\
	#lumis=/eos/user/c/cmsdqm/www/CAF/certification/Collisions25/Cert_Collisions2025_391658_398903_Golden.json

size=$(du -b test_pico.root | awk '{print $1}')
sizeInKB=$((size / 1024))
echo "size is $sizeInKB KB"
sizePerEvent=$((sizeInKB / ${NEVENTS}))
echo "size (KB) per event: $sizePerEvent"

python3 make_workbook.py

# Possible samples for inputs:
#/SingleNeutrino_E-10_gun/Run3Winter25Reco-FlatPU0to120_142X_mcRun3_2025_realistic_v9-v3/GEN-SIM-RECO