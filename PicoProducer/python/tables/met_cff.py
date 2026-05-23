import FWCore.ParameterSet.Config as cms
from  PhysicsTools.NanoAOD.common_cff import *

from PhysicsTools.NanoAOD.met_cff import puppiMetTable

def metTables(process, src="slimmedMETsPuppi"):
    process.picoMETTable = puppiMetTable.clone(
        src=cms.InputTag(src),
        name=cms.string("PuppiMET"),
        doc=cms.string("PUPPI MET for PicoAOD"),
        variables=cms.PSet(
            PTVars
        )
    )

    process.picoMETTableTask = cms.Task(process.picoMETTable)
    process.picoMETTableSeq = cms.Sequence(process.picoMETTableTask)
    return process
