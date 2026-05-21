import FWCore.ParameterSet.Config as cms
from PhysicsTools.NanoAOD.common_cff import Var

electronTable = cms.EDProducer(
    "SimpleCandidateFlatTableProducer",
    src=cms.InputTag("slimmedElectrons"),
    cut=cms.string("pt > 5"),
    name=cms.string("Electron"),
    doc=cms.string("slimmedElectrons with minimal PicoAOD variables"),
    singleton=cms.bool(False),
    extension=cms.bool(False),
    variables=cms.PSet(
        pt=Var("pt", float, precision=10, doc="electron pT"),
        eta=Var("eta", float, precision=12, doc="electron eta"),
        phi=Var("phi", float, precision=12, doc="electron phi"),
        mass=Var("mass", float, precision=10, doc="electron mass"),
        charge=Var("charge", int, doc="electron charge"),
    ),
)

picoElectronTables = cms.Sequence(electronTable)
