# ntuple definition: HGCAL NanoAOD, reconstruction tables only (NANO:@HGCAL)
# Tracksters, TICL candidates, general and GSF tracks. No sim/association tables,
# no layer clusters, no gen particles; needs nothing beyond RECOSIM.
NTUPLE_KIND=cmsdriver
NTUPLE_STEP='NANO:@HGCAL'
NTUPLE_EVENTCONTENT=NANOAODSIM
NTUPLE_DATATIER=NANOAODSIM
NTUPLE_CUSTOMISE=''
NTUPLE_INSPECT='ticlTrackstersCLUE3DHigh TICLCandidates GeneralTrack'
NTUPLE_DESCRIPTION='NANO:@HGCAL (HGCAL reco tables only)'
