# ---------------------------------------------------------------------------
# cmsDriver customisation for the RECO step of the GEN-SIM-RAW -> Pico chain.
#
# RECOSIM event content keeps SimTracks/SimVertices and genParticles but drops
# the TrackingParticles and the tracker DigiSimLinks, which the 'sim' table
# group of RECO_to_pico needs (TP table, track<->TP hit association). The
# premixed Run-3 samples carry a pruned copy of both (charged status-1 signal
# particles: prunedTrackingParticles / prunedDigiSimLinks) next to the full
# mix:MergedTrackTruth. Keep them all in the RECO output of the chain.
#
# It also drops, on input, HLT products that offline RECO does not use and
# whose classes may be missing when the RECO release is older than the one
# that produced the RAW (e.g. the Run3Scouting rechits of CMSSW_15_0_18 are
# unknown to CMSSW_15_0_4 and make PoolSource fail on 'missing dictionaries').
#
# Usage:
#   cmsDriver.py step1 -s RAW2DIGI,L1Reco,RECO,RECOSIM ... \
#     --customise Reco2Pico/PicoProducer/samples_workflows/run3_rawsim/recoCustomise.keepSimTruth
# ---------------------------------------------------------------------------
import FWCore.ParameterSet.Config as cms

SIM_TRUTH_KEEP = [
    'keep *_mix_MergedTrackTruth_*',          # TrackingParticles + TrackingVertices (signal + pile-up)
    'keep *_prunedTrackingParticles_*_*',     # charged status-1 signal TPs ...
    'keep *_prunedDigiSimLinks_*_*',          # ... and their pixel/strip DigiSimLinks (hit association)
    'keep SimTracks_g4SimHits_*_*',           # (already in RECOSIM, listed for clarity)
    'keep SimVertexs_g4SimHits_*_*',
    'keep PCaloHits_g4SimHits_EcalHitsEB_*',  # calorimeter sim hits of the signal event (simcalo group)
    'keep PCaloHits_g4SimHits_EcalHitsEE_*',
    'keep PCaloHits_g4SimHits_EcalHitsES_*',
    'keep PCaloHits_g4SimHits_HcalHits_*',
    'keep *_genParticles_*_*',
    'keep *_ak4GenJetsNoNu_*_*',
    'keep *_ak4GenJets_*_*',
    'keep *_addPileupInfo_*_*',
]


DROP_ON_INPUT = [
    'drop *_hltScouting*_*_HLT',   # scouting packers (rechits, tracks, ...): not read by offline RECO
]


def keepSimTruth(process):
    if hasattr(process, 'source') and process.source.type_() == 'PoolSource':
        if not hasattr(process.source, 'inputCommands'):
            process.source.inputCommands = cms.untracked.vstring('keep *')
        for cmd in DROP_ON_INPUT:
            if cmd not in process.source.inputCommands:
                process.source.inputCommands.append(cmd)
        print('run3_rawsim.recoCustomise.keepSimTruth: input drop commands: %s' % ', '.join(DROP_ON_INPUT))
    n = 0
    for name, mod in process.outputModules_().items():
        for cmd in SIM_TRUTH_KEEP:
            if cmd not in mod.outputCommands:
                mod.outputCommands.append(cmd)
        n += 1
    print('run3_rawsim.recoCustomise.keepSimTruth: sim-truth keep statements added to %d output module(s)' % n)
    return process
