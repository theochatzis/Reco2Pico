import FWCore.ParameterSet.Config as cms
from PhysicsTools.NanoAOD.common_cff import ExtVar
from PhysicsTools.NanoAOD.globalVariablesTableProducer_cfi import globalVariablesTableProducer
from PhysicsTools.NanoAOD.globals_cff import puTable


def eventTables(
    process,
    isMC=True,
    puSrc="slimmedAddPileupInfo",
    pvSrc="offlineSlimmedPrimaryVertices",
):
    """Create event-level Pico tables.
    """
    event_tables = []

    process.rhoTable = globalVariablesTableProducer.clone(
        name=cms.string("Rho"),
        variables=cms.PSet(
            fixedGridRhoAll=ExtVar(
                cms.InputTag("fixedGridRhoAll"),
                "double",
                doc="rho from all PF Candidates, no foreground removal",
            ),
            fixedGridRhoFastjetAll=ExtVar(
                cms.InputTag("fixedGridRhoFastjetAll"),
                "double",
                doc="rho from all PF Candidates, used e.g. for JECs",
            ),
            fixedGridRhoFastjetCentralNeutral=ExtVar(
                cms.InputTag("fixedGridRhoFastjetCentralNeutral"),
                "double",
                doc="rho from neutral PF Candidates with |eta| < 2.5",
            ),
            fixedGridRhoFastjetCentralCalo=ExtVar(
                cms.InputTag("fixedGridRhoFastjetCentralCalo"),
                "double",
                doc="rho from calo towers with |eta| < 2.5",
            ),
            fixedGridRhoFastjetCentral=ExtVar(
                cms.InputTag("fixedGridRhoFastjetCentral"),
                "double",
                doc="rho from all PF Candidates in the central region",
            ),
            fixedGridRhoFastjetCentralChargedPileUp=ExtVar(
                cms.InputTag("fixedGridRhoFastjetCentralChargedPileUp"),
                "double",
                doc="rho from charged pileup PF Candidates in the central region",
            ),
        ),
    )
    event_tables.append(process.rhoTable)

    if isMC:
        process.puTable = puTable.clone(
            src=cms.InputTag(puSrc),
            pvsrc=cms.InputTag(pvSrc),
            savePtHatMax=cms.bool(False),
        )
        event_tables.append(process.puTable)

    process.picoEventTableTask = cms.Task(*event_tables)
    process.picoEventTableSeq = cms.Sequence(process.picoEventTableTask)
    return process
