import FWCore.ParameterSet.Config as cms
from PhysicsTools.NanoAOD.common_cff import Var

metTable = cms.EDProducer(
    "SimpleCandidateFlatTableProducer",
    src=cms.InputTag("slimmedMETs"),
    cut=cms.string(""),
    name=cms.string("MET"),
    doc=cms.string("slimmedMETs first entry"),
    singleton=cms.bool(True),
    extension=cms.bool(False),
    variables=cms.PSet(
        pt=Var("pt", float, precision=10, doc="MET pT"),
        phi=Var("phi", float, precision=12, doc="MET phi"),
        sumEt=Var("sumEt", float, precision=10, doc="MET sumEt"),
    ),
)

picoMetTables = cms.Sequence(metTable)
