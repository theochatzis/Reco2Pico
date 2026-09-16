#!/bin/bash

NEVENTS=100
cmsRun AOD_to_pico_cfg.py \
	inputFiles=/store/mc/Run3Winter25Reco/SingleNeutrino_E-10_gun/AODSIM/FlatPU0to120_142X_mcRun3_2025_realistic_v9-v3/2520000/00178db0-9ab1-48e3-8181-171c68428dbb.root \
	output=test_pico.root \
	maxEvents=${NEVENTS} \
	tables=event,jets,muons,electrons,pfcands,tracks,vertices,rechits recHitMinAbsEnergy=0.1 #\
	#lumis=/eos/user/c/cmsdqm/www/CAF/certification/Collisions25/Cert_Collisions2025_391658_398903_Golden.json

size=$(du -b test_pico.root | awk '{print $1}')
sizeInKB=$((size / 1024))
echo "size is $sizeInKB KB"
sizePerEvent=$((sizeInKB / ${NEVENTS}))
echo "size (KB) per event: $sizePerEvent"

python3 make_workbook.py

# Possible samples for inputs:
#/SingleNeutrino_E-10_gun/Run3Winter25Reco-FlatPU0to120_142X_mcRun3_2025_realistic_v9-v3/AODSIM
#/ZTo2Mu_Bin-M-50to120_TuneCP5_13p6TeV_powheg-pythia8/Run3Winter25Reco-142X_mcRun3_2025_realistic_v7-v2/AODSIM