"""Generator and Geant4 truth tables for AOD/RECO MC.

genParticleTables: GenPart (pruned genParticles, NanoAOD style, plus every
                   status-1 particle) and GenJet (ak4GenJetsNoNu).
simTables:         SimTrack / SimVertex (g4SimHits), SimJet (anti-kt 0.4 jets of
                   the SimTrack candidates), TP (TrackingParticles) and
                   TrackTPLink (track <-> TrackingParticle hit association).

Track <-> TrackingParticle association (tpAssociation):
  "chi2": TrackAssociatorByChi2 on the full TrackingParticle collection (track
          parameters vs. TP momentum/vertex, chi2 < 25, quality = -chi2). Default:
          it needs no DigiSimLinks, which premixed RAW keeps only for a pruned TP
          subset.
  "hits": quickTrackAssociatorByHits on prunedTrackingParticles / prunedDigiSimLinks
          (quality = shared-hit fractions). In the Run-3 premixed samples the
          pruning keeps the charged status-1 descendants of b/c hadrons only, so
          links exist for those tracks alone.
  "none": no TrackTPLink table content.
The TP table itself is written from mix:MergedTrackTruth; in premixed samples
that collection holds the signal event only (pile-up TPs are not merged).
"""
import FWCore.ParameterSet.Config as cms

from PhysicsTools.NanoAOD.common_cff import Var, P4Vars
from PhysicsTools.NanoAOD.genparticles_cff import genParticleTable
from PhysicsTools.NanoAOD.jetMC_cff import genJetTable
from PhysicsTools.PatAlgos.slimming.prunedGenParticles_cfi import prunedGenParticles


def genParticleTables(process, genParticles="genParticles", genJetMinPt=5.0):
    """GenPart table and GenJet table.

    The gen jets are re-clustered in the job from genParticles (anti-kt 0.4, no
    neutrinos, same definition as ak4GenJetsNoNu) so that their constituents
    can be resolved to GenPart rows and to the sim-jet matching; the
    collections stored in the file do not keep their constituent references.
    """
    from RecoJets.Configuration.GenJetParticles_cff import genParticlesForJetsNoNu
    from RecoJets.JetProducers.ak4GenJets_cfi import ak4GenJets

    process.picoPrunedGenParticles = prunedGenParticles.clone(
        src=cms.InputTag(genParticles),
        select=list(prunedGenParticles.select) + ["keep status == 1"],
    )
    process.picoGenParticlesForJetsNoNu = genParticlesForJetsNoNu.clone(src=cms.InputTag(genParticles))
    process.picoAk4GenJetsNoNu = ak4GenJets.clone(
        src=cms.InputTag("picoGenParticlesForJetsNoNu"),
        jetPtMin=cms.double(genJetMinPt),
    )
    process.picoGenPartTable = genParticleTable.clone(
        src=cms.InputTag("picoPrunedGenParticles"),
        name=cms.string("GenPart"),
        doc=cms.string("generator particles: NanoAOD pruning plus all status-1 particles"),
        externalVariables=cms.PSet(),
    )
    process.picoGenJetTable = genJetTable.clone(
        src=cms.InputTag("picoAk4GenJetsNoNu"),
        cut=cms.string(""),
        name=cms.string("GenJet"),
        doc=cms.string("anti-kt 0.4 jets of the visible generator particles (ak4GenJetsNoNu definition, re-clustered in the job)"),
        variables=cms.PSet(
            P4Vars,
            nConstituents=Var("numberOfDaughters()", "uint8", doc="number of constituents"),
        ),
    )
    process.picoGenParticleTask = cms.Task(
        process.picoPrunedGenParticles,
        process.picoGenParticlesForJetsNoNu,
        process.picoAk4GenJetsNoNu,
        process.picoGenPartTable,
        process.picoGenJetTable,
    )
    return process.picoGenParticleTask


def simTables(
    process,
    simTracks="g4SimHits",
    trackingParticles=("mix", "MergedTrackTruth"),
    tracks="generalTracks",
    trackTableMinPt=0.0,
    tpPileupMinPt=1.0,
    tpSignalMinPt=0.0,
    simJetSelection="leaves",
    simJetMinPt=5.0,
    tpAssociation="chi2",
):
    """SimTrack, SimVertex, SimJet, TP and TrackTPLink tables.

    Requires genParticleTables() to have been called (GenPart row indices).
    """
    if not hasattr(process, "picoPrunedGenParticles"):
        raise RuntimeError("simTables: call genParticleTables() first (GenPart table is needed for the indices)")

    modules = []

    # --- sim jets: SimTrack -> GenParticle candidates -> anti-kt 0.4 ---------
    from RecoJets.JetProducers.ak4GenJets_cfi import ak4GenJets

    process.picoSimTrackCandidates = cms.EDProducer(
        "PicoSimTrackCandidateProducer",
        simTracks=cms.InputTag(simTracks),
        simVertices=cms.InputTag(simTracks),
        selection=cms.string(simJetSelection),
        excludeNeutrinos=cms.bool(True),
        signalOnly=cms.bool(True),
        minPt=cms.double(0.0),
    )
    # jetPtMin at the producer (not a table cut): SimTrack_simJetIdx indexes the collection
    process.picoAk4SimJets = ak4GenJets.clone(
        src=cms.InputTag("picoSimTrackCandidates"),
        jetPtMin=cms.double(simJetMinPt),
    )
    process.picoSimJetTable = genJetTable.clone(
        src=cms.InputTag("picoAk4SimJets"),
        cut=cms.string(""),
        name=cms.string("SimJet"),
        doc=cms.string(
            "anti-kt 0.4 jets of the Geant4 SimTracks (selection '%s', no neutrinos): "
            "generator jets after the detector-level decays and conversions" % simJetSelection
        ),
        variables=cms.PSet(
            P4Vars,
            nConstituents=Var("numberOfDaughters()", "uint8", doc="number of SimTrack constituents"),
        ),
    )
    modules += [process.picoSimTrackCandidates, process.picoAk4SimJets, process.picoSimJetTable]

    # --- SimTrack / SimVertex -------------------------------------------------
    process.picoSimTrackTable = cms.EDProducer(
        "PicoSimTrackTableProducer",
        simTracks=cms.InputTag(simTracks),
        simVertices=cms.InputTag(simTracks),
        genParticles=cms.InputTag("genParticles"),
        genPartTableSrc=cms.InputTag("picoPrunedGenParticles"),
        simJets=cms.InputTag("picoAk4SimJets"),
        simJetConstituentIndex=cms.InputTag("picoSimTrackCandidates", "simTrackIndex"),
        trackName=cms.string("SimTrack"),
        vertexName=cms.string("SimVertex"),
    )
    modules.append(process.picoSimTrackTable)

    # --- SimJet <-> GenJet ancestry matching ------------------------------------
    process.picoSimGenJetMatchTable = cms.EDProducer(
        "PicoSimGenJetMatchProducer",
        simJets=cms.InputTag("picoAk4SimJets"),
        simCandidates=cms.InputTag("picoSimTrackCandidates"),
        simCandidateIndex=cms.InputTag("picoSimTrackCandidates", "simTrackIndex"),
        simTracks=cms.InputTag(simTracks),
        simVertices=cms.InputTag(simTracks),
        genJets=cms.InputTag("picoAk4GenJetsNoNu"),
        genParticles=cms.InputTag("genParticles"),
        genPartTableSrc=cms.InputTag("picoPrunedGenParticles"),
        matchName=cms.string("SimGenJetMatch"),
        genConstituentsName=cms.string("GenJetConst"),
        writeGenConstituents=cms.bool(True),
    )
    modules.append(process.picoSimGenJetMatchTable)

    # --- TrackingParticles and track association --------------------------------
    association = ""
    if tpAssociation not in ("chi2", "hits", "none"):
        raise ValueError("tpAssociation must be chi2, hits or none (got %r)" % tpAssociation)
    if tpAssociation == "chi2":
        from SimTracker.TrackAssociatorProducers.trackAssociatorByChi2_cfi import trackAssociatorByChi2

        process.picoTrackAssociatorByChi2 = trackAssociatorByChi2.clone()
        process.picoTrackingParticleRecoTrackAssociation = cms.EDProducer(
            "TrackAssociatorEDProducer",
            associator=cms.InputTag("picoTrackAssociatorByChi2"),
            label_tp=cms.InputTag(*trackingParticles),
            label_tr=cms.InputTag(tracks),
            ignoremissingtrackcollection=cms.untracked.bool(False),
        )
        modules += [process.picoTrackAssociatorByChi2, process.picoTrackingParticleRecoTrackAssociation]
        association = "picoTrackingParticleRecoTrackAssociation"
    elif tpAssociation == "hits":
        from SimTracker.TrackAssociation.trackPrunedMCMatchTask_cff import (
            prunedTpClusterProducer,
            quickPrunedTrackAssociatorByHits,
        )

        process.picoPrunedTpClusterProducer = prunedTpClusterProducer.clone()
        process.picoQuickPrunedTrackAssociatorByHits = quickPrunedTrackAssociatorByHits.clone(
            cluster2TPSrc=cms.InputTag("picoPrunedTpClusterProducer"),
        )
        process.picoTrackingParticleRecoTrackAssociation = cms.EDProducer(
            "TrackAssociatorEDProducer",
            associator=cms.InputTag("picoQuickPrunedTrackAssociatorByHits"),
            label_tp=cms.InputTag("prunedTrackingParticles"),
            label_tr=cms.InputTag(tracks),
            ignoremissingtrackcollection=cms.untracked.bool(False),
        )
        modules += [
            process.picoPrunedTpClusterProducer,
            process.picoQuickPrunedTrackAssociatorByHits,
            process.picoTrackingParticleRecoTrackAssociation,
        ]
        association = "picoTrackingParticleRecoTrackAssociation"

    process.picoTrackingParticleTable = cms.EDProducer(
        "PicoTrackingParticleTableProducer",
        src=cms.InputTag(*trackingParticles),
        tracks=cms.InputTag(tracks),
        association=cms.InputTag(association),
        genParticles=cms.InputTag("genParticles"),
        genPartTableSrc=cms.InputTag("picoPrunedGenParticles"),
        simTracks=cms.InputTag(simTracks),
        name=cms.string("TP"),
        linkName=cms.string("TrackTPLink"),
        qualityDoc=cms.string(
            "-chi2 of the track/TP parameter comparison (TrackAssociatorByChi2)"
            if tpAssociation == "chi2"
            else "shared-hit fraction (quickTrackAssociatorByHits)"
        ),
        signalMinPt=cms.double(tpSignalMinPt),
        pileupMinPt=cms.double(tpPileupMinPt),
        trackTableMinPt=cms.double(trackTableMinPt),
    )
    modules.append(process.picoTrackingParticleTable)

    process.picoSimTask = cms.Task(*modules)
    return process.picoSimTask


def caloSimHitParameters(simTracks="g4SimHits"):
    """PCaloHit collections and HCAL sampling factors (digitiser values with the
    era modifiers applied) shared by the sim-calo and the PF-truth producers."""
    from SimCalorimetry.HcalSimProducers.hcalSimParameters_cfi import hcalSimParameters as hsp

    return dict(
        ecalHits=cms.VInputTag(cms.InputTag(simTracks, "EcalHitsEB"), cms.InputTag(simTracks, "EcalHitsEE")),
        preshowerHits=cms.VInputTag(cms.InputTag(simTracks, "EcalHitsES")),
        hcalHits=cms.VInputTag(cms.InputTag(simTracks, "HcalHits")),
        hcalTestNumbering=cms.bool(True),
        hbSamplingFactors=cms.vdouble(list(hsp.hb.samplingFactors)),
        heSamplingFactors=cms.vdouble(list(hsp.he.samplingFactors)),
        hoSamplingFactors=cms.vdouble(list(hsp.ho.samplingFactors)),
        heFirstRing=cms.int32(int(hsp.he.firstRing.value())),
        hf1SamplingFactor=cms.double(float(hsp.hf1.samplingFactor.value())),
        hf2SamplingFactor=cms.double(float(hsp.hf2.samplingFactor.value())),
    )


def simCaloTables(
    process,
    simTracks="g4SimHits",
    simJetMinPt=5.0,
    ecalCellThreshold=0.0,
    hcalCellThreshold=0.0,
    chargedMaxAbsEta=2.5,
    chargedMinPt=0.5,
):
    """SimCalo, SimPFCand, SimCaloJet, SimPFJet and their GenJet matches.

    Needs the calorimeter PCaloHits (g4SimHits EcalHitsEB/EE/ES, HcalHits) in
    the input, which standard RECOSIM drops (kept by run3_rawsim's
    recoCustomise.keepSimTruth), and simTables()/genParticleTables() before.
    The HCAL sampling factors are the digitiser's (hcalSimParameters, with the
    era modifiers applied), so the deposits are GeV-equivalent like the digis.
    """
    if not hasattr(process, "picoSimTrackCandidates"):
        raise RuntimeError("simCaloTables: call simTables() first")
    from RecoJets.JetProducers.ak4GenJets_cfi import ak4GenJets

    process.load("Geometry.HcalCommonData.hcalDDDRecConstants_cfi")
    process.picoSimCaloCandidates = cms.EDProducer(
        "PicoSimCaloCandidateProducer",
        simTracks=cms.InputTag(simTracks),
        simVertices=cms.InputTag(simTracks),
        ecalCellThreshold=cms.double(ecalCellThreshold),
        hcalCellThreshold=cms.double(hcalCellThreshold),
        chargedMaxAbsEta=cms.double(chargedMaxAbsEta),
        chargedMinPt=cms.double(chargedMinPt),
        **caloSimHitParameters(simTracks)
    )
    process.picoAk4SimCaloJets = ak4GenJets.clone(
        src=cms.InputTag("picoSimCaloCandidates", "calo"), jetPtMin=cms.double(simJetMinPt)
    )
    process.picoAk4SimPFJets = ak4GenJets.clone(
        src=cms.InputTag("picoSimCaloCandidates", "pf"), jetPtMin=cms.double(simJetMinPt)
    )
    process.picoSimCaloTable = cms.EDProducer(
        "PicoSimCaloTableProducer",
        simTracks=cms.InputTag(simTracks),
        src=cms.string("picoSimCaloCandidates"),
        caloJets=cms.InputTag("picoAk4SimCaloJets"),
        pfJets=cms.InputTag("picoAk4SimPFJets"),
        caloName=cms.string("SimCalo"),
        pfName=cms.string("SimPFCand"),
    )
    jetVars = cms.PSet(
        P4Vars,
        nConstituents=Var("numberOfDaughters()", "uint8", doc="number of constituents"),
    )
    process.picoSimCaloJetTable = genJetTable.clone(
        src=cms.InputTag("picoAk4SimCaloJets"),
        cut=cms.string(""),
        name=cms.string("SimCaloJet"),
        doc=cms.string("anti-kt 0.4 jets of the per-particle calorimeter deposits (SimCalo): calorimeter-only truth jets"),
        variables=jetVars,
    )
    process.picoSimPFJetTable = genJetTable.clone(
        src=cms.InputTag("picoAk4SimPFJets"),
        cut=cms.string(""),
        name=cms.string("SimPFJet"),
        doc=cms.string("anti-kt 0.4 jets of the ideal PF candidates (SimPFCand): tracker momentum for charged particles in acceptance, calorimeter deposit otherwise"),
        variables=jetVars,
    )
    match = process.picoSimGenJetMatchTable
    process.picoSimCaloGenJetMatchTable = match.clone(
        simJets=cms.InputTag("picoAk4SimCaloJets"),
        simCandidates=cms.InputTag("picoSimCaloCandidates", "calo"),
        simCandidateIndex=cms.InputTag("picoSimCaloCandidates", "caloSimTrackIndex"),
        matchName=cms.string("SimCaloGenJetMatch"),
        writeGenConstituents=cms.bool(False),
    )
    process.picoSimPFGenJetMatchTable = match.clone(
        simJets=cms.InputTag("picoAk4SimPFJets"),
        simCandidates=cms.InputTag("picoSimCaloCandidates", "pf"),
        simCandidateIndex=cms.InputTag("picoSimCaloCandidates", "pfSimTrackIndex"),
        matchName=cms.string("SimPFGenJetMatch"),
        writeGenConstituents=cms.bool(False),
    )
    process.picoSimCaloTask = cms.Task(
        process.picoSimCaloCandidates,
        process.picoAk4SimCaloJets,
        process.picoAk4SimPFJets,
        process.picoSimCaloTable,
        process.picoSimCaloJetTable,
        process.picoSimPFJetTable,
        process.picoSimCaloGenJetMatchTable,
        process.picoSimPFGenJetMatchTable,
    )
    return process.picoSimCaloTask
