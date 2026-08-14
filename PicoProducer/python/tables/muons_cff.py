import FWCore.ParameterSet.Config as cms
from PhysicsTools.NanoAOD.common_cff import *

from PhysicsTools.NanoAOD.muons_cff import muonTable

def muonTables(process, src="slimmedMuons"):
    process.picoMuonTable = muonTable.clone(
        src=cms.InputTag(src),
        name=cms.string("Muon"),
        doc=cms.string("Muons for PicoAOD"),
        variables=cms.PSet(
            CandVars,
            looseId  = Var("passed('CutBasedIdLoose')",bool, doc="muon is loose muon"),
            mediumId = Var("passed('CutBasedIdMedium')",bool,doc="cut-based ID, medium WP"),
            tightId = Var("passed('CutBasedIdTight')",bool,doc="cut-based ID, tight WP"),
            pfIsoId = Var("passed('PFIsoVeryLoose')+passed('PFIsoLoose')+passed('PFIsoMedium')+passed('PFIsoTight')+passed('PFIsoVeryTight')+passed('PFIsoVeryVeryTight')","uint8",doc="PFIso ID from miniAOD selector (1=PFIsoVeryLoose, 2=PFIsoLoose, 3=PFIsoMedium, 4=PFIsoTight, 5=PFIsoVeryTight, 6=PFIsoVeryVeryTight)"),
            pfRelIso04_all=Var(
                "(pfIsolationR04().sumChargedHadronPt + max(pfIsolationR04().sumNeutralHadronEt + pfIsolationR04().sumPhotonEt - 0.5*pfIsolationR04().sumPUPt, 0.0)) / pt",
                float,
                doc="PF relative isolation, dR=0.4, delta-beta corrected",
                precision=6,
            ),
        ),
        externalVariables = cms.PSet()
    )
    process.picoMuonTableTask = cms.Task(process.picoMuonTable)
    process.picoMuonTableSeq = cms.Sequence(process.picoMuonTableTask)
    return process
