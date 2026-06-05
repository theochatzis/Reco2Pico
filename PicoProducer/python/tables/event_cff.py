import FWCore.ParameterSet.Config as cms
from PhysicsTools.NanoAOD.common_cff import *
from PhysicsTools.NanoAOD.nano_eras_cff import *
from PhysicsTools.NanoAOD.globalVariablesTableProducer_cfi import globalVariablesTableProducer
# from PhysicsTools.NanoAOD.simpleBeamspotFlatTableProducer_cfi import simpleBeamspotFlatTableProducer
# from PhysicsTools.NanoAOD.simpleGenEventFlatTableProducer_cfi import simpleGenEventFlatTableProducer
# from PhysicsTools.NanoAOD.simpleGenFilterFlatTableProducerLumi_cfi import simpleGenFilterFlatTableProducerLumi

from PhysicsTools.NanoAOD.globals_cff import puTable

# Inspired by https://github.com/cms-sw/cmssw/blob/102a2fe0dea95b180c64a7e80df89c6004c7f71b/PhysicsTools/NanoAOD/python/globals_cff.py#L4
event_tables = []
def eventTables(process, isMC=True):
    process.rhoTable = globalVariablesTableProducer.clone(
    name = cms.string("Rho"),
    variables = cms.PSet(
        fixedGridRhoAll = ExtVar( cms.InputTag("fixedGridRhoAll"), "double", doc = "rho from all PF Candidates, no foreground removal (for isolation of prompt photons)" ),
        fixedGridRhoFastjetAll = ExtVar( cms.InputTag("fixedGridRhoFastjetAll"), "double", doc = "rho from all PF Candidates, used e.g. for JECs" ),
        fixedGridRhoFastjetCentralNeutral = ExtVar( cms.InputTag("fixedGridRhoFastjetCentralNeutral"), "double", doc = "rho from neutral PF Candidates with |eta| < 2.5, used e.g. for rho corrections of some lepton isolations" ),
        fixedGridRhoFastjetCentralCalo = ExtVar( cms.InputTag("fixedGridRhoFastjetCentralCalo"), "double", doc = "rho from calo towers with |eta| < 2.5, used e.g. egamma PFCluster isolation" ),
        fixedGridRhoFastjetCentral = ExtVar( cms.InputTag("fixedGridRhoFastjetCentral"), "double", doc = "rho from all PF Candidates for central region, used e.g. for JECs" ),
        fixedGridRhoFastjetCentralChargedPileUp = ExtVar( cms.InputTag("fixedGridRhoFastjetCentralChargedPileUp"), "double", doc = "rho from charged PF Candidates for central region, used e.g. for JECs" ),
    )
    )
    event_tables.append(process.rhoTable)

    if isMC:
        process.puTable = puTable.clone(
            savePtHatMax = cms.bool(False),
        )
        event_tables.append(process.puTable)
    
    # Add all the tables in Task and Sequence
    process.picoEventTableTask = cms.Task(*event_tables)

    seq = event_tables[0]
    for table in event_tables[1:]:
        seq = seq + table

    process.picoEventTableSeq = cms.Sequence(seq)


    # process.picoEventTable = cms.EDProducer(
    #     "GlobalVariablesTableProducer",
    #     name=cms.string(""),
    #     extension=cms.bool(False),
    #     variables=cms.PSet(
    #         fixedGridRhoFastjetAll=ExtVar(
    #             cms.InputTag("fixedGridRhoFastjetAll"),
    #             float,
    #             doc="rho from fixedGridRhoFastjetAll",
    #             precision=6,
    #         ),
    #     ),
    # )
    return process
