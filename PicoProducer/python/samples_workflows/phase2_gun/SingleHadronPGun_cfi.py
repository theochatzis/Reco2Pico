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
# gun_varparsing_tail.py (pdgId=, pMin=, pMax=, etaMin=, etaMax=, etaSide=); the
# values below are the defaults. The gun draws eta in ONE interval, so the
# negative endcap is covered by gun_options.apply_gun flipping the window to
# [-MaxEta, -MinEta] in odd-numbered jobs (etaSide=both).
#
# MinP = 0.2 GeV: the gun is flat in |p|, so E = sqrt(p^2 + m^2) starts at
# 0.24 GeV (pi), 0.53 GeV (K), 0.96 GeV (p). Whether such a particle survives
# into the ntuple is decided downstream (CaloParticle MinEnergy in step 2,
# HGCalGenPart pt cut in the nano); gun_options.apply_gun_thresholds lowers
# both, see "Low-energy thresholds" in README.md.

import FWCore.ParameterSet.Config as cms

generator = cms.EDProducer("FlatRandomMultiParticlePGunProducer",
    PGunParameters = cms.PSet(
        PartID    = cms.vint32(211),
        ProbParts = cms.vdouble(1.0),
        MinP      = cms.double(0.2),
        MaxP      = cms.double(200.0),
        MinEta    = cms.double(1.6),
        MaxEta    = cms.double(2.9),
        MinPhi    = cms.double(-3.14159265359),
        MaxPhi    = cms.double(3.14159265359),
    ),
    Verbosity       = cms.untracked.int32(0),
    psethack        = cms.string('single charged hadron, flat p 0.2-200 GeV, 1.6<|eta|<2.9 (sign per job)'),
    AddAntiParticle = cms.bool(False),
    firstRun        = cms.untracked.uint32(1),
)
