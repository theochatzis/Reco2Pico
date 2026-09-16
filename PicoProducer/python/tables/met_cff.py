import FWCore.ParameterSet.Config as cms
from PhysicsTools.NanoAOD.common_cff import *

from PhysicsTools.NanoAOD.met_cff import puppiMetTable, rawPuppiMetTable


def metTables(process, src="slimmedMETsPuppi"):

    process.picoMETTable = puppiMetTable.clone(
        src=cms.InputTag(src),
        name=cms.string("PuppiMET"),
        doc=cms.string("PUPPI MET for PicoAOD"),
        variables=cms.PSet(
            PTVars
        )
    )

    process.picoRawMETTable = rawPuppiMetTable.clone(
        src=process.picoMETTable.src,
        name=cms.string("RawPuppiMET"),
        doc=cms.string("raw Puppi MET"),
        variables=cms.PSet(
            # Note: we don't copy PTVars here!
            pt=Var(
                "uncorPt",
                float,
                doc="pt",
                precision=6
            ),
            phi=Var(
                "uncorPhi",
                float,
                doc="phi",
                precision=6
            ),
        ),
    )

    process.picoMETTableTask = cms.Task(
        process.picoMETTable,
        process.picoRawMETTable,
    )

    process.picoMETTableSeq = cms.Sequence(
        process.picoMETTableTask
    )

    return process