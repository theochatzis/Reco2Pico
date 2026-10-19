"""Generator and Geant4 truth tables for AOD/RECO MC.

genParticleTables: GenPart (pruned genParticles, NanoAOD style, plus every
                   status-1 particle) and GenJet (ak4GenJetsNoNu).
simTables:         SimTrack / SimVertex (g4SimHits), SimJet (anti-kt 0.4 jets of
                   the SimTrack candidates: by default the calorimeter-entrance
                   particles, flagged by PicoCaloEntranceProducer from the
                   SimTrack tree and the calorimeter sim hits), TP
                   (TrackingParticles) and TrackTPLink (track <-> TrackingParticle
                   hit association).

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
    simJetSelection="entrance",
    simJetMinPt=5.0,
    tpAssociation="chi2",
    trackerMaxRadius=123.0,
    trackerMaxAbsZ=293.0,
):
    """SimTrack, SimVertex, SimJet, TP and TrackTPLink tables.

    Requires genParticleTables() to have been called (GenPart row indices).
    simJetSelection "entrance" (default) needs the calorimeter sim hits in the
    input (see simCaloTables); "leaves", "boundary" and "primaries" do not.
    """
    if not hasattr(process, "picoPrunedGenParticles"):
        raise RuntimeError("simTables: call genParticleTables() first (GenPart table is needed for the indices)")

    modules = []

    # --- calorimeter-entrance particles (SimTrack tree + calorimeter sim hits) ---
    process.load("Geometry.HcalCommonData.hcalDDDRecConstants_cfi")
    process.picoCaloEntrance = cms.EDProducer(
        "PicoCaloEntranceProducer",
        simTracks=cms.InputTag(simTracks),
        simVertices=cms.InputTag(simTracks),
        trackerMaxRadius=cms.double(trackerMaxRadius),
        trackerMaxAbsZ=cms.double(trackerMaxAbsZ),
        **caloSimHitParameters(simTracks)
    )
    modules.append(process.picoCaloEntrance)

    # --- sim jets: SimTrack -> GenParticle candidates -> anti-kt 0.4 ---------
    from RecoJets.JetProducers.ak4GenJets_cfi import ak4GenJets

    process.picoSimTrackCandidates = cms.EDProducer(
        "PicoSimTrackCandidateProducer",
        simTracks=cms.InputTag(simTracks),
        simVertices=cms.InputTag(simTracks),
        caloEntrance=cms.InputTag("picoCaloEntrance"),
        selection=cms.string(simJetSelection),
        momentum=cms.string("production"),
        excludeNeutrinos=cms.bool(True),
        signalOnly=cms.bool(True),
        minPt=cms.double(0.0),
    )
    # jetPtMin at the producer (not a table cut): SimTrack_simJetIdx indexes the collection
    process.picoAk4SimJets = ak4GenJets.clone(
        src=cms.InputTag("picoSimTrackCandidates"),
        jetPtMin=cms.double(simJetMinPt),
    )
    # the same particles with their momentum at the calorimeter face (material, bending)
    process.picoSimTrackCandidatesBoundary = process.picoSimTrackCandidates.clone(momentum=cms.string("boundary"))
    process.picoAk4SimBoundaryJets = ak4GenJets.clone(
        src=cms.InputTag("picoSimTrackCandidatesBoundary"),
        jetPtMin=cms.double(simJetMinPt),
    )
    process.picoSimJetTable = genJetTable.clone(
        src=cms.InputTag("picoAk4SimJets"),
        cut=cms.string(""),
        name=cms.string("SimJet"),
        doc=cms.string(
            "anti-kt 0.4 jets of the Geant4 SimTracks (selection '%s', no neutrinos): "
            "the calorimeter-entrance particles with their production momenta, i.e. the generator jets "
            "after the decays, conversions and interactions simulated by Geant4 in the tracker" % simJetSelection
            if simJetSelection == "entrance"
            else "anti-kt 0.4 jets of the Geant4 SimTracks (selection '%s', no neutrinos): "
            "generator jets after the detector-level decays and conversions" % simJetSelection
        ),
        variables=cms.PSet(
            P4Vars,
            nConstituents=Var("numberOfDaughters()", "uint8", doc="number of SimTrack constituents"),
        ),
    )
    process.picoSimBoundaryJetTable = process.picoSimJetTable.clone(
        src=cms.InputTag("picoAk4SimBoundaryJets"),
        name=cms.string("SimBoundaryJet"),
        doc=cms.string(
            "anti-kt 0.4 jets of the same SimTrack candidates as SimJet with their momentum at the calorimeter face "
            "(recorded at the boundary crossing): adds the energy loss in the tracker material and the bending"
        ),
    )
    modules += [
        process.picoSimTrackCandidates,
        process.picoAk4SimJets,
        process.picoSimJetTable,
        process.picoSimTrackCandidatesBoundary,
        process.picoAk4SimBoundaryJets,
        process.picoSimBoundaryJetTable,
    ]

    # --- SimTrack / SimVertex -------------------------------------------------
    process.picoSimTrackTable = cms.EDProducer(
        "PicoSimTrackTableProducer",
        simTracks=cms.InputTag(simTracks),
        simVertices=cms.InputTag(simTracks),
        genParticles=cms.InputTag("genParticles"),
        genPartTableSrc=cms.InputTag("picoPrunedGenParticles"),
        simJets=cms.InputTag("picoAk4SimJets"),
        simJetConstituentIndex=cms.InputTag("picoSimTrackCandidates", "simTrackIndex"),
        caloEntrance=cms.InputTag("picoCaloEntrance"),
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
    process.picoSimBoundaryGenJetMatchTable = process.picoSimGenJetMatchTable.clone(
        simJets=cms.InputTag("picoAk4SimBoundaryJets"),
        simCandidates=cms.InputTag("picoSimTrackCandidatesBoundary"),
        simCandidateIndex=cms.InputTag("picoSimTrackCandidatesBoundary", "simTrackIndex"),
        matchName=cms.string("SimBoundaryGenJetMatch"),
        writeGenConstituents=cms.bool(False),
    )
    modules.append(process.picoSimBoundaryGenJetMatchTable)

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


# Scale of the sim deposits per subdetector (EB, EE, ES, HB, HE, HO, HF depth 1, HF depth 2),
# measured on the classically mixed sample (run3_mix, 10-event test of 17 Oct 2026) as the
# median of reconstructed cell energy / in-time sim deposit per cell, where every cell's deposit
# is known. The digitiser GeV-equivalent reproduces the rechit scale in EB (1.00), EE (1.05) and
# HO (1.05); HB/HE rechits are at 0.74/0.75 of it (the PF cluster calibration brings the
# hadrons back up); the HF conversion from shower-library photoelectrons misses the gain:
# 14.2 (depth 1) and 12.8 (depth 2), broad (16-84%: 10.6-18.1).
# SIM_SCALE (sim-level objects): the digitiser scale with the HF gain applied, so that the
#   SimCalo deposits are GeV-equivalent everywhere;
# RECHIT_SCALE (attribution of reconstructed candidates): the rechit scale, the right cap for
#   sharing a reconstructed cell energy between signal and pile-up deposits.
SIM_SCALE = [1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 14.2, 12.8]
RECHIT_SCALE = [1.0, 1.05, 1.0, 0.74, 0.75, 1.05, 14.2, 12.8]


def caloSimHitParameters(simTracks="g4SimHits", pileupTruth="", rechitScale=False):
    """PCaloHit collections and HCAL sampling factors (digitiser values with the
    era modifiers applied) shared by the sim-calo and the PF-truth producers.
    pileupTruth: label of the PicoMixedTruthProducer of a classically mixed
    event (its in-time and out-of-time pile-up hits are read too).
    rechitScale: put the deposits on the rechit scale (RECHIT_SCALE, for the
    attribution of reconstructed candidates) instead of the digitiser scale
    with the HF gain (SIM_SCALE)."""
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
        pileupHits=cms.string(pileupTruth),
        rechitScale=cms.vdouble(*(RECHIT_SCALE if rechitScale else SIM_SCALE)),
    )


def simCaloTables(
    process,
    simTracks="g4SimHits",
    simJetMinPt=5.0,
    ecalCellThreshold=0.0,
    hcalCellThreshold=0.0,
    chargedMaxAbsEta=2.5,
    chargedMinPt=0.5,
    trackerMaxRadius=123.0,
    trackerMaxAbsZ=293.0,
    writeCells=True,
    pileupTruth="",
):
    """SimCalo, SimCaloCell, SimPFCand, SimCaloJet, SimCaloCellJet, SimPFJet and
    their GenJet matches.

    pileupTruth (label of PicoMixedTruthProducer, classically mixed events):
    adds the pile-up deposit columns of SimCaloCell, the pile-up entrance
    particles (picoCaloEntrancePU) and three jets with pile-up: SimCaloCellPUJet
    (cells with signal + in-time pile-up), SimPFPUJet (ideal PF of signal +
    pile-up) and SimPFPUCHSJet (the same without the trackable charged pile-up),
    each matched to the gen jets by the signal ancestry.

    The deposits are bookkept per calorimeter-entrance particle (picoCaloEntrance
    from simTables()); SimCaloJet clusters the per-particle deposits,
    SimCaloCellJet the cells themselves (same energy, calorimeter geometry
    instead of per-particle directions), SimPFJet the ideal PF candidates.

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
        caloEntrance=cms.InputTag("picoCaloEntrance"),
        ecalCellThreshold=cms.double(ecalCellThreshold),
        hcalCellThreshold=cms.double(hcalCellThreshold),
        chargedMaxAbsEta=cms.double(chargedMaxAbsEta),
        chargedMinPt=cms.double(chargedMinPt),
        trackerMaxRadius=cms.double(trackerMaxRadius),
        trackerMaxAbsZ=cms.double(trackerMaxAbsZ),
        **caloSimHitParameters(simTracks)
    )
    if pileupTruth:
        process.picoCaloEntrancePU = cms.EDProducer(
            "PicoCaloEntranceProducer",
            simTracks=cms.InputTag(pileupTruth, "pileup"),
            simVertices=cms.InputTag(pileupTruth, "pileup"),
            trackerMaxRadius=cms.double(trackerMaxRadius),
            trackerMaxAbsZ=cms.double(trackerMaxAbsZ),
            pileup=cms.bool(True),
            **caloSimHitParameters(simTracks, pileupTruth)
        )
        process.picoSimCaloCandidates.pileupSimTracks = cms.InputTag(pileupTruth, "pileup")
        process.picoSimCaloCandidates.pileupSimVertices = cms.InputTag(pileupTruth, "pileup")
        process.picoSimCaloCandidates.pileupCaloEntrance = cms.InputTag("picoCaloEntrancePU")
        process.picoSimCaloCandidates.pileupHits = cms.string(pileupTruth)
    process.picoAk4SimCaloJets = ak4GenJets.clone(
        src=cms.InputTag("picoSimCaloCandidates", "calo"), jetPtMin=cms.double(simJetMinPt)
    )
    process.picoAk4SimCaloCellJets = ak4GenJets.clone(
        src=cms.InputTag("picoSimCaloCandidates", "cells"), jetPtMin=cms.double(simJetMinPt)
    )
    process.picoAk4SimPFJets = ak4GenJets.clone(
        src=cms.InputTag("picoSimCaloCandidates", "pf"), jetPtMin=cms.double(simJetMinPt)
    )
    process.picoSimCaloTable = cms.EDProducer(
        "PicoSimCaloTableProducer",
        simTracks=cms.InputTag(simTracks),
        src=cms.string("picoSimCaloCandidates"),
        caloJets=cms.InputTag("picoAk4SimCaloJets"),
        cellJets=cms.InputTag("picoAk4SimCaloCellJets"),
        pfJets=cms.InputTag("picoAk4SimPFJets"),
        caloName=cms.string("SimCalo"),
        cellName=cms.string("SimCaloCell"),
        pfName=cms.string("SimPFCand"),
        writeCells=cms.bool(writeCells),
        pileup=cms.bool(bool(pileupTruth)),
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
    process.picoSimCaloCellJetTable = genJetTable.clone(
        src=cms.InputTag("picoAk4SimCaloCellJets"),
        cut=cms.string(""),
        name=cms.string("SimCaloCellJet"),
        doc=cms.string("anti-kt 0.4 jets of the calorimeter cells with sim-hit deposits (SimCaloCell): the same energy as SimCaloJet with the calorimeter geometry instead of per-particle directions"),
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
    process.picoSimCaloCellGenJetMatchTable = match.clone(
        simJets=cms.InputTag("picoAk4SimCaloCellJets"),
        simCandidates=cms.InputTag("picoSimCaloCandidates", "cells"),
        simCandidateIndex=cms.InputTag("picoSimCaloCandidates", "cellSub"),  # unused with constituentShares
        constituentShares=cms.InputTag("picoSimCaloCandidates"),
        matchName=cms.string("SimCaloCellGenJetMatch"),
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
        process.picoAk4SimCaloCellJets,
        process.picoAk4SimPFJets,
        process.picoSimCaloTable,
        process.picoSimCaloJetTable,
        process.picoSimCaloCellJetTable,
        process.picoSimPFJetTable,
        process.picoSimCaloGenJetMatchTable,
        process.picoSimCaloCellGenJetMatchTable,
        process.picoSimPFGenJetMatchTable,
    )
    if pileupTruth:
        # jets with the in-time pile-up: the calorimeter cells as a rechit sees them, the ideal
        # PF of signal + pile-up, and the same after a perfect charged-hadron subtraction
        process.picoAk4SimCaloCellPUJets = ak4GenJets.clone(
            src=cms.InputTag("picoSimCaloCandidates", "cellsPU"), jetPtMin=cms.double(simJetMinPt)
        )
        process.picoAk4SimPFPUJets = ak4GenJets.clone(
            src=cms.InputTag("picoSimCaloCandidates", "pfPU"), jetPtMin=cms.double(simJetMinPt)
        )
        process.picoAk4SimPFPUCHSJets = ak4GenJets.clone(
            src=cms.InputTag("picoSimCaloCandidates", "pfPUCHS"), jetPtMin=cms.double(simJetMinPt)
        )
        process.picoSimCaloCellPUJetTable = genJetTable.clone(
            src=cms.InputTag("picoAk4SimCaloCellPUJets"),
            cut=cms.string(""),
            name=cms.string("SimCaloCellPUJet"),
            doc=cms.string("anti-kt 0.4 jets of the calorimeter cells with their signal + in-time pile-up sim deposits: the calorimeter truth with pile-up, no noise, no thresholds"),
            variables=jetVars,
        )
        process.picoSimPFPUJetTable = genJetTable.clone(
            src=cms.InputTag("picoAk4SimPFPUJets"),
            cut=cms.string(""),
            name=cms.string("SimPFPUJet"),
            doc=cms.string("anti-kt 0.4 jets of the ideal PF candidates of the signal and of the in-time pile-up interactions (charged trackable from momentum, the rest from deposits)"),
            variables=jetVars,
        )
        process.picoSimPFPUCHSJetTable = genJetTable.clone(
            src=cms.InputTag("picoAk4SimPFPUCHSJets"),
            cut=cms.string(""),
            name=cms.string("SimPFPUCHSJet"),
            doc=cms.string("as SimPFPUJet without the trackable charged pile-up particles: a perfect charged-hadron subtraction, what remains is the neutral and untrackable pile-up"),
            variables=jetVars,
        )
        process.picoSimCaloCellPUGenJetMatchTable = match.clone(
            simJets=cms.InputTag("picoAk4SimCaloCellPUJets"),
            simCandidates=cms.InputTag("picoSimCaloCandidates", "cellsPU"),
            simCandidateIndex=cms.InputTag("picoSimCaloCandidates", "cellPUSub"),  # unused with constituentShares
            constituentShares=cms.InputTag("picoSimCaloCandidates"),
            constituentSharesPrefix=cms.string("cellPUShare"),
            matchName=cms.string("SimCaloCellPUGenJetMatch"),
            writeGenConstituents=cms.bool(False),
        )
        process.picoSimPFPUGenJetMatchTable = match.clone(
            simJets=cms.InputTag("picoAk4SimPFPUJets"),
            simCandidates=cms.InputTag("picoSimCaloCandidates", "pfPU"),
            simCandidateIndex=cms.InputTag("picoSimCaloCandidates", "pfPUSimTrackIndex"),
            matchName=cms.string("SimPFPUGenJetMatch"),
            writeGenConstituents=cms.bool(False),
        )
        process.picoSimPFPUCHSGenJetMatchTable = match.clone(
            simJets=cms.InputTag("picoAk4SimPFPUCHSJets"),
            simCandidates=cms.InputTag("picoSimCaloCandidates", "pfPUCHS"),
            simCandidateIndex=cms.InputTag("picoSimCaloCandidates", "pfPUCHSSimTrackIndex"),
            matchName=cms.string("SimPFPUCHSGenJetMatch"),
            writeGenConstituents=cms.bool(False),
        )
        process.picoSimCaloTask.add(
            process.picoCaloEntrancePU,
            process.picoAk4SimCaloCellPUJets,
            process.picoAk4SimPFPUJets,
            process.picoAk4SimPFPUCHSJets,
            process.picoSimCaloCellPUJetTable,
            process.picoSimPFPUJetTable,
            process.picoSimPFPUCHSJetTable,
            process.picoSimCaloCellPUGenJetMatchTable,
            process.picoSimPFPUGenJetMatchTable,
            process.picoSimPFPUCHSGenJetMatchTable,
        )
    return process.picoSimCaloTask
