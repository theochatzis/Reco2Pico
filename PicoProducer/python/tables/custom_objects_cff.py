import FWCore.ParameterSet.Config as cms
from PhysicsTools.NanoAOD.common_cff import Var, P4Vars


def customObjectTables(process):
    """Tiny example of building one custom collection and writing one table."""
    process.picoDiMuonProducer = cms.EDProducer(
        "CandViewShallowCloneCombiner",
        decay=cms.string("slimmedMuons@+ slimmedMuons@-"),
        cut=cms.string("mass > 0"),
    )

    process.picoDiMuonTable = cms.EDProducer(
        "SimpleCompositeCandidateFlatTableProducer",
        src=cms.InputTag("picoDiMuonProducer"),
        cut=cms.string(""),
        name=cms.string("DiMuon"),
        doc=cms.string("minimal opposite-sign dimuon table"),
        singleton=cms.bool(False),
        extension=cms.bool(False),
        variables=cms.PSet(
            P4Vars,
            charge=Var("charge", int, doc="dimuon charge"),
        ),
    )

    process.picoCustomObjectTask = cms.Task(process.picoDiMuonProducer, process.picoDiMuonTable)
    process.picoCustomObjectSeq = cms.Sequence(process.picoCustomObjectTask)
    return process
