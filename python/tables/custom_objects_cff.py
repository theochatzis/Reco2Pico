import FWCore.ParameterSet.Config as cms
from PhysicsTools.NanoAOD.common_cff import Var

picoHighPtMuonTable = cms.EDProducer(
    "SimpleCandidateFlatTableProducer",
    src=cms.InputTag("slimmedMuons"),
    cut=cms.string("pt > 20 && abs(eta) < 2.4"),
    name=cms.string("PicoHighPtMuon"),
    doc=cms.string("Example custom Pico object: selected high-pT muons"),
    singleton=cms.bool(False),
    extension=cms.bool(False),
    variables=cms.PSet(
        pt=Var("pt", float, precision=10, doc="object pT"),
        eta=Var("eta", float, precision=12, doc="object eta"),
        phi=Var("phi", float, precision=12, doc="object phi"),
        charge=Var("charge", int, doc="object charge"),
    ),
)

picoCustomObjectTables = cms.Sequence(picoHighPtMuonTable)
