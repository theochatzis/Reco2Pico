# Reco2Pico/PicoProducer/python/tables/jets_cff.py

import FWCore.ParameterSet.Config as cms
from  PhysicsTools.NanoAOD.common_cff import *

from PhysicsTools.NanoAOD.jetsAK4_Puppi_cff import jetPuppiTable
from PhysicsTools.NanoAOD.jetMC_cff import jetMCTable, genJetTable

jet_tables = []

def jetTables(process, src="slimmedJetsPuppi", isMC=True):
    """picoJetTable = an AK4 Puppi Jets Table
    Inspired from: NanoAOD/python/jetsAK4_Puppi_cff
    https://github.com/cms-sw/cmssw/blob/7ec24a49fc652e32e42e96243b975e83233ea986/PhysicsTools/NanoAOD/python/jetsAK4_Puppi_cff.py
    """    
    process.picoJetTable = jetPuppiTable.clone(
        src=cms.InputTag(src),
        name=cms.string("Jet"),
        doc=cms.string("AK4 PUPPI jets for PicoAOD"),
        variables=cms.PSet(
            P4Vars,
            area=Var("jetArea()", float, doc="jet area", precision=10),
            nConstituents = Var("numberOfDaughters()","uint8",doc="Number of particles in the jet"),
            chMultiplicity = Var("chargedMultiplicity()","uint8",doc="(Puppi-weighted) Number of charged particles in the jet"),
            neMultiplicity = Var("neutralMultiplicity()","uint8",doc="(Puppi-weighted) Number of neutral particles in the jet"),
            rawFactor = Var("1.-jecFactor('Uncorrected')",float,doc="1 - Factor to get back to raw pT",precision=6),
            chHEF = Var("chargedHadronEnergyFraction()", float, doc="charged Hadron Energy Fraction", precision=6),
            neHEF = Var("neutralHadronEnergyFraction()", float, doc="neutral Hadron Energy Fraction", precision=6),
            chEmEF = Var("chargedEmEnergyFraction()", float, doc="charged Electromagnetic Energy Fraction", precision=6),
            neEmEF = Var("neutralEmEnergyFraction()", float, doc="neutral Electromagnetic Energy Fraction", precision=6),
            hfHEF = Var("HFHadronEnergyFraction()",float,doc="hadronic Energy Fraction in HF",precision=6),
            hfEmEF = Var("HFEMEnergyFraction()",float,doc="electromagnetic Energy Fraction in HF",precision=6),
            muEF = Var("muonEnergyFraction()", float, doc="muon Energy Fraction", precision=6),
        ),
        externalVariables=cms.PSet(),
    )

    jet_tables.append(process.picoJetTable)
    
    process.picoJetTableTask = cms.Task(process.picoJetTable)
    process.picoJetTableSeq = cms.Sequence(process.picoJetTableTask)

    if isMC:
        #
        # Extension of the Jet table to keep the gen info
        #
        process.picoJetMCTable = jetMCTable.clone(
            src = cms.InputTag(src),
            name = process.picoJetTable.name,
            variables = cms.PSet(
                genJetIdx = jetMCTable.variables.genJetIdx
            )
        )

        jet_tables.append(process.picoJetMCTable)

        process.picoGenJetTable = genJetTable.clone()
        jet_tables.append(process.picoGenJetTable)

    # Add all the tables in Task and Sequence
    process.picoJetTableTask = cms.Task(*jet_tables)

    seq = jet_tables[0]
    for table in jet_tables[1:]:
        seq = seq + table

    process.picoJetTableSeq = cms.Sequence(seq)


    return process

