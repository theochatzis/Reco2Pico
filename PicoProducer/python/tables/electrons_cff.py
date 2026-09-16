import FWCore.ParameterSet.Config as cms
from PhysicsTools.NanoAOD.common_cff import CandVars, Var
from PhysicsTools.NanoAOD.electrons_cff import electronTable


def electronTables(process, src="slimmedElectrons", includeIDs=True):
    variables = cms.PSet(CandVars)

    if includeIDs:
        variables.cutBasedID_veto = Var(
            "userInt('cutBasedElectronID-RunIIIWinter22-V1-veto')",
            int,
            doc="RunIIIWinter22 V1 veto cut-based electron ID",
        )
        variables.cutBasedID_loose = Var(
            "userInt('cutBasedElectronID-RunIIIWinter22-V1-loose')",
            int,
            doc="RunIIIWinter22 V1 loose cut-based electron ID",
        )
        variables.cutBasedID_medium = Var(
            "userInt('cutBasedElectronID-RunIIIWinter22-V1-medium')",
            int,
            doc="RunIIIWinter22 V1 medium cut-based electron ID",
        )
        variables.cutBasedID_tight = Var(
            "userInt('cutBasedElectronID-RunIIIWinter22-V1-tight')",
            int,
            doc="RunIIIWinter22 V1 tight cut-based electron ID",
        )

    process.picoElectronTable = electronTable.clone(
        src=cms.InputTag(src),
        name=cms.string("Electron"),
        doc=cms.string("Electrons for PicoAOD"),
        variables=variables,
        externalVariables=cms.PSet(),
    )

    process.picoElectronTableTask = cms.Task(process.picoElectronTable)
    process.picoElectronTableSeq = cms.Sequence(process.picoElectronTableTask)
    return process
