# Phase-2 single charged-hadron gun, flat in |p| (GeV) and eta, full phi.
#
# cmsDriver generator fragment, used as
#   cmsDriver.py Reco2Pico/PicoProducer/python/samples_workflows/phase2_gun/SingleHadronPGun_cfi.py --step GEN,SIM ...
#
# NOTE: CMSSW_16_1_0_pre2 does not provide a "FlatRandomPGunProducer" plugin
# (see IOMC/ParticleGuns/src/SealModule.cc).  FlatRandomMultiParticlePGunProducer
# is the flat-in-|p| gun available in the release: it shoots one particle per
# event, drawn from PartID with relative weights ProbParts, uniformly in
# [MinP, MaxP], [MinEta, MaxEta] and [MinPhi, MaxPhi].  With a single PartID it
# is exactly a single-species flat-p gun.
#
# The species and kinematic window are overridden per job by
# gun_varparsing_tail.py (pdgId=, pMin=, pMax=, etaMin=, etaMax=); the values
# below are the defaults.

import FWCore.ParameterSet.Config as cms

generator = cms.EDProducer("FlatRandomMultiParticlePGunProducer",
    PGunParameters = cms.PSet(
        PartID    = cms.vint32(211),
        ProbParts = cms.vdouble(1.0),
        MinP      = cms.double(1.0),
        MaxP      = cms.double(200.0),
        MinEta    = cms.double(1.6),
        MaxEta    = cms.double(2.9),
        MinPhi    = cms.double(-3.14159265359),
        MaxPhi    = cms.double(3.14159265359),
    ),
    Verbosity       = cms.untracked.int32(0),
    psethack        = cms.string('single charged hadron, flat p 1-200 GeV, 1.6<eta<2.9'),
    AddAntiParticle = cms.bool(False),
    firstRun        = cms.untracked.uint32(1),
)
