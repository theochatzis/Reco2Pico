# ---------------------------------------------------------------------------
# cmsDriver customisations of the classically mixed Run-3 chain
# (GEN-SIM + minimum-bias GEN-SIM -> DIGI -> RECO -> Pico), see README.md.
#
# pileupTruth (DIGI step): run PicoMixedTruthProducer after the mixing module,
#   which turns the transient CrossingFrames of the pile-up events into
#   persistent collections (in-time pile-up SimTracks/SimVertices and
#   calorimeter sim hits, out-of-time deposits per cell and crossing), and keep
#   them together with the signal sim truth in the RAW output.
# keepPileupTruth (RECO step): pass those products through the RECO output.
#
# Usage:
#   cmsDriver.py step0 -s DIGI,L1,DIGI2RAW --pileup ... --pileup_input ... \
#     --customise Reco2Pico/PicoProducer/samples_workflows/run3_mix/mixCustomise.pileupTruth
#   cmsDriver.py step1 -s RAW2DIGI,L1Reco,RECO,RECOSIM ... \
#     --customise Reco2Pico/PicoProducer/samples_workflows/run3_rawsim/recoCustomise.keepSimTruth \
#     --customise Reco2Pico/PicoProducer/samples_workflows/run3_mix/mixCustomise.keepPileupTruth
# ---------------------------------------------------------------------------
import FWCore.ParameterSet.Config as cms

PILEUP_TRUTH_LABEL = 'picoMixedTruth'

PILEUP_TRUTH_KEEP = [
    'keep *_%s_*_*' % PILEUP_TRUTH_LABEL,     # pile-up SimTracks/SimVertices, in-time hits, out-of-time cell sums
    'keep SimTracks_g4SimHits_*_*',           # signal sim truth (as recoCustomise.keepSimTruth)
    'keep SimVertexs_g4SimHits_*_*',
    'keep PCaloHits_g4SimHits_EcalHitsEB_*',
    'keep PCaloHits_g4SimHits_EcalHitsEE_*',
    'keep PCaloHits_g4SimHits_EcalHitsES_*',
    'keep PCaloHits_g4SimHits_HcalHits_*',
    'keep *_genParticles_*_*',
    'keep *_addPileupInfo_*_*',
    'keep *_mix_MergedTrackTruth_*',
]


def _add_keeps(process, keeps, tag):
    n = 0
    for name, mod in process.outputModules_().items():
        for cmd in keeps:
            if cmd not in mod.outputCommands:
                mod.outputCommands.append(cmd)
        n += 1
    print('run3_mix.mixCustomise.%s: keep statements added to %d output module(s)' % (tag, n))


def pileupTruth(process):
    if not hasattr(process, 'mix'):
        raise RuntimeError('mixCustomise.pileupTruth: no mixing module in the process (classical mixing expected)')
    # the digitisers read the pile-up through accumulators and the mixing module builds no
    # CrossingFrame unless asked: ask for the calorimeter hits, the SimTracks and the SimVertices
    # (transient products, consumed by PicoMixedTruthProducer in this job)
    process.mix.mixObjects.mixCH.crossingFrames = cms.untracked.vstring('EcalHitsEB', 'EcalHitsEE', 'EcalHitsES', 'HcalHits')
    process.mix.mixObjects.mixTracks.makeCrossingFrame = cms.untracked.bool(True)
    process.mix.mixObjects.mixVertices.makeCrossingFrame = cms.untracked.bool(True)
    # TrackingParticles of the in-time pile-up too (the default keeps the signal ones only), so
    # that a reconstructed track of a pile-up particle can be attributed to the pile-up
    process.mix.digitizers.mergedtruth.select.signalOnlyTP = cms.bool(False)
    process.mix.digitizers.mergedtruth.select.intimeOnlyTP = cms.bool(True)
    setattr(process, PILEUP_TRUTH_LABEL, cms.EDProducer(
        'PicoMixedTruthProducer',
        mixLabel=cms.string('mix'),
        simTracksInstance=cms.string('g4SimHits'),
        simVerticesInstance=cms.string('g4SimHits'),
        caloHitInstances=cms.vstring('EcalHitsEB', 'EcalHitsEE', 'EcalHitsES', 'HcalHits'),
        minBunch=cms.int32(int(process.mix.minBunch.value())),
        maxBunch=cms.int32(int(process.mix.maxBunch.value())),
    ))
    # right after the mixing module, in the digitisation path
    process.digitisation_step += getattr(process, PILEUP_TRUTH_LABEL)
    _add_keeps(process, PILEUP_TRUTH_KEEP, 'pileupTruth')
    return process


def keepPileupTruth(process):
    _add_keeps(process, PILEUP_TRUTH_KEEP, 'keepPileupTruth')
    return process
