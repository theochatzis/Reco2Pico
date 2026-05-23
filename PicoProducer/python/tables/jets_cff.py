# Reco2Pico/PicoProducer/python/tables/jets_cff.py

import FWCore.ParameterSet.Config as cms
from  PhysicsTools.NanoAOD.common_cff import *

from PhysicsTools.NanoAOD.jetsAK4_Puppi_cff import jetPuppiTable

def jetTables(process, src="slimmedJetsPuppi"):

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
            rawFactor=Var(
                "jecFactor('Uncorrected')",
                float,
                doc="1 - Factor to get back to raw pT",
                precision=6,
            ),
            chHEF=Var(
                "chargedHadronEnergyFraction()",
                float,
                doc="charged hadron energy fraction",
                precision=6,
            ),
            neHEF=Var(
                "neutralHadronEnergyFraction()",
                float,
                doc="neutral hadron energy fraction",
                precision=6,
            ),
            chEmEF=Var(
                "chargedEmEnergyFraction()",
                float,
                doc="charged EM energy fraction",
                precision=6,
            ),
            neEmEF=Var(
                "neutralEmEnergyFraction()",
                float,
                doc="neutral EM energy fraction",
                precision=6,
            ),
            muEF=Var(
                "muonEnergyFraction()",
                float,
                doc="muon energy fraction",
                precision=6,
            ),
        ),
        externalVariables=cms.PSet(),
    )

    process.picoJetTableTask = cms.Task(process.picoJetTable)
    process.picoJetTableSeq = cms.Sequence(process.picoJetTableTask)

    return process

