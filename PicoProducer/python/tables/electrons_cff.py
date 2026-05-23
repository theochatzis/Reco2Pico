import FWCore.ParameterSet.Config as cms
from PhysicsTools.NanoAOD.common_cff import *

from PhysicsTools.NanoAOD.electrons_cff import electronTable


def electronTables(process, src="slimmedElectrons"):
    process.picoElectronTable = electronTable.clone(
        src=cms.InputTag(src),
        name=cms.string("Electron"),
        doc=cms.string("minimal slimmedElectrons table"),
        variables=cms.PSet(
            CandVars,
            cutBasedID_veto=Var(
                "userInt('cutBasedElectronID-RunIIIWinter22-V1-veto')",
                int,
                doc="RunIIIWinter22 V1 veto cut-based electron ID",
            ),
            cutBasedID_loose=Var(
                "userInt('cutBasedElectronID-RunIIIWinter22-V1-loose')",
                int,
                doc="RunIIIWinter22 V1 loose cut-based electron ID",
            ),
            cutBasedID_medium=Var(
                "userInt('cutBasedElectronID-RunIIIWinter22-V1-medium')",
                int,
                doc="RunIIIWinter22 V1 medium cut-based electron ID",
            ),
            cutBasedID_tight=Var(
                "userInt('cutBasedElectronID-RunIIIWinter22-V1-tight')",
                int,
                doc="RunIIIWinter22 V1 tight cut-based electron ID",
            ),
        ),
        externalVariables = cms.PSet()
    )
    process.picoElectronTableTask = cms.Task(process.picoElectronTable)
    process.picoElectronTableSeq = cms.Sequence(process.picoElectronTableTask)
    return process
