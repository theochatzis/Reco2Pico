import FWCore.ParameterSet.Config as cms
from PhysicsTools.NanoAOD.common_cff import Var

jetTable = cms.EDProducer(
    "SimpleCandidateFlatTableProducer",
    src=cms.InputTag("slimmedJets"),
    cut=cms.string("pt > 15"),
    name=cms.string("Jet"),
    doc=cms.string("slimmedJets with minimal PicoAOD variables"),
    singleton=cms.bool(False),
    extension=cms.bool(False),
    variables=cms.PSet(
        pt=Var("pt", float, precision=10, doc="jet pT"),
        eta=Var("eta", float, precision=12, doc="jet eta"),
        phi=Var("phi", float, precision=12, doc="jet phi"),
        mass=Var("mass", float, precision=10, doc="jet mass"),
        area=Var("jetArea", float, precision=10, doc="jet area"),
        btagDeepFlavB=Var("bDiscriminator('pfDeepFlavourJetTags:probb') + bDiscriminator('pfDeepFlavourJetTags:probbb') + bDiscriminator('pfDeepFlavourJetTags:problepb')", float, precision=10, doc="DeepJet b score"),
    ),
)

picoJetTables = cms.Sequence(jetTable)
