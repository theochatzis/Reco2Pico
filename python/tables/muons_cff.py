import FWCore.ParameterSet.Config as cms
from PhysicsTools.NanoAOD.common_cff import Var

muonTable = cms.EDProducer(
    "SimpleCandidateFlatTableProducer",
    src=cms.InputTag("slimmedMuons"),
    cut=cms.string("pt > 3"),
    name=cms.string("Muon"),
    doc=cms.string("slimmedMuons with minimal PicoAOD variables"),
    singleton=cms.bool(False),
    extension=cms.bool(False),
    variables=cms.PSet(
        pt=Var("pt", float, precision=10, doc="muon pT"),
        eta=Var("eta", float, precision=12, doc="muon eta"),
        phi=Var("phi", float, precision=12, doc="muon phi"),
        mass=Var("mass", float, precision=10, doc="muon mass"),
        charge=Var("charge", int, doc="muon charge"),
        tightId=Var("passed('CutBasedIdTight')", bool, doc="tight muon ID flag"),
        pfRelIso04_all=Var("(pfIsolationR04().sumChargedHadronPt + max(pfIsolationR04().sumNeutralHadronEt + pfIsolationR04().sumPhotonEt - 0.5*pfIsolationR04().sumPUPt, 0.0))/pt", float, precision=10, doc="PF relative isolation, dR=0.4"),
    ),
)

picoMuonTables = cms.Sequence(muonTable)
