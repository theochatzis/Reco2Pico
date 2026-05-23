import FWCore.ParameterSet.Config as cms
from PhysicsTools.NanoAOD.common_cff import *



def eventTables(process):
    process.picoEventTable = cms.EDProducer(
        "GlobalVariablesTableProducer",
        name=cms.string(""),
        extension=cms.bool(False),
        variables=cms.PSet(
            fixedGridRhoFastjetAll=ExtVar(
                cms.InputTag("fixedGridRhoFastjetAll"),
                float,
                doc="rho from fixedGridRhoFastjetAll",
                precision=6,
            ),
        ),
    )
    process.picoEventTableTask = cms.Task(process.picoEventTable)
    process.picoEventTableSeq = cms.Sequence(process.picoEventTableTask)
    return process
