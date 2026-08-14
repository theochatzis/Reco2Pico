# Reco2Pico/PicoProducer/python/tables/genJets_cff.py

import FWCore.ParameterSet.Config as cms
from  PhysicsTools.NanoAOD.common_cff import *

# from https://github.com/cms-sw/cmssw/blob/7ec24a49fc652e32e42e96243b975e83233ea986/PhysicsTools/NanoAOD/python/jetMC_cff.py

from PhysicsTools.NanoAOD.jetMC_cff import genJetTable

def genJetTables(process, src="slimmedGenJets"):
    process.picoGenJetTable = genJetTable.clone(
        src = cms.InputTag("slimmedGenJets"),
        cut = cms.string("pt > 10"),
        name = cms.string("GenJet"),
        doc  = cms.string("slimmedGenJets, i.e. ak4 Jets made with visible genparticles"),
        variables = cms.PSet(P4Vars
        )
    )

    process.picoGenJetTableTask = cms.Task(process.picoGenJetTable)
    process.picoGenJetTableSeq = cms.Sequence(process.picoGenJetTableTask)

    return process
