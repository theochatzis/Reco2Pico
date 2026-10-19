# ntuple definition: standard physics NanoAOD (NANO:@PHYS) from RECO.
# The central NANO reads MiniAOD, so PAT runs in the same step (as in the relval
# step3 "...,RECOSIM,PAT,NANO:@..."). Runs on Phase-2 gun events (checked on the
# local test); the table content has not been reviewed for this use.
NTUPLE_KIND=cmsdriver
NTUPLE_STEP='PAT,NANO:@PHYS'
NTUPLE_EVENTCONTENT=NANOAODSIM
NTUPLE_DATATIER=NANOAODSIM
NTUPLE_CUSTOMISE=''
NTUPLE_INSPECT='GenPart Jet Muon Electron'
NTUPLE_DESCRIPTION='PAT,NANO:@PHYS (standard NanoAOD with PAT in the same step)'
