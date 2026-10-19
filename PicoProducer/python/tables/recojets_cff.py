"""Reconstructed PF jets re-clustered in the job (anti-kt 0.4: plain PF, CHS,
Puppi), their constituents, the attribution of the PF candidates to the
simulated particles of the signal event, and the ancestry-based match of
every jet collection to GenJet.

Re-clustering in the job (standard ak4PFJets / ak4PFJetsCHS / ak4PFJetsPuppi
definitions, raw, no JEC) guarantees that the constituents resolve to the
particleFlow collection of the file; the stored jets do not keep their
constituent references for CHS and Puppi.

Needs: the 'pfcands', 'genparts' and 'sim' groups (track <-> TP association)
and the calorimeter sim hits in the input (run3_rawsim keepSimTruth).
"""
import FWCore.ParameterSet.Config as cms

from PhysicsTools.NanoAOD.common_cff import Var, P4Vars, ExtVar

from Reco2Pico.PicoProducer.tables.sim_cff import caloSimHitParameters


JET_COLLECTIONS = {
    # table name: (module label, puppi weights or "")
    "PFJet": ("picoAk4PFJets", ""),
    "PFJetCHS": ("picoAk4PFJetsCHS", ""),
    "PFJetPuppi": ("picoAk4PFJetsPuppi", "puppi"),
}


def recoJetTables(process, pfCandMinPt=0.0, jetMinPt=5.0, collections=None, puppiJEC=True):
    """puppiJEC: evaluate the GlobalTag AK4PFPuppi corrections (L1FastJet and
    L1FastL2L3) on the raw Puppi jets and store the factors as
    PFJetPuppi_jecL1 / PFJetPuppi_jecL1L2L3 (the jets stay raw)."""
    if not hasattr(process, "picoTrackingParticleRecoTrackAssociation"):
        raise RuntimeError("recoJetTables: the 'sim' group with tpAssociation=chi2 or hits is needed (track <-> TP association)")
    collections = list(JET_COLLECTIONS) if collections is None else list(collections)

    from RecoJets.JetProducers.ak4PFJets_cfi import ak4PFJets, ak4PFJetsCHS, ak4PFJetsPuppi

    process.load("CommonTools.ParticleFlow.pfNoPileUpJME_cff")
    process.load("CommonTools.PileupAlgos.Puppi_cff")
    process.picoAk4PFJets = ak4PFJets.clone(jetPtMin=cms.double(jetMinPt))
    process.picoAk4PFJetsCHS = ak4PFJetsCHS.clone(jetPtMin=cms.double(jetMinPt))
    process.picoAk4PFJetsPuppi = ak4PFJetsPuppi.clone(jetPtMin=cms.double(jetMinPt))

    process.picoPFCandTruthTable = cms.EDProducer(
        "PicoPFCandTruthProducer",
        candidates=cms.InputTag("particleFlow"),
        tracks=cms.InputTag("generalTracks"),
        association=cms.InputTag("picoTrackingParticleRecoTrackAssociation"),
        simTracks=cms.InputTag("g4SimHits"),
        ebRecHits=cms.InputTag("ecalRecHit", "EcalRecHitsEB"),
        eeRecHits=cms.InputTag("ecalRecHit", "EcalRecHitsEE"),
        esRecHits=cms.InputTag("ecalPreshowerRecHit", "EcalRecHitsES"),
        hbheRecHits=cms.InputTag("hbhereco"),
        hfRecHits=cms.InputTag("hfreco"),
        hoRecHits=cms.InputTag("horeco"),
        candMinPt=cms.double(pfCandMinPt),
        minShareFraction=cms.double(0.01),
        **caloSimHitParameters()
    )

    jetVars = cms.PSet(
        P4Vars,
        area=Var("jetArea()", float, doc="jet catchment area (for JECs)", precision=10),
        nConstituents=Var("numberOfDaughters()", "uint8", doc="number of constituents"),
        chHEF=Var("chargedHadronEnergyFraction()", float, doc="charged hadron energy fraction", precision=10),
        neHEF=Var("neutralHadronEnergyFraction()", float, doc="neutral hadron energy fraction", precision=10),
        phEF=Var("photonEnergyFraction()", float, doc="photon energy fraction", precision=10),
        elEF=Var("electronEnergyFraction()", float, doc="electron energy fraction", precision=10),
        muEF=Var("muonEnergyFraction()", float, doc="muon energy fraction", precision=10),
        hfHEF=Var("HFHadronEnergyFraction()", float, doc="HF hadron energy fraction", precision=10),
        hfEMEF=Var("HFEMEnergyFraction()", float, doc="HF EM energy fraction", precision=10),
    )
    modules = [process.pfNoPileUpJMETask, process.puppi, process.picoAk4PFJets, process.picoAk4PFJetsCHS,
               process.picoAk4PFJetsPuppi, process.picoPFCandTruthTable]
    puppiExternal = cms.PSet()
    if puppiJEC:
        process.load("JetMETCorrections.Configuration.JetCorrectors_cff")
        process.picoPuppiJecL1 = cms.EDProducer(
            "PicoJetCorrectionValueMapProducer",
            jets=cms.InputTag("picoAk4PFJetsPuppi"),
            corrector=cms.InputTag("ak4PFPuppiL1FastjetCorrector"),
        )
        process.picoPuppiJecL1L2L3 = cms.EDProducer(
            "PicoJetCorrectionValueMapProducer",
            jets=cms.InputTag("picoAk4PFJetsPuppi"),
            corrector=cms.InputTag("ak4PFPuppiL1FastL2L3Corrector"),
        )
        modules += [process.ak4PFPuppiL1FastL2L3CorrectorTask, process.picoPuppiJecL1, process.picoPuppiJecL1L2L3]
        puppiExternal = cms.PSet(
            jecL1=ExtVar(cms.InputTag("picoPuppiJecL1"), float, doc="GlobalTag AK4PFPuppi L1FastJet factor (multiplies the raw jet)", precision=10),
            jecL1L2L3=ExtVar(cms.InputTag("picoPuppiJecL1L2L3"), float, doc="GlobalTag AK4PFPuppi L1FastJet+L2Relative+L3Absolute factor (multiplies the raw jet)", precision=10),
        )
    for name in collections:
        label, weights = JET_COLLECTIONS[name]
        table = cms.EDProducer(
            "SimplePFJetFlatTableProducer",
            src=cms.InputTag(label),
            cut=cms.string(""),
            name=cms.string(name),
            doc=cms.string("%s: anti-kt 0.4 %s jets re-clustered in the job, raw (no JEC)" % (label, name[2:] or "PF")),
            singleton=cms.bool(False),
            extension=cms.bool(False),
            variables=jetVars,
            externalVariables=puppiExternal if name == "PFJetPuppi" else cms.PSet(),
        )
        setattr(process, "pico%sTable" % name, table)
        match = cms.EDProducer(
            "PicoRecoJetGenMatchProducer",
            jets=cms.InputTag(label),
            candidates=cms.InputTag("particleFlow"),
            weights=cms.InputTag(weights),
            truth=cms.string("picoPFCandTruthTable"),
            simTracks=cms.InputTag("g4SimHits"),
            simVertices=cms.InputTag("g4SimHits"),
            genJets=cms.InputTag("picoAk4GenJetsNoNu"),
            genParticles=cms.InputTag("genParticles"),
            name=cms.string(name),
            candMinPt=cms.double(pfCandMinPt),
        )
        setattr(process, "pico%sGenMatchTable" % name, match)
        modules += [table, match]

    process.picoRecoJetTask = cms.Task(*modules)
    return process.picoRecoJetTask
