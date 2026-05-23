import FWCore.ParameterSet.Config as cms
from PhysicsTools.NanoAOD.common_cff import Var, P4Vars


def userJetTables(process, src="selectedUserJets"):
    process.picoUserJetTable = cms.EDProducer(
        "SimpleCandidateFlatTableProducer",
        src=cms.InputTag(src),
        cut=cms.string(""),
        name=cms.string("UserJet"),
        doc=cms.string("minimal user-selected jet table"),
        singleton=cms.bool(False),
        extension=cms.bool(False),
        variables=cms.PSet(
            P4Vars,
            charge=Var("charge", int, doc="electric charge"),
            rawFactor=Var("1. - jecFactor('Uncorrected')", float, doc="1 - raw JEC factor", precision=6),
        ),
    )
    process.picoUserJetTableTask = cms.Task(process.picoUserJetTable)
    process.picoUserJetTableSeq = cms.Sequence(process.picoUserJetTableTask)
    return process
