# ntuple definition: HGCAL validation NanoAOD (DPGAnalysis/HGCalNanoAOD, NANO:@HGCALVal)
# Reco tracksters/candidates/tracks + sim tracksters, reco<->sim associations,
# layer clusters and gen particles. Needs the prevalidation customisation because
# RECOSIM does not write the sim/association products (see hgcalNanoPrevalidation.py
# and "Step 4: the NANO prevalidation trick" in phase2_gun/README.md).
NTUPLE_KIND=cmsdriver
NTUPLE_STEP='NANO:@HGCALVal'
NTUPLE_EVENTCONTENT=NANOAODSIM
NTUPLE_DATATIER=NANOAODSIM
NTUPLE_CUSTOMISE='Reco2Pico/PicoProducer/samples_workflows/common/hgcalNanoPrevalidation.customise'
NTUPLE_INSPECT='ticlTrackstersCLUE3DHigh ticlSimTrackstersfromCPs TICLCandidates GeneralTrack HGCalLayerClusters SimCl2CPWithFraction'
NTUPLE_DESCRIPTION='NANO:@HGCALVal (HGCAL reco+sim tables, with prevalidation customise)'
