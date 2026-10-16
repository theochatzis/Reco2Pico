# ntuple definition: Reco2Pico RECO_to_pico workflow (hand-written cfg) with the
# full low-level content: PF candidates, tracks, vertices, PF clusters, PF
# blocks/elements/links, generator particles and jets, Geant4 SimTracks and
# SimJets, TrackingParticles and track<->TP associations.
# The cfg honours the bdriver arguments itself (VarParsing 'analysis' +
# output/skipEvents); NTUPLE_ARGS are appended to every call of this step.
NTUPLE_KIND=cfg
NTUPLE_CFG='Reco2Pico/PicoProducer/python/workflows/RECO_to_pico_cfg.py'
NTUPLE_ARGS="isMC=true era=${ERA:-Run3_2025} globalTag=${GT:-150X_mcRun3_2026_realistic_v4} tables=${PICO_TABLES:-event,muons,electrons,jets,pfcands,tracks,vertices,pfclusters,pfblocks,genparts,sim,simcalo,recojets}"
NTUPLE_INSPECT='PFCand Track Vertex PFClusterECAL PFClusterHCAL PFBlockElem PFBlockLink PFCandElem GenPart GenJet GenJetConst SimTrack SimVertex SimJet SimGenJetMatch SimCalo SimPFCand SimCaloJet SimPFJet SimCaloGenJetMatch SimPFGenJetMatch PFCandTruth PFCandSim PFJet PFJetCHS PFJetPuppi PFJetGenMatch PFJetCHSGenMatch PFJetPuppiGenMatch TP TrackTPLink'
NTUPLE_DESCRIPTION='RECO_to_pico (PF candidates + blocks/elements/links, gen, Geant4 sim, TrackingParticles)'
